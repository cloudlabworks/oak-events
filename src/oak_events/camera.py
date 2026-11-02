"""DepthAI v3 runner: OAK camera -> events. Requires ``pip install 'oak-events[camera]'``.

Privacy model, enforced here:

* Only two host output queues exist: the spatial detection network's
  detections and the stereo depth map. Colour frames stay on the camera; they
  feed the on-chip network and are never linked to a host queue.
* Each depth map is reduced to a coarse grid of cell medians and dropped.
  Nothing but JSON lines is ever written.
* Telemetry, crash dumps and auto-calibration are off (see ``privacy``), and
  every run records that state in a ``privacy`` event before DepthAI loads.
"""

from . import privacy  # must stay first: sets DepthAI env before depthai loads

import hashlib
import time
from pathlib import Path
from typing import Any, Callable

from .events import ConfidenceStats, DepthChangeDetector, PersonTracker, Zone, make_event
from .sink import JsonlSink

INSTALL_HINT = "depthai is not installed. Install the camera extra: pip install 'oak-events[camera]'"

DISCOVERY_TIMEOUT_S = 240.0  # a PoE camera can need 30 s to a few minutes to free up after a previous host exits
DISCOVERY_POLL_S = 5.0
MAX_RECONNECT_ATTEMPTS = 5


class CameraUnavailable(RuntimeError):
    """depthai is missing, or no camera could be opened."""


def import_depthai() -> Any:
    try:
        import depthai as dai  # noqa: PLC0415  (lazy on purpose)
    except ImportError as exc:
        raise CameraUnavailable(INSTALL_HINT) from exc
    return dai


def discover(dai: Any, device_id: str | None = None, timeout_s: float = DISCOVERY_TIMEOUT_S,
             poll_s: float = DISCOVERY_POLL_S, sleep: Callable[[float], None] = time.sleep,
             clock: Callable[[], float] = time.monotonic) -> Any | None:
    """Find a device by id (or the first available one), retrying until ``timeout_s``."""
    t0 = clock()
    while True:
        devices = list(dai.Device.getAllAvailableDevices())
        if device_id:
            info = next((d for d in devices if d.getDeviceId() == device_id), None)
        else:
            info = devices[0] if devices else None
        if info is not None or clock() - t0 >= timeout_s:
            return info
        sleep(poll_s)


