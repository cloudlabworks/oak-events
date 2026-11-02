# oak-events model card

| | |
| --- | --- |
| Owner | Alex Alvord, CloudLab Works |
| Version | Published 2026-11-02; written against commit 00d9053 |
| Review | At each release that changes model guidance, and at least once a year (next by 2027-11-01) |

## 1. What oak-events ships

oak-events ships **no model** and trains none. The deployer passes a local DepthAI model archive
(NNArchive, `.tar.xz`) with `--model`. oak-events never downloads a model at runtime. Any detection archive
whose classes include `person` works; `--person-label` selects another class name.

The model runs **on the camera** (Luxonis RVC2 or RVC4 chip). The host receives only its detections: label,
confidence, 3-D position and box centre. Only the `person` class (or the class named by `--person-label`)
produces events; all other classes are ignored.

## 2. Reference model

The model named in the README example. The archive described here is the one cached on the maintainer's test host:

| Field | Value | Source |
| --- | --- | --- |
| Name | YOLOv6 Nano (YOLOv6n R2), variant `luxonis/yolov6-nano:r2-coco-512x288`, platform RVC2 | README; archive `config.json` |
| Developed by | Meituan Vision AI Department | Luxonis model page |
| Distributed by | Luxonis model zoo (HubAI), marked official | Luxonis model API, read 2026-11-02 |
| Licence | GPL-3.0 | Luxonis model page; upstream repository `meituan/YOLOv6` |
| Training data | COCO, 80 object classes | Luxonis model page |
| Architecture | EfficientRep backbone, Rep-PAN neck, anchor-free decoupled head; 4.317 M parameters, 2.032 GFLOPs | Luxonis model page |
| Input | 1 x 3 x 288 x 512, uint8, BGR | Archive `config.json` |
| Precision and format | FP16, compiled blob for the RVC2 (Myriad X) chip; not a pickle, not executable on the host | Archive `config.json`, `buildinfo.json` |
| Conversion | Luxonis ModelConverter 0.1.2 with OpenVINO 2022.3 compile tool, 2024-07-24 | Archive `buildinfo.json` |
| Built-in thresholds | Confidence 0.5, IoU 0.5, at most 300 detections | Archive `config.json` |
| Reported accuracy | 35.9 mAP on COCO val2017 at 640 x 640 (upstream figure; not measured at 512 x 288) | Luxonis model page, citing upstream |
| Reported speed | 63.6 inferences per second on RVC2 at FP16 | Luxonis benchmark |
| Archive file | `yolov6n-r2-288x512.rvc2.tar.xz`, 8,029,484 bytes | Maintainer's test host |
| SHA-256 | `8372e2dec2d5e192e6ad9555b9412c3e31101b06e68121cfd08e92d4a4641122` | Computed 2026-11-02 |

The archive with this hash was downloaded on 2026-10-11, the day of oak-events' live test. The test log does
not record which archive file was loaded, so the link between this hash and the live test is likely but
UNVERIFIED. The zoo now lists 4 versions of this model; a new download may differ. Check the hash of what you
download and compare with this card.

## 3. Intended use and limits

**Intended:** detect that a person is present in a zone, for presence events.

**Out of scope:** identifying or recognising people; estimating age, gender or other attributes; counting
people where accuracy matters; safety or security decisions; children's monitoring; use in private spaces.

**Known limits**

1. COCO images are mostly everyday photos at eye level. Expect lower recall for people seen from above,
   lying down, far away, small in frame, partly hidden, in low light or at unusual angles.
2. Photos, screens, posters and mannequins can be detected as people.
3. The 512 x 288 input is smaller than the 640 x 640 used for the published accuracy figure.
4. Fairness across skin tones, clothing, body types and mobility aids has not been evaluated by
   CloudLab Works. Whether upstream evaluated it is UNKNOWN.
5. Depth is aligned to the colour image only approximately, so zone edges are fuzzy.
6. CloudLab Works has run only a functional live test (camera up, baseline built, about 10 frames per
   second). It has not measured accuracy. **Commitment:** a documented spot-check on the test camera by
   2027-03-31.

## 4. Failure modes

| Failure | Effect on events | Mitigation | Risk |
| --- | --- | --- | --- |
| Person not detected (false negative) | Missing `person_enter`, or early `person_exit` after 10 s | Gone timeout; deployer tunes `--person-confidence` | Medium |
| Non-person detected (false positive) | Spurious `person_enter` | 3 confirm frames; 0.5 confidence | Medium |
| Class name not `person` | No person events at all | `--person-label` | Low |
| Model file missing or unreadable | `camera` event `error`, exit code 3 | Supervisor restarts; `doctor` | Low |
| Camera disconnects | `camera` events `reconnect` then `pipeline_stopped` | DepthAI reconnects up to 5 times; supervisor restart; `camera_health` turns `stale` | Low |
| Depth noise | False `depth_change` | Noisy-cell exclusion; 60 s hold; pause while a person is present | Low |

## 5. Open-model risk

| Factor | Assessment |
| --- | --- |
| Licence | GPL-3.0. oak-events does not redistribute the model; a deployer who redistributes the archive must follow GPL-3.0 |
| Provenance | Official Luxonis conversion of the upstream Meituan model; no cryptographic signature is available, so provenance relies on the Luxonis zoo and the hash above |
| Format | Compiled device blob, not a serialized Python object, so loading it cannot run code on the host |
| Updates | oak-events never updates the model. Deployers pin a file. CloudLab Works checks the Luxonis model page at each review and updates this card when the reference changes |
| Vulnerability monitoring | DepthAI and Luxonis repositories and advisories are checked at each review; model-specific vulnerability scanning is not done |

## 6. Documentation requirements

Any model CloudLab Works names as a reference must have, in this card: name and variant, developer and
distributor, licence, training data, input and format, thresholds, reported metrics with their source,
archive hash, intended and out-of-scope uses, known limits, CloudLab Works' own evaluation, failure modes,
open-model risk, and review date. At each review the fields are checked against the archive's `config.json`
and `buildinfo.json`, the Luxonis model page and a fresh SHA-256 of the archive. This card was checked that
way on 2026-11-02.
