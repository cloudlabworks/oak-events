# oak-events model card

| | |
| --- | --- |
| Owner | Alex Alvord, CloudLab Works |
| Version | Published 2026-11-02; written against commit 00d9053. Revised, approved by Alex Alvord and published 2026-11-02: verification steps (section 2.1), provenance (section 2.2), monitoring and spot-check (section 7), bias and fairness (section 8) |
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

### 2.1 Verifying a model archive

Check the archive at every handover: when you download it, when you copy it to the host that runs
oak-events, and every time oak-events loads it.

1. **Hash.** Compare with the SHA-256 above (Linux `sha256sum`, macOS `shasum -a 256`):

   ```bash
   echo "8372e2dec2d5e192e6ad9555b9412c3e31101b06e68121cfd08e92d4a4641122  yolov6n-r2-288x512.rvc2.tar.xz" | sha256sum -c -
   ```

   It must print `OK`. Tested on macOS (`shasum -a 256 -c -`) and Debian 13 (`sha256sum -c -`) on
   2026-11-02 against the archive described here.

2. **Contents.** The archive must hold exactly three regular files, and nothing that runs on the host:

   ```bash
   tar -tvJf yolov6n-r2-288x512.rvc2.tar.xz
   ```

   Expected: `config.json`, `buildinfo.json` and `yolov6n-r2-288x512.superblob`, each a regular file
   (the listing starts with `-`). Any other file, a link, or a Python, pickle or script file means the
   archive is not the one described here: do not use it. Checked 2026-11-02.

3. **At every load** (from the 0.1.2 and later): run with
   `--model-sha256 8372e2dec2d5e192e6ad9555b9412c3e31101b06e68121cfd08e92d4a4641122`. oak-events
   computes the archive's SHA-256 before opening the camera and refuses to start on a mismatch (a
   `camera` event with `state` `error`, exit code 3). Every `camera` `up` event records the hash of
   the archive that was loaded, so the event files show which model ran.

If you use another archive, record its hash the day you download it and use that value instead.

### 2.2 Provenance

