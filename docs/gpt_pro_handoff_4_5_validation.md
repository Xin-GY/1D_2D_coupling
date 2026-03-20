# GPT Pro 交接提示词：4.5 验证章节整合

你现在接手的仓库是：`1d_2d_coupling`

请基于当前仓库状态继续工作，不要从头重做，不要重跑 chapter 全套实验。你的任务不是修改求解器，而是基于现有结果，生成一版可直接用于论文“4.5 模型验证”部分的中文学术写作内容。

## 必须先阅读的内容

1. `docs/chapter_coupling_time_discretization.md`
2. `docs/benchmark_case_notes.md`
3. `docs/section_4_5_validation_integration.md`
4. `artifacts/chapter_coupling_analysis_fastest_exact/summaries/summary_table.csv`
5. `artifacts/chapter_coupling_analysis_fastest_exact/summaries/summary_table_small_cases.csv`
6. `artifacts/chapter_coupling_analysis_fastest_exact/summaries/summary_table_test7_partitions.csv`
7. `artifacts/chapter_coupling_analysis_fastest_exact/summaries/exchange_link_summary.csv`
8. `artifacts/chapter_coupling_analysis_fastest_exact/plots/`

## 背景约束

- 当前综合场景结果使用的是 `surrogate_test7_overtopping_only_variant`，不是 official full Test 7。
- 这里的“obs”应理解为“观测值（或参考解）”；当前 chapter 结果主要是内部验证，不是实测率定。
- `strict_global_min_dt` 是参考解。
- 不得编造实测数据。
- 不得把 surrogate benchmark 写成 official full Test 7。
- 不得用 benchmark 中 `arrival_time_error = 0` 去证明“到达时间完全无误差”。
- 必须区分 benchmark 结果与 small mechanism 结果的用途：
  - benchmark：过程线、空间分布、界面守恒与综合一致性
  - small mechanism：early arrival、峰现时刻、特定耦合机理敏感性

## 你的输出目标

请生成一版可直接嵌入以下结构的中文学术写作文本：

- `4.5.1 验证层次与内容`
- `4.5.2 过程线验证指标`
- `4.5.3 空间淹没与界面专项指标`
- `4.5.4 验证结果的判定原则`

要求：

1. 使用论文风格中文。
2. 不要泛泛而谈，要明确引用现有图和现有数字。
3. 为每个小节给出：
   - 建议插图位置
   - 图题建议
   - 与上下文衔接的过渡句
4. 额外给出两张建议表：
   - 主表：benchmark interval 指标对比表
   - 补充表：small mechanism arrival/phase 指标表
5. 给出每张表建议列名。
6. 输出时不要只给提纲，要给可直接写进论文的段落。

## 可直接使用的关键结果

### benchmark 过程线指标

- `yield_schedule`
  - `stage_rmse = 0.2551`
  - `discharge_rmse = 0.6022`
  - `phase_lag = -33.5 s`
  - `hydrograph_NSE = 0.9663`
- `fixed_interval = 2 s`
  - `stage_rmse = 0.00466`
  - `discharge_rmse = 0.03656`
  - `phase_lag = -0.5 s`
  - `hydrograph_NSE = 0.99988`
- `fixed_interval = 3 s`
  - `stage_rmse = 0.00813`
  - `discharge_rmse = 0.04441`
  - `phase_lag = -1.0 s`
  - `hydrograph_NSE = 0.99982`
- `fixed_interval = 5 s`
  - `stage_rmse = 0.01723`
  - `discharge_rmse = 0.07647`
  - `phase_lag = -2.0 s`
  - `hydrograph_NSE = 0.99946`
- `fixed_interval = 10 s`
  - `stage_rmse = 0.07036`
  - `discharge_rmse = 0.18707`
  - `phase_lag = -5.0 s`
  - `hydrograph_NSE = 0.99674`
- `fixed_interval = 15 s`
  - `stage_rmse = 0.14722`
  - `discharge_rmse = 0.37468`
  - `phase_lag = -40.0 s`
  - `hydrograph_NSE = 0.98694`

### early-arrival 小算例

- `early_arrival_pulse_fixed_interval_005s`
  - `stage_rmse = 0.00278`
  - `peak_time_error = -0.5 s`
  - `arrival_time_error = 0.1236 s`
  - `phase_lag = 0.0 s`
  - `hydrograph_NSE = 0.99994`
- `early_arrival_pulse_fixed_interval_015s`
  - `stage_rmse = 0.02130`
  - `peak_time_error = 1.5 s`
  - `arrival_time_error = 1.0145 s`
  - `phase_lag = -1.0 s`
  - `hydrograph_NSE = 0.99967`

