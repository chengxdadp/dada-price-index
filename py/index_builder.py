#!/usr/bin/env python3
"""
价格指数计算模块

计算物价指数，支持增量更新和口径变更链接。
"""

import pandas as pd
import os
import argparse

from db_manager import get_db


# ============ 口径变更配置 ============
# 链接点：2025年12月下旬
LINK_POINT = (2025, 12, 3)  # (年, 月, 旬)

# 新基期：2026年1月上旬
NEW_BASE_POINT = (2026, 1, 1)

# 2026年1月起删除的产品
REMOVED_PRODUCTS_2026 = [
    '苯乙烯（一级品）',
    '聚氯乙烯（SG5）',
    '汽油（92#国VI）',
    '普通混煤（4500大卡）',
    '山西大混（5000大卡）',
    '大同混煤（5800大卡）',
    '普通硅酸盐水泥（P.O 42.5袋装）',
]

# 2026年1月起新增的产品
NEW_PRODUCTS_2026 = [
    '乙醇（95.0%）',
    '冰醋酸（99.5%及以上）',
    '磷酸铁锂（普通动力型）',
    '多晶硅（致密料）',
    '白糖（国标一级白砂糖）',
    '磷肥（55%磷酸一铵）',
    '钾肥（港口62%白色氯化钾）',
]

# 规格变更：浮法平板玻璃从4.8/5mm调整为5/6mm
SPEC_CHANGES_2026 = {
    '浮法平板玻璃': {'old': '4.8/5mm', 'new': '5/6mm'}
}


def period_to_tuple(year, month, period):
    """将年月旬转换为可比较的元组"""
    return (year, month, period)


def is_after_link_point(year, month, period):
    """判断是否在口径变更点之后"""
    return period_to_tuple(year, month, period) > LINK_POINT


def get_next_period(year, month, period):
    """获取下一期的年月旬"""
    if period < 3:
        return year, month, period + 1
    elif month < 12:
        return year, month + 1, 1
    else:
        return year + 1, 1, 1


def get_prev_period(year, month, period):
    """获取上一期的年月旬"""
    if period > 1:
        return year, month, period - 1
    elif month > 1:
        return year, month - 1, 3
    else:
        return year - 1, 12, 3


def build_price_index(base_year=2020, base_month=9, base_period=2):
    """
    计算物价指数（全量模式，简化版）
    以2020年9月中旬为基期100

    从SQLite数据库读取数据。
    """
    db = get_db()

    # 获取所有期次
    periods_df = db.get_all_periods()
    if periods_df.empty:
        print("没有价格数据")
        return pd.DataFrame()

    # 获取基期价格
    base_prices = db.get_price_data_for_period(base_year, base_month, base_period)
    if not base_prices:
        print(f"基期{base_year}年{base_month}月第{base_period}旬的价格数据不存在")
        return pd.DataFrame()

    valid_goods = set(base_prices.keys())

    # 计算各期指数
    results = []
    for _, row in periods_df.iterrows():
        year, month, period = int(row['Year']), int(row['Month']), int(row['Period'])

        current_prices = db.get_price_data_for_period(year, month, period)
        if not current_prices:
            continue

        # 只计算有基期价格的商品
        common_goods = set(current_prices.keys()) & valid_goods

        if common_goods:
            rel_indices = []
            for good in common_goods:
                rel_idx = current_prices[good] / base_prices[good] * 100
                rel_indices.append(rel_idx)
            avg_index = sum(rel_indices) / len(rel_indices)

            results.append({
                'Year': year,
                'Month': month,
                'Period': period,
                'PriceIndex': avg_index
            })

    if results:
        index_df = pd.DataFrame(results)
        index_df = index_df.sort_values(['Year', 'Month', 'Period']).reset_index(drop=True)
        return index_df

    return pd.DataFrame()


