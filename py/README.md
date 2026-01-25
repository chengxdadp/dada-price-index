# 中国生产资料价格指数分析工具

本项目基于国家统计局发布的《流通领域重要生产资料市场价格变动情况》数据，构建高频价格指数并进行可视化分析。

## 项目结构

```
D:\RD\Economy\Price\
├── Price Base.xlsx           # 原始Excel数据文件
├── analyze_Price.ipynb      # 原始Jupyter notebook（已拆分为py模块）
├── df_all_links.pkl         # 缓存的链接数据
├── price_table.pkl          # 缓存的价格表格数据
├── price_index.pkl          # 计算得到的价格指数数据
├── charts/                  # 生成的图表文件夹
│   ├── timeline_full.png    # 完整时间序列图
│   ├── by_year.png         # 按年分组对比图
│   └── recent_comparison.png # 最近两年对比图
└── py/                      # Python模块文件夹
    ├── __init__.py
    ├── data_utils.py        # 数据爬取工具模块
    ├── index_builder.py     # 价格指数计算模块
    ├── chart_maker.py       # 图表生成模块
    ├── update.py           # 主更新脚本
    └── README.md           # 本文档
```

## 功能模块详解

### 1. data_utils.py - 数据爬取工具

**主要功能：**
- 从国家统计局网站爬取价格数据
- 增量更新机制，避免重复下载
- 断点续传支持

**核心函数：**
```python
# 爬取单个价格表格
fetch_price_table(url)

# 批量爬取链接页面
fetch_all_links(start_page=1, end_page=100)

# 增量更新链接数据
update_links()

# 增量更新价格数据
update_price_data()

# 加载已保存的数据
load_price_data()
load_links_data()
```

**数据源：**
- 主页：https://www.stats.gov.cn/sj/zxfb/index.html
- 数据格式：旬度发布，包含59类重要生产资料价格
- 时间范围：2020年9月至今

### 2. index_builder.py - 价格指数计算

**主要功能：**
- 构建等权重价格指数
- 基期设定：2020年9月中旬=100
- 计算环比、同比增长率

**核心函数：**
```python
# 构建价格指数（主函数）
build_price_index(df_price=None, base_year=2020, base_month=9, base_period=2)

# 获取最新指数值
get_latest_index_value(index_df=None)

# 计算增长率
calculate_growth_rate(index_df=None, periods_back=1)

# 获取指定年份数据
get_year_data(index_df=None, year=2025)

# 保存/加载指数数据
save_index_data(index_df, filename='price_index.pkl')
load_index_data(filename='price_index.pkl')
```

**指数计算方法：**
1. 提取各期各商品价格数据
2. 以2020年9月中旬价格为基期
3. 计算各商品相对指数
4. 等权重平均得到综合指数

### 3. chart_maker.py - 图表生成

**主要功能：**
- 生成多种类型的可视化图表
- 自动保存高分辨率图片
- 支持中文显示

**核心函数：**
```python
# 完整时间序列图
plot_full_timeline(index_df=None, save_path=None)

# 按年份分组对比图
plot_by_year(index_df=None, save_path=None)

# 最近两年对比图
plot_recent_comparison(index_df=None, year1=2024, year2=2025, save_path=None)

# 生成所有图表
generate_all_charts(index_df=None, output_dir='charts')

# 显示最新统计信息
show_latest_stats(index_df=None)
```

**图表类型：**
- **时间序列图：** 展示指数的完整历史趋势
- **年度对比图：** 按年份分组，便于比较季节性规律
- **近期对比图：** 重点对比最近两年的走势

### 4. update.py - 主更新脚本

**使用方法：**
```bash
# 完整更新（爬取最新数据+重新计算指数+生成图表）
python py/update.py

# 仅更新图表（不爬取新数据，使用已有数据重新生成图表）
python py/update.py --chart

# 查看帮助信息
python py/update.py --help
```

**完整更新流程：**
1. 更新链接数据（检查是否有新发布的数据）
2. 更新价格数据（爬取新的价格表格）
3. 计算价格指数（重新构建指数序列）
4. 显示最新统计信息
5. 生成所有图表

## 快速开始

### 环境要求

