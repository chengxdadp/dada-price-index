#!/usr/bin/env python3
"""
主更新脚本
运行此脚本更新数据并生成最新图表
"""

import os
import sys
from datetime import datetime

# 添加当前目录到路径以便导入模块
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
sys.path.insert(0, current_dir)

from data_utils import update_links, update_price_data
from index_builder import (
    build_price_index,
    build_price_index_full_with_chain,
    incremental_update,
    save_index_data,
    verify_incremental_vs_full,
    load_existing_index
)
from chart_maker import generate_all_charts, show_latest_stats
from db_manager import get_db, close_db


def main(full_mode=False):
    """
    主函数：完整的数据更新流程

    参数：
        full_mode: 是否使用全量重算模式（默认为增量更新）
    """
    print("=" * 50)
    print("中国生产资料价格指数更新程序")
    print("=" * 50)
    print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"更新模式：{'全量重算' if full_mode else '增量更新'}")
    print()

    try:
        # 切换到父目录
        os.chdir(parent_dir)

        # 步骤1：更新链接数据
        print("步骤1：更新链接数据...")
        print("-" * 30)
        update_links()
        print()

        # 步骤2：更新价格数据
        print("步骤2：更新价格数据...")
        print("-" * 30)
        update_price_data()
        print()

        # 步骤3：计算价格指数
        print("步骤3：计算价格指数...")
        print("-" * 30)

        if full_mode:
            # 全量重算模式
            print("使用全量重算模式（带口径变更链接）...")
            index_df = build_price_index_full_with_chain()
            if not index_df.empty:
                save_index_data(index_df)
        else:
            # 增量更新模式
            print("使用增量更新模式...")
            index_df, msg = incremental_update()
            if index_df is None:
                print(f"增量更新失败：{msg}")
                print("自动切换到全量重算模式...")
                index_df = build_price_index_full_with_chain()
                if not index_df.empty:
                    save_index_data(index_df)

        if index_df is not None and not index_df.empty:
            print()

            # 步骤4：显示最新统计信息
            print("步骤4：最新统计信息")
            print("-" * 30)
            show_latest_stats(index_df)

            # 步骤5：生成图表
            print("步骤5：生成图表...")
            print("-" * 30)
            generate_all_charts(index_df)

        else:
            print("警告：没有有效的指数数据")

        print("=" * 50)
        print("数据更新完成！")
        print(f"结束时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)

    except Exception as e:
        print(f"错误：程序执行失败 - {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        close_db()

    return 0


def quick_chart_update():
    """快速图表更新（仅重新生成图表，不更新数据）"""
    print("快速图表更新模式")
    print("-" * 30)

    try:
        os.chdir(parent_dir)

        # 从数据库读取现有数据
        index_df = load_existing_index()

        if index_df is not None and not index_df.empty:
            show_latest_stats(index_df)
            generate_all_charts(index_df)
            print("图表更新完成！")
        else:
            print("没有数据可处理")

    except Exception as e:
        print(f"错误：{e}")
        return 1
    finally:
        close_db()

    return 0


def run_verify():
    """运行验证测试"""
    print("运行增量更新与全量计算一致性验证...")
    print("-" * 30)

    try:
        os.chdir(parent_dir)
        result = verify_incremental_vs_full()
        return 0 if result else 1
    except Exception as e:
        print(f"验证失败：{e}")
        return 1
    finally:
        close_db()


def run_migrate():
    """运行数据迁移"""
    print("运行 Pickle 到 SQLite 数据迁移...")
    print("-" * 30)

    try:
        os.chdir(parent_dir)
        from migrate_to_sqlite import migrate_all
        success = migrate_all()
        return 0 if success else 1
    except Exception as e:
        print(f"迁移失败：{e}")
        import traceback
        traceback.print_exc()
        return 1


def show_status():
    """显示当前数据库状态"""
    try:
        os.chdir(parent_dir)
        db = get_db()
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

    except Exception as e:
        print(f"获取状态失败：{e}")
        return 1
    finally:
        close_db()

    return 0


def show_help():
    """显示帮助信息"""
    print("""
使用方法：
python update.py [选项]

选项：
  无参数      - 增量更新（默认模式，更新数据+生成图表）
  --full      - 全量重算模式（从基期开始重新计算整个历史序列）
  --chart     - 仅更新图表（不更新数据）
  --verify    - 验证增量更新与全量计算的一致性
  --migrate   - 从 pickle 文件迁移数据到 SQLite
  --status    - 显示当前数据库状态
  --help, -h  - 显示此帮助信息

示例：
  python update.py           # 增量更新（推荐日常使用）
  python update.py --full    # 全量重算（口径变更或数据修复时使用）
  python update.py --chart   # 仅更新图表
  python update.py --verify  # 运行一致性验证
  python update.py --migrate # 从 pickle 迁移数据
  python update.py --status  # 查看数据库状态

说明：
  - 数据存储在 SQLite 数据库中 (price_data.db)
  - 增量更新模式：读取已有指数序列，仅计算新增期数，效率更高
  - 全量重算模式：从基期开始重新计算，用于口径变更或数据修复
  - 2026年1月起统计局调整了监测品种，系统会自动处理口径变更
""")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ['--help', '-h']:
            show_help()
            sys.exit(0)
        elif arg == '--chart':
            sys.exit(quick_chart_update())
        elif arg == '--full':
            sys.exit(main(full_mode=True))
        elif arg == '--verify':
            sys.exit(run_verify())
        elif arg == '--migrate':
            sys.exit(run_migrate())
        elif arg == '--status':
            sys.exit(show_status())
        else:
            print(f"未知参数：{arg}")
            show_help()
            sys.exit(1)
    else:
        # 默认使用增量更新模式
        sys.exit(main(full_mode=False))
