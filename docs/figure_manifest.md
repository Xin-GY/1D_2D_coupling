# Figure Manifest Notes

## Purpose
- `figure_manifest.csv/json` 是 chapter 级自动出图的登记表。
- 每一张图都对应一个独立脚本，脚本只从 artifacts 读取数据，不依赖内存对象。

## Output Location
- `artifacts/chapter_coupling_analysis/tables/figure_manifest.csv`
- `artifacts/chapter_coupling_analysis/tables/figure_manifest.json`
- 同步副本也会写到 `summaries/`

## Required Columns
- `figure_id`
- `script_path`
- `input_data_paths`
- `output_png_path`
- `caption_draft_cn`
- `caption_draft_en`
- `chapter_section`

## Usage
- 论文写作时，可直接从 manifest 中挑选主图并复用中英文 caption 草稿。
- 若重跑实验导致数据更新，只需重新执行：
  - `python -m experiments.run_coupling_sweep`
- 对应图和 manifest 会自动刷新。
