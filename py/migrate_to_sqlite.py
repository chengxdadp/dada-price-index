#!/usr/bin/env python3
"""
Pickle 到 SQLite 迁移脚本

将现有的 pickle 文件数据迁移到 SQLite 数据库。
"""

import os
import sys
import pandas as pd

# 添加当前目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, current_dir)

from db_manager import DatabaseManager


def migrate_all(db_path=None):
    """
    执行完整的数据迁移

    参数:
        db_path: 目标数据库路径，默认为项目根目录下的 data/price_data.db
    """
    print("=" * 60)
    print("Pickle to SQLite 数据迁移")
    print("=" * 60)

    # 切换到数据目录
    os.chdir(parent_dir)

    # 检查 pickle 文件
    pkl_files = {
        'links': 'df_all_links.pkl',
        'prices': 'price_table.pkl',
        'index': 'price_index.pkl'
    }

    missing_files = []
    for name, path in pkl_files.items():
        if not os.path.exists(path):
            missing_files.append(path)

    if missing_files:
        print(f"警告：以下文件不存在，将跳过：")
        for f in missing_files:
            print(f"  - {f}")
        print()

    # 初始化数据库
    if db_path is None:
        db_path = os.path.join(parent_dir, 'data', 'price_data.db')

    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    print(f"目标数据库：{db_path}")

    # 如果数据库已存在，询问是否覆盖
    if os.path.exists(db_path):
        response = input("数据库已存在，是否覆盖？(y/N): ").strip().lower()
        if response != 'y':
            print("取消迁移")
            return False
        os.remove(db_path)
        print("已删除旧数据库")

    db = DatabaseManager(db_path)
    print("数据库已初始化")
    print()

    # 迁移链接数据
    if os.path.exists(pkl_files['links']):
        print("-" * 40)
        print("迁移链接数据...")
        try:
            df_links = pd.read_pickle(pkl_files['links'])
            count = db.migrate_links_from_dataframe(df_links)
            print(f"  原始记录数：{len(df_links)}")
            print(f"  成功迁移：{count}")
        except Exception as e:
            print(f"  错误：{e}")
    else:
        print("跳过链接数据（文件不存在）")
    print()

    # 迁移价格数据
    if os.path.exists(pkl_files['prices']):
        print("-" * 40)
        print("迁移价格数据...")
        try:
            df_prices = pd.read_pickle(pkl_files['prices'])
            count = db.migrate_prices_from_dataframe(df_prices)
            print(f"  原始期次数：{len(df_prices)}")
            print(f"  成功迁移：{count}")
        except Exception as e:
            print(f"  错误：{e}")
    else:
        print("跳过价格数据（文件不存在）")
    print()

    # 迁移指数数据
    if os.path.exists(pkl_files['index']):
        print("-" * 40)
        print("迁移指数数据...")
        try:
            df_index = pd.read_pickle(pkl_files['index'])
            count = db.migrate_index_from_dataframe(df_index)
            print(f"  原始记录数：{len(df_index)}")
            print(f"  成功迁移：{count}")
        except Exception as e:
            print(f"  错误：{e}")
    else:
        print("跳过指数数据（文件不存在）")
    print()

    # 显示统计信息
    print("-" * 40)
    print("迁移完成，数据库统计：")
    stats = db.get_statistics()
    print(f"  链接记录数：{stats['links_count']}")
    print(f"  期次记录数：{stats['periods_count']}")
    print(f"  价格明细数：{stats['price_items_count']}")
    print(f"  指数记录数：{stats['index_count']}")
    if 'latest_link' in stats:
        print(f"  最新链接：{stats['latest_link']}")
    if 'latest_index' in stats:
        print(f"  最新指数：{stats['latest_index']}")
    print()

    # 验证数据完整性
    print("-" * 40)
    print("验证数据完整性...")
    errors = verify_migration(db, pkl_files)
    if errors:
        print("发现以下问题：")
        for err in errors:
            print(f"  - {err}")
    else:
        print("数据验证通过！")
    print()

    print("=" * 60)
    print("迁移完成！")
    print(f"数据库文件：{db_path}")
    print("=" * 60)

    db.close()
    return True


def verify_migration(db, pkl_files):
    """验证迁移后的数据完整性"""
    errors = []

    # 验证链接数据
    if os.path.exists(pkl_files['links']):
        df_links = pd.read_pickle(pkl_files['links'])
        db_links = db.get_all_links()
        if len(df_links) != len(db_links):
            errors.append(f"链接数不匹配：pickle={len(df_links)}, sqlite={len(db_links)}")

    # 验证价格数据
    if os.path.exists(pkl_files['prices']):
        df_prices = pd.read_pickle(pkl_files['prices'])
        db_periods = db.get_all_periods()
        if len(df_prices) != len(db_periods):
            errors.append(f"期次数不匹配：pickle={len(df_prices)}, sqlite={len(db_periods)}")

    # 验证指数数据
    if os.path.exists(pkl_files['index']):
        df_index = pd.read_pickle(pkl_files['index'])
        db_index = db.get_index_series()
        if len(df_index) != len(db_index):
            errors.append(f"指数数不匹配：pickle={len(df_index)}, sqlite={len(db_index)}")

        # 抽样验证指数值
        if not df_index.empty and not db_index.empty:
            # 验证第一条
            first_pkl = df_index.iloc[0]
            first_db = db_index.iloc[0]
            if abs(first_pkl['PriceIndex'] - first_db['PriceIndex']) > 0.0001:
                errors.append(f"首条指数值不匹配：pickle={first_pkl['PriceIndex']}, sqlite={first_db['PriceIndex']}")

            # 验证最后一条
            last_pkl = df_index.iloc[-1]
            last_db = db_index.iloc[-1]
            if abs(last_pkl['PriceIndex'] - last_db['PriceIndex']) > 0.0001:
                errors.append(f"末条指数值不匹配：pickle={last_pkl['PriceIndex']}, sqlite={last_db['PriceIndex']}")

    return errors


def show_current_status():
    """显示当前数据库状态"""
    db_path = os.path.join(parent_dir, 'data', 'price_data.db')

    if not os.path.exists(db_path):
        print("数据库不存在，请先运行迁移")
        return

    db = DatabaseManager(db_path)
    stats = db.get_statistics()

    print("=" * 40)
    print("当前数据库状态")
    print("=" * 40)
    print(f"链接记录数：{stats['links_count']}")
    print(f"期次记录数：{stats['periods_count']}")
    print(f"价格明细数：{stats['price_items_count']}")
    print(f"指数记录数：{stats['index_count']}")
    if 'latest_link' in stats:
        print(f"最新链接：{stats['latest_link']}")
    if 'latest_index' in stats:
        print(f"最新指数：{stats['latest_index']}")

    db.close()


def main():
    """主函数"""
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg == '--status':
            show_current_status()
            return 0
        elif arg == '--help':
            print("""
Pickle to SQLite 迁移脚本

用法：
  python migrate_to_sqlite.py           执行迁移
  python migrate_to_sqlite.py --status  查看当前数据库状态
  python migrate_to_sqlite.py --help    显示帮助信息

说明：
  此脚本将现有的 pickle 文件数据迁移到 SQLite 数据库。
  迁移完成后，系统将使用 SQLite 进行数据存储。

  源文件：
    - df_all_links.pkl  -> period_links 表
    - price_table.pkl   -> periods + price_items 表
    - price_index.pkl   -> price_index 表

  目标文件：
    - data/price_data.db (SQLite 数据库)
""")
            return 0

    success = migrate_all()
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
