#!/usr/bin/env python3
"""主更新脚本。"""

import os
import sys
from datetime import datetime

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, current_dir)
sys.path.insert(0, parent_dir)

from _loader import load_local_module

mod_data = load_local_module('02_data_utils.py', 'dada_data_utils')
mod_index = load_local_module('04_index_builder.py', 'dada_index_builder')
mod_chart = load_local_module('05_chart_maker.py', 'dada_chart_maker')
mod_db = load_local_module('03_db_manager.py', 'dada_db_manager')

update_links = mod_data.update_links
update_price_data = mod_data.update_price_data
build_price_index_full_with_chain = mod_index.build_price_index_full_with_chain
incremental_update = mod_index.incremental_update
save_index_data = mod_index.save_index_data
verify_incremental_vs_full = mod_index.verify_incremental_vs_full
load_existing_index = mod_index.load_existing_index

generate_all_charts = mod_chart.generate_all_charts
show_latest_stats = mod_chart.show_latest_stats
render_readme = mod_chart.render_readme

get_db = mod_db.get_db
close_db = mod_db.close_db


def main(full_mode=False, offline=False):
    print('=' * 50)
    print('中国生产资料价格指数更新程序')
    print('=' * 50)
    print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"更新模式：{'离线模式' if offline else ('全量重算' if full_mode else '增量更新')}")
    print()

    try:
        os.chdir(parent_dir)

        if not offline:
            print('步骤1：更新链接数据...')
            print('-' * 30)
            update_links()
            print()

            print('步骤2：更新价格数据...')
            print('-' * 30)
            update_price_data()
            print()
        else:
            print('步骤1/2：离线模式，跳过联网抓取（仅使用本地 SQLite 数据）')
            print('-' * 30)
            print()

        print('步骤3：计算价格指数...')
        print('-' * 30)

        if full_mode:
            print('使用全量重算模式（带口径变更链接）...')
            index_df = build_price_index_full_with_chain()
            if not index_df.empty:
                save_index_data(index_df)
        else:
            print('使用增量更新模式...')
            index_df, msg = incremental_update()
            if index_df is None:
                print(f'增量更新失败：{msg}')
                print('自动切换到全量重算模式...')
                index_df = build_price_index_full_with_chain()
                if not index_df.empty:
                    save_index_data(index_df)

        if index_df is not None and not index_df.empty:
            print()
            print('步骤4：最新统计信息')
            print('-' * 30)
            show_latest_stats(index_df)

            print('步骤5：生成图表...')
            print('-' * 30)
            generate_all_charts(index_df)

            print('步骤6：更新 README...')
            print('-' * 30)
            render_readme(index_df)
        else:
            print('警告：没有有效的指数数据')

        print('=' * 50)
        print('数据更新完成！')
        print(f"结束时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print('=' * 50)

    except Exception as e:
        print(f'错误：程序执行失败 - {e}')
        import traceback
        traceback.print_exc()
        return 1
    finally:
        close_db()

    return 0


def quick_chart_update():
    print('快速图表更新模式')
    print('-' * 30)

    try:
        os.chdir(parent_dir)
        index_df = load_existing_index()

        if index_df is not None and not index_df.empty:
            show_latest_stats(index_df)
            generate_all_charts(index_df)
            render_readme(index_df)
            print('图表与 README 更新完成！')
        else:
            print('没有数据可处理')

    except Exception as e:
        print(f'错误：{e}')
        return 1
    finally:
        close_db()

    return 0


def run_verify():
    print('运行增量更新与全量计算一致性验证...')
    print('-' * 30)
    try:
        os.chdir(parent_dir)
        return 0 if verify_incremental_vs_full() else 1
    except Exception as e:
        print(f'验证失败：{e}')
        return 1
    finally:
        close_db()


def run_migrate():
    print('运行 Pickle 到 SQLite 数据迁移...')
    print('-' * 30)
    try:
        os.chdir(parent_dir)
        migrate_mod = load_local_module('06_migrate_to_sqlite.py', 'dada_migrate')
        return 0 if migrate_mod.migrate_all() else 1
    except Exception as e:
        print(f'迁移失败：{e}')
        import traceback
        traceback.print_exc()
        return 1


def show_status():
    try:
        os.chdir(parent_dir)
        stats = get_db().get_statistics()
        print('=' * 40)
        print('当前数据库状态')
        print('=' * 40)
        print(f"链接记录数：{stats['links_count']}")
        print(f"期次记录数：{stats['periods_count']}")
        print(f"价格明细数：{stats['price_items_count']}")
        print(f"指数记录数：{stats['index_count']}")
        if 'latest_link' in stats:
            print(f"最新链接：{stats['latest_link']}")
        if 'latest_index' in stats:
            print(f"最新指数：{stats['latest_index']}")
    except Exception as e:
        print(f'获取状态失败：{e}')
        return 1
    finally:
        close_db()

    return 0


def show_help():
    print("""
使用方法：
python scripts/01_update.py [选项]

选项：
  无参数      - 增量更新（默认模式，更新数据+生成图表）
  --offline   - 离线更新（只使用本地数据库，不联网抓取）
  --full      - 全量重算模式（从基期开始重新计算整个历史序列）
  --chart     - 仅更新图表（不更新数据）
  --verify    - 验证增量更新与全量计算的一致性
  --migrate   - 从 pickle 文件迁移数据到 SQLite
  --status    - 显示当前数据库状态
  --help, -h  - 显示此帮助信息
""")


if __name__ == '__main__':
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ['--help', '-h']:
            sys.exit(0 if not show_help() else 0)
        if arg == '--chart':
            sys.exit(quick_chart_update())
        if arg == '--full':
            sys.exit(main(full_mode=True))
        if arg == '--offline':
            sys.exit(main(offline=True))
        if arg == '--verify':
            sys.exit(run_verify())
        if arg == '--migrate':
            sys.exit(run_migrate())
        if arg == '--status':
            sys.exit(show_status())
        print(f'未知参数：{arg}')
        show_help()
        sys.exit(1)
    sys.exit(main(full_mode=False))
