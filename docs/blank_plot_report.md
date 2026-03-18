# Blank Plot Audit Report

## Scope
- 扫描目录：
  - `artifacts/chapter_coupling_analysis/plots/`
  - `artifacts/chapter_coupling_analysis_fastest_exact/plots/`
- 扫描对象：
  - 仓库内已生成的 chapter 级 PNG 图
  - 同时结合各自 `summaries/figure_manifest.csv` 的脚本映射信息

## Audit Policy
- 本轮 blank/near-blank 判定不再只看“整张图有没有非白像素”。
- 新判据同时检查：
  - 全图非白像素比例
  - 全图像素方差
  - 面板内部非白像素比例
  - 面板内部像素方差
  - 面板内部色彩丰富度
- 这样可以识别出“有坐标轴和图框，但数据线/柱/曲面实际上没有画出来，或完全贴着坐标轴导致视觉上近似空白”的情况。

## Current Combined Audit
- 总图片数：52
- 当前 blank 数量：0
- 当前 near-blank 数量：0
- 当前空白/近空白文件清单：无

## Pre-Fix Findings In This Round
按新的“面板内部无数据也算 near-blank”口径，在本轮修复前共识别出 4 张 near-blank 图：

1. `artifacts/chapter_coupling_analysis/plots/arrival_time_error_vs_interval.png`
2. `artifacts/chapter_coupling_analysis/plots/interval_normalized_axes.png`
3. `artifacts/chapter_coupling_analysis_fastest_exact/plots/arrival_time_error_vs_interval.png`
4. `artifacts/chapter_coupling_analysis_fastest_exact/plots/interval_normalized_axes.png`

## Root Cause Classification

### 1. All values are constant or degenerate
- `arrival_time_error_vs_interval.png`
- `interval_normalized_axes.png`
- 当前 benchmark summary 中：
  - `arrival_time_error` 全部为 `0.0`
  - `peak_stage_error` 全部为 `0.0`
- 原图把这些退化序列直接画成贴在零轴上的柱状图或折线图，视觉上只剩坐标轴与图框。

### 2. Axis overlap / layout makes valid data look blank
- 这 4 张图不是“文件损坏”或“保存失败”。
- 它们的根因是：
  - 数据存在，但退化为常数；
  - y 轴范围没有对常数序列做 padding；
  - 结果是图元与零轴完全重叠，读图时会被误认为“没有数据”。

### 3. Geometry / `.msh` dependency
- 本轮 combined audit 中未再发现依赖未跟踪 `.msh` 才能重绘的空白图。
- 2D 主图继续依赖 `plot_cache/mesh_geometry.npz`，不是运行时 `.msh`。

### 4. Data filtering / NaN / missing geometry
- 本轮 current artifacts 中未发现由数据筛空、全 NaN、geometry 读取失败导致的剩余 blank 图。

## Fix Actions
- 修改 `scripts/_plot_common.py`
  - blank audit 增加面板内部内容密度与色彩丰富度指标
  - 增加 `axis_limits_with_padding(...)`
- 修改 `scripts/plot_arrival_time_error_vs_interval.py`
  - 从“零高度柱状图”改为“线+marker+零轴参考线”
  - 对常数序列显式增加 y 轴 padding
  - 对退化 benchmark 序列加 annotation
- 修改 `scripts/plot_interval_normalized_axes.py`
  - 两个子图都改成“线+marker+零轴参考线”
  - 对常数序列显式增加 y 轴 padding
  - 对退化序列加 annotation
- 重新生成以上 4 张受影响图片
- 重新跑 combined blank audit，当前结果为 0 blank / 0 near-blank

## Fix Result
- 修复前：4 张 near-blank
- 修复后：0 张 blank，0 张 near-blank

## Audit Artifacts
- `artifacts/chapter_coupling_analysis_fastest_exact/logs/blank_plot_audit_all.csv`
- `artifacts/chapter_coupling_analysis_fastest_exact/logs/blank_plot_audit_all.json`

## Notes
- 本轮没有重跑 chapter 全套模拟。
- 只重绘了受影响的 plot outputs。
- 2D 图的主风格保持不变：
  - full-mesh face coloring
  - gray mesh lines
