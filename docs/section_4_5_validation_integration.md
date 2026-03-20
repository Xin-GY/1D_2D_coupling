# 4.5 验证章节图表整合建议

本文当前可直接用于“4.5 模型验证”部分的结果，主要来自 `artifacts/chapter_coupling_analysis_fastest_exact/`。这一套结果的定位是“以 `strict_global_min_dt` 为参考解的内部对比验证”，而不是实测率定或官方全设施 benchmark 复现。因此，本节的写法应将“观测值”统一表述为“观测值（或参考解）”，并明确当前综合场景采用的是 `surrogate_test7_overtopping_only_variant`，即以河岸漫顶交换为主的 overtopping-only surrogate benchmark，而不是 official full Test 7。

## 使用原则

1. `4.5` 章节以“验证”为核心，不强行并入计算成本占比图。`cost_share_stacked` 和 `relative_cost_vs_accuracy` 更适合放在后续时间离散或效率分析章节。
2. benchmark 结果主要用来支撑：
   - 关键断面过程线一致性；
   - 空间淹没格局一致性；
   - 界面交换守恒与方向合理性。
3. `arrival_time_error` 不宜直接用 benchmark 结果论证，因为当前 benchmark 汇总中该指标基本退化为 `0.0`。到达时间敏感性应由 `early_arrival_pulse` 小型机理算例支撑。
4. 4.5 中的定量表述应优先引用 `artifacts/chapter_coupling_analysis_fastest_exact/summaries/summary_table.csv`、`summary_table_small_cases.csv`、`summary_table_test7_partitions.csv` 与 `exchange_link_summary.csv`。

## 4.5.1 验证层次与内容

### 建议插图

- 主图：`artifacts/chapter_coupling_analysis_fastest_exact/plots/test7_geometry_and_mesh.png`
- 可选补图：`artifacts/chapter_coupling_analysis_fastest_exact/plots/coupling_schematic.png`

### 建议写法

这一小节主要承担“验证对象说明”的功能，不建议堆叠定量指标。可先说明验证被划分为基本水力过程、界面耦合专项和综合场景三个层次，然后引出综合场景所采用的 benchmark 几何。这里最适合引用 `test7_geometry_and_mesh.png`，说明当前综合验证场景由一维主河道、三片洪泛区分区以及若干 lateral/frontal 接口构成，能够覆盖河道漫顶入泛区、洪泛区回流及端部直连边界交换等关键过程。若前文尚未专门交代耦合类型，可在本节末补充 `coupling_schematic.png`，用作读者理解后续界面交换图的前置说明；若前文已详细解释耦合结构，则该图不必重复出现。

### 可直接改写的段落

可在本节末采用如下表述：

“综合场景验证采用 `surrogate_test7_overtopping_only_variant`。该算例保留了主河道—洪泛平原耦合洪水过程中的核心要素，包括一维河道主槽、Floodplain 1/2/3 三片洪泛区、侧向漫顶交换界面以及端部直连边界，但不包含涵洞、闸门或桥梁等离散设施路径。因此，本节验证结论主要适用于以河岸漫顶交换为主的河道—洪泛平原耦合场景，而不直接外推至具有复杂局部控制构筑物的城市洪水问题。”

## 4.5.2 过程线验证指标

### 建议插图

- `artifacts/chapter_coupling_analysis_fastest_exact/plots/stage_hydrographs_1d.png`
- `artifacts/chapter_coupling_analysis_fastest_exact/plots/discharge_hydrographs_1d.png`
- 可选补图：`artifacts/chapter_coupling_analysis_fastest_exact/plots/xt_stage_river.png`

### 建议主表

表 4-x 可命名为“不同交换时间离散策略下 benchmark 关键断面过程线指标对比”。建议列：

- scheduler / interval
- `stage_rmse`
- `discharge_rmse`
- `hydrograph_NSE`
- `phase_lag`

推荐纳入的 benchmark 行：

