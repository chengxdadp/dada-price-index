# 达达物价指数

![完整时间序列图](charts/timeline_full.png)
![按年对比图](charts/by_year.png)
![近期对比图](charts/recent_comparison.png)

基于国家统计局《流通领域重要生产资料市场价格变动情况》构建的高频物价指数，基期设为 **2020 年 9 月中旬 = 100**，并处理 **2025 年 12 月下旬 → 2026 年 1 月上旬** 的口径变更衔接，持续更新至最新数据。项目内置从数据获取、指数计算到图表输出的完整流程，数据存储采用 SQLite。

> English version: [README_EN.md](README_EN.md)

## 基础统计指标（当前数据库结果）

运行 `python py/update.py` 或 `python py/update.py --chart` 会打印最新一期指标。基于当前 `data/price_data.db` 读取到的最新结果如下：

```
最新数据：2026年1月第2旬
价格指数：129.67
环比增长：0.68%
同比增长：1.69%
```

如需查看数据库总体规模，可使用 `python py/update.py --status`。

## 目录结构

```
/workspace/dada-price-index
├── data/
│   └── price_data.db       # SQLite 数据库
├── charts/                 # 图表输出
└── py/
    ├── data_utils.py       # 数据抓取与增量更新
    ├── db_manager.py       # SQLite 访问层
    ├── index_builder.py    # 指数计算与口径变更衔接
    ├── chart_maker.py      # 可视化
    ├── update.py           # 主更新入口
    └── migrate_to_sqlite.py # pickle -> SQLite 迁移
```

## 数据来源与口径

- 数据来源：国家统计局发布的《流通领域重要生产资料市场价格变动情况》
- 频率：旬度（上旬 / 中旬 / 下旬）
- 基期：2020 年 9 月中旬 = 100
- 口径变更（2026 年 1 月起）：在 `py/index_builder.py` 中配置删除、新增及规格变更的品种，按环比涨跌幅衔接。

## 主要流程

运行主脚本 `py/update.py` 会依次完成：

1. **更新链接数据**（检查最新发布）
2. **更新价格数据**（抓取并写入 SQLite）
3. **计算指数**（增量更新优先，必要时自动切换全量重算）
4. **输出统计与图表**

## 常用命令

```bash
# 默认增量更新（推荐）
python py/update.py

# 全量重算
python py/update.py --full

# 仅生成图表
python py/update.py --chart

# 增量 vs 全量一致性校验
python py/update.py --verify

# 数据迁移（pickle -> SQLite）
python py/update.py --migrate

# 数据库状态
python py/update.py --status
```

## 依赖环境

```bash
pip install -r requirements.txt
```
