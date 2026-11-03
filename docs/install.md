# Install

## Supported hardware

| Device | Status |
| --- | --- |
| RVC2: OAK-D PoE | Tested live (DepthAI 3.11, bootloader 0.0.29, macOS arm64) |
| RVC2: OAK-D (USB) | Expected to work; untested, reports welcome |
| RVC4 (e.g. OAK 4) | Untested; reports welcome |

Requires Python 3.10 or later. Running the camera requires DepthAI v3
(`depthai>=3.9`). Linux and macOS are the listed platforms.

## Install from PyPI

oak-events is published on PyPI as [`oak-events`](https://pypi.org/project/oak-events/).
The core package depends only on `numpy`. Two extras add the rest:

| Extra | Adds | Needed for |
| --- | --- | --- |
| `camera` | `depthai>=3.9` | `oak-events run`, and device details in `oak-events doctor` |
| `mcp` | `mcp>=1.0` (official MCP Python SDK) | `oak-events mcp` |

On the host that has the camera and also serves agents, install both:

```bash
pip install 'oak-events[camera,mcp]'
```

A host that only serves events to agents (for example a sandboxed MCP server
reading a copied or shared events directory) needs only the `mcp` extra:

```bash
pip install 'oak-events[mcp]'
```

Check the install:

```bash
oak-events --version
oak-events doctor
```

`doctor` works without a camera and without `depthai` installed; it then
reports `depthai: not installed`.

To verify the downloaded files against their build provenance, see
[Security](security.md#verifying-a-release).

## Fetch a model once

oak-events never downloads anything at runtime. Fetch a detection NNArchive
from the Luxonis model zoo once, with DepthAI itself, and keep the file:

```python
import depthai as dai

path = dai.getModelFromZoo(
    dai.NNModelDescription(model="luxonis/yolov6-nano:r2-coco-512x288", platform="RVC2")
)
print(path)  # copy this .tar.xz somewhere stable and pass it to --model
```

This one step contacts the Luxonis model hub. Check the exact model slug on the
Luxonis model zoo; any detection NNArchive whose classes include `person`
works (use `--person-label` if the class has another name). For RVC4, use
`platform="RVC4"`.

The [model card](MODEL_CARD.md) describes the reference detector and gives the
SHA-256 of the archive the project tested. Check the hash of what you download
and, once you trust a file, pin it with `--model-sha256` (see
[Configuration](configuration.md#model-integrity-check)).

## Install from source

```bash
git clone https://github.com/cloudlabworks/oak-events.git
cd oak-events
python3 -m venv .venv
.venv/bin/pip install -e '.[mcp]' pytest
.venv/bin/pytest -q
```

Tests need neither a camera nor `depthai`. Add the `camera` extra to run
against real hardware.
