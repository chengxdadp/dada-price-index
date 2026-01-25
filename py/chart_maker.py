import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from index_builder import build_price_index
import matplotlib

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号


def plot_full_timeline(index_df=None, save_path=None):
    """绘制完整时间序列图"""
    if index_df is None:
        index_df = build_price_index()
    
    plt.figure(figsize=(15, 6))
    
    # 绘制线图
    plt.plot(range(len(index_df)), index_df['PriceIndex'], marker='o', markersize=3)
    
    # 自定义x轴标签
    x_ticks = []
    x_labels = []
    prev_year = None
    shown_months = set()
    
    for idx, (year, month, period) in enumerate(zip(index_df['Year'], index_df['Month'], index_df['Period'])):
        if year != prev_year:
            shown_months = set()
        
        if (year != prev_year or (month % 3 == 0 and month not in shown_months)):
            x_ticks.append(idx)
            if year != prev_year:
                x_labels.append(f'{year}-{month}')
                prev_year = year
            else:
                x_labels.append(f'{month}')
            shown_months.add(month)
    
    plt.xticks(x_ticks, x_labels, rotation=45, ha='right')
    
    # 添加标签和标题
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
    """按年份分组绘制图表"""
    if index_df is None:
        index_df = build_price_index()
    
    plt.figure(figsize=(15, 6))
    
    colors = [
        '#1f77b4',  # 蓝色
        "#0effe3",  # 青色
        '#2ca02c',  # 绿色
        '#8c564b',  # 棕色
        '#9467bd',  # 紫色
        '#d62728',  # 红色
    ]
    
    years = sorted(index_df['Year'].unique())
    n_years = len(years)
    
    # 绘制所有年份（除了最新一年）
    for year, color in zip(years[:-1], colors[:-1]):
        year_data = index_df[index_df['Year'] == year]
        x = year_data['Month'] + (year_data['Period'] - 1) * 0.33
        plt.plot(x, year_data['PriceIndex'], 
                 marker='o', markersize=3, 
                 color=color, 
                 label=str(year),
                 linewidth=1.5,
                 alpha=0.6)
    
    # 突出显示最新年份
    latest_year = years[-1]
    latest_data = index_df[index_df['Year'] == latest_year]
    x = latest_data['Month'] + (latest_data['Period'] - 1) * 0.33
    plt.plot(x, latest_data['PriceIndex'], 
             marker='o', markersize=4, 
             color=colors[-1],
             label=str(latest_year),
             linewidth=3,
             zorder=5)
    
    plt.xticks(range(1, 13), 
               ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
               rotation=0)
    
    plt.xlabel('Month')
    plt.ylabel('Price Index (2020.9=100)')
    plt.title('China Producer Price Index by Year')
    plt.legend(title='Year', bbox_to_anchor=(1.02, 1), 
              loc='upper left', borderaxespad=0)
    plt.grid(True, linestyle='--', alpha=0.15)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"图表已保存到: {save_path}")
    
    plt.close()


def plot_recent_comparison(index_df=None, year1=None, year2=None, save_path=None):
    """绘制最近两年的对比图"""
    if index_df is None:
        index_df = build_price_index()
    years = sorted(index_df['Year'].unique())
    if year2 is None:
        year2 = years[-1]
    if year1 is None:
        year1 = years[-2]
    
    
    # 筛选数据
    data_year1 = index_df[index_df['Year'] == year1].copy()
    data_year2 = index_df[index_df['Year'] == year2].copy()
    
    plt.figure(figsize=(12, 6))
    
    # 生成x轴位置
    x_year1 = data_year1['Month'] + (data_year1['Period'] - 1) * 0.33
    x_year2 = data_year2['Month'] + (data_year2['Period'] - 1) * 0.33
    
    # 绘制数据线
    plt.plot(x_year1, data_year1['PriceIndex'], 
             marker='o', markersize=6,
             color='#ff7f0e',  # 橙色
             linewidth=1.5,
             linestyle='--',
             label=str(year1))
    
    plt.plot(x_year2, data_year2['PriceIndex'], 
             marker='o', markersize=8,
             color='#1f77b4',  # 蓝色
             linewidth=2,
             label=str(year2))
    
    # 设置x轴
    x_ticks = np.arange(1, 13, 1)
    plt.xticks(x_ticks, 
               ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])
    
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
    """生成所有图表并保存"""
    import os
    
    if index_df is None:
        index_df = build_price_index()
    
    # 创建输出目录
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    print("开始生成图表...")
    
    # 完整时间序列图
    plot_full_timeline(index_df, f'{output_dir}/timeline_full.png')
    
    # 按年分组图
    plot_by_year(index_df, f'{output_dir}/by_year.png')
    
    # 最近两年对比图
    plot_recent_comparison(index_df, save_path=f'{output_dir}/recent_comparison.png')
    
    print("所有图表生成完成！")


def show_latest_stats(index_df=None):
    """显示最新统计信息"""
    if index_df is None:
        index_df = build_price_index()
    
    if index_df.empty:
        print("没有数据可显示")
        return
    
    latest = index_df.iloc[-1]
    print(f"\n最新数据：{latest['Year']}年{latest['Month']}月第{latest['Period']}旬")
    print(f"价格指数：{latest['PriceIndex']:.2f}")
    
    # 计算环比增长
    if len(index_df) > 1:
        previous = index_df.iloc[-2]['PriceIndex']
        growth = (latest['PriceIndex'] - previous) / previous * 100
        print(f"环比增长：{growth:.2f}%")
    
    # 计算同比增长（如果有去年同期数据）
    last_year = latest['Year'] - 1
    same_period_last_year = index_df[
        (index_df['Year'] == last_year) & 
        (index_df['Month'] == latest['Month']) & 
        (index_df['Period'] == latest['Period'])
    ]
    
    if not same_period_last_year.empty:
        last_year_value = same_period_last_year.iloc[0]['PriceIndex']
        yoy_growth = (latest['PriceIndex'] - last_year_value) / last_year_value * 100
        print(f"同比增长：{yoy_growth:.2f}%")
    
    print()


if __name__ == "__main__":
    # 构建指数
    index_df = build_price_index()
    
    if not index_df.empty:
        # 显示统计信息
        show_latest_stats(index_df)
        
        # 生成图表
        generate_all_charts(index_df)
    else:
        print("没有数据可处理")