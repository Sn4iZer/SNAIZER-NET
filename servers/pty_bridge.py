"""Run one process inside a fresh pseudo-terminal and bridge it asynchronously.

POSIX only (Linux / macOS); imported lazily by the SSH gateway.
"""

import asyncio
import contextlib
import errno
import fcntl
import os
import pty
import signal
import struct
import termios
from collections.abc import Callable, Mapping, Sequence

READ_CHUNK = 65536
KILL_GRACE_SECONDS = 3.0


def set_winsize(fd: int, columns: int, rows: int) -> None:
    """Set the PTY window size (what the child sees via TIOCGWINSZ)."""
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, columns, 0, 0))


class PtyProcess:
    """A child process attached to a PTY, with non-blocking I/O on the master side."""

    def __init__(
        self,
        process: asyncio.subprocess.Process,
        master_fd: int,
        on_output: Callable[[bytes], None],
    ) -> None:
        self.process = process
        self.master_fd = master_fd
        self.on_output = on_output
        self._loop = asyncio.get_running_loop()
        self._pending = bytearray()
        self._reading = False
        self._closed = False

    @classmethod
    async def spawn(
        cls,
        argv: Sequence[str],
        *,
        env: Mapping[str, str],
        cwd: str,
        columns: int,
        rows: int,
        on_output: Callable[[bytes], None],
    ) -> "PtyProcess":
        """Start ``argv`` in a new session on a new PTY of the given size."""
        master_fd, slave_fd = pty.openpty()
        try:
            set_winsize(master_fd, columns, rows)
            process = await asyncio.create_subprocess_exec(
                *argv,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                env=dict(env),
                cwd=cwd,
                start_new_session=True,
                close_fds=True,
            )
        except BaseException:
            os.close(master_fd)
            raise
        finally:
            os.close(slave_fd)
        os.set_blocking(master_fd, False)
        bridge = cls(process, master_fd, on_output)
        bridge.resume_reading()
        return bridge

    def resume_reading(self) -> None:
        """Start (or restart) forwarding child output."""
        if not self._reading and not self._closed:
            self._loop.add_reader(self.master_fd, self._on_readable)
            self._reading = True

    def pause_reading(self) -> None:
        """Stop forwarding output (back-pressure from the SSH channel)."""
        if self._reading:
            self._loop.remove_reader(self.master_fd)
            self._reading = False

    def _on_readable(self) -> None:
        try:
            data = os.read(self.master_fd, READ_CHUNK)
        except BlockingIOError:
            return
        except OSError as error:
            if error.errno != errno.EIO:  # EIO == child closed its side
                raise
            data = b""
        if data:
            self.on_output(data)
        else:
            self.pause_reading()

    def write(self, data: bytes) -> None:
        """Send keystrokes to the child, buffering if the PTY is full."""
        if self._closed:
            return
        self._pending.extend(data)
        self._flush()

    def _flush(self) -> None:
        while self._pending and not self._closed:
            try:
                written = os.write(self.master_fd, self._pending)
            except BlockingIOError:
                self._loop.add_writer(self.master_fd, self._on_writable)
                return
            except OSError:
                self._pending.clear()
                return
            del self._pending[:written]
        with contextlib.suppress(ValueError, OSError):
            self._loop.remove_writer(self.master_fd)

    def _on_writable(self) -> None:
        self._flush()

    def resize(self, columns: int, rows: int) -> None:
        """Resize the PTY and notify the child (it has no controlling tty)."""
        if self._closed or self.process.returncode is not None:
            return
        set_winsize(self.master_fd, columns, rows)
        with contextlib.suppress(ProcessLookupError):
            os.killpg(self.process.pid, signal.SIGWINCH)

    async def wait(self) -> int:
        """Wait for the child to exit, drain remaining output, return its code."""
        code = await self.process.wait()
        for _ in range(100):  # give the reader up to ~1s to hit EOF
            if not self._reading:
                break
            await asyncio.sleep(0.01)
        self.close()
        return code

    async def terminate(self) -> None:
        """SIGTERM the child's process group, then SIGKILL after a grace period."""
        if self.process.returncode is not None:
            return
        with contextlib.suppress(ProcessLookupError):
            os.killpg(self.process.pid, signal.SIGTERM)
        try:
            await asyncio.wait_for(self.process.wait(), KILL_GRACE_SECONDS)
        except TimeoutError:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(self.process.pid, signal.SIGKILL)
            await self.process.wait()

    def close(self) -> None:
        """Release the PTY master."""
        if self._closed:
            return
        self.pause_reading()
        with contextlib.suppress(ValueError, OSError):
            self._loop.remove_writer(self.master_fd)
        self._closed = True
        with contextlib.suppress(OSError):
            os.close(self.master_fd)
