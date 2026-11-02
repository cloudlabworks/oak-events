# Contributing to oak-events

Thanks for helping. Bug reports, hardware reports (especially RVC4) and small,
focused pull requests are all welcome.

## The one rule

**No pictures leave the camera.** Changes must not:

- link a colour, preview or passthrough output to a host queue,
- write images, depth maps or arrays (`.jpg`, `.png`, `.npy`, ...) to disk,
- add an MCP tool or event field that carries image data.

`tests/test_no_images.py` and the privacy tests enforce part of this; reviewers
check the rest.

## Development setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[mcp]' pytest
.venv/bin/pytest -q
```

CI installs from the hash-pinned lists in `requirements/` instead; see
`requirements/README.md` to add or update a tool.

The parsing code (zones files, event files) also has an Atheris fuzz harness,
run for 60 s by the `fuzz` workflow on every push and pull request. Atheris has
Linux x86_64 wheels only:

```bash
pip install --require-hashes -r requirements/fuzz.txt
PYTHONPATH=src python fuzz/fuzz_events.py -dict=fuzz/events.dict -max_total_time=60 fuzz/corpus
```

A crash writes the input to `crash-*`; add it as a test in
`tests/test_parsing_robustness.py` with the fix.

Tests must pass **without a camera and without `depthai` installed**; that is
what CI runs (Ubuntu and macOS, Python 3.11 and 3.13). Put event logic in
`events.py` (pure, testable with synthetic data) and keep `camera.py` a thin
adapter around DepthAI.

If you have hardware, also try `pip install -e '.[camera]'` and
`oak-events doctor`, then a short `oak-events run`, and mention the device and
results in your PR.

## Pull requests

- One change per PR, with tests for new logic.
- Update `README.md` (event schema table) when you add or change an event.
- Add a line under "Unreleased" in `CHANGELOG.md`.
- Do not include device ids, network addresses, hostnames or personal paths in
  code, tests, docs or example output.

## Code of conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md).
