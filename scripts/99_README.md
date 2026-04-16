# 价格指数脚本说明（py/）

本目录包含数据抓取、指数计算、可视化与数据库管理的全部核心脚本。项目使用 SQLite 数据库存储，默认路径为 `data/price_data.db`（位于项目根目录下的 `data/` 文件夹）。

## 模块概览

- **data_utils.py**：数据爬取与增量更新  
  负责从国家统计局网站抓取《流通领域重要生产资料市场价格变动情况》数据，并将链接与价格表写入数据库。  
  - `fetch_price_table(url)`: 抓取单个页面的价格表格  
  - `update_links()`: 拉取最新发布链接并写入 `period_links`  
  - `update_price_data()`: 根据链接抓取价格表写入 `periods` + `price_items`  
  - `load_price_data()/load_links_data()`: 读取已有数据  

- **db_manager.py**：SQLite 数据库访问层  
  提供统一的数据库接口，包含表结构初始化、读写、统计与迁移辅助方法。  
  - `DatabaseManager`: 主类，自动初始化表结构  
  - `get_all_links()/get_all_periods()/get_index_series()`: 查询数据  
  - `insert_period_prices()/upsert_index()`: 写入价格与指数  
  - `get_statistics()`: 输出数据库基本统计  

- **index_builder.py**：指数计算与口径变更衔接  
  负责构建高频价格指数，并处理 2025 年 12 月下旬 → 2026 年 1 月上旬的口径变更链接。  
  - `build_price_index_full_with_chain()`: 全量计算（含口径衔接）  
  - `incremental_update()`: 增量更新（推荐日常使用）  
  - `verify_incremental_vs_full()`: 验证增量与全量一致性  
  - `calculate_growth_rate()`: 计算环比/同比涨跌  

- **chart_maker.py**：图表生成  
  根据指数序列输出三类图表，并保存至 `charts/`：  
  - `plot_full_timeline()`：完整时间序列  
  - `plot_by_year()`：年度对比  
  - `plot_recent_comparison()`：近两年对比  
  - `generate_all_charts()`：一键生成全部图表  

- **update.py**：主更新入口  
  组合各模块执行完整流程（抓取 → 计算 → 图表）。  
  - 默认：增量更新  
  - `--full`：全量重算  
  - `--chart`：仅重绘图表  
  - `--verify`：一致性验证  
  - `--migrate`：从 pickle 迁移到 SQLite  
  - `--status`：查看数据库统计  

- **migrate_to_sqlite.py**：迁移脚本  
  将旧版 `df_all_links.pkl / price_table.pkl / price_index.pkl` 迁移到 SQLite，并进行完整性校验。

## 常用命令

```bash
# 默认增量更新
python py/update.py

# 全量重算
python py/update.py --full

# 仅生成图表
python py/update.py --chart

# 数据迁移
python py/update.py --migrate

# 数据库状态
python py/update.py --status
```
