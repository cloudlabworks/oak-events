"""Pure event logic: no DepthAI, no I/O, no pictures.

Everything here takes plain numbers (detections) or a 2-D depth array in
millimetres and returns event dicts. The camera runner feeds it; the tests feed
it synthetic data.

Event schema: every event is a flat dict with

* ``ts``   - ISO-8601 local time with UTC offset, second precision
* ``kind`` - event kind (``person_enter``, ``person_exit``, ``depth_baseline``,
  ``depth_change``, ``camera``, ``alive``)
* kind-specific fields; person and depth events carry ``zone``.
"""

from __future__ import annotations

import datetime as _dt
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

DEFAULT_ZONE = "view"

Event = dict[str, Any]


def now_iso() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def make_event(kind: str, ts: str | None = None, **fields: Any) -> Event:
    """Build an event dict. ``ts`` defaults to the current local time."""
    return {"ts": ts or now_iso(), "kind": kind, **fields}


# --------------------------------------------------------------------------- zones


@dataclass(frozen=True)
class Zone:
    """A named region of the view.

    ``bbox`` is ``(x0, y0, x1, y1)`` in normalized image coordinates (0..1,
    origin top-left). ``z_min_mm`` / ``z_max_mm`` bound the distance from the
    camera. Any part left as ``None`` does not constrain. The default zone,
    ``view``, is the whole field of view at any distance.
    """

    name: str = DEFAULT_ZONE
    bbox: tuple[float, float, float, float] | None = None
    z_min_mm: float | None = None
    z_max_mm: float | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("zone name must not be empty")
        if self.bbox is not None:
            if len(self.bbox) != 4:
                raise ValueError(f"zone {self.name!r}: bbox must be [x0, y0, x1, y1]")
            x0, y0, x1, y1 = (float(v) for v in self.bbox)
            if not (0.0 <= x0 < x1 <= 1.0 and 0.0 <= y0 < y1 <= 1.0):
                raise ValueError(f"zone {self.name!r}: bbox must satisfy 0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1")
            object.__setattr__(self, "bbox", (x0, y0, x1, y1))
        if self.z_min_mm is not None and self.z_max_mm is not None and self.z_min_mm >= self.z_max_mm:
            raise ValueError(f"zone {self.name!r}: z_min_mm must be below z_max_mm")

    def contains_z(self, z_mm: float) -> bool:
        if self.z_min_mm is not None and z_mm < self.z_min_mm:
            return False
        if self.z_max_mm is not None and z_mm > self.z_max_mm:
            return False
        return True

    def contains(self, z_mm: float, cx: float | None = None, cy: float | None = None) -> bool:
        """Does a detection at depth ``z_mm`` (and optional normalized centre) fall in the zone?

        Detections without an image position are matched on the depth range only.
        """
        if not self.contains_z(z_mm):
            return False
        if self.bbox is not None and cx is not None and cy is not None:
            x0, y0, x1, y1 = self.bbox
            return x0 <= cx <= x1 and y0 <= cy <= y1
        return True

    def crop(self, depth: np.ndarray) -> np.ndarray:
        """Return the zone's part of a depth array, with out-of-range pixels set to 0 (invalid)."""
        out = depth
        if self.bbox is not None:
            h, w = depth.shape
            x0, y0, x1, y1 = self.bbox
            r0, r1 = int(round(y0 * h)), max(int(round(y1 * h)), int(round(y0 * h)) + 1)
            c0, c1 = int(round(x0 * w)), max(int(round(x1 * w)), int(round(x0 * w)) + 1)
            out = depth[r0:r1, c0:c1]
        if self.z_min_mm is not None or self.z_max_mm is not None:
            out = out.copy()
            lo = self.z_min_mm if self.z_min_mm is not None else -np.inf
            hi = self.z_max_mm if self.z_max_mm is not None else np.inf
            out[(out < lo) | (out > hi)] = 0
        return out


