import os
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager

from _loader import load_local_module

build_price_index = load_local_module('04_index_builder.py', 'dada_index_builder').build_price_index

# 设置中文字体（自动选择可用字体，避免 SimHei 缺失导致大量告警）
_FONT_CANDIDATES = [
    'SimHei',
    'Noto Sans CJK SC',
    'Microsoft YaHei',
    'PingFang SC',
    'WenQuanYi Zen Hei',
    'Source Han Sans CN',
]
_AVAILABLE_FONTS = {f.name for f in font_manager.fontManager.ttflist}
_SELECTED_FONTS = [f for f in _FONT_CANDIDATES if f in _AVAILABLE_FONTS]
if not _SELECTED_FONTS:
    _SELECTED_FONTS = ['DejaVu Sans']

plt.rcParams['font.sans-serif'] = _SELECTED_FONTS + ['DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

MONTH_LABELS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def _period_to_x(month, period):
    return month + (period - 1) / 3.0


def _get_stats(index_df):
    latest = index_df.iloc[-1]
    mom = None
    yoy = None

    if len(index_df) > 1:
        prev = index_df.iloc[-2]['PriceIndex']
        mom = (latest['PriceIndex'] - prev) / prev * 100

    last_year_data = index_df[
        (index_df['Year'] == latest['Year'] - 1)
        & (index_df['Month'] == latest['Month'])
        & (index_df['Period'] == latest['Period'])
    ]
    if not last_year_data.empty:
        last_year_value = last_year_data.iloc[0]['PriceIndex']
        yoy = (latest['PriceIndex'] - last_year_value) / last_year_value * 100

    return {
        'year': int(latest['Year']),
        'month': int(latest['Month']),
        'period': int(latest['Period']),
        'index': float(latest['PriceIndex']),
        'mom': mom,
        'yoy': yoy,
    }


def _period_cn(period):
    return {1: '上旬', 2: '中旬', 3: '下旬'}.get(period, f'第{period}旬')


def plot_full_timeline(index_df=None, save_path=None):
    if index_df is None:
        index_df = build_price_index()

    plt.figure(figsize=(15, 6))
    plt.plot(range(len(index_df)), index_df['PriceIndex'], marker='o', markersize=3)

    x_ticks, x_labels = [], []
    prev_year = None
    shown_months = set()
    for idx, (year, month, _) in enumerate(zip(index_df['Year'], index_df['Month'], index_df['Period'])):
        if year != prev_year:
            shown_months = set()
        if year != prev_year or (month % 3 == 0 and month not in shown_months):
            x_ticks.append(idx)
            x_labels.append(f'{year}-{month}' if year != prev_year else f'{month}')
            prev_year = year
            shown_months.add(month)

    plt.xticks(x_ticks, x_labels, rotation=45, ha='right')
    plt.xlabel('Date')
    plt.ylabel('Price Index')
    plt.title('China Producer Price Index based on high frequency data')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.subplots_adjust(bottom=0.15)

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"图表已保存到: {save_path}")
    plt.close()


def plot_by_year(index_df=None, save_path=None):
    if index_df is None:
        index_df = build_price_index()

    plt.figure(figsize=(15, 6))

    years = sorted(index_df['Year'].unique())
    color_map = plt.cm.get_cmap('tab20', max(len(years), 3))

    for i, year in enumerate(years):
        year_data = index_df[index_df['Year'] == year]
        x = _period_to_x(year_data['Month'], year_data['Period'])
        is_latest = year == years[-1]
        plt.plot(
            x,
            year_data['PriceIndex'],
            marker='o',
            markersize=4 if is_latest else 3,
            color=color_map(i),
            label=str(year),
            linewidth=2.8 if is_latest else 1.4,
            alpha=0.95 if is_latest else 0.65,
            zorder=5 if is_latest else 2,
        )

    plt.xticks(range(1, 13), MONTH_LABELS)
    plt.xlabel('Month')
    plt.ylabel('Price Index (2020.9=100)')
    plt.title('China Producer Price Index by Year')
    plt.legend(title='Year', bbox_to_anchor=(1.02, 1), loc='upper left', borderaxespad=0)
    plt.grid(True, linestyle='--', alpha=0.15)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"图表已保存到: {save_path}")
    plt.close()


