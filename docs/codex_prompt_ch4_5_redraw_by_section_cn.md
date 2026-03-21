# Codex 提示词：4.5 节配图重绘（按小节组织，中文论文图）

你现在接手仓库 `Xin-GY/1D_2D_coupling`。请不要修改求解器，不要重跑实验，不要重跑 chapter sweep；只允许基于现有 `artifacts/chapter_coupling_analysis/`、`artifacts/chapter_coupling_analysis_fastest_exact/`、`cases/*/plot_cache/`、`docs/` 以及已生成的 `plots/`、`summaries/`、case 原始 CSV/JSON 结果进行重绘。

本提示词面向“实现重绘”的 Codex，不是论文写作 GPT。请直接开始执行，不要停留在方案讨论。

## 一、统一总约束

1. 默认同时覆盖两套 chapter 根目录：
   - `artifacts/chapter_coupling_analysis/`
   - `artifacts/chapter_coupling_analysis_fastest_exact/`
2. 默认以 `chapter_coupling_analysis_fastest_exact` 作为论文主图来源，旧 `chapter_coupling_analysis` 同步生成一套对照版 `_cn` 图。
3. 所有输出必须新增 `_cn` 后缀，不覆盖现有 chapter 图。
4. 不允许修改求解器，不允许重跑 full chapter，不允许重跑 chapter sweep。
5. 不允许回退到点云 / scatter 作为 2D 主图。
6. 若某张图所需字段在现有 summary 中不存在，可读取 case 级原始 CSV/JSON 补足；仍不允许为此重跑 full chapter。
7. 若缺任何关键 CSV / JSON / `plot_cache`，必须显式报错，不允许静默退化为白图或空图。

## 二、统一中文命名与风格

### 2.1 方案名称映射

- `strict_global_min_dt` -> `严格同步参考方案`
- `yield_schedule` -> `事件触发式方案`
- `fixed_interval_002s` -> `固定步长 2 s`
- `fixed_interval_003s` -> `固定步长 3 s`
- `fixed_interval_005s` -> `固定步长 5 s`
- `fixed_interval_010s` -> `固定步长 10 s`
- `fixed_interval_015s` -> `固定步长 15 s`
- `fixed_interval_030s` -> `固定步长 30 s`
- `fixed_interval_060s` -> `固定步长 60 s`
- `fixed_interval_300s` -> `固定步长 300 s`

### 2.2 小算例名称映射

- `frontal_basin_fill` -> `正向耦合蓄水算例`
- `lateral_overtopping_return` -> `侧向耦合漫顶—回流算例`
- `early_arrival_pulse` -> `正向耦合快速首达算例`
- `regime_switch_backwater_or_mixed` -> `混合耦合回水—流态切换算例`
- 当前 benchmark 综合算例 -> `正向—侧向复合耦合综合算例`

### 2.3 代表链路名称映射

- `fp1_overtop` -> `漫顶交换链路 1`
- `fp2_return` -> `回流交换链路`
- `front_main` -> `正向边界链路`

### 2.4 图形风格

1. 所有图题、坐标轴、图例均使用中文。
2. 参考方案使用最醒目的实线；其余方案优先通过线型区分，避免只依赖颜色。
3. 2D 图必须保持：
   - `full-mesh face coloring`
   - `gray mesh lines`
4. 2D 图必须使用 `equal aspect`。
5. 2D 差异图必须使用对称色标。
6. NaN / 无数据单元必须使用浅灰色，不得留成白块。
7. 多 panel 对比图尽量共享色标范围。

## 三、图件—小节对照表