def build_price_index_full_with_chain(base_year=2020, base_month=9, base_period=2):
    """
    全量计算物价指数（带口径变更链接）

    处理逻辑：
    1. 链接点及之前：使用原基期(2020年9月中旬)，价格/基期价格*100
    2. 2026年1月上旬（第一期）：用环比涨跌幅从链接点桥接，计算该期指数
    3. 2026年1月上旬之后：以2026年1月上旬为新基期(=100)计算相对指数，
       再乘以缩放因子(2026年1月上旬的长序列指数值)衔接到长序列
    """
    db = get_db()

    # 获取所有期次
    periods_df = db.get_all_periods()
    if periods_df.empty:
        print("没有价格数据")
        return pd.DataFrame()

    # 按时间排序
    periods_df = periods_df.sort_values(['Year', 'Month', 'Period'])

    # 获取原基期价格
    old_base_prices = db.get_price_data_for_period(base_year, base_month, base_period)
    if not old_base_prices:
        print(f"基期{base_year}年{base_month}月第{base_period}旬的价格数据不存在")
        return pd.DataFrame()

    results = []
    link_point_index_value = 100.0
    new_base_prices = None
    new_base_index_value = None

    for _, row in periods_df.iterrows():
        year, month, period = int(row['Year']), int(row['Month']), int(row['Period'])

        current_prices = db.get_price_data_for_period(year, month, period)
        if not current_prices:
            continue

        if not is_after_link_point(year, month, period):
            # ===== 链接点及之前：使用原基期 =====
            common_goods = set(current_prices.keys()) & set(old_base_prices.keys())

            if common_goods:
                rel_indices = []
                for good in common_goods:
                    rel_idx = current_prices[good] / old_base_prices[good] * 100
                    rel_indices.append(rel_idx)
                avg_index = sum(rel_indices) / len(rel_indices)

                results.append({
                    'Year': year,
                    'Month': month,
                    'Period': period,
                    'PriceIndex': avg_index,
                    'ChainBase': 'original'
                })

                # 记录链接点的指数值
                if (year, month, period) == LINK_POINT:
                    link_point_index_value = avg_index

        elif (year, month, period) == NEW_BASE_POINT:
            # ===== 2026年1月上旬：用环比涨跌幅从链接点桥接 =====
            pct_changes = db.get_pct_changes_for_period(year, month, period)

            # 过滤掉被删除的产品
            valid_pct = [p['pct'] for p in pct_changes if p['good'] not in REMOVED_PRODUCTS_2026]

            if valid_pct:
                avg_pct_change = sum(valid_pct) / len(valid_pct)
                new_base_index_value = link_point_index_value * (1 + avg_pct_change / 100)
            else:
                new_base_index_value = link_point_index_value

            new_base_prices = current_prices

            results.append({
                'Year': year,
                'Month': month,
                'Period': period,
                'PriceIndex': new_base_index_value,
                'ChainBase': 'chained_2026'
            })

        else:
            # ===== 2026年1月上旬之后：以新基期价格计算相对指数 =====
            if new_base_prices is None or new_base_index_value is None:
                continue

            common_goods = set(current_prices.keys()) & set(new_base_prices.keys())

            if common_goods:
                rel_indices = []
                for good in common_goods:
                    rel_idx = current_prices[good] / new_base_prices[good] * 100
                    rel_indices.append(rel_idx)
                avg_rel_index = sum(rel_indices) / len(rel_indices)

                # 长序列指数 = 相对指数 / 100 * 缩放因子
                long_index = avg_rel_index / 100 * new_base_index_value

                results.append({
                    'Year': year,
                    'Month': month,
                    'Period': period,
                    'PriceIndex': long_index,
                    'ChainBase': 'chained_2026'
                })

    if results:
        index_df = pd.DataFrame(results)
        index_df = index_df.sort_values(['Year', 'Month', 'Period']).reset_index(drop=True)
        return index_df

    return pd.DataFrame()


def load_existing_index():
    """加载已有的指数序列（从SQLite）"""
    db = get_db()
    df = db.get_index_series()
    if not df.empty:
        return df
    return None


def get_last_period(index_df):
    """获取指数序列的最后一期"""
    if index_df is None or index_df.empty:
        return None
    last_row = index_df.iloc[-1]
    return {
        'year': int(last_row['Year']),
        'month': int(last_row['Month']),
        'period': int(last_row['Period']),
        'index': float(last_row['PriceIndex']),
        'chain_base': last_row.get('ChainBase', 'original')
    }


