"""A clearly-labelled SIMULATED IoT telemetry panel (random demo data)."""

import random
from collections import deque
from dataclasses import dataclass

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Sparkline, Static

from snaizer_net.markup import tint
from snaizer_net.widgets.motion import motion_enabled

SAMPLES = 40
UPDATE_SECONDS = 0.5


@dataclass(frozen=True)
class SensorSpec:
    """A fake sensor: value range, max step per tick, display unit."""

    key: str
    label: str
    low: float
    high: float
    step: float
    unit: str
    decimals: int = 1


SENSORS = (
    SensorSpec("temp", "NODE TEMP", 21.0, 29.0, 0.4, "°C"),
    SensorSpec("signal", "LoRa SIGNAL", -92.0, -58.0, 2.5, "dBm", 0),
    SensorSpec("packets", "MQTT MSG/s", 40.0, 260.0, 18.0, "", 0),
)


class SensorPanel(Vertical):
    """Sparklines fed by a random walk; frozen when animations are off."""

    def __init__(self, *, id: str | None = None, seed: int | None = None) -> None:
        super().__init__(id=id)
        self.border_title = "Simulated IoT feed (demo data, not real telemetry)"
        self._rng = random.Random(seed)
        self.series: dict[str, deque[float]] = {}
        for spec in SENSORS:
            value = self._rng.uniform(spec.low, spec.high)
            values: deque[float] = deque(maxlen=SAMPLES)
            for _ in range(SAMPLES):
                value = self._walk(spec, value)
                values.append(value)
            self.series[spec.key] = values

    def compose(self) -> ComposeResult:
        """One row per sensor: label, sparkline, current value."""
        for spec in SENSORS:
            with Horizontal(classes="sensor-row"):
                yield Static(tint("dim", spec.label), classes="sensor-label")
                yield Sparkline(list(self.series[spec.key]), id=f"spark-{spec.key}")
                yield Static("", id=f"value-{spec.key}", classes="sensor-value")

    def on_mount(self) -> None:
        """Show the initial readings and start the feed."""
        self._refresh_values()
        self.set_interval(UPDATE_SECONDS, self._tick)

    def _walk(self, spec: SensorSpec, value: float) -> float:
        value += self._rng.uniform(-spec.step, spec.step)
        return max(spec.low, min(spec.high, value))

    def _tick(self) -> None:
        if not motion_enabled(self) or not self.display:
            return
        for spec in SENSORS:
            values = self.series[spec.key]
            values.append(self._walk(spec, values[-1]))
            self.query_one(f"#spark-{spec.key}", Sparkline).data = list(values)
        self._refresh_values()

    def _refresh_values(self) -> None:
        for spec in SENSORS:
            current = self.series[spec.key][-1]
            self.query_one(f"#value-{spec.key}", Static).update(
                tint("green", f"{current:.{spec.decimals}f}{spec.unit}", "bold")
            )
