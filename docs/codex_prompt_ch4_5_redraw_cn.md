# Codex 提示词：4.5 节配图重绘（中文论文图）

说明：当前文档是“总约束版”；`docs/codex_prompt_ch4_5_redraw_by_section_cn.md` 是“按 4.5 小节组织版”。

你现在接手仓库 `Xin-GY/1D_2D_coupling`。请不要修改求解器，不要重跑 full chapter，不要新增模拟；只允许基于现有 `artifacts/chapter_coupling_analysis/`、`artifacts/chapter_coupling_analysis_fastest_exact/` 中已经生成的 `summaries`、`plots`、`cases/*/plot_cache/` 与 case 原始 CSV/JSON 结果进行重绘。

本任务面向“实现重绘”的 Codex，不是论文写作 GPT。请直接开始执行，不要停留在方案讨论。

## 0. 总约束

1. 默认覆盖两套 chapter 根目录：
   - `artifacts/chapter_coupling_analysis/`
   - `artifacts/chapter_coupling_analysis_fastest_exact/`
2. 默认优先使用 `chapter_coupling_analysis_fastest_exact` 作为论文主图来源；旧 chapter 根目录同步生成一套对照版 `_cn` 图。
3. 所有输出必须新增 `_cn` 后缀，不覆盖现有 chapter 图。
4. 不允许改求解器，不允许重跑 full chapter，不允许回退到点云 / scatter 作为 2D 主图。
5. 若某张图所需字段在现有 summary 中不存在，可读取 case 级原始 CSV 补足；仍不允许为此重跑 full chapter。
6. 若缺任何关键 CSV / JSON / `plot_cache`，必须显式报错，不允许静默退化为白图或空图。

## 1. 统一输出规则

你必须新增并使用以下 4 个脚本：

1. `scripts/plot_ch4_5_hydrographs_cn.py`
2. `scripts/plot_ch4_5_2d_maps_cn.py`
3. `scripts/plot_ch4_5_interval_sweep_cn.py`
4. `scripts/plot_ch4_5_exchange_cn.py`

每个脚本都必须满足：

1. 支持参数化 `--output-root`。
2. 默认可分别对以下两个根目录运行：
   - `artifacts/chapter_coupling_analysis`
   - `artifacts/chapter_coupling_analysis_fastest_exact`
3. 输出 PNG 和 PDF 两个版本。
4. 文件名统一使用 `_cn` 后缀，例如：
   - `stage_hydrographs_1d_cn.png/.pdf`
   - `discharge_hydrographs_1d_cn.png/.pdf`
   - `max_depth_map_cn.png/.pdf`
   - `max_depth_difference_map_cn.png/.pdf`
   - `flood_front_overlay_cn.png/.pdf`
   - `rmse_vs_interval_cn.png/.pdf`
   - `phase_lag_vs_interval_cn.png/.pdf`
   - `arrival_time_error_vs_interval_cn.png/.pdf`
   - `exchange_q_timeseries_cn.png/.pdf`
5. 在脚本开头用注释写清关键输入依赖路径。
6. 运行时先做存在性检查，缺文件直接报错，不静默失败。
7. 逐图打印实际读取的输入文件清单。

## 2. 统一中文命名

图题、坐标轴、图例统一使用中文。不要在图中直接使用代码名。

### 2.1 方案名称映射

- `strict_global_min_dt` -> `严格同步参考方案`
- `yield_schedule` -> `事件触发式方案`
- `fixed_interval_002s` -> `固定步长 2 s`
- `fixed_interval_003s` -> `固定步长 3 s`
- `fixed_interval_005s` -> `固定步长 5 s`
- `fixed_interval_010s` -> `固定步长 10 s`
- `fixed_interval_015s` -> `固定步长 15 s`

如脚本中还要显示 `30/60/300 s`，对应写为：
- `固定步长 30 s`
- `固定步长 60 s`
- `固定步长 300 s`

### 2.2 代表链路名称映射

- `fp1_overtop` -> `漫顶交换链路 1`
- `fp2_return` -> `回流交换链路`
- `front_main` -> `正向边界链路`

### 2.3 综合算例名称要求