def incremental_update(base_year=2020, base_month=9, base_period=2):
    """
    增量更新指数序列

    逻辑：
    1. 读取已有指数序列，获取最后一期
    2. 从数据库中获取新增期数
    3. 根据期次位置选择计算方式：
       - 2025年12月下旬及之前：用价格相对于2020年9月中旬基期计算
       - 2026年1月上旬：用环比涨跌幅从链接点桥接
       - 2026年1月上旬之后：用价格相对于2026年1月上旬新基期计算，再乘以缩放因子
    4. 追加写入数据库
    """
    db = get_db()

    # 加载已有指数序列
    existing_index = load_existing_index()

    if existing_index is None or existing_index.empty:
        print("提示：没有已有的指数序列，将执行全量计算")
        full_index = build_price_index_full_with_chain(base_year, base_month, base_period)
        if not full_index.empty:
            # 保存到数据库
            for _, row in full_index.iterrows():
                db.upsert_index(
                    int(row['Year']), int(row['Month']), int(row['Period']),
                    float(row['PriceIndex']),
                    row.get('ChainBase', 'original')
                )
        return full_index, "执行全量计算"

    last_period_info = get_last_period(existing_index)
    if last_period_info is None:
        print("提示：无法获取最后一期信息，将执行全量计算")
        return build_price_index_full_with_chain(base_year, base_month, base_period), "执行全量计算"

    last_year = last_period_info['year']
    last_month = last_period_info['month']
    last_period = last_period_info['period']
    last_index = last_period_info['index']

    print(f"已有序列最后一期：{last_year}年{last_month}月第{last_period}旬，指数值：{last_index:.2f}")

    # 获取新增期数
    new_periods = db.get_periods_after(last_year, last_month, last_period)

    if new_periods.empty:
        print("没有新数据需要更新")
        return existing_index, "无新数据"

    # 检查序列连续性
    expected_year, expected_month, expected_period = get_next_period(last_year, last_month, last_period)
    first_new = new_periods.iloc[0]

    if (int(first_new['Year']), int(first_new['Month']), int(first_new['Period'])) != (expected_year, expected_month, expected_period):
        print(f"警告：序列不连续！预期下一期为{expected_year}年{expected_month}月第{expected_period}旬，")
        print(f"但新数据起始于{first_new['Year']}年{first_new['Month']}月第{first_new['Period']}旬")
        print("建议运行全量重算：python update.py --full")
        return None, "序列不连续"

    # 获取原基期价格
    old_base_prices = db.get_price_data_for_period(base_year, base_month, base_period)
    if not old_base_prices:
        print("错误：无法获取基期价格数据")
        return None, "基期数据不存在"

    # 尝试获取新基期信息
    new_base_prices = None
    new_base_index_value = None

    # 检查已有序列中是否已包含新基期
    new_base_info = db.get_index(NEW_BASE_POINT[0], NEW_BASE_POINT[1], NEW_BASE_POINT[2])
    if new_base_info:
        new_base_index_value = new_base_info['PriceIndex']
        new_base_prices = db.get_price_data_for_period(NEW_BASE_POINT[0], NEW_BASE_POINT[1], NEW_BASE_POINT[2])

    # 逐期计算并追加
    new_rows = []
    current_index = last_index

    for _, period_row in new_periods.iterrows():
        year = int(period_row['Year'])
        month = int(period_row['Month'])
        period = int(period_row['Period'])

        # 判断期次位置
        after_link = is_after_link_point(year, month, period)
        is_new_base = (year, month, period) == NEW_BASE_POINT
        after_new_base = period_to_tuple(year, month, period) > NEW_BASE_POINT

        current_prices = db.get_price_data_for_period(year, month, period)
        if not current_prices:
            print(f"警告：{year}年{month}月第{period}旬没有价格数据，跳过")
            continue

        if not after_link:
            # ===== 2025年12月下旬及之前：使用价格相对于原基期计算 =====
            common_goods = set(current_prices.keys()) & set(old_base_prices.keys())

            if not common_goods:
                print(f"错误：{year}年{month}月第{period}旬没有共同商品")
                return None, "无共同商品"

            rel_indices = []
            for good in common_goods:
                rel_idx = current_prices[good] / old_base_prices[good] * 100
                rel_indices.append(rel_idx)
            new_index = sum(rel_indices) / len(rel_indices)
            chain_base = 'original'
            print(f"  {year}年{month}月第{period}旬：指数{new_index:.2f} [原基期计算]")

        elif is_new_base:
            # ===== 2026年1月上旬：用环比涨跌幅从链接点桥接 =====
            print(f"检测到口径变更点：{year}年{month}月第{period}旬")
            print("口径变更说明：")
            print(f"  - 删除产品：{', '.join(REMOVED_PRODUCTS_2026)}")
            print(f"  - 新增产品：{', '.join(NEW_PRODUCTS_2026)}")
            print(f"  - 链接点指数值：{current_index:.2f}")

            pct_changes = db.get_pct_changes_for_period(year, month, period)
            valid_pct = [p['pct'] for p in pct_changes if p['good'] not in REMOVED_PRODUCTS_2026]

            if not valid_pct:
                print(f"错误：无法获取{year}年{month}月第{period}旬的环比涨跌幅")
                return None, "获取环比失败"

            avg_pct_change = sum(valid_pct) / len(valid_pct)
            new_index = current_index * (1 + avg_pct_change / 100)
            chain_base = 'chained_2026'

            # 保存新基期信息
            new_base_index_value = new_index
            new_base_prices = current_prices

            print(f"  {year}年{month}月第{period}旬：环比{avg_pct_change:+.2f}%，指数{new_index:.2f} [环比桥接]")
            print(f"  新基期指数值（缩放因子）：{new_base_index_value:.2f}")

        elif after_new_base:
            # ===== 2026年1月上旬之后：用价格相对于新基期计算 =====
            if new_base_prices is None or new_base_index_value is None:
                print(f"错误：新基期数据不存在，无法计算{year}年{month}月第{period}旬")
                return None, "新基期数据不存在"

            common_goods = set(current_prices.keys()) & set(new_base_prices.keys())

            if not common_goods:
                print(f"错误：{year}年{month}月第{period}旬与新基期没有共同商品")
                return None, "无共同商品"

            rel_indices = []
            for good in common_goods:
                rel_idx = current_prices[good] / new_base_prices[good] * 100
                rel_indices.append(rel_idx)
            avg_rel_index = sum(rel_indices) / len(rel_indices)

            # 长序列指数 = 相对指数 / 100 * 缩放因子
            new_index = avg_rel_index / 100 * new_base_index_value
            chain_base = 'chained_2026'
            print(f"  {year}年{month}月第{period}旬：相对指数{avg_rel_index:.2f}，长序列指数{new_index:.2f} [新基期计算]")

        else:
            print(f"错误：未知的期次位置 {year}年{month}月第{period}旬")
            return None, "未知期次位置"

        # 直接写入数据库
        db.upsert_index(year, month, period, new_index, chain_base)

        new_rows.append({
            'Year': year,
            'Month': month,
            'Period': period,
            'PriceIndex': new_index,
            'ChainBase': chain_base
        })

        current_index = new_index

    if new_rows:
        print(f"增量更新完成，新增{len(new_rows)}期数据")
        # 返回更新后的完整序列
        return db.get_index_series(), "增量更新成功"

    return existing_index, "无新数据"


