"""Container healthcheck: succeed if ``127.0.0.1:$HEALTH_PORT`` accepts TCP."""

import os
import socket
import sys


def main() -> int:
    """Return 0 when the service port accepts connections."""
    port = int(os.environ.get("HEALTH_PORT", "8000"))
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=3):
            return 0
    except OSError:
        return 1


if __name__ == "__main__":
    sys.exit(main())
