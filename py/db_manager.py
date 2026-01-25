#!/usr/bin/env python3
"""
SQLite 数据库管理模块

提供统一的数据库访问接口，替代原有的 pickle 文件存储方式。
"""

import sqlite3
import pandas as pd
import os
from datetime import datetime
from contextlib import contextmanager


# 数据库文件默认路径
DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'price_data.db')


class DatabaseManager:
    """价格数据 SQLite 数据库管理器"""

    def __init__(self, db_path=None):
        """
        初始化数据库连接

        参数:
            db_path: 数据库文件路径，默认为项目根目录下的 price_data.db
        """
        self.db_path = db_path or DEFAULT_DB_PATH
        self.conn = None
        self._connect()
        self.init_schema()

    def _connect(self):
        """建立数据库连接"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        # 启用外键约束
        self.conn.execute("PRAGMA foreign_keys = ON")

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @contextmanager
    def transaction(self):
        """事务上下文管理器"""
        try:
            yield
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def init_schema(self):
        """初始化数据库表结构"""
        cursor = self.conn.cursor()

        # 表1: 链接数据
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS period_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year INTEGER NOT NULL,
                month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
                period INTEGER NOT NULL CHECK (period BETWEEN 1 AND 3),
                url TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(year, month, period)
            )
        """)

        # 表2: 期次（价格数据的父表）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS periods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year INTEGER NOT NULL,
                month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
                period INTEGER NOT NULL CHECK (period BETWEEN 1 AND 3),
                source_url TEXT,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(year, month, period)
            )
        """)

        # 表3: 价格明细
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                period_id INTEGER NOT NULL,
                good_name TEXT NOT NULL,
                unit TEXT,
                current_price REAL,
                price_change REAL,
                price_change_pct REAL,
                FOREIGN KEY (period_id) REFERENCES periods(id) ON DELETE CASCADE,
                UNIQUE(period_id, good_name)
            )
        """)

        # 表4: 价格指数
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_index (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year INTEGER NOT NULL,
                month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
                period INTEGER NOT NULL CHECK (period BETWEEN 1 AND 3),
                price_index REAL NOT NULL,
                chain_base TEXT DEFAULT 'original',
                calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(year, month, period)
            )
        """)

        # 表5: 元数据
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_period_links_date ON period_links(year, month, period)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_periods_date ON periods(year, month, period)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_items_period ON price_items(period_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_items_good ON price_items(good_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_index_date ON price_index(year, month, period)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_index_chain ON price_index(chain_base)")

        self.conn.commit()

    # ========== 链接数据操作 ==========

    def insert_link(self, year, month, period, url):
        """
        插入一条链接记录

        返回:
            bool: 是否成功插入（如果已存在则返回 False）
        """
        try:
            self.conn.execute("""
                INSERT INTO period_links (year, month, period, url)
                VALUES (?, ?, ?, ?)
            """, (year, month, period, url))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def link_exists(self, year, month, period):
        """检查链接是否已存在"""
        cursor = self.conn.execute("""
            SELECT 1 FROM period_links WHERE year = ? AND month = ? AND period = ?
        """, (year, month, period))
        return cursor.fetchone() is not None

    def get_link(self, year, month, period):
        """获取指定期次的链接"""
        cursor = self.conn.execute("""
            SELECT url FROM period_links WHERE year = ? AND month = ? AND period = ?
        """, (year, month, period))
        row = cursor.fetchone()
        return row['url'] if row else None

    def get_all_links(self):
        """获取所有链接，返回 DataFrame"""
        df = pd.read_sql_query("""
            SELECT year, month, period, url
            FROM period_links
            ORDER BY year, month, period
        """, self.conn)
        df.columns = ['Year', 'Month', 'Period', 'URL']
        return df

    def get_latest_link(self):
        """获取最新的链接记录"""
        cursor = self.conn.execute("""
            SELECT year, month, period, url
            FROM period_links
            ORDER BY year DESC, month DESC, period DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
        if row:
            return {'Year': row['year'], 'Month': row['month'], 'Period': row['period'], 'URL': row['url']}
        return None

    # ========== 价格数据操作 ==========

    def insert_period_prices(self, year, month, period, price_df, source_url=None):
        """
        插入一个期次的价格数据（事务性操作）

        参数:
            year, month, period: 期次标识
            price_df: 价格表 DataFrame，列为 [商品名称, 单位, 本期价格, 涨跌额, 涨跌幅]
            source_url: 数据来源 URL

        返回:
            bool: 是否成功插入
        """
        try:
            with self.transaction():
                # 插入期次记录
                cursor = self.conn.execute("""
                    INSERT INTO periods (year, month, period, source_url)
                    VALUES (?, ?, ?, ?)
                """, (year, month, period, source_url))
                period_id = cursor.lastrowid

                # 插入价格明细
                for _, row in price_df.iterrows():
                    good_name = row.iloc[0] if len(row) > 0 else None
                    unit = row.iloc[1] if len(row) > 1 else None
                    current_price = self._parse_float(row.iloc[2]) if len(row) > 2 else None
                    price_change = self._parse_float(row.iloc[3]) if len(row) > 3 else None
                    price_change_pct = self._parse_float(row.iloc[4]) if len(row) > 4 else None

                    # 跳过空行或标题行
                    if not good_name or pd.isna(good_name) or str(good_name).strip() == '':
                        continue

                    self.conn.execute("""
                        INSERT INTO price_items (period_id, good_name, unit, current_price, price_change, price_change_pct)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (period_id, str(good_name).strip(), unit, current_price, price_change, price_change_pct))

            return True
        except sqlite3.IntegrityError:
            return False

    def _parse_float(self, value):
        """安全解析浮点数"""
        if pd.isna(value):
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def period_exists(self, year, month, period):
        """检查期次是否已存在"""
        cursor = self.conn.execute("""
            SELECT 1 FROM periods WHERE year = ? AND month = ? AND period = ?
        """, (year, month, period))
        return cursor.fetchone() is not None

    def get_period_id(self, year, month, period):
        """获取期次 ID"""
        cursor = self.conn.execute("""
            SELECT id FROM periods WHERE year = ? AND month = ? AND period = ?
        """, (year, month, period))
        row = cursor.fetchone()
        return row['id'] if row else None

    def get_period_prices(self, year, month, period):
        """
        获取指定期次的价格表

        返回:
            DataFrame: 价格表，列为 [商品名称, 单位, 本期价格, 涨跌额, 涨跌幅]
        """
        period_id = self.get_period_id(year, month, period)
        if period_id is None:
            return None

        df = pd.read_sql_query("""
            SELECT good_name, unit, current_price, price_change, price_change_pct
            FROM price_items
            WHERE period_id = ?
            ORDER BY id
        """, self.conn, params=(period_id,))

        # 重命名列以匹配原有格式
        df.columns = ['商品名称', '单位', '本期价格(元)', '比上期价格涨跌(元)', '涨跌幅(%)']
        return df

    def get_all_periods(self):
        """获取所有期次列表"""
        df = pd.read_sql_query("""
            SELECT year, month, period, source_url, fetched_at
            FROM periods
            ORDER BY year, month, period
        """, self.conn)
        df.columns = ['Year', 'Month', 'Period', 'SourceURL', 'FetchedAt']
        return df

    def get_periods_after(self, year, month, period):
        """获取指定期次之后的所有期次"""
        df = pd.read_sql_query("""
            SELECT year, month, period
            FROM periods
            WHERE (year > ?) OR (year = ? AND month > ?) OR (year = ? AND month = ? AND period > ?)
            ORDER BY year, month, period
        """, self.conn, params=(year, year, month, year, month, period))
        df.columns = ['Year', 'Month', 'Period']
        return df

    def get_price_data_for_period(self, year, month, period):
        """
        获取指定期次的价格数据（用于指数计算）

        返回:
            dict: {商品名称: 价格}
        """
        period_id = self.get_period_id(year, month, period)
        if period_id is None:
            return {}

        cursor = self.conn.execute("""
            SELECT good_name, current_price
            FROM price_items
            WHERE period_id = ? AND current_price IS NOT NULL
        """, (period_id,))

        return {row['good_name']: row['current_price'] for row in cursor.fetchall()}

    def get_pct_changes_for_period(self, year, month, period):
        """
        获取指定期次的环比涨跌幅（用于口径变更衔接）

        返回:
            list: [{'good': 商品名称, 'pct': 涨跌幅}, ...]
        """
        period_id = self.get_period_id(year, month, period)
        if period_id is None:
            return []

        cursor = self.conn.execute("""
            SELECT good_name, price_change_pct
            FROM price_items
            WHERE period_id = ? AND price_change_pct IS NOT NULL
        """, (period_id,))

        return [{'good': row['good_name'], 'pct': row['price_change_pct']} for row in cursor.fetchall()]

    # ========== 价格指数操作 ==========

    def insert_index(self, year, month, period, index_value, chain_base='original'):
        """
        插入一条价格指数记录

        返回:
            bool: 是否成功插入
        """
        try:
            self.conn.execute("""
                INSERT INTO price_index (year, month, period, price_index, chain_base)
                VALUES (?, ?, ?, ?, ?)
            """, (year, month, period, index_value, chain_base))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def update_index(self, year, month, period, index_value, chain_base=None):
        """更新已有的价格指数记录"""
        if chain_base is not None:
            self.conn.execute("""
                UPDATE price_index
                SET price_index = ?, chain_base = ?, calculated_at = CURRENT_TIMESTAMP
                WHERE year = ? AND month = ? AND period = ?
            """, (index_value, chain_base, year, month, period))
        else:
            self.conn.execute("""
                UPDATE price_index
                SET price_index = ?, calculated_at = CURRENT_TIMESTAMP
                WHERE year = ? AND month = ? AND period = ?
            """, (index_value, year, month, period))
        self.conn.commit()

    def upsert_index(self, year, month, period, index_value, chain_base='original'):
        """插入或更新价格指数记录"""
        self.conn.execute("""
            INSERT INTO price_index (year, month, period, price_index, chain_base)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(year, month, period) DO UPDATE SET
                price_index = excluded.price_index,
                chain_base = excluded.chain_base,
                calculated_at = CURRENT_TIMESTAMP
        """, (year, month, period, index_value, chain_base))
        self.conn.commit()

    def index_exists(self, year, month, period):
        """检查指数是否已存在"""
        cursor = self.conn.execute("""
            SELECT 1 FROM price_index WHERE year = ? AND month = ? AND period = ?
        """, (year, month, period))
        return cursor.fetchone() is not None

    def get_index(self, year, month, period):
        """获取指定期次的指数值"""
        cursor = self.conn.execute("""
            SELECT price_index, chain_base
            FROM price_index
            WHERE year = ? AND month = ? AND period = ?
        """, (year, month, period))
        row = cursor.fetchone()
        if row:
            return {'PriceIndex': row['price_index'], 'ChainBase': row['chain_base']}
        return None

    def get_latest_index(self):
        """获取最新的指数记录"""
        cursor = self.conn.execute("""
            SELECT year, month, period, price_index, chain_base
            FROM price_index
            ORDER BY year DESC, month DESC, period DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
        if row:
            return {
                'Year': row['year'],
                'Month': row['month'],
                'Period': row['period'],
                'PriceIndex': row['price_index'],
                'ChainBase': row['chain_base']
            }
        return None

    def get_index_series(self, start_year=None, end_year=None):
        """
        获取指数序列

        返回:
            DataFrame: 指数序列，列为 [Year, Month, Period, PriceIndex, ChainBase]
        """
        query = "SELECT year, month, period, price_index, chain_base FROM price_index"
        params = []

        conditions = []
        if start_year is not None:
            conditions.append("year >= ?")
            params.append(start_year)
        if end_year is not None:
            conditions.append("year <= ?")
            params.append(end_year)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY year, month, period"

        df = pd.read_sql_query(query, self.conn, params=params)
        df.columns = ['Year', 'Month', 'Period', 'PriceIndex', 'ChainBase']
        return df

    def get_index_count(self):
        """获取指数记录总数"""
        cursor = self.conn.execute("SELECT COUNT(*) FROM price_index")
        return cursor.fetchone()[0]

    # ========== 元数据操作 ==========

    def set_metadata(self, key, value):
        """设置元数据"""
        self.conn.execute("""
            INSERT INTO metadata (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
        """, (key, value))
        self.conn.commit()

    def get_metadata(self, key):
        """获取元数据"""
        cursor = self.conn.execute("SELECT value FROM metadata WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row['value'] if row else None

    # ========== 迁移辅助方法 ==========

    def migrate_links_from_dataframe(self, df):
        """
        从 DataFrame 迁移链接数据

        参数:
            df: 包含 [Year, Month, Period, URL] 列的 DataFrame
        """
        count = 0
        for _, row in df.iterrows():
            if self.insert_link(int(row['Year']), int(row['Month']), int(row['Period']), row['URL']):
                count += 1
        return count

    def migrate_prices_from_dataframe(self, df):
        """
        从 DataFrame 迁移价格数据

        参数:
            df: 包含 [Year, Month, Period, PriceTable] 列的 DataFrame
        """
        count = 0
        for _, row in df.iterrows():
            year, month, period = int(row['Year']), int(row['Month']), int(row['Period'])
            price_table = row['PriceTable']

            # 获取 source_url（如果有的话）
            source_url = None
            if hasattr(price_table, 'attrs') and 'source_url' in price_table.attrs:
                source_url = price_table.attrs['source_url']

            if self.insert_period_prices(year, month, period, price_table, source_url):
                count += 1
        return count

    def migrate_index_from_dataframe(self, df):
        """
        从 DataFrame 迁移指数数据

        参数:
            df: 包含 [Year, Month, Period, PriceIndex, ChainBase?] 列的 DataFrame
        """
        count = 0
        for _, row in df.iterrows():
            chain_base = row.get('ChainBase', 'original') if 'ChainBase' in df.columns else 'original'
            if pd.isna(chain_base):
                chain_base = 'original'
            if self.insert_index(
                int(row['Year']),
                int(row['Month']),
                int(row['Period']),
                float(row['PriceIndex']),
                chain_base
            ):
                count += 1
        return count

    def get_statistics(self):
        """获取数据库统计信息"""
        stats = {}

        cursor = self.conn.execute("SELECT COUNT(*) FROM period_links")
        stats['links_count'] = cursor.fetchone()[0]

        cursor = self.conn.execute("SELECT COUNT(*) FROM periods")
        stats['periods_count'] = cursor.fetchone()[0]

        cursor = self.conn.execute("SELECT COUNT(*) FROM price_items")
        stats['price_items_count'] = cursor.fetchone()[0]

        cursor = self.conn.execute("SELECT COUNT(*) FROM price_index")
        stats['index_count'] = cursor.fetchone()[0]

        # 最新期次
        latest_link = self.get_latest_link()
        if latest_link:
            stats['latest_link'] = f"{latest_link['Year']}年{latest_link['Month']}月第{latest_link['Period']}旬"

        latest_index = self.get_latest_index()
        if latest_index:
            stats['latest_index'] = f"{latest_index['Year']}年{latest_index['Month']}月第{latest_index['Period']}旬: {latest_index['PriceIndex']:.4f}"

        return stats


# 模块级便捷函数
_default_db = None


def get_db(db_path=None):
    """获取默认数据库实例"""
    global _default_db
    if _default_db is None or db_path is not None:
        _default_db = DatabaseManager(db_path)
    return _default_db


def close_db():
    """关闭默认数据库连接"""
    global _default_db
    if _default_db is not None:
        _default_db.close()
        _default_db = None