def get_latest_index_value(index_df=None):
    """获取最新的指数值"""
    if index_df is None:
        db = get_db()
        latest = db.get_latest_index()
        if latest:
            return {
                'year': latest['Year'],
                'month': latest['Month'],
                'period': latest['Period'],
                'index': latest['PriceIndex']
            }
        return None

    if not index_df.empty:
        latest = index_df.iloc[-1]
        return {
            'year': latest['Year'],
            'month': latest['Month'],
            'period': latest['Period'],
            'index': latest['PriceIndex']
        }
    return None


def calculate_growth_rate(index_df=None, periods_back=1):
    """计算指数增长率"""
    if index_df is None:
        index_df = load_existing_index()

    if index_df is None or len(index_df) < periods_back + 1:
        return None

    current = index_df.iloc[-1]['PriceIndex']
    previous = index_df.iloc[-(periods_back + 1)]['PriceIndex']

    growth_rate = (current - previous) / previous * 100
    return growth_rate


def get_year_data(index_df=None, year=2025):
    """获取指定年份的数据"""
    if index_df is None:
        index_df = load_existing_index()

    if index_df is None:
        return pd.DataFrame()

    year_data = index_df[index_df['Year'] == year]
    return year_data


def save_index_data(index_df):
    """保存指数数据到数据库"""
    db = get_db()
    count = 0
    for _, row in index_df.iterrows():
        db.upsert_index(
            int(row['Year']), int(row['Month']), int(row['Period']),
            float(row['PriceIndex']),
            row.get('ChainBase', 'original')
        )
        count += 1
    print(f"指数数据已保存到数据库，共{count}条记录")