- `strict_global_min_dt`
- `yield_schedule`
- `fixed_interval_002s`
- `fixed_interval_003s`
- `fixed_interval_005s`
- `fixed_interval_010s`
- `fixed_interval_015s`
- `fixed_interval_030s`
- `fixed_interval_060s`
- `fixed_interval_300s`

### 可直接引用的数字

- `yield_schedule` 相对 `strict`：
  - `stage_rmse = 0.2551`
  - `discharge_rmse = 0.6022`
  - `phase_lag = -33.5 s`
  - `hydrograph_NSE = 0.9663`
- `fixed_interval = 2 s`：
  - `stage_rmse = 0.00466`
  - `discharge_rmse = 0.03656`
  - `phase_lag = -0.5 s`
  - `hydrograph_NSE = 0.99988`
- `fixed_interval = 3 s`：
  - `stage_rmse = 0.00813`
  - `discharge_rmse = 0.04441`
  - `phase_lag = -1.0 s`
  - `hydrograph_NSE = 0.99982`
- `fixed_interval = 5 s`：
  - `stage_rmse = 0.01723`
  - `discharge_rmse = 0.07647`
  - `phase_lag = -2.0 s`
  - `hydrograph_NSE = 0.99946`
- `fixed_interval = 10 s`：
  - `stage_rmse = 0.07036`
  - `discharge_rmse = 0.18707`
  - `phase_lag = -5.0 s`
  - `hydrograph_NSE = 0.99674`
- `fixed_interval = 15 s`：
  - `stage_rmse = 0.14722`
  - `discharge_rmse = 0.37468`
  - `phase_lag = -40.0 s`
  - `hydrograph_NSE = 0.98694`

### 过程线部分的写作重点

这部分不宜把 `arrival_time_error` 写成 benchmark 的主论据，因为当前 benchmark 汇总中该指标几乎全为零。更稳妥的写法是：benchmark 结果主要说明在综合洪泛场景下，过程线误差首先体现在涨落过程和后段相位修正上，而不是首到达时刻本身。也就是说，对于当前 surrogate benchmark，交换时间离散带来的主要差异并非“洪水是否到达”，而是“到达后水位和流量过程如何偏离参考解”。

### 到达时间敏感性补充表

表 4-y 可命名为“小型机理算例中固定交换间隔对到达时间与相位误差的影响”。建议从 `summary_table_small_cases.csv` 中选取：

- `early_arrival_pulse_fixed_interval_005s`
- `early_arrival_pulse_fixed_interval_015s`

建议列：

- case
- `exchange_interval`
- `arrival_time_error`
- `peak_time_error`
- `phase_lag`
- `stage_rmse`

可直接引用的数字：

- `early_arrival_pulse_fixed_interval_005s`
  - `arrival_time_error = 0.1236 s`
  - `peak_time_error = -0.5 s`
  - `phase_lag = 0.0 s`
  - `stage_rmse = 0.00278`
- `early_arrival_pulse_fixed_interval_015s`
  - `arrival_time_error = 1.0145 s`
  - `peak_time_error = 1.5 s`
  - `phase_lag = -1.0 s`
  - `stage_rmse = 0.02130`

### 可直接改写的段落

“由关键断面水位与流量过程线可见，在以 `strict_global_min_dt` 为参考解时，`2–5 s` 的固定交换间隔仍能较好保持过程线形态，其中 `2 s`、`3 s` 与 `5 s` 的水位均方根误差分别仅为 `0.00466`、`0.00813` 和 `0.01723`，对应的 Nash–Sutcliffe 效率系数均接近 1。相比之下，`yield_schedule` 虽然能够维持总体趋势，但其水位过程均方根误差已增至 `0.2551`，并出现 `-33.5 s` 的相位超前，说明较稀疏的交换事件会削弱后段过程的再现能力。随着固定交换间隔增大至 `10 s` 及以上，过程线误差与相位偏移进一步放大，其中 `15 s` 工况的水位均方根误差已达 `0.1472`，表明峰值阶段及退水阶段的界面修正已出现明显失真。”

