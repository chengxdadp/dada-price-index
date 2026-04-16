# 达达物价指数

![最近两年对比图](charts/recent_comparison.png)

基于国家统计局《流通领域重要生产资料市场价格变动情况》构建的高频物价指数项目，基期设为 **2020 年 9 月中旬 = 100**，并处理 **2025 年 12 月下旬 → 2026 年 1 月上旬** 的口径变更衔接。

> English version: [README_EN.md](README_EN.md)

## 项目阐述

- 数据来源：国家统计局发布的旬度价格数据。
- 更新方式：增量抓取 + SQLite 持久化，避免重复抓取历史数据。
- 存储文件：`data/price_data.db`。
- 脚本目录：`scripts/`（使用 `01/02/...` 编号管理）。

## 更新日志

- 2026-04-16 03:57:37：执行脚本后自动重建 README（图表与最新统计同步更新）。

## 最新统计指标

```text
最新数据：2026年4月上旬
价格指数：146.90
环比增长：2.12%
同比增长：15.88%
```

## 完整时间序列

![完整时间序列图](charts/timeline_full.png)

## 历年指数对比图

![按年对比图](charts/by_year.png)

## 项目介绍

### 目录结构

```text
/workspace/dada-price-index
├── data/
│   └── price_data.db
├── charts/
└── scripts/
    ├── 01_update.py
    ├── 02_data_utils.py
    ├── 03_db_manager.py
    ├── 04_index_builder.py
    ├── 05_chart_maker.py
    └── 06_migrate_to_sqlite.py
```

### 主要流程

运行 `python scripts/01_update.py`：
1. 更新链接数据。
2. 增量抓取新增期次价格（历史数据由 SQLite 保留）。
3. 增量计算指数，必要时自动全量重算。
4. 生成图表与 README 最新指标。

### 常用命令

```bash
python scripts/01_update.py
python scripts/01_update.py --full
python scripts/01_update.py --offline
python scripts/01_update.py --chart
python scripts/01_update.py --verify
python scripts/01_update.py --migrate
python scripts/01_update.py --status
```

### 覆盖范围

当前时间序列覆盖：**2020 年 - 2026 年**。