def file_sha256(path: str | Path, chunk_size: int = 1 << 20) -> str:
    """Lower-case hex SHA-256 of a file, read in chunks."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _label_name(labels: list[str], idx: int) -> str:
    return labels[idx] if 0 <= idx < len(labels) else str(idx)


def _device_model(device: Any) -> str | None:
    for attr in ("getProductName", "getDeviceName"):
        fn = getattr(device, attr, None)
        if fn is None:
            continue
        try:
            name = fn()
        except Exception:  # noqa: BLE001  (best effort metadata)
            continue
        if name:
            return str(name)
    return None


def _bootloader(device: Any) -> str | None:
    try:
        v = device.getBootloaderVersion()
    except Exception:  # noqa: BLE001
        return None
    return str(v) if v is not None else None


def run(
    sink: JsonlSink,
    model: str | Path,
    device_id: str | None = None,
    zones: list[Zone] | None = None,
    fps: float = 10.0,
    alive_every_s: float = 300.0,
    person_label: str = "person",
    person_confidence: float = 0.5,
    confirm_frames: int = 3,
    gone_seconds: float = 10.0,
    grid: tuple[int, int] = (6, 8),
    baseline_frames: int = 60,
    change_frac: float = 0.15,
    hold_seconds: float = 60.0,
    noisy_frac: float = 0.10,
    discovery_timeout_s: float = DISCOVERY_TIMEOUT_S,
    model_sha256: str | None = None,
    confidence_stats: bool = False,
) -> int:
    """Run until the pipeline stops. Returns a process exit code.

    Exit codes: 1 pipeline stopped, 2 no device found, 3 bad model path or
    model hash mismatch.
    Just before DepthAI loads, a ``privacy`` event records the privacy state.
    The model archive's SHA-256 is
    computed at every start and recorded in the ``camera`` ``up`` event; with
    ``model_sha256`` set, a different hash stops the run before the camera is
    opened. With ``confidence_stats``, ``alive`` events carry per-zone
    detection-confidence statistics.
    Exceptions propagate; the CLI turns them into a ``camera`` ``error`` event.
    Run under a supervisor that restarts on exit.
    """
    zones = zones or [Zone()]
    model_path = Path(model).expanduser()
    if not model_path.is_file():
        sink.emit("camera", state="error", detail=f"model archive not found: {model_path.name}")
        return 3
    model_digest = file_sha256(model_path)
    if model_sha256 is not None and model_digest != model_sha256.strip().lower():
        sink.emit("camera", state="error", detail=f"model archive SHA-256 mismatch: {model_path.name}",
                  model=model_path.name, model_sha256=model_digest, expected_sha256=model_sha256.strip().lower())
        return 3

    sink.emit("privacy", **privacy.event_fields())
    dai = import_depthai()
    info = discover(dai, device_id, timeout_s=discovery_timeout_s)
    if info is None:
        sink.emit("camera", state="not_found", device=device_id)
        return 2

    device = dai.Device(info)
    device.setMaxReconnectionAttempts(
        MAX_RECONNECT_ATTEMPTS, lambda status: sink.emit("camera", state="reconnect", detail=str(status))
    )
    trackers = [PersonTracker(confirm_frames, gone_seconds, person_confidence, zone, person_label,
                              stats=ConfidenceStats() if confidence_stats else None) for zone in zones]
    detectors = [DepthChangeDetector(grid, baseline_frames, noisy_frac, change_frac, hold_seconds, zone)
                 for zone in zones]

    with dai.Pipeline(device) as p:
        rgb = p.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_A)
        left = p.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_B)
        right = p.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_C)
        stereo = p.create(dai.node.StereoDepth)
        left.requestOutput((640, 400)).link(stereo.left)
        right.requestOutput((640, 400)).link(stereo.right)
        sdn = p.create(dai.node.SpatialDetectionNetwork).build(rgb, stereo, dai.NNArchive(str(model_path)), fps=fps)
        labels = list(sdn.getClasses() or [])
        # The ONLY two host queues. Never add one for rgb / preview / passthrough.
        q_det = sdn.out.createOutputQueue(maxSize=4, blocking=False)
        q_depth = stereo.depth.createOutputQueue(maxSize=2, blocking=False)
        p.start()
        sink.emit("camera", state="up", device=info.getDeviceId(), device_model=_device_model(device),
                  bootloader=_bootloader(device), model=model_path.name, model_sha256=model_digest,
                  model_sha256_checked=model_sha256 is not None, zones=[z.name for z in zones])

        last_alive, frames = time.monotonic(), 0
        while p.isRunning():
            now = time.monotonic()
            det = q_det.tryGet()
            if det is not None:
                frames += 1
                rows = []
                for d in det.detections:
                    sc = d.spatialCoordinates
                    rows.append((_label_name(labels, int(d.label)), float(d.confidence), float(sc.x), float(sc.y),
                                 float(sc.z), (d.xmin + d.xmax) / 2.0, (d.ymin + d.ymax) / 2.0))
                for tracker in trackers:
                    for ev in tracker.update(rows, now):
                        sink.write(ev)
            dep = q_depth.tryGet()
            if dep is not None:
                frame = dep.getFrame()
                del dep
                for tracker, detector in zip(trackers, detectors):
                    for ev in detector.update(frame, now, person_present=tracker.present):
                        sink.write(ev)
                del frame  # reduced to cell medians above; nothing is kept
            if now - last_alive >= alive_every_s:
                sink.write(alive_event(frames / (now - last_alive), trackers))
                last_alive, frames = now, 0
            time.sleep(0.01)
    sink.emit("camera", state="pipeline_stopped")
    return 1


def alive_event(det_fps: float, trackers: list[PersonTracker]) -> dict[str, Any]:
    """The heartbeat event; adds per-zone ``confidence`` statistics when the trackers collect them."""
    fields: dict[str, Any] = {
        "det_fps": round(det_fps, 1),
        "person": any(t.present for t in trackers),
        "occupied": [t.zone.name for t in trackers if t.present],
    }
    if any(t.stats is not None for t in trackers):
        fields["confidence"] = {t.zone.name: t.stats.snapshot() for t in trackers if t.stats is not None}
    return make_event("alive", **fields)


def list_devices() -> list[dict[str, Any]]:
    """Describe visible devices for ``doctor`` (raises CameraUnavailable without depthai)."""
    dai = import_depthai()
    out = []
    for info in dai.Device.getAllAvailableDevices():
        entry: dict[str, Any] = {
            "device_id": info.getDeviceId(),
            "state": str(getattr(info, "state", "")),
            "protocol": str(getattr(info, "protocol", "")),
            "platform": str(getattr(info, "platform", "")),
        }
        entry["bootloader"] = _probe_bootloader(dai, info)
        out.append(entry)
    return out


def _probe_bootloader(dai: Any, info: Any) -> str | None:
    """Read the bootloader version of a device that is not booted by another host (best effort).

    A device that is already running a pipeline (state BOOTED) is left alone.
    """
    state = str(getattr(info, "state", "")).upper()
    if "UNBOOTED" not in state and "BOOTLOADER" not in state:
        return None
    try:
        with dai.DeviceBootloader(info) as bl:
            return str(bl.getVersion())
    except Exception:  # noqa: BLE001  (busy / booted / unsupported: just report unknown)
        return None