def load_index_data():
    """加载指数数据"""
    db = get_db()
    df = db.get_index_series()
    if df.empty:
        print("数据库中没有指数数据")
    return df


def verify_incremental_vs_full():
    """
    验证增量更新与全量计算的一致性
    """
    print("=" * 50)
    print("验证增量更新与全量计算的一致性")
    print("=" * 50)

    db = get_db()

    # 检查是否有数据
    periods = db.get_all_periods()
    if periods.empty:
        print("没有价格数据")
        return False

    # 全量计算
    print("\n1. 执行全量计算...")
    full_index = build_price_index_full_with_chain()

    if full_index.empty:
        print("全量计算失败")
        return False

    # 获取数据库中的指数序列
    print("\n2. 获取数据库中的指数序列...")
    db_index = db.get_index_series()

    if db_index.empty:
        print("数据库中没有指数数据，跳过对比")
        return True

    # 对比结果
    print("\n3. 对比结果...")

    compare_count = min(5, len(full_index), len(db_index))

    print(f"\n最后{compare_count}期对比：")
    print(f"{'期次':<20} {'全量计算':<15} {'数据库值':<15} {'差异':<10}")
    print("-" * 60)

    all_match = True
    full_last = full_index.tail(compare_count)
    db_last = db_index.tail(compare_count)

    for i in range(compare_count):
        full_row = full_last.iloc[i]
        db_row = db_last.iloc[i]

        period_str = f"{int(full_row['Year'])}年{int(full_row['Month'])}月第{int(full_row['Period'])}旬"
        full_val = full_row['PriceIndex']
        db_val = db_row['PriceIndex']
        diff = abs(full_val - db_val)

        match_str = "OK" if diff < 0.01 else "X"
        print(f"{period_str:<20} {full_val:<15.4f} {db_val:<15.4f} {diff:<10.4f} {match_str}")

        if diff >= 0.01:
            all_match = False

    print()
    if all_match:
        print("验证通过：数据库中的指数与全量计算结果一致")
    else:
        print("验证失败：存在差异，请检查数据")

    return all_match


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description='高频物价指数计算工具')
    parser.add_argument('--full', action='store_true', help='执行全量重算（默认为增量更新）')
    parser.add_argument('--verify', action='store_true', help='验证增量更新与全量计算的一致性')

    args = parser.parse_args()

    if args.verify:
        verify_incremental_vs_full()
        return

    if args.full:
        print("执行全量重算模式...")
        index_df = build_price_index_full_with_chain()
        if not index_df.empty:
            save_index_data(index_df)
    else:
        print("执行增量更新模式...")
        index_df, msg = incremental_update()
        if index_df is None:
            print(f"增量更新失败：{msg}")
            print("建议使用 --full 参数执行全量重算")
            return

    if index_df is not None and not index_df.empty:
        latest = get_latest_index_value(index_df)
        if latest:
            print(f"\n最新指数：{latest['year']}年{latest['month']}月第{latest['period']}旬 = {latest['index']:.2f}")


if __name__ == '__main__':
    main()
