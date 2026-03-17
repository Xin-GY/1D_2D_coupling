# Table Manifest Notes

## Purpose
- `table_manifest.csv/json` 记录 chapter 分析中每一张主表的来源、关键列与 caption 草稿。
- 它与 `figure_manifest` 配套，便于把自动实验产物直接映射到论文主文或附录。

## Output Location
- `artifacts/chapter_coupling_analysis/tables/table_manifest.csv`
- `artifacts/chapter_coupling_analysis/tables/table_manifest.json`
- 同步副本也会写到 `summaries/`

## Required Columns
- `table_id`
- `source_csv_or_json`
- `key_columns`
- `caption_draft_cn`
- `caption_draft_en`
- `chapter_section`

## Core Tables
- `summary_table`
- `summary_table_mesh`
- `summary_table_test7_partitions`
- `summary_table_small_cases`
- `timing_breakdown`
- `exchange_link_summary`

## Intended Use
- 主文优先使用：
  - `summary_table`
  - `summary_table_test7_partitions`
  - `timing_breakdown`
  - `exchange_link_summary`
- 其余表可作为附录、补充材料或方法章节支持表。