def _is_number(value: Any) -> bool:
    """JSON numbers only: ``True`` / ``False`` are ints in Python but not numbers here."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def parse_zones(spec: Any) -> list[Zone]:
    """Parse zones from ``{"zones": [...]}`` or a bare list of zone objects.

    Each zone object: ``{"name": str, "bbox": [x0, y0, x1, y1]?, "z_mm": [min, max]?}``.
    ``z_mm`` entries may be ``null`` to leave that side open.
    """
    items = spec.get("zones", []) if isinstance(spec, dict) else spec
    if not isinstance(items, list):
        raise ValueError("zones must be a list or an object with a 'zones' list")
    zones: list[Zone] = []
    for item in items:
        if not isinstance(item, dict) or "name" not in item:
            raise ValueError(f"each zone needs a name: {item!r}")
        name = item["name"]
        z = item.get("z_mm")
        if z is None:
            z = [None, None]
        elif not isinstance(z, list):
            raise ValueError(f"zone {name!r}: z_mm must be [min, max], each a number or null")
        if len(z) != 2:
            raise ValueError(f"zone {name!r}: z_mm must be [min, max]")
        if not all(v is None or _is_number(v) for v in z):
            raise ValueError(f"zone {name!r}: z_mm must be [min, max], each a number or null")
        bbox = item.get("bbox")
        if bbox is not None:
            # Wrong length is left to Zone, which already reports it.
            if not isinstance(bbox, list) or (len(bbox) == 4 and not all(_is_number(v) for v in bbox)):
                raise ValueError(f"zone {name!r}: bbox must be [x0, y0, x1, y1], four numbers")
            bbox = tuple(bbox)
        zones.append(Zone(str(name), bbox, z[0], z[1]))
    names = [z.name for z in zones]
    if len(names) != len(set(names)):
        raise ValueError("zone names must be unique")
    return zones or [Zone()]


def load_zones(path: str | Path | None) -> list[Zone]:
    if path is None:
        return [Zone()]
    with open(Path(path).expanduser(), encoding="utf-8") as fh:
        return parse_zones(json.load(fh))


# --------------------------------------------------------------------------- people

# A detection: (label, confidence, x_mm, y_mm, z_mm) with an optional trailing
# normalized centre (cx, cy) used for bbox zones.
Detection = Sequence[Any]


class PersonTracker:
    """Turn per-frame detections into debounced ``person_enter`` / ``person_exit`` events.

    * A person must be seen in ``confirm_frames`` consecutive frames before
      ``person_enter`` fires (flicker suppression).
    * ``person_exit`` fires once nobody has been seen for ``gone_seconds``;
      it carries ``dwell_s`` (first confirmed sighting to last sighting).
    * ``now`` is a monotonic clock in seconds supplied by the caller.
    """

    def __init__(
        self,
        confirm_frames: int = 3,
        gone_seconds: float = 10.0,
        min_confidence: float = 0.5,
        zone: Zone | None = None,
        label: str = "person",
    ) -> None:
        if confirm_frames < 1:
            raise ValueError("confirm_frames must be >= 1")
        self.confirm_frames = confirm_frames
        self.gone_seconds = gone_seconds
        self.min_confidence = min_confidence
        self.zone = zone or Zone()
        self.label = label
        self._streak = 0
        self._since: float | None = None
        self._last_seen = 0.0

    @property
    def present(self) -> bool:
        return self._since is not None

    def _people(self, detections: Iterable[Detection]) -> list[Detection]:
        out = []
        for det in detections:
            label, conf, _x, _y, z = det[:5]
            if str(label) != self.label or conf < self.min_confidence:
                continue
            cx, cy = (det[5], det[6]) if len(det) >= 7 else (None, None)
            if self.zone.contains(z, cx, cy):
                out.append(det)
        return out

    def update(self, detections: Iterable[Detection], now: float) -> list[Event]:
        people = self._people(detections)
        events: list[Event] = []
        self._streak = self._streak + 1 if people else 0
        if people and (self.present or self._streak >= self.confirm_frames):
            self._last_seen = now
            if not self.present:
                self._since = now
                nearest = min(int(d[4]) for d in people)
                events.append(make_event("person_enter", zone=self.zone.name, count=len(people), nearest_mm=nearest))
        elif self.present and now - self._last_seen > self.gone_seconds:
            assert self._since is not None
            events.append(make_event("person_exit", zone=self.zone.name, dwell_s=int(self._last_seen - self._since)))
            self._since = None
        return events


# --------------------------------------------------------------------------- depth


def cell_medians(depth: np.ndarray, grid: tuple[int, int], min_valid_frac: float = 0.2) -> np.ndarray:
    """Median valid depth per grid cell; 0 where too few pixels are valid (0 = invalid)."""
    rows, cols = grid
    h, w = depth.shape
    out = np.zeros(grid, dtype=np.float32)
    for r in range(rows):
        for c in range(cols):
            blk = depth[r * h // rows:(r + 1) * h // rows, c * w // cols:(c + 1) * w // cols]
            valid = blk[blk > 0]
            if blk.size and valid.size > blk.size * min_valid_frac:
                out[r, c] = float(np.median(valid))
    return out


class DepthChangeDetector:
    """Detect lasting depth changes in a coarse grid of cells, with no picture kept.

    1. The first ``baseline_frames`` frames (taken while nobody is present)
       build a per-cell baseline: median, plus the median absolute deviation.
       Cells whose MAD exceeds ``noisy_frac`` of the baseline, or that are
       invalid too often, are marked noisy and never judged. Emits
       ``depth_baseline``.
    2. After that, a cell whose median moved by more than ``change_frac`` of
       its baseline for ``hold_seconds`` straight emits ``depth_change`` and
       becomes the new baseline for that cell.
    3. While a person is present, judging pauses and pending changes reset:
       people are not scenery.

    Each frame's array is reduced to cell medians and discarded.
    """

    def __init__(
        self,
        grid: tuple[int, int] = (6, 8),
        baseline_frames: int = 60,
        noisy_frac: float = 0.10,
        change_frac: float = 0.15,
        hold_seconds: float = 60.0,
        zone: Zone | None = None,
        min_valid_frac: float = 0.2,
        max_invalid_frac: float = 0.2,
    ) -> None:
        if baseline_frames < 1:
            raise ValueError("baseline_frames must be >= 1")
        self.grid = (int(grid[0]), int(grid[1]))
        self.baseline_frames = baseline_frames
        self.noisy_frac = noisy_frac
        self.change_frac = change_frac
        self.hold_seconds = hold_seconds
        self.zone = zone or Zone()
        self.min_valid_frac = min_valid_frac
        self.max_invalid_frac = max_invalid_frac
        self.baseline: np.ndarray | None = None
        self._acc: list[np.ndarray] = []
        self._pending: dict[tuple[int, int], float] = {}

    @property
    def ready(self) -> bool:
        return self.baseline is not None

    def update(self, depth: np.ndarray, now: float, person_present: bool = False) -> list[Event]:
        if depth.ndim != 2:
            raise ValueError("depth must be a 2-D array in millimetres")
        if person_present:
            self._pending.clear()
            return []
        g = cell_medians(self.zone.crop(depth), self.grid, self.min_valid_frac)
        if self.baseline is None:
            return self._accumulate(g)
        return self._judge(g, now)

    def _accumulate(self, g: np.ndarray) -> list[Event]:
        self._acc.append(g)
        if len(self._acc) < self.baseline_frames:
            return []
        st = np.stack(self._acc)
        self._acc = []
        base = np.median(st, axis=0)
        mad = np.median(np.abs(st - base), axis=0)
        noisy = (base <= 0) | (mad > self.noisy_frac * base) | ((st == 0).mean(axis=0) > self.max_invalid_frac)
        base[noisy] = 0  # 0 = not judged
        self.baseline = base
        return [make_event("depth_baseline", zone=self.zone.name, cells_judged=int((base > 0).sum()),
                           cells_noisy=int(noisy.sum()), grid=list(self.grid))]

    def _judge(self, g: np.ndarray, now: float) -> list[Event]:
        base = self.baseline
        assert base is not None
        moved = (base > 0) & (g > 0) & (np.abs(g - base) > self.change_frac * base)
        for rc in zip(*np.nonzero(moved)):
            self._pending.setdefault((int(rc[0]), int(rc[1])), now)
        for rc in [k for k in self._pending if not moved[k]]:
            self._pending.pop(rc)
        held = sorted(rc for rc, t0 in self._pending.items() if now - t0 >= self.hold_seconds)
        if not held:
            return []
        event = make_event("depth_change", zone=self.zone.name, cells=[f"r{r}c{c}" for r, c in held],
                           delta_mm=[int(g[rc] - base[rc]) for rc in held])
        for rc in held:
            base[rc] = g[rc]
            self._pending.pop(rc)
        return [event]