“需要指出的是，当前综合 benchmark 中的到达时间误差并不能敏感地区分不同交换间隔，其原因在于该场景的首到达过程主要发生在首次 exchange 之前。因此，到达时间敏感性的验证应主要依赖 `early_arrival_pulse` 小型机理算例。该算例表明，当交换间隔由 `5 s` 增大至 `15 s` 时，到达时间误差由 `0.1236 s` 增大至 `1.0145 s`，说明对于早到达型过程，交换时间步长对波前推进时刻的影响远早于 benchmark 过程线中所反映的后段误差。”

## 4.5.3 空间淹没与界面专项指标

### 建议插图

- 空间分布主图：
  - `artifacts/chapter_coupling_analysis_fastest_exact/plots/2d_max_depth_map.png`
  - `artifacts/chapter_coupling_analysis_fastest_exact/plots/2d_arrival_time_map.png`
  - `artifacts/chapter_coupling_analysis_fastest_exact/plots/2d_difference_map.png`
  - `artifacts/chapter_coupling_analysis_fastest_exact/plots/flood_front_overlay.png`
- Floodplain 分区对比：
  - `artifacts/chapter_coupling_analysis_fastest_exact/plots/floodplain_partition_compare.png`
- 界面专项图：
  - `artifacts/chapter_coupling_analysis_fastest_exact/plots/exchange_q_timeseries.png`
  - `artifacts/chapter_coupling_analysis_fastest_exact/plots/exchange_deta_timeseries.png`
  - `artifacts/chapter_coupling_analysis_fastest_exact/plots/exchange_volume_cumulative.png`
  - `artifacts/chapter_coupling_analysis_fastest_exact/plots/exchange_event_alignment.png`

### 空间分布写法要点

空间分布部分要同时说明两件事。第一，最大水深场、到达时间场和前沿扩展形态是否保持一致。第二，三片洪泛区的局部差异是否会因为交换时间离散而被放大。这里建议把 `2d_max_depth_map.png`、`2d_difference_map.png` 与 `floodplain_partition_compare.png` 结合使用：前两者负责展示全域空间差异的主导位置，后者负责说明 Floodplain 1/2/3 是否具有一致的误差特征。

### 可直接引用的数字

从 benchmark 汇总中可直接引用：

- `yield_schedule`：
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

这些结果可用来支撑这样一个表述：当前 benchmark 中，淹没范围边界整体仍保持较高重合度，但最大水深分布会随着交换间隔增大而逐步偏离参考解。因此，若只看最终淹没范围是否重合，容易高估模型在空间水深再现上的稳定性。

### 界面专项写法要点

界面专项验证应优先围绕三类代表 link 组织：

- 强 lateral overtopping：`fp1_overtop`
- 强回流 link：`fp2_return`
- 代表性 frontal/direct link：`front_main`

从 `exchange_link_summary.csv` 可直接引用：

- strict benchmark:
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

### 可直接改写的段落

“空间分布结果表明，不同交换时间离散方案对最终淹没范围边界的影响相对有限，在当前 surrogate benchmark 中，各工况的 `wet_area_iou` 均接近 1。然而，若进一步比较最大水深场则可以发现，随着交换间隔增大，场变量误差呈持续累积趋势。例如，`2 s`、`5 s`、`10 s`、`15 s` 与 `300 s` 工况的最大水深场差异分别约为 `0.0020`、`0.0057`、`0.0181`、`0.0325` 与 `0.1918`。这表明仅以最终淹没范围是否重合作为验证依据是不充分的，仍需结合最大水深场、到达时间场和前沿扩展过程进行综合判断。”

“界面专项结果进一步说明了误差来源。对于 benchmark 中的代表性界面，`fp1_overtop`、`fp2_return` 与 `front_main` 的界面闭合误差均为零，说明当前耦合框架在局部体积交换上保持了严格的双边守恒。其中，`fp2_return` 的峰值交换流量达到 `41.3321`，明显高于 `fp1_overtop` 的 `19.1568`，反映出洪泛区退水回流过程在综合场景中具有不可忽视的贡献。结合 `exchange_q_timeseries` 与 `exchange_deta_timeseries` 可进一步看到，界面交换流量的时序变化与一维—二维水位差的演化总体保持一致，这为综合场景下洪泛区滞蓄与回流过程的可信性提供了物理基础。”

