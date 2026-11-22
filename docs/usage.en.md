# Usage guide

[Back to English README](../README.md) · [简体中文](usage.zh-CN.md)

Run commands from the package root. `../my-character` below is your workspace; use a new version directory for production outputs. Fill paths, hashes, reviewer names and timestamps from actual evidence. Template values do not grant approval.

## Structures and active versions

```bash
python3 scripts/sprite_tools.py structure examples/structure.json ../pose-demo-v001
```

Outputs independent PNGs, `sequence.png`, `structure.gif` and `structure.json`. The included structure example is a static pose; design real actions frame by frame.

Structure fields include `canvas`, `ground_y`, `action_id`, `direction`, `loop`, `head_radius` and `frames`. Each frame needs a unique `id`, a positive duration in 10ms increments, `support`, `joints_2d`, `near_far`, and far-to-near `depth_order` containing exactly `L`, `R` and `body`.

Optional fields include `garment_polygon`, `contacts`, `props`, `furniture`, `trajectories` and `center_of_mass`. A contact uses `joint`, `target` and `state` (`touch` / `approach` / `release`). A prop needs `points` and `layer` (`back` / `front`). When an action declares `requires_contacts` or `requires_props`, every frame must provide the corresponding data. Review GIFs may replay; runtime looping is defined by JSON `loop`.

Build the active mapping from the [manifest template](../templates/manifest-v2.json). Each asset reference contains `file` and `sha256`; paths are relative to the manifest directory. Groups specify `id`, `version`, action/direction/loop, `pivot`, references and structure mappings. Character groups also need complete frame mappings, a GIF and a sequence image. The manifest produced by `build_demo.py` demonstrates the complete character fields.

## Review, feedback and atlas export

```bash
python3 scripts/sprite_tools.py review ../my-character/manifest.json ../my-character/review/index.html --reviews ../my-character/reviews.json
python3 scripts/sprite_tools.py import-reviews ../my-character/manifest.json ../my-character/review-feedback.json ../my-character/reviews.json
python3 scripts/sprite_tools.py sheet ../my-character/manifest.json GROUP_ID ../my-character/reviews.json ../my-character/exports/v001
```

Omit `--reviews` if there is no review history yet. In the page, enter the reviewer, choose the structure or character stage, describe issues with frame IDs, save the decision and export JSON. Then import it using the command above. Saving in the page does not write to disk. Import checks the version snapshot; changing group assets invalidates old approvals. Human attribution must reflect a real review. The tool neither authenticates reviewers nor judges art quality.

`sheet` requires current character-group approval and identical logical canvases for all selected frames. It does not resize or trim. `--columns 4 --padding 2` controls layout. The PNG and JSON include frame rectangles, logical dimensions, normalized pivots, actions, directions, durations and source hashes.

## Method C: programmatic protection

Copy [c-task.json](../templates/c-task.json) and set `task_id`, a shared `registry`, `original`, `generated` and `protection_mask`. Paths are relative to the task JSON. All three images must use identical dimensions and coordinates. Set the confirmation fields only after checking that the protected regions are stationary.

- `edit_mask` goes to the model: transparent requests edits; opaque requests preservation.
- `protection_mask` goes to the compositor: alpha=255 selects original pixels; alpha=0 selects generated pixels. Include both protected and editable regions. No intermediate alpha or feathering; RGB does not define the boundary.

```bash
python3 scripts/sprite_tools.py composite ../my-character/c-task.json ../my-character/c-results/v001
```

Outputs `final_composite.png`, `difference.png`, `comparison.png` (original / AI / composite) and `pixel_report.json`. Zero change applies only to the selected region of the actual supplied baseline. It does not prove that a native source was never resized or that the motion is natural.

The second attempt keeps the same baseline and model return, sets `attempt=2`, references the first report in `previous_report`, and changes the effective alpha boundary. Both attempts share the task ID and registry. Do not reset the count by changing either. If the second composite still has broken seams, follow the production rules to select a visually qualified A/B candidate or leave the frame awaiting repair.

## Offline requests and recovery

The [request-task template](../templates/request-task.json) references the current manifest, structure approval, palette and its approval, a budget file, adapter capabilities and a query method. The budget file needs `max_calls`, `source: "human"`, and real `reviewer` / `reviewed_at` values. Preserve previously agreed task limits.

```bash
python3 scripts/sprite_tools.py prepare ../my-character/task.json ../my-character/requests/v001
python3 scripts/sprite_tools.py claim ../my-character/requests/v001/request.json ../my-character/submission.json
python3 scripts/sprite_tools.py recover ../my-character/requests/v001/request.json
python3 scripts/sprite_tools.py receipt ../my-character/requests/v001/request.json ../my-character/receipt.json
```

`prepare` copies inputs and saves the outgoing prompt and hashes without networking. Before the host submits to a provider, `claim` records a stable `client_request_id` and `query_instructions`; it does not call a service. The host then submits the packaged request and saves the job's query identifier. On timeout, query that job rather than submitting again.

A receipt includes matching `request_id` and `client_request_id`, `status` (`RETURNED` / `FAILED` / `UNKNOWN`) and `query_evidence`. A successful receipt also needs `raw: {"file": "result.png", "sha256": "actual hash"}`, resolved relative to the receipt. `UNKNOWN` remains in flight: keep querying. Do not fabricate failure to unlock a request.

## Candidate selection and visual evidence

```bash
python3 scripts/sprite_tools.py select ../my-character/selection-review.json ../my-character/selections/v001
```

The input contains `c_attempts` (at most two) and `model_candidates`. C entries need hashed `report` and `image` references. Model entries need an `image`, the actual `method`, and `mild_redraw`. Each entry's `visual_review` records the reviewer, viewing `evidence`, and `identity_ok`, `action_ok`, `connections_ok`, `target_scale_ok`, `sequence_ok`.

Fallback to a qualified model candidate requires two failed C attempts or an explicit `c_not_applicable_reason`. If none qualifies, output is `NEEDS_REVIEW`. A selection is still a candidate; record character approval and engine validation separately.

**design by santu**
