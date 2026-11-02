# Hash-pinned tool lists for the workflows

Each `*.in` file lists what one workflow needs; the matching `*.txt` pins every
package, including transitive ones, to an exact version and the SHA-256 of
every published file. The workflows install with `pip install --require-hashes`,
so a changed or substituted file fails the install.

| File | Used by |
| --- | --- |
| `ci.txt` | `.github/workflows/ci.yml`: hatchling, numpy, mcp, pytest, ruff |
| `fuzz.txt` | `.github/workflows/fuzz.yml`: atheris and numpy for `fuzz/fuzz_events.py` |
| `release.txt` | `.github/workflows/release.yml`: build and hatchling |

hatchling is in the lists because the package is installed and built without
build isolation (`--no-build-isolation`, `python -m build --no-isolation`);
with isolation, pip would fetch the build backend unpinned.

After editing an `.in` file, regenerate its `.txt` (one command per file):

```bash
uv pip compile --universal --python-version 3.11 --generate-hashes \
  --custom-compile-command "see requirements/README.md" \
  requirements/ci.in -o requirements/ci.txt
```

`--universal` keeps one file valid for every OS and Python version in the CI
matrix. The weekly Dependabot pip update for `/` also reads this `requirements/`
folder and regenerates the hashes in its pull requests.
