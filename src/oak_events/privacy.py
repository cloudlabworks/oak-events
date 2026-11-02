"""Privacy defaults for DepthAI, applied at import time.

DepthAI ships with telemetry, crash-dump collection and on-device
auto-calibration enabled. oak-events turns all three off before ``depthai`` is
imported. ``camera.py`` imports this module first for that reason.

The values are *forced*, not defaulted: a pre-set ``DEPTHAI_TELEMETRY=1`` is
overwritten. The only way to keep DepthAI's own behaviour is the explicit
opt-in ``OAK_EVENTS_ALLOW_TELEMETRY=1``, in which case this module leaves the
environment untouched.
"""

from __future__ import annotations

import os
from typing import MutableMapping

OPT_IN_ENV = "OAK_EVENTS_ALLOW_TELEMETRY"

PRIVACY_ENV: dict[str, str] = {
    "DEPTHAI_TELEMETRY": "0",
    "DEPTHAI_DISABLE_CRASHDUMP_COLLECTION": "1",
    "DEPTHAI_AUTOCALIBRATION": "OFF",
}


def opted_in(environ: MutableMapping[str, str] | None = None) -> bool:
    env = os.environ if environ is None else environ
    return env.get(OPT_IN_ENV, "").strip() == "1"


def apply(environ: MutableMapping[str, str] | None = None) -> dict[str, str]:
    """Force the privacy variables unless the user explicitly opted in.

    Returns the variables that were set (empty when opted in).
    """
    env = os.environ if environ is None else environ
    if opted_in(env):
        return {}
    for key, value in PRIVACY_ENV.items():
        env[key] = value
    return dict(PRIVACY_ENV)


def state(environ: MutableMapping[str, str] | None = None) -> dict[str, object]:
    """Report the current privacy-relevant environment, for ``oak-events doctor``."""
    env = os.environ if environ is None else environ
    current = {key: env.get(key) for key in PRIVACY_ENV}
    return {
        "opted_in_to_telemetry": opted_in(env),
        "env": current,
        "private": all(current[k] == v for k, v in PRIVACY_ENV.items()),
    }


def event_fields(environ: MutableMapping[str, str] | None = None) -> dict[str, object]:
    """Flat fields for the ``privacy`` event that ``oak-events run`` emits at startup.

    ``deviations`` names the variables that differ from the private defaults,
    so a deployer can alert on ``private: false`` without parsing the values.
    """
    current = state(environ)
    env = current["env"]
    assert isinstance(env, dict)
    return {
        "private": current["private"],
        "telemetry_opt_in": current["opted_in_to_telemetry"],
        "deviations": sorted(k for k, v in PRIVACY_ENV.items() if env.get(k) != v),
    }


APPLIED = apply()