| 论文小节 | 推荐主图 | 建议输出文件 |
|---|---|---|
| 4.5 节开头 | 耦合模型测试工况与耦合关系示意图 | `coupling_schematic_cn.png` |
| 4.5 节开头 | 河道—三分区洪泛平原综合算例构型与网格图 | `composite_case_geometry_mesh_cn.png` |
| 4.5.1 | 正向耦合蓄水算例构型及边界条件示意图 | `front_fill_case_schematic_cn.png` |
| 4.5.1 | 不同耦合时间步长下正向耦合蓄水算例水位过程线对比图 | `front_fill_stage_compare_cn.png` |
| 4.5.2 | 侧向耦合漫顶—回流算例构型及交换路径示意图 | `lateral_overtop_return_schematic_cn.png` |
| 4.5.2 | 不同耦合时间步长下侧向耦合漫顶—回流算例水位过程线对比图 | `lateral_overtop_return_stage_compare_cn.png` |
| 4.5.2 | 侧向耦合漫顶—回流算例代表性交换流量与界面水位差时序图 | `lateral_overtop_return_exchange_diag_cn.png` |
| 4.5.3 | 正向耦合快速首达算例构型及脉冲入流条件示意图 | `front_fast_arrival_schematic_cn.png` |
| 4.5.3 | 正向耦合快速首达算例首达阶段水位过程线局部放大图 | `front_fast_arrival_zoom_cn.png` |
| 4.5.3 | 首达时刻误差与峰现时刻误差随耦合时间步长变化图 | `front_fast_arrival_timing_error_vs_interval_cn.png` |
| 4.5.4 | 混合耦合回水—流态切换算例构型示意图 | `mixed_backwater_switch_schematic_cn.png` |
| 4.5.4 | 不同耦合时间步长下混合耦合回水—流态切换算例水位过程线对比图 | `mixed_backwater_switch_stage_compare_cn.png` |
| 4.5.4 | 混合耦合回水—流态切换算例相位差随耦合时间步长变化图 | `mixed_backwater_switch_phase_lag_vs_interval_cn.png` |
| 4.5.5 | 综合算例主河道水位过程线对比图 | `stage_hydrographs_1d_cn.png` |
| 4.5.5 | 综合算例主河道流量过程线对比图 | `discharge_hydrographs_1d_cn.png` |
| 4.5.5 | 综合算例二维最大水深分布图 | `max_depth_map_cn.png` |
| 4.5.5 | 综合算例二维最大水深差异图 | `max_depth_difference_map_cn.png` |
| 4.5.5 | 综合算例洪泛前沿叠置图 | `flood_front_overlay_cn.png` |
| 4.5.5 | 综合算例代表性链路交换流量时序图 | `exchange_q_timeseries_cn.png` |
| 4.5.5 | 综合算例代表性链路界面水位差时序图 | `exchange_deta_timeseries_cn.png` |
| 4.5.5 | 综合算例代表性链路累计交换体积图 | `exchange_volume_cumulative_cn.png` |
| 4.5.6 | 不同测试算例水位 RMSE 随耦合时间步长变化图 | `rmse_vs_interval_cn.png` |
| 4.5.6 | 不同测试算例相位差随耦合时间步长变化图 | `phase_lag_vs_interval_cn.png` |
| 4.5.6 | 不同测试算例首达时刻误差随耦合时间步长变化图 | `arrival_time_error_vs_interval_cn.png` |

## 四、可直接投喂给 Codex 的提示词

### 提示词 1：重绘 4.5 节总示意图与综合算例构型图

你现在接手仓库 `Xin-GY/1D_2D_coupling`。请不要修改求解器，不要重跑实验，只基于现有 `docs/`、两套 chapter 根目录下的 `plots/` 和 `cases/*/plot_cache/` 重绘 4.5 节开头需要的两张图。

目标：
1. 重绘“耦合模型测试工况与耦合关系示意图”。
2. 重绘“河道—三分区洪泛平原综合算例构型与网格图”。

绘图要求：
1. 第一张图用于统一说明正向耦合、侧向耦合、混合耦合和复合耦合四类关系。
2. 第二张图若复用现有 `test7_geometry_and_mesh.png`，请去掉 Test 7 字样，统一改写为“河道—三分区洪泛平原综合算例构型与网格图”。
3. 所有图中文字均用中文。
4. 网格图必须保持 equal aspect，并保留适度细灰网格线，不能退化为点云图。
5. 输出文件名：
   - `coupling_schematic_cn.png/.pdf`
   - `composite_case_geometry_mesh_cn.png/.pdf`
6. 将脚本保存为 `scripts/plot_ch4_5_overview_cn.py`。
7. 终端输出实际读取的输入文件清单。

额外要求：
1. 先检查 `docs/chapter_coupling_time_discretization.md`、`docs/figure_manifest.md` 与现有 `plots/`。
2. 若几何数据来自 `plot_cache`，请在脚本注释中写明具体来源。

### 提示词 2：重绘 4.5.1 正向耦合蓄水算例图组

你现在接手仓库 `Xin-GY/1D_2D_coupling`。请不要修改求解器，不要重跑实验，只基于现有 small-case 输出结果重绘 4.5.1 所需图件。

目标：
1. 绘制“正向耦合蓄水算例构型及边界条件示意图”。
2. 绘制“不同耦合时间步长下正向耦合蓄水算例水位过程线对比图”。
3. 可选：绘制“正向耦合蓄水算例水位 RMSE 随耦合时间步长变化图”。

数据与映射：
1. 该算例对应仓库中的 `frontal_basin_fill`。
2. 优先读取两套 chapter 根目录下的 `summaries/summary_table_small_cases.csv`。
3. 若存在 case 级过程线缓存或时序结果，也请读取以重绘水位过程线。