### 空间分布指标

- `yield_schedule`
  - `max_depth_map_difference = 0.04675`
  - `wet_area_iou = 1.0`
- `fixed_interval = 2 s`
  - `max_depth_map_difference = 0.00204`
  - `wet_area_iou = 1.0`
- `fixed_interval = 5 s`
  - `max_depth_map_difference = 0.00566`
  - `wet_area_iou = 1.0`
- `fixed_interval = 10 s`
  - `max_depth_map_difference = 0.01807`
  - `wet_area_iou = 1.0`
- `fixed_interval = 15 s`
  - `max_depth_map_difference = 0.03250`
  - `wet_area_iou = 1.0`
- `fixed_interval = 30 s`
  - `max_depth_map_difference = 0.05967`
  - `wet_area_iou = 1.0`
- `fixed_interval = 60 s`
  - `max_depth_map_difference = 0.07606`
  - `wet_area_iou = 1.0`
- `fixed_interval = 300 s`
  - `max_depth_map_difference = 0.19181`
  - `wet_area_iou = 1.0`

### 界面代表 link

- `fp1_overtop`
  - `peak_Q_exchange = 19.1568`
  - `cumulative_exchange_volume = 1118.63`
  - `link_mass_closure_error = 0.0`
- `fp2_return`
  - `peak_Q_exchange = 41.3321`
  - `cumulative_exchange_volume = 980.21`
  - `link_mass_closure_error = 0.0`
- `front_main`
  - `peak_Q_exchange = 26.0022`
  - `cumulative_exchange_volume = 2571.88`
  - `link_mass_closure_error = 0.0`

## 建议插图

### 4.5.1
- `artifacts/chapter_coupling_analysis_fastest_exact/plots/test7_geometry_and_mesh.png`
- 若前文尚未介绍耦合类型，可补 `artifacts/chapter_coupling_analysis_fastest_exact/plots/coupling_schematic.png`

### 4.5.2
- `artifacts/chapter_coupling_analysis_fastest_exact/plots/stage_hydrographs_1d.png`
- `artifacts/chapter_coupling_analysis_fastest_exact/plots/discharge_hydrographs_1d.png`
- 可选：`artifacts/chapter_coupling_analysis_fastest_exact/plots/xt_stage_river.png`

### 4.5.3
- `artifacts/chapter_coupling_analysis_fastest_exact/plots/2d_max_depth_map.png`
- `artifacts/chapter_coupling_analysis_fastest_exact/plots/2d_arrival_time_map.png`
- `artifacts/chapter_coupling_analysis_fastest_exact/plots/2d_difference_map.png`
- `artifacts/chapter_coupling_analysis_fastest_exact/plots/flood_front_overlay.png`
- `artifacts/chapter_coupling_analysis_fastest_exact/plots/floodplain_partition_compare.png`
- `artifacts/chapter_coupling_analysis_fastest_exact/plots/exchange_q_timeseries.png`
- `artifacts/chapter_coupling_analysis_fastest_exact/plots/exchange_deta_timeseries.png`
- `artifacts/chapter_coupling_analysis_fastest_exact/plots/exchange_volume_cumulative.png`
- `artifacts/chapter_coupling_analysis_fastest_exact/plots/exchange_event_alignment.png`

### 4.5.4
- `artifacts/chapter_coupling_analysis_fastest_exact/plots/rmse_vs_interval.png`
- `artifacts/chapter_coupling_analysis_fastest_exact/plots/peak_error_vs_interval.png`
- `artifacts/chapter_coupling_analysis_fastest_exact/plots/phase_lag_vs_interval.png`
- `artifacts/chapter_coupling_analysis_fastest_exact/plots/arrival_time_error_vs_interval.png`
  - 仅在 small mechanism 语境下使用，不要作为 benchmark 主图

## 额外要求

1. 请在输出中明确说明：
   - 4.5 的验证证据来自“局部机理 + 界面交换 + 综合场景”三层。
   - benchmark 主要证明综合一致性。
   - small mechanism 主要证明到达时间和机理敏感性。
2. 不要把 `wet_area_iou = 1.0` 直接写成“空间结果完全一致”；要指出最大水深场仍存在差异。
3. 结论要克制：
   - 可以说“在以河岸漫顶交换为主的场景下具有较好一致性和可信性”
   - 不要外推到涵洞、闸门、泵站等复杂结构场景

## 你最终要输出的内容

1. 一版完整的 4.5 节中文写作稿
2. 每个小节的插图位置建议
3. 2 张建议表的标题、列名和表中应放哪些 case
4. 一段总括性结论，用于 4.5.4 末尾
