# 达达物价指数 / Dada Price Index

基于国家统计局《流通领域重要生产资料市场价格变动情况》构建的高频物价指数，基期设为 **2020 年 9 月中旬 = 100**，并处理 **2025 年 12 月下旬 → 2026 年 1 月上旬** 的口径变更衔接，持续更新至最新数据。项目内置从数据获取、指数计算到图表输出的完整流程，数据存储采用 SQLite。  
The project builds a high‑frequency Producer Price Index (PPI) from National Bureau of Statistics releases. The base period is **mid‑September 2020 = 100**, and the methodology change from **late December 2025 to early January 2026** is chain‑linked for continuity. The pipeline covers crawling, index calculation, visualization, and SQLite storage.

## 目录结构 / Project Structure

```
/workspace/dada-price-index
├── price_data.db          # SQLite 数据库 / SQLite database
├── charts/                # 图表输出 / Charts output
└── py/
    ├── data_utils.py      # 数据抓取与增量更新 / Crawling & incremental updates
    ├── db_manager.py      # SQLite 访问层 / SQLite access layer
    ├── index_builder.py   # 指数计算与口径变更衔接 / Index + chain-linking
    ├── chart_maker.py     # 可视化 / Visualization
    ├── update.py          # 主更新入口 / Main update entry
    └── migrate_to_sqlite.py # pickle -> SQLite 迁移 / Migration
```

## 数据来源与口径 / Data Source & Methodology

- 数据来源：国家统计局发布的《流通领域重要生产资料市场价格变动情况》  
  Source: NBS “Important Means of Production Price Changes” releases.
- 频率：旬度（上旬 / 中旬 / 下旬）  
  Frequency: ten‑day periods (early/mid/late).
- 基期：2020 年 9 月中旬 = 100  
  Base: mid‑September 2020 = 100.
- 口径变更（2026 年 1 月起）：在 `py/index_builder.py` 中配置删除、新增及规格变更的品种，按环比涨跌幅衔接。  
  Methodology change (from Jan 2026): removed/added/spec‑changed items are configured in `py/index_builder.py` and linked via average MoM change.

## 主要流程 / Main Workflow

运行主脚本 `py/update.py` 会依次完成：  
Running `py/update.py` performs:

1. **更新链接数据**（检查最新发布）  
   Update release links.
2. **更新价格数据**（抓取并写入 SQLite）  
   Fetch price tables and store in SQLite.
3. **计算指数**  
   - 增量更新优先；若序列不连续则自动切换全量重算  
   - Incremental update by default, fallback to full rebuild if needed.
4. **输出统计与图表**  
   Show latest stats and generate charts.

## 常用命令 / Common Commands

```bash
# 默认增量更新 / Incremental update (recommended)
python py/update.py

# 全量重算 / Full rebuild
python py/update.py --full

# 仅生成图表 / Charts only
python py/update.py --chart

# 增量 vs 全量一致性校验 / Verify incremental vs full
python py/update.py --verify

# 数据迁移（pickle -> SQLite）/ Migration
python py/update.py --migrate

# 数据库状态 / DB status
python py/update.py --status
```

## 依赖环境 / Dependencies

```bash
pip install pandas requests beautifulsoup4 matplotlib numpy
```