图题和图注中不要写 `Test 7`，统一写为：
- `河道—三分区洪泛平原综合算例`

## 3. 统一图形风格

1. 采用论文风格中文标题、中文坐标轴、中文图例。
2. `严格同步参考方案` 使用最醒目的实线。
3. 其余方案优先通过线型区分，避免只依赖颜色。
4. 2D 图必须保持：
   - `full-mesh face coloring`
   - `gray mesh lines`
5. 不允许以 `scatter` / centroid 点云作为 2D 主图。
6. 2D 差异图必须使用对称色标。
7. NaN / 无数据单元必须用浅灰色显示，不能留成白块。
8. 多 panel 对比图尽量共享色标范围。
9. 2D 图必须使用 `equal aspect`。

## 4. 图组 1：一维过程线图

使用脚本：`scripts/plot_ch4_5_hydrographs_cn.py`

### 4.1 目标

1. 重绘 benchmark 综合算例的主河道水位过程线图。
2. 重绘 benchmark 综合算例的主河道流量过程线图。

### 4.2 数据口径

1. 默认绘制 benchmark 综合算例。
2. 使用现有：
   - `stage_timeseries_1d.csv`
   - `discharge_timeseries.csv`
3. 方案至少展示：
   - `严格同步参考方案`
   - `事件触发式方案`
   - `固定步长 2 s`
   - `固定步长 3 s`
   - `固定步长 5 s`
   - `固定步长 10 s`
   - `固定步长 15 s`

### 4.3 图面要求

1. 水位图纵轴：`水位 / m`
2. 水位图横轴：`时间 / s`
3. 流量图纵轴：`流量 / m³/s`
4. 流量图横轴：`时间 / s`
5. 文件名：
   - `stage_hydrographs_1d_cn.png/.pdf`
   - `discharge_hydrographs_1d_cn.png/.pdf`

## 5. 图组 2：二维最大水深图、差异图与洪泛前沿图

使用脚本：`scripts/plot_ch4_5_2d_maps_cn.py`

### 5.1 目标

1. 重绘综合算例二维最大水深图。
2. 重绘二维最大水深差异图。
3. 重绘洪泛前沿叠置图。

### 5.2 数据口径

1. 使用 benchmark 综合算例。
2. 最大水深图对比：
   - `严格同步参考方案`
   - `事件触发式方案`
   - `固定步长 5 s`
   - `固定步长 15 s`
3. 差异图固定以 `严格同步参考方案` 为参考，以 `固定步长 15 s` 为代表偏差工况。
4. 洪泛前沿图使用：
   - `严格同步参考方案` 的 mesh-based 背景
   - `严格同步参考方案 vs 固定步长 15 s` 的前沿叠置
5. 几何必须优先从 `cases/<case>/plot_cache/` 读取；缺 cache 直接报错。

### 5.3 图面要求

1. 最大水深图采用统一色标范围，多图共享 colorbar。
2. 差异图色标标题写为：`最大水深差值 / m`
3. NaN / 无数据单元使用浅灰色。
4. 网格线使用浅灰细线轻微叠加。
5. 文件名：
   - `max_depth_map_cn.png/.pdf`
   - `max_depth_difference_map_cn.png/.pdf`
   - `flood_front_overlay_cn.png/.pdf`

## 6. 图组 3：时间步长扫描总结图

使用脚本：`scripts/plot_ch4_5_interval_sweep_cn.py`

### 6.1 目标

1. 重绘水位 RMSE 随耦合时间步长变化图。
2. 重绘 phase lag 随耦合时间步长变化图。
3. 重绘首达时刻误差随耦合时间步长变化图。
4. 如有现成字段，可选补一张峰现时刻误差图。

### 6.2 数据口径

1. 用 `summary_table.csv` 绘制综合算例曲线。
2. 用 `summary_table_small_cases.csv` 叠加四个小算例曲线。
3. 横轴默认用对数坐标，覆盖：
   - `2 / 3 / 5 / 10 / 15 / 30 / 60 / 300 s`
