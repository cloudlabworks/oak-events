# oak-events software bill of materials (SBOM)

| | |
| --- | --- |
| Owner | Alex Alvord, CloudLab Works |
| Current SBOM | `sbom-oak-events-0.1.2-c4fe71e.cdx.json`; licence summary `sbom-licenses-0.1.2-c4fe71e.md`. Previous: `sbom-oak-events-0.1.1-00d9053.cdx.json` (CycloneDX 1.6, JSON) |
| Regenerated | At every release (security baseline, section 7) and at least once a year |

## What the current SBOM covers

- oak-events 0.1.2 built from commit c4fe71e with the version set to 0.1.2, installed with both extras: `oak-events[camera,mcp]`.
- oak-events as the root component, and 31 components: the 30 Python packages it pulls in plus `pip`
  from the virtual environment, resolved on 2026-11-02 on macOS arm64 with Python 3.14, including
  `depthai` 3.11.0, `mcp` 2.3.0 and `numpy` 2.5.4.
- Licences of the 30 dependencies are permissive or public-domain style (MIT, BSD-3-Clause, Apache-2.0,
  MIT-0, PSF-2.0, 0BSD, Zlib, CC0-1.0); oak-events itself is MIT.
- Changes from the 0.1.1 SBOM: `pip` 26.2.1 to 26.3; every other component is unchanged.
- Provenance re-checked on 2026-11-02 for these 31 components with the PyPI integrity API (supply chain
  policy section 4.1): 22 publish attestations for every file, 9 publish none (annotated-types, cffi,
  depthai, h11, httpcore2, httpx2, opentelemetry-api, pycparser, pydantic_core). Same result as for 0.1.1.

**Not covered:**

- Native libraries and device firmware bundled inside the `depthai` wheel; they are not listed as separate
  components.
- The detection model. oak-events does not ship one; the reference model and its SHA-256 are in
  `MODEL_CARD.md`.
- Other platforms and Python versions may resolve different package versions, because `pyproject.toml`
  declares ranges, not pins.

## How to generate it

Use two throwaway virtual environments, one for oak-events and one for the tool, so the tool does not appear
in the SBOM:

```bash
git clone https://github.com/cloudlabworks/oak-events && cd oak-events
python3 -m venv /tmp/sbom-target
/tmp/sbom-target/bin/pip install '.[camera,mcp]'

python3 -m venv /tmp/sbom-tool
/tmp/sbom-tool/bin/pip install cyclonedx-bom pip-licenses

/tmp/sbom-tool/bin/cyclonedx-py environment --pyproject pyproject.toml \
  --of JSON --output-reproducible \
  -o docs/sbom-oak-events-$(python3 -c "import tomllib;print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")-$(git rev-parse --short HEAD).cdx.json \
  /tmp/sbom-target/bin/python

# Licence summary
/tmp/sbom-tool/bin/pip-licenses --python /tmp/sbom-target/bin/python --format=markdown --with-urls
```

Tool versions used for the current file: cyclonedx-bom 7.6.0 (`cyclonedx-py`), pip-licenses 5.5.5.

## Check before publishing

1. The file contains no local paths, hostnames or user names (`grep -E '/Users/|/home/|/tmp/' <file>` finds
   nothing).
2. The component count matches `pip list` in the target environment, minus oak-events (the root component).
3. Delete the two virtual environments afterwards.

**Commitment:** generate the SBOM in `release.yml` and attach it to each GitHub release by 2027-02-28.