绘图要求：
1. 图例统一用中文，方案名称使用“严格同步参考方案”“固定步长 5 s”等，不使用代码名。
2. 水位过程线图横轴为“时间 / s”，纵轴为“水位 / m”。
3. 重点对比 5 s、15 s、60 s、300 s 与严格同步参考方案；若 2 s 数据可用，也可保留。
4. 正向耦合蓄水算例构型示意图应标出一维来水边界、正向耦合边界和二维蓄水区。
5. 输出文件名：
   - `front_fill_case_schematic_cn.png/.pdf`
   - `front_fill_stage_compare_cn.png/.pdf`
   - `front_fill_rmse_vs_interval_cn.png/.pdf`
6. 将脚本保存为 `scripts/plot_ch4_5_front_fill_cn.py`。

额外要求：
1. 若过程线数据文件不止一个，请在脚本末尾打印每条曲线对应的实际输入文件。
2. 如果只找到了 summary 而找不到过程线缓存，请明确报错并停止，不要生成假的过程线图。

### 提示词 3：重绘 4.5.2 侧向耦合漫顶—回流算例图组

你现在接手仓库 `Xin-GY/1D_2D_coupling`。请不要修改求解器，不要重跑实验，只基于现有 small-case 输出结果重绘 4.5.2 所需图件。

目标：
1. 绘制“侧向耦合漫顶—回流算例构型及交换路径示意图”。
2. 绘制“不同耦合时间步长下侧向耦合漫顶—回流算例水位过程线对比图”。
3. 绘制“侧向耦合漫顶—回流算例代表性交换流量与界面水位差时序图”。

数据与映射：
1. 该算例对应仓库中的 `lateral_overtopping_return`。
2. 优先读取两套 chapter 根目录下的 `summaries/summary_table_small_cases.csv`。
3. 若存在接口诊断时序文件，优先读取代表性 link 的 `Q_ex(t)` 与 `Δη(t)`。

绘图要求：
1. 构型图中应明确标示河道、洪泛区、侧向漫顶交换带及退水回流方向。
2. 水位过程线图重点对比严格同步参考方案、固定步长 5 s、15 s、60 s、300 s。
3. 交换诊断图采用双 panel：上图为“交换流量 / m³/s”，下图为“界面水位差 / m”。
4. 图题中统一使用“侧向耦合漫顶—回流算例”，不要使用仓库代码名。
5. 输出文件名：
   - `lateral_overtop_return_schematic_cn.png/.pdf`
   - `lateral_overtop_return_stage_compare_cn.png/.pdf`
   - `lateral_overtop_return_exchange_diag_cn.png/.pdf`
6. 将脚本保存为 `scripts/plot_ch4_5_lateral_return_cn.py`。

额外要求：
1. 若 link 级诊断数据包含多条链路，请选取最能代表“外泄—回流”过程的一条，并在脚本注释中说明选择理由。
2. 缺少接口诊断数据时请报错，不要退化为只画过程线。

### 提示词 4：重绘 4.5.3 正向耦合快速首达算例图组

你现在接手仓库 `Xin-GY/1D_2D_coupling`。请不要修改求解器，不要重跑实验，只基于现有 small-case 输出结果重绘 4.5.3 所需图件。

目标：
1. 绘制“正向耦合快速首达算例构型及脉冲入流条件示意图”。
2. 绘制“正向耦合快速首达算例首达阶段水位过程线局部放大图”。
3. 绘制“首达时刻误差与峰现时刻误差随耦合时间步长变化图”。

数据与映射：
1. 该算例对应仓库中的 `early_arrival_pulse`。
2. 请优先检查两套 chapter 根目录下的 `summaries/summary_table_small_cases.csv` 中与 arrival/peak/phase 相关的列。
3. 若存在 case 级局部过程线时序，请用于首达局部放大图。

绘图要求：
1. 首达局部放大图应至少显示严格同步参考方案、固定步长 5 s 和 15 s。
2. 首达误差图和峰现误差图可做成双 panel；横轴统一为“耦合时间步长 / s”。
3. 若时间步长跨越 2、5、15、60、300 s，优先使用对数横轴。
4. 不要把 `arrival_time_error = 0` 解释为“完全无误差”；图注中应写明该图用于识别首达敏感区间和误差锁定现象。
5. 输出文件名：
   - `front_fast_arrival_schematic_cn.png/.pdf`
   - `front_fast_arrival_zoom_cn.png/.pdf`
   - `front_fast_arrival_timing_error_vs_interval_cn.png/.pdf`