def plot_recent_comparison(index_df=None, year1=None, year2=None, save_path=None):
    if index_df is None:
        index_df = build_price_index()

    years = sorted(index_df['Year'].unique())
    if len(years) < 2:
        return

    year2 = year2 if year2 is not None else years[-1]
    year1 = year1 if year1 is not None else years[-2]

    data_year1 = index_df[index_df['Year'] == year1].copy()
    data_year2 = index_df[index_df['Year'] == year2].copy()

    plt.figure(figsize=(12, 6))

    x_year1 = _period_to_x(data_year1['Month'], data_year1['Period'])
    x_year2 = _period_to_x(data_year2['Month'], data_year2['Period'])

    plt.plot(x_year1, data_year1['PriceIndex'], marker='o', markersize=6, color='#ff7f0e', linewidth=1.5, linestyle='--', label=str(year1))
    plt.plot(x_year2, data_year2['PriceIndex'], marker='o', markersize=8, color='#1f77b4', linewidth=2, label=str(year2))

    plt.xticks(np.arange(1, 13, 1), MONTH_LABELS)
    plt.title(f'China High Frequency Producer Price Index ({year1}-{year2})', fontsize=12, pad=15)
    plt.xlabel('Month', fontsize=10)
    plt.ylabel('Price Index (2020.9=100)', fontsize=10)
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"图表已保存到: {save_path}")
    plt.close()


def generate_all_charts(index_df=None, output_dir='charts'):
    if index_df is None:
        index_df = build_price_index()

    os.makedirs(output_dir, exist_ok=True)

    print('开始生成图表...')
    plot_full_timeline(index_df, f'{output_dir}/timeline_full.png')
    plot_by_year(index_df, f'{output_dir}/by_year.png')
    plot_recent_comparison(index_df, save_path=f'{output_dir}/recent_comparison.png')
    print('所有图表生成完成！')


def render_readme(index_df, readme_path='README.md'):
    stats = _get_stats(index_df)
    generated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    year_min = int(index_df['Year'].min())
    year_max = int(index_df['Year'].max())
    latest_period_text = f"{stats['year']}年{stats['month']}月{_period_cn(stats['period'])}"

    mom_text = f"{stats['mom']:.2f}%" if stats['mom'] is not None else 'N/A'
    yoy_text = f"{stats['yoy']:.2f}%" if stats['yoy'] is not None else 'N/A'

    content = f"""# 达达物价指数

![最近两年对比图](charts/recent_comparison.png)

基于国家统计局《流通领域重要生产资料市场价格变动情况》构建的高频物价指数项目，基期设为 **2020 年 9 月中旬 = 100**，并处理 **2025 年 12 月下旬 → 2026 年 1 月上旬** 的口径变更衔接。

> English version: [README_EN.md](README_EN.md)

## 项目阐述

- 数据来源：国家统计局发布的旬度价格数据。
- 更新方式：增量抓取 + SQLite 持久化，避免重复抓取历史数据。
- 存储文件：`data/price_data.db`。
- 脚本目录：`scripts/`（使用 `01/02/...` 编号管理）。

## 更新日志

- {generated_at}：执行脚本后自动重建 README（图表与最新统计同步更新）。

## 最新统计指标

```text
最新数据：{latest_period_text}
价格指数：{stats['index']:.2f}
环比增长：{mom_text}
同比增长：{yoy_text}
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

当前时间序列覆盖：**{year_min} 年 - {year_max} 年**。
"""

    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f'README 已更新: {readme_path}')


def show_latest_stats(index_df=None):
    if index_df is None:
        index_df = build_price_index()

    if index_df.empty:
        print('没有数据可显示')
        return

    stats = _get_stats(index_df)
    print(f"\n最新数据：{stats['year']}年{stats['month']}月第{stats['period']}旬")
    print(f"价格指数：{stats['index']:.2f}")
    if stats['mom'] is not None:
        print(f"环比增长：{stats['mom']:.2f}%")
    if stats['yoy'] is not None:
        print(f"同比增长：{stats['yoy']:.2f}%")
    print()


if __name__ == '__main__':
    df = build_price_index()
    if not df.empty:
        show_latest_stats(df)
        generate_all_charts(df)
        render_readme(df)
    else:
        print('没有数据可处理')
