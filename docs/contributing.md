# Contributing and licence

Bug reports, hardware reports (especially RVC4) and small, focused pull
requests are all welcome on
[GitHub](https://github.com/cloudlabworks/oak-events). The full guide is
[`CONTRIBUTING.md`](https://github.com/cloudlabworks/oak-events/blob/main/CONTRIBUTING.md)
in the repository; this page summarizes it.

## The one rule

**No pictures leave the camera.** Changes must not:

- link a colour, preview or passthrough output to a host queue,
- write images, depth maps or arrays (`.jpg`, `.png`, `.npy`, ...) to disk,
- add an MCP tool or event field that carries image data.

`tests/test_no_images.py` and the privacy tests enforce part of this;
reviewers check the rest.

## Development setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[mcp]' pytest
.venv/bin/pytest -q
```

Tests must pass **without a camera and without `depthai` installed**; that is
what CI runs (Ubuntu and macOS, Python 3.11 and 3.13). CI installs its tools
from the hash-pinned lists in `requirements/`. Put event logic in `events.py`
(pure, testable with synthetic data) and keep `camera.py` a thin adapter
around DepthAI.

The parsing code (zones files, event files) also has an Atheris fuzz harness,
run for 60 seconds on every push and pull request.

If you have hardware, also try `pip install -e '.[camera]'` and
`oak-events doctor`, then a short `oak-events run`, and mention the device and
results in your pull request.

## Pull requests

- One change per pull request, with tests for new logic.
- Update the event schema in `README.md` and in this documentation
  ([Events reference](events.md)) when you add or change an event.
- Add a line under "Unreleased" in `CHANGELOG.md`.
- Do not include device ids, network addresses, hostnames or personal paths in
  code, tests, docs or example output.

## Editing this documentation

These pages live in the `docs/` folder of the repository and are published
with GitBook. Edit the Markdown files and open a pull request like any other
change; `docs/SUMMARY.md` sets the page order.

## Code of conduct

This project follows the
[Contributor Covenant](https://github.com/cloudlabworks/oak-events/blob/main/CODE_OF_CONDUCT.md).

## Licence

oak-events is released under the
[MIT licence](https://github.com/cloudlabworks/oak-events/blob/main/LICENSE).
By contributing you agree your work is released under the same licence.

oak-events is an independent community project by CloudLab Works, not
affiliated with or endorsed by Luxonis. OAK and DepthAI are Luxonis
trademarks, used here only to say which hardware and SDK the tool works with.