6. 将脚本保存为 `scripts/plot_ch4_5_fast_arrival_cn.py`。

额外要求：
1. 若 summary 中已给出 `arrival_time_error` 和 `peak_time_error`，请直接读取，不要手工重新估算。
2. 缺少时序数据时，局部放大图可以只比较能够明确读取到的方案，但必须在终端说明原因。

### 提示词 5：重绘 4.5.4 混合耦合回水—流态切换算例图组

你现在接手仓库 `Xin-GY/1D_2D_coupling`。请不要修改求解器，不要重跑实验，只基于现有 small-case输出结果重绘 4.5.4 所需图件。

目标：
1. 绘制“混合耦合回水—流态切换算例构型示意图”。
2. 绘制“不同耦合时间步长下混合耦合回水—流态切换算例水位过程线对比图”。
3. 绘制“混合耦合回水—流态切换算例相位差随耦合时间步长变化图”。

数据与映射：
1. 该算例对应仓库中的 `regime_switch_backwater_or_mixed`。
2. 优先读取两套 chapter 根目录下 `summary_table_small_cases.csv` 中相应 case 的 RMSE、phase lag 和过程线指标。

绘图要求：
1. 构型示意图中同时体现正向耦合边界、侧向交换边界及回水控制位置。
2. 水位过程线对比图至少包含严格同步参考方案、固定步长 5 s、15 s、60 s、300 s。
3. 相位差图横轴为“耦合时间步长 / s”，纵轴为“相位差 / s”。
4. 该图的重点是说明后期偏移和持续修正能力，不要把主结论写成首达失真。
5. 输出文件名：
   - `mixed_backwater_switch_schematic_cn.png/.pdf`
   - `mixed_backwater_switch_stage_compare_cn.png/.pdf`
   - `mixed_backwater_switch_phase_lag_vs_interval_cn.png/.pdf`
6. 将脚本保存为 `scripts/plot_ch4_5_mixed_backwater_cn.py`。

额外要求：
1. 若没有足够密的时序数据支撑完整过程线，请优先保证相位差图和关键时段过程线图的质量。
2. 缺文件时 fail-fast。

### 提示词 6：重绘 4.5.5 正向—侧向复合耦合综合算例图组

你现在接手仓库 `Xin-GY/1D_2D_coupling`。请不要修改求解器，不要重跑实验，只基于现有两套 chapter 根目录下的 `plots/`、`summaries/` 和 `cases/*/plot_cache/` 重绘 4.5.5 所需图件。

目标：
1. 重绘主河道水位过程线对比图。
2. 重绘主河道流量过程线对比图。
3. 重绘二维最大水深分布图。
4. 重绘二维最大水深差异图。
5. 重绘洪泛前沿叠置图。
6. 重绘代表性链路交换流量时序图。
7. 重绘代表性链路界面水位差时序图。
8. 重绘代表性链路累计交换体积图。

数据与映射：
1. 本小节对应当前综合算例主结果，请优先使用两套 chapter 根目录下的：
   - `summaries/summary_table.csv`
   - `summaries/summary_table_test7_partitions.csv`
   - `summaries/exchange_link_summary.csv`
   - 以及已有 `plots/` / field cache / case 原始结果
2. 若 `plot_cache` 完整，请优先使用 cache 几何重绘二维图，不要退化为 scatter。

绘图要求：
1. 水位与流量过程线图统一使用中文图题和中文图例。重点比较：
   - 严格同步参考方案
   - 事件触发式方案
   - 固定步长 2 s
   - 固定步长 3 s
   - 固定步长 5 s
   - 固定步长 10 s
   - 固定步长 15 s
2. 二维最大水深图采用 mesh-based renderer、equal aspect、共享色标；差异图必须使用对称色标，色标标题写为“最大水深差值 / m”。
3. 综合算例所有图题统一使用“河道—三分区洪泛平原综合算例”，不要出现 Test 7 字样。
4. 交换诊断图中代表性链路统一命名为：
   - 漫顶交换链路 1
   - 回流交换链路
   - 正向边界链路
5. 交换流量图纵轴为“交换流量 / m³/s”；界面水位差图纵轴为“界面水位差 / m”；累计交换体积图纵轴为“累计交换体积 / m³”。
6. 输出文件名：
   - `stage_hydrographs_1d_cn.png/.pdf`
   - `discharge_hydrographs_1d_cn.png/.pdf`
   - `max_depth_map_cn.png/.pdf`
   - `max_depth_difference_map_cn.png/.pdf`
   - `flood_front_overlay_cn.png/.pdf`
   - `exchange_q_timeseries_cn.png/.pdf`
   - `exchange_deta_timeseries_cn.png/.pdf`
   - `exchange_volume_cumulative_cn.png/.pdf`
