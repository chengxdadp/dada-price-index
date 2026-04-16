# Dada Price Index

![Recent comparison](charts/recent_comparison.png)
![Full timeline](charts/timeline_full.png)
![Yearly comparison](charts/by_year.png)

This project builds a high‑frequency Producer Price Index (PPI) from the National Bureau of Statistics “Important Means of Production Price Changes” releases. The base period is **mid‑September 2020 = 100**, and the methodology change from **late December 2025 to early January 2026** is chain‑linked for continuity. The pipeline covers crawling, index calculation, visualization, and SQLite storage.

## Basic Stats (Current DB Output)

Running `python scripts/01_update.py` or `python scripts/01_update.py --chart` prints the latest indicators. Based on the current `data/price_data.db`, the latest output is:

```
Latest: 2026-04 (early)
Price Index: 146.90
MoM: 2.12%
YoY: 15.88%
```

Use `python scripts/01_update.py --status` for database summary statistics.

## Project Structure

```
/workspace/dada-price-index
├── data/
│   └── price_data.db       # SQLite database
├── charts/                 # Chart outputs
└── scripts/
    ├── 01_update.py       # Main update entry
    ├── 02_data_utils.py   # Crawling & incremental updates
    ├── 03_db_manager.py   # SQLite access layer
    ├── 04_index_builder.py # Index + chain-linking
    ├── 05_chart_maker.py  # Visualization + README rendering
    └── 06_migrate_to_sqlite.py # pickle -> SQLite migration
```

## Data Source & Methodology

- Source: NBS “Important Means of Production Price Changes” releases
- Frequency: ten‑day periods (early/mid/late)
- Base: mid‑September 2020 = 100
- Methodology change (from Jan 2026): removed/added/spec‑changed items are configured in `scripts/04_index_builder.py` and linked via average MoM change.

## Main Workflow

Running `python scripts/01_update.py` performs:

1. **Update release links**
2. **Fetch price tables** (store in SQLite)
3. **Compute index** (incremental preferred, fallback to full rebuild)
4. **Show stats and generate charts**

## Common Commands

```bash
# Incremental update (recommended)
python scripts/01_update.py

# Full rebuild
python scripts/01_update.py --full

# Charts only
python scripts/01_update.py --chart

# Verify incremental vs full
python scripts/01_update.py --verify

# Migration (pickle -> SQLite)
python scripts/01_update.py --migrate

# DB status
python scripts/01_update.py --status
```

## Dependencies

```bash
pip install -r requirements.txt
```
