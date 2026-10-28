"""Earth to Mars one-way light time, from NASA/JPL Horizons.

`data/horizons_mars_*.txt` is the raw reply of the Horizons API for Mars (499) as seen
from the center of the Earth (500@399), one row per day, quantities 20 (range) and
23 (Sun-Observer-Target elongation). Nothing here is a model of the orbits.
"""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from pathlib import Path

# Light travel time of one astronomical unit, in seconds (IAU 2012 AU / c).
AU_LIGHT_SECONDS = 499.004783836

# Below this Sun-Earth-Mars angle the Sun's corona garbles the link. Missions plan
# around "solar conjunction" blackouts of roughly two weeks; 3 degrees is the usual
# conservative cut and is an assumption of this project, not a Horizons output.
BLACKOUT_ELONGATION_DEG = 3.0

_ROW = re.compile(
    r"^\s*(\d{4}-[A-Za-z]{3}-\d{2}) \d{2}:\d{2},[^,]*,[^,]*,\s*([\d.]+),\s*([-\d.]+),\s*([\d.]+),"
)


@dataclass(frozen=True)
class Day:
    date: dt.date
    delta_au: float
    elongation_deg: float

    @property
    def one_way_s(self) -> float:
        return self.delta_au * AU_LIGHT_SECONDS

    @property
    def blackout(self) -> bool:
        return self.elongation_deg < BLACKOUT_ELONGATION_DEG


def load(path: str | Path) -> list[Day]:
    days: list[Day] = []
    inside = False
    for line in Path(path).read_text().splitlines():
        if line.startswith("$$SOE"):
            inside = True
        elif line.startswith("$$EOE"):
            break
        elif inside:
            m = _ROW.match(line)
            if not m:
                raise ValueError(f"unparsed Horizons row: {line!r}")
            d = dt.datetime.strptime(m.group(1), "%Y-%b-%d").date()
            days.append(Day(d, float(m.group(2)), float(m.group(4))))
    if not days:
        raise ValueError("no ephemeris rows found")
    return days
