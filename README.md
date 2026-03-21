# 1D_2D_coupling

本仓库用于研究河道一维网络与洪泛区二维浅水域之间的 GPU fast-mode 耦合计算，当前主线工作集中在以下三部分：

- `coupling/`：耦合调度、1D/2D 适配层、交换链路与网格构建。
- `experiments/`：benchmark、小算例、chapter 级批处理、汇总指标与重绘入口。
- `artifacts/`：chapter 结果、A/B 对照结果、plot cache、图表与汇总表。

## 当前默认实现

- 2D 侧仅支持新版 GPUInlet fast-mode 主路径。
- 1D 侧默认 backend 为 `fastest_exact`，但 `legacy` backend 仍保留用于对照和回归。
- chapter 级默认结果目录：
  - `artifacts/chapter_coupling_analysis_fastest_exact/`
- 旧对照结果目录：
  - `artifacts/chapter_coupling_analysis/`

## 推荐阅读顺序

1. [coupling/README.md](coupling/README.md)：当前耦合实现路径、调度逻辑与 artifacts 写出链路。
2. [docs/fastest_exact_coupling_call_path.md](docs/fastest_exact_coupling_call_path.md)：fastest_exact backend 的代码级调用链审计。
3. [docs/chapter_coupling_time_discretization.md](docs/chapter_coupling_time_discretization.md)：chapter 结果与结论口径。
4. [docs/reproducibility.md](docs/reproducibility.md)：如何仅依赖现有 artifacts 重绘结果。

## 常用入口

- chapter 选定 case 刷新：
  - `python -m experiments.run_fastest_exact_refresh`
- 单 case 运行：
  - `python -m experiments.run_single_case ...`
- 4.5 节中文配图：
  - `python -m scripts.plot_ch4_5_hydrographs_cn`
  - `python -m scripts.plot_ch4_5_2d_maps_cn`
  - `python -m scripts.plot_ch4_5_exchange_cn`
  - `python -m scripts.plot_ch4_5_interval_summary_cn`

## 结果位置

- chapter 主结果：`artifacts/chapter_coupling_analysis_fastest_exact/plots/` 与 `summaries/`
- 旧 chapter 对照：`artifacts/chapter_coupling_analysis/plots/` 与 `summaries/`
- 1200 s 综合案例 rerun：`artifacts/chapter_case_reruns/benchmark_1200_legacy/`

## 说明

仓库中存在部分面向论文写作的中文重绘脚本与文档，它们都基于现有模拟结果和 plot cache 工作，不会修改求解器本体。