7. 将脚本保存为：
   - `scripts/plot_ch4_5_hydrographs_cn.py`
   - `scripts/plot_ch4_5_2d_maps_cn.py`
   - `scripts/plot_ch4_5_exchange_cn.py`

额外要求：
1. 先检查现有 `plots/` 中是否已有可复用图；若已有，则在脚本中实现“基于源数据重新绘图”，而不是简单重命名旧图。
2. 终端输出每张图对应的输入文件清单。
3. 若二维 cache 缺失则报错，不允许静默生成空白图。
4. 同类图可集中到同一个脚本中实现，只要输出文件名与数据口径满足要求即可。

### 提示词 7：重绘 4.5.6 时间步长敏感性总结图

你现在接手仓库 `Xin-GY/1D_2D_coupling`。请不要修改求解器，不要重跑实验，只基于现有 summary 表重绘 4.5.6 的总结图。

目标：
1. 重绘“不同测试算例水位 RMSE 随耦合时间步长变化图”。
2. 重绘“不同测试算例相位差随耦合时间步长变化图”。
3. 重绘“不同测试算例首达时刻误差随耦合时间步长变化图”。

数据要求：
1. 优先读取两套 chapter 根目录下：
   - `summaries/summary_table.csv`
   - `summaries/summary_table_small_cases.csv`
2. 请在脚本中建立 case 名称映射，将仓库 case 名转换为中文案例名称。

绘图要求：
1. 横轴统一为“耦合时间步长 / s”，优先使用对数横轴。
2. RMSE 图纵轴写为“水位 RMSE / m”。
3. 相位差图纵轴写为“相位差 / s”。
4. 首达误差图纵轴写为“首达时刻误差 / s”。
5. 图例必须使用中文案例名称：
   - 正向耦合蓄水算例
   - 侧向耦合漫顶—回流算例
   - 正向耦合快速首达算例
   - 混合耦合回水—流态切换算例
   - 正向—侧向复合耦合综合算例
6. 在 RMSE 图中使用浅色阴影或括号标出综合算例的推荐区间 `3–5 s`。
7. 首达误差图要明确说明：该图主要用于快速首达算例，不能据此宣称综合算例“首达完全无误差”。
8. 输出文件名：
   - `rmse_vs_interval_cn.png/.pdf`
   - `phase_lag_vs_interval_cn.png/.pdf`
   - `arrival_time_error_vs_interval_cn.png/.pdf`
9. 将脚本保存为 `scripts/plot_ch4_5_interval_summary_cn.py`。

额外要求：
1. 先检查 summary 表中实际存在的列名；缺列时报错。
2. 在终端打印“实际纳入绘图的 case 名称”和“实际读取的指标列名”。
3. 同类图也可集中到之前统一脚本中实现，只要输出文件名与数据口径满足要求即可。

## 五、建议的出图顺序

1. 先重绘 4.5.5 综合算例图组：这些图最可能直接用于正文主图。
2. 再重绘 4.5.6 时间步长敏感性总结图：这组图可统一服务于全文结论。
3. 之后依次重绘 4.5.3、4.5.2、4.5.4、4.5.1 的小算例图组。
4. 最后补总示意图和构型图，用于章节开头或答辩 PPT。

## 六、给 Codex 的总约束句

> 请不要修改求解器，不要重跑任何实验，不要重跑 full chapter sweep。你只能基于现有 `artifacts/chapter_coupling_analysis/`、`artifacts/chapter_coupling_analysis_fastest_exact/`、`summaries/`、`plots/`、`cases/*/plot_cache/` 和 `docs/` 重绘论文第 4.5 节图件。所有脚本必须可重复运行，缺文件时 fail-fast，不能静默生成空白图。所有图题、坐标轴和图例均使用中文，且不得在图题中使用 Test 7 表述。请优先输出综合算例图组与时间步长敏感性总结图，再输出各小算例图组。

## 七、测试与验收要求

1. 将新 `_cn` 图纳入现有：
   - `tests/test_plot_outputs.py`
   - `tests/test_blank_plot_detection.py`
   - `tests/test_2d_mesh_rendering.py`
2. 若现有测试不足以覆盖 `_cn` 图，则新增最小测试覆盖。
3. 验收标准固定为：
   - 不重跑 chapter 模拟
   - 两套根目录都生成对应 `_cn` 图
   - 新图无空白 / 近空白
   - 2D 图无 scatter 主视觉
   - 所有图标题、坐标轴、图例均为中文