4. `3–5 s` 推荐区间必须用阴影或注释标出。
5. `快速首达脉冲算例` 必须单独突出显示，因为它对首达误差最敏感。
6. 对综合算例 `arrival_time_error = 0`，必须在图注或脚本注释中明确解释为：
   - `该综合算例的主要差异不集中在首达时刻。`
   - 不允许将其写成“首达完全无误差”。

### 6.3 图面要求

1. 横轴统一：`耦合时间步长 / s`
2. RMSE 图纵轴：`水位 RMSE / m`
3. phase lag 图纵轴：`相位差 / s`
4. 首达误差图纵轴：`首达时刻误差 / s`
5. 小算例图例名称统一为：
   - `前向边界蓄水算例`
   - `侧向漫顶—回流算例`
   - `快速首达脉冲算例`
   - `回水—流态切换算例`
   - `河道—三分区洪泛平原综合算例`
6. 文件名：
   - `rmse_vs_interval_cn.png/.pdf`
   - `phase_lag_vs_interval_cn.png/.pdf`
   - `arrival_time_error_vs_interval_cn.png/.pdf`
   - 如实现峰现时刻误差图，则另存 `_cn` 文件

### 6.4 列检查

脚本运行前必须先检查：
1. 所需 summary 表存在。
2. 所需案例存在。
3. 所需指标列存在；不存在则直接报错。

## 7. 图组 4：界面交换诊断图

使用脚本：`scripts/plot_ch4_5_exchange_cn.py`

### 7.1 目标

1. 重绘代表性链路交换流量时序图。
2. 重绘代表性链路水位差时序图。
3. 重绘累计交换体积图。

### 7.2 数据口径

1. 默认绘制以下方案：
   - `严格同步参考方案`
   - `事件触发式方案`
   - `固定步长 5 s`
   - `固定步长 15 s`
2. 使用 `exchange_link_timeseries.csv` 或现有等价 link-level 时序原始文件。
3. 固定链路：
   - `fp1_overtop`
   - `fp2_return`
   - `front_main`
4. 若 summary 中已有 representative link 配置，可优先复用，但默认仍以上述三条为准。
5. 若任一方案缺链路数据，必须显式报错并指出缺失的 case/link，不允许悄悄生成不完整图件。

### 7.3 图面要求

1. 图例名称统一为：
   - `漫顶交换链路 1`
   - `回流交换链路`
   - `正向边界链路`
2. 交换流量图纵轴：`交换流量 / m³/s`
3. 水位差图纵轴：`界面水位差 / m`
4. 累计交换体积图纵轴：`累计交换体积 / m³`
5. 图中应通过图注、注释或脚本说明明确指出：
   - 各方案均保持质量闭合；
   - 差异主要来自交换事件在时间上的分配方式不同。
6. 文件名：
   - `exchange_q_timeseries_cn.png/.pdf`
   - `exchange_deta_timeseries_cn.png/.pdf`
   - `exchange_volume_cumulative_cn.png/.pdf`

## 8. QA 与测试要求

完成重绘后，必须执行以下检查：

1. 逐图打印输入文件清单。
2. 对所有新 `_cn` 图执行 blank / near-blank QA。
3. 验证 2D 图仍走 mesh-based 渲染主路径，而不是 scatter 主视觉。
4. 若仓库已有以下测试：
   - `tests/test_plot_outputs.py`
   - `tests/test_blank_plot_detection.py`
   - `tests/test_2d_mesh_rendering.py`
   则应将新 `_cn` 图纳入这些测试；若无法直接复用，则新增最小测试覆盖。

### 8.1 验收标准

必须同时满足：
1. 不重跑 chapter 模拟。
2. 两套根目录都生成对应 `_cn` 图。
3. 新图无空白 / 近空白。
4. 2D 图无 scatter 主视觉。
5. 所有图标题、坐标轴、图例均为中文。

## 9. 最终输出

完成后，请给出：

1. 新增的 4 个脚本路径。
2. 每个脚本实际读取的输入文件清单。
3. 两套 chapter 根目录中新生成的 `_cn` 图文件清单。
4. 哪些测试被更新或新增。
5. blank / near-blank QA 结果。
6. 如遇到任何无法仅凭现有 artifacts 重绘的图，明确指出缺失了哪些字段或文件。

请直接开始实现，不要停留在方案讨论。
