# 操作指南

[返回中文首页](../README.zh-CN.md) · [English](usage.en.md)

在包根目录运行命令。以下 `../my-character` 指用户工作目录；生产输出使用新版本目录。模板中的路径、哈希、审核者与时间需要真实填写，示例状态不构成批准。

## 结构与有效版本

```bash
python3 scripts/sprite_tools.py structure examples/structure.json ../pose-demo-v001
```

输出独立 PNG、`sequence.png`、`structure.gif` 与 `structure.json`。内置示例只有静态姿势；真实动作需逐帧设计。

结构字段包括 `canvas`、`ground_y`、`action_id`、`direction`、`loop`、`head_radius` 和 `frames`。逐帧指定唯一 `id`、以 10ms 为单位的正时长、`support`、`joints_2d`、`near_far` 和由远到近排列的 `depth_order`（恰好包含 `L`、`R`、`body`）。

按需提供 `garment_polygon`、`contacts`、`props`、`furniture`、`trajectories`、`center_of_mass`。接触字段为 `joint`、`target` 和 `state`（`touch` / `approach` / `release`）；道具需 `points` 与 `layer`（`back` / `front`）。动作声明 `requires_contacts` 或 `requires_props` 时，每帧必须提供对应内容。结构 GIF 可循环审阅，实际动作循环以 JSON 的 `loop` 为准。

从[manifest 模板](../templates/manifest-v2.json)建立当前有效映射。每个资源引用含 `file` 和 `sha256`，路径相对 manifest 所在目录。每组提供 `id`、`version`、动作/方向/循环、`pivot`、参考和结构映射；人物部分需完整帧映射以及 GIF、帧序图。用 `build_demo.py` 生成的 manifest 可查看完整人物字段示例。

## 审核、意见与图集

```bash
python3 scripts/sprite_tools.py review ../my-character/manifest.json ../my-character/review/index.html --reviews ../my-character/reviews.json
python3 scripts/sprite_tools.py import-reviews ../my-character/manifest.json ../my-character/review-feedback.json ../my-character/reviews.json
python3 scripts/sprite_tools.py sheet ../my-character/manifest.json GROUP_ID ../my-character/reviews.json ../my-character/exports/v001
```

首次没有审核历史时可省略 `--reviews`。在页面填审核者，选择结构或人物阶段，写明帧 ID 和问题，保存意见后导出 JSON，再运行导入命令。页面保存不直接写磁盘。导入校验版本摘要；改变组资源后旧批准失效。审核归属字段由真实人工提供，工具不认证审核者身份，也不自动判断美术质量。

`sheet` 要求当前人物组有效批准，所有选定帧画布相同；不缩放、不 trim。`--columns 4 --padding 2` 控制排布。输出 PNG 和 JSON，含帧矩形、逻辑尺寸、归一化 pivot、动作、方向、时长和源哈希。

## C 程序保护

复制 [c-task.json](../templates/c-task.json)，填写 `task_id`、共享 `registry`、`original`、`generated`、`protection_mask`。路径相对任务 JSON；三图必须同尺寸、同坐标。实际确认静止保护区后才能填写两个确认字段。

- `edit_mask` 给模型：透明表示允许修改，不透明表示请求保留。
- `protection_mask` 给程序：alpha=255 使用底图，alpha=0 使用生成图。必须同时有编辑区和保护区，不允许灰度 alpha 或羽化；RGB 不决定边界。

```bash
python3 scripts/sprite_tools.py composite ../my-character/c-task.json ../my-character/c-results/v001
```

输出 `final_composite.png`、`difference.png`、`comparison.png`（原图 / AI / 合成）和 `pixel_report.json`。零变化仅指实际输入底图的选定区域，不证明原生母图未缩放或动作自然。

第二版使用同底图和AI返回，`attempt=2`，`previous_report` 指第一版报告，且必须改变有效 alpha 边界。两版共用同一任务 ID 和注册表；不得通过换注册表或任务 ID 重置次数。第二版仍割裂时，按生产规则选择视觉合格的 A/B 候选或保留待修。

## 离线请求与恢复

[request-task 模板](../templates/request-task.json)引用当前 manifest、结构批准、色板及批准、预算文件、适配器能力与查询方法。预算文件必须含 `max_calls`、`source: "human"`、真实 `reviewer` 和 `reviewed_at`。保留任务既有次数上限。

```bash
python3 scripts/sprite_tools.py prepare ../my-character/task.json ../my-character/requests/v001
python3 scripts/sprite_tools.py claim ../my-character/requests/v001/request.json ../my-character/submission.json
python3 scripts/sprite_tools.py recover ../my-character/requests/v001/request.json
python3 scripts/sprite_tools.py receipt ../my-character/requests/v001/request.json ../my-character/receipt.json
```

`prepare` 复制输入、保存实发 prompt 与哈希，不联网。`claim` 在宿主实际提交前登记稳定的 `client_request_id` 和 `query_instructions`，不调用服务。宿主随后提交包中请求，并保存原任务查询标识；超时执行查询而非重新提交。

回执含匹配的 `request_id`、`client_request_id`、`status`（`RETURNED` / `FAILED` / `UNKNOWN`）及 `query_evidence`；成功回执还需 `raw: {"file": "result.png", "sha256": "实际哈希"}`，相对回执文件定位。`UNKNOWN` 保持在途，继续查询；不要自行伪造失败来解锁。

## 候选选择与视觉证据

```bash
python3 scripts/sprite_tools.py select ../my-character/selection-review.json ../my-character/selections/v001
```

输入包含 `c_attempts`（最多两项）和 `model_candidates`。C项需 `report` / `image` 哈希引用；模型项需 `image`、真实 `method` 和 `mild_redraw`。每项 `visual_review` 记录实际审核者、`evidence`，以及 `identity_ok`、`action_ok`、`connections_ok`、`target_scale_ok`、`sequence_ok`。

两次 C 失败或明确填写 `c_not_applicable_reason` 后，才进入合格模型候选回退。无合格项输出 `NEEDS_REVIEW`。选择结果仍是候选，人物批准与引擎验收另行记录。

**design by santu**