```bash
pip install pandas requests beautifulsoup4 matplotlib numpy
```

### 首次使用

如果是首次使用，需要先爬取历史数据：

```bash
# 进入项目目录
cd D:\RD\Economy\Price

# 运行完整更新
python py/update.py
```

### 日常使用

```bash
# 每日更新（通常只需要这一个命令）
python py/update.py

# 如果数据没有更新，仅重新生成图表
python py/update.py --chart
```

## 数据文件说明

### 缓存文件（自动生成）

- **df_all_links.pkl：** 包含所有价格数据页面的链接信息
  ```python
  columns: ['Year', 'Month', 'Period', 'URL']
  # Period: 1=上旬, 2=中旬, 3=下旬
  ```

- **price_table.pkl：** 包含所有爬取的原始价格表格数据
  ```python
  columns: ['Year', 'Month', 'Period', 'PriceTable']
  # PriceTable: 包含具体价格数据的DataFrame
  ```

- **price_index.pkl：** 计算得到的价格指数时间序列
  ```python
  columns: ['Year', 'Month', 'Period', 'PriceIndex']
  # PriceIndex: 以2020年9月中旬为100的价格指数
  ```

### 输出文件

- **charts/timeline_full.png：** 完整时间序列图
- **charts/by_year.png：** 按年分组对比图  
- **charts/recent_comparison.png：** 最近两年对比图

## 技术细节

### 数据爬取策略

1. **增量更新：** 只爬取新发布的数据，避免重复下载
2. **断点续传：** 支持中断后恢复，每爬取一页立即保存
3. **去重处理：** 自动去除重复的链接和数据
4. **容错机制：** 单个页面失败不影响整体流程

### 指数计算方法

1. **商品范围：** 覆盖黑色金属、有色金属、化工、石油天然气、煤炭、非金属建材、农产品、农业生产资料、林产品等9大类59种商品
2. **权重方法：** 等权重平均
3. **基期选择：** 2020年9月中旬（疫情后经济恢复期，价格相对稳定）
4. **频率：** 旬度数据，每月3个观测值

### 可视化特点

1. **中文支持：** 自动配置中文字体
2. **高分辨率：** 300 DPI，适合报告使用
3. **交互设计：** 突出显示最新年份数据
4. **自适应布局：** 根据数据长度自动调整x轴标签

## 自定义使用

### 修改基期

```python
from index_builder import build_price_index

# 使用2021年1月上旬为基期
index_df = build_price_index(base_year=2021, base_month=1, base_period=1)
```

### 生成特定图表

```python
import sys
import os

# 添加路径（如果不在py目录下运行）
sys.path.append('py')
# 或者直接在py目录下运行

from chart_maker import plot_recent_comparison
from index_builder import build_price_index

# 构建指数数据
index_df = build_price_index()

# 比较2023年和2024年
plot_recent_comparison(index_df, year1=2023, year2=2024, save_path='comparison_2023_2024.png')
```

### 获取特定数据

```python
from data_utils import load_price_data
from index_builder import get_year_data

# 加载数据
df_price = load_price_data()
index_df = build_price_index(df_price)

# 获取2025年数据
data_2025 = get_year_data(index_df, year=2025)
print(data_2025)
```

## 注意事项

1. **网络连接：** 需要稳定的网络连接访问stats.gov.cn
2. **访问频率：** 代码中已加入延时控制，避免过于频繁的请求
3. **数据完整性：** 如果某期数据格式异常，会跳过该期但不影响其他数据
4. **文件路径：** 所有pkl文件保存在主目录下，图表保存在charts/文件夹下
5. **字体问题：** 如果中文显示异常，可能需要安装SimHei字体

## 更新日志

- **v1.0：** 基础功能，支持数据爬取、指数计算、图表生成
- **当前版本：** 支持增量更新、断点续传、多种图表类型

## 联系方式

如有问题或建议，请联系项目维护者。  

---

**项目特色：**
- 🚀 一键更新：单个命令完成数据获取到图表生成
- 📊 高频数据：旬度频率，比月度数据更及时
- 🎯 增量更新：智能检测新数据，效率更高
- 📈 多维可视化：时间序列、年度对比、近期追踪
- 🔧 模块化设计：易于扩展和维护