## 4.5.4 验证结果的判定原则

### 建议插图

- `artifacts/chapter_coupling_analysis_fastest_exact/plots/rmse_vs_interval.png`
- `artifacts/chapter_coupling_analysis_fastest_exact/plots/peak_error_vs_interval.png`
- `artifacts/chapter_coupling_analysis_fastest_exact/plots/phase_lag_vs_interval.png`
- 可选补图：`artifacts/chapter_coupling_analysis_fastest_exact/plots/arrival_time_error_vs_interval.png`，但仅在解释 `early_arrival_pulse` 时使用

### 建议写法

这一小节不再重复公式，而是归纳前述结果能否满足“守恒性、过程再现能力、空间分布再现能力、界面一致性”四个验证目标。建议按照以下顺序组织：

1. 系统与界面守恒性；
2. 关键断面过程线一致性；
3. 空间淹没格局一致性；
4. 界面双向交换时序与方向合理性；
5. 适用范围边界。

### 可直接改写的总结段

“综合上述结果可以认为，本文所构建的一维—二维耦合方法在以河岸漫顶交换为主的河道—洪泛平原洪水过程模拟中表现出较好的可信性。首先，系统总体积误差未表现出失控累积趋势，且代表性界面的体积闭合误差均为零，说明耦合交换在局部和整体层面均保持了较好的守恒性。其次，在过程线再现方面，`2–5 s` 的固定交换间隔能够较好保持与参考解的一致性，而 `10 s` 及以上工况开始表现出更明显的峰值与相位偏差；`yield_schedule` 虽可降低交换频次，但其在 benchmark 中已表现出较显著的相位偏移。再次，在空间分布方面，模型能够较好再现洪泛边界位置，但最大水深场对交换时间离散更为敏感，因此应联合使用淹没范围与水深场进行评价。最后，小型机理算例表明，对于关键到达发生在首次 exchange 之前的过程，交换间隔过大将明显削弱到达时间的再现能力。由此可见，‘过程线拟合较好’本身并不足以证明耦合方法可靠，只有守恒性、界面一致性和空间分布再现性同时得到满足时，才能认为该方法在工程应用中具有可信性。”

“需要强调的是，上述验证结论仅适用于当前 overtopping-only 的河道—洪泛平原耦合场景。若后续进一步引入涵洞、闸门、泵站调度、压力流或局部三维效应，则界面边界条件、能量损失机理和控制逻辑将明显复杂化，届时仍需开展针对性的补充验证。”

## 图表与段落对应清单

| 小节 | 建议主图 | 建议配套表/指标 | 主要论点 |
| --- | --- | --- | --- |
| 4.5.1 | `test7_geometry_and_mesh.png` | 无 | 说明验证对象、几何和界面类型 |
| 4.5.2 | `stage_hydrographs_1d.png`、`discharge_hydrographs_1d.png` | benchmark 指标表 | 说明过程线误差随交换间隔增大而放大 |
| 4.5.2 补充 | 可不单独插图，或引用 `arrival_time_error_vs_interval.png` | small mechanism arrival/phase 表 | 说明 early-arrival 对 coarse interval 更敏感 |
| 4.5.3 | `2d_max_depth_map.png`、`2d_difference_map.png`、`flood_front_overlay.png` | partition summary + link summary | 说明空间格局与界面交换的物理一致性 |
| 4.5.4 | `rmse_vs_interval.png`、`peak_error_vs_interval.png`、`phase_lag_vs_interval.png` | 前述表格汇总引用 | 形成判定性结论与适用范围边界 |

## 不建议在 4.5 主文中使用的图

- `cost_share_stacked.png`
- `relative_cost_vs_accuracy.png`
- `summary_dashboard.png`

这些图更适合放在后续关于时间离散影响、效率对比或实现代价分析的章节，而不是“模型验证”主段落。