| Step | Who | Evidence | Signed? |
| --- | --- | --- | --- |
| Architecture and training on COCO | Meituan ([meituan/YOLOv6](https://github.com/meituan/YOLOv6), GPL-3.0) | Upstream repository and paper ([arXiv:2209.02976](https://arxiv.org/abs/2209.02976)) | No signature found for upstream weights |
| Conversion to an RVC2 blob | Luxonis, ModelConverter 0.1.2 with the OpenVINO 2022.3 compile tool, 2024-07-24 | Archive `buildinfo.json` | No |
| Distribution | Luxonis model zoo (HubAI), model marked official | Luxonis model API, read 2026-11-02 | No signature offered; download over HTTPS |
| Download by the deployer | Deployer, once, with `dai.getModelFromZoo` (README) | The archive's SHA-256, compared with this card | Hash only |
| Load | oak-events, on each start | `--model-sha256` (0.1.2 and later) and the hash in the `camera` `up` event | Hash only |

Hash pinning detects a changed file; it does not prove who made it. A signature from the model provider
would. CloudLab Works checks at each review whether Luxonis has started signing model archives, and
verifies signatures once they are offered. **Commitment:** next check by 2027-11-01 (owner: Alex Alvord).

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
   CloudLab Works. No upstream fairness evaluation was found (section 8).
5. Depth is aligned to the colour image only approximately, so zone edges are fuzzy.
6. CloudLab Works has run only a functional live test (camera up, baseline built, about 10 frames per
   second). It has not measured accuracy. **Commitment:** a documented spot-check on the test camera by
   2027-03-31, using the procedure in section 7.

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
and `buildinfo.json`, the Luxonis model page and a fresh SHA-256 of the archive, and the archive contents
are checked as in section 2.1. The bias and fairness notes (section 8) are re-checked against upstream and
published research. This card was checked that way on 2026-11-02.

The verification steps in section 2.1 are reviewed with this card: at each release that changes model
guidance, at each change of reference model, and at least once a year.

## 7. Monitoring detection quality

oak-events cannot see pictures, so it cannot score its own detections. Two things help.

**Confidence statistics** (from the 0.1.2 and later). With `oak-events run --confidence-stats`,
every `alive` event carries, per zone, the number of person detections at or above the threshold
(`n`), their `mean`, `min` and `max` confidence, and the number below the threshold (`below`), for the
time since the previous `alive` event. Only numbers are kept.

Watch the trend on a scene that does not change. Signs that something changed (camera moved, lighting,
lens dirt, a different model, a firmware update):

- the mean confidence for a zone drops by more than 0.1 against the same hours of the previous week;
- `below` grows to more than twice its usual share of `n + below`;
- `n` falls to zero in hours when people are normally present.

```bash
jq -c 'select(.kind == "alive" and .confidence) | {ts, confidence}' DIR/*.jsonl
```

**Spot-check procedure.** Run it when you install a camera, after any of the changes above, and at
least once a month. CloudLab Works runs it on its test camera by 2027-03-31 and at each change of
reference model, and records the result in this card.

1. Turn on `--confidence-stats` and note the date, camera position, lighting, model hash and
   oak-events version.
2. With the people who use the space, and with their agreement, walk through each zone 20 times:
   standing, walking, sitting, and, where it fits the space, lying down, carrying something, and at the
   far edge of the zone. Count the `person_enter` events. Expected: 20 of 20 for standing and walking.
3. Show the camera a printed photo and a screen with a person on it for 30 seconds each. Count any
   `person_enter` events: each one is a false positive (threat model T9).
4. Leave the zone empty for 10 minutes. Count any `person_enter` events.
5. Record the counts and the confidence statistics. Compare with the last check. If standing or walking
   detection is below 18 of 20, or empty-zone or photo tests produce events, fix the cause (position,
   light, threshold, model) before relying on the events.

No picture is taken or stored at any step; the check uses the events only.

## 8. Bias and fairness

**Upstream evaluation.** The YOLOv6 README and paper report accuracy on COCO val2017 only. No
evaluation of detection rates across groups of people was found: the upstream README has no mention
of bias, fairness, demographics or skin tone (searched 2026-11-02), nor does the paper's abstract.
The Luxonis model page cites the upstream accuracy figure. Upstream fairness evaluation is therefore
UNKNOWN, and treated as not done.

**Published research on similar detectors.** These studies did not test YOLOv6. They show the kinds of
gaps to expect from person detectors trained on everyday photographs:

- Wilson, Hoffman and Morgenstern, *Predictive Inequity in Object Detection*, 2019
  ([arXiv:1902.11097](https://arxiv.org/abs/1902.11097)): detectors performed less well on pedestrians
  with darker skin tones (Fitzpatrick 4 to 6) on BDD100K, and time of day and occlusion did not explain
  the gap.
- Brandão, *Age and gender bias in pedestrian detection algorithms*, 2019
  ([arXiv:1906.10490](https://arxiv.org/abs/1906.10490)): all 24 top pedestrian detectors tested had
  higher miss rates on children; gender differences were not significant.

**Known and possible gaps for oak-events**

| Group or condition | Expected effect | Status |
| --- | --- | --- |
| Children, people small in frame or far away | Lower recall: late or missing `person_enter`, early `person_exit` | Likely (section 3 limit 1; Brandão 2019). Not measured |
| People lying down, sitting low, or seen from above | Lower recall | Likely (section 3 limit 1). Not measured |
| People using wheelchairs or other mobility aids | UNKNOWN | Not measured; COCO coverage UNKNOWN |
| Darker skin tones, especially in low light | Possibly lower recall | Possible (Wilson 2019, on other detectors). UNKNOWN for this model |
| Unusual clothing, costumes, heavy coats | UNKNOWN | Not measured |

**What this means for use.** Events may be less reliable for some people in view. That is one reason
oak-events must not be used for safety, care or security decisions (section 3, and the acceptable use
policy). Deployers should run the spot-check (section 7) with the people who actually use the space.

**Regular evaluation.** CloudLab Works re-checks upstream and published research at each review of
this card, at least once a year. The first CloudLab Works spot-check (by 2027-03-31) will include the
poses and heights available at the test site, with the agreement of the people involved. A household
test cannot measure differences across skin tones or mobility aids with any confidence; CloudLab Works
will say so in the result rather than claim a fairness evaluation it has not done.
