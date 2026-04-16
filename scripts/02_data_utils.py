#!/usr/bin/env python3
"""
数据获取和更新工具模块

提供链接爬取、价格数据获取等功能。
"""

import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import time
import os

from _loader import load_local_module

get_db = load_local_module('03_db_manager.py', 'dada_db_manager').get_db


def fetch_price_table(url):
    """爬取指定URL的价格表格"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
    }
    response = requests.get(url, headers=headers)
    response.encoding = response.apparent_encoding
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table')
    rows = table.find_all('tr')
    headers = [th.get_text(strip=True) for th in rows[0].find_all(['th', 'td'])]
    data = []
    for row in rows[1:]:
        cols = [td.get_text(strip=True) for td in row.find_all('td')]
        if cols:
            data.append(cols)
    df = pd.DataFrame(data, columns=headers)
    return df


def fetch_all_links(start_page=1, end_page=100):
    """批量爬取链接页面，获取所有相关链接"""
    all_records = []
    period_map = {'上旬': 1, '中旬': 2, '下旬': 3}
    pattern = re.compile(r"(\d{4})年(\d{1,2})月(上旬|中旬|下旬)流通领域重要生产资料市场价格变动情况")

    for i in range(start_page, end_page):
        if i == 0:
            page_url = 'https://www.stats.gov.cn/sj/zxfb/index.html'
        else:
            page_url = f'https://www.stats.gov.cn/sj/zxfb/index_{i}.html'

        try:
            resp = requests.get(page_url)
            resp.encoding = resp.apparent_encoding
            soup = BeautifulSoup(resp.text, 'html.parser')

            for a in soup.find_all('a', href=True):
                title = a.get('title', '')
                m = pattern.match(title)
                if m:
                    year = int(m.group(1))
                    month = int(m.group(2))
                    period = period_map.get(m.group(3), None)
                    href = a['href']
                    full_url = urljoin(page_url, href)
                    all_records.append({'Year': year, 'Month': month, 'Period': period, 'URL': full_url})

            if i % 10 == 0:
                print(f'已完成第{i}页')
            time.sleep(1)

        except Exception as e:
            print(f'第{i}页爬取失败：', e)

    df_all_links = pd.DataFrame(all_records).drop_duplicates(subset=['Year', 'Month', 'Period', 'URL']).reset_index(drop=True)
    return df_all_links


def update_links():
    """增量更新链接数据"""
    db = get_db()

    # 获取现有最新记录
    latest = db.get_latest_link()
    if latest:
        print(f"现有链接最新日期: {latest['Year']}年{latest['Month']}月第{latest['Period']}旬")

    # 获取最新链接
    new_records = []
    pattern = re.compile(r"(\d{4})年(\d{1,2})月(上旬|中旬|下旬)流通领域重要生产资料市场价格变动情况")
    period_map = {'上旬': 1, '中旬': 2, '下旬': 3}

    for i in range(3):  # 检查前3页
        if i == 0:
            page_url = 'https://www.stats.gov.cn/sj/zxfb/index.html'
        else:
            page_url = f'https://www.stats.gov.cn/sj/zxfb/index_{i}.html'

        try:
            resp = requests.get(page_url)
            resp.encoding = resp.apparent_encoding
            soup = BeautifulSoup(resp.text, 'html.parser')

            for a in soup.find_all('a', href=True):
                title = a.get('title', '')
                m = pattern.match(title)
                if m:
                    year = int(m.group(1))
                    month = int(m.group(2))
                    period = period_map.get(m.group(3))
                    href = a['href']
                    full_url = urljoin(page_url, href)

                    # 检查是否已存在
                    if not db.link_exists(year, month, period):
                        new_records.append({'Year': year, 'Month': month, 'Period': period, 'URL': full_url})

            time.sleep(2)

        except Exception as e:
            print(f"获取页面 {page_url} 失败: {e}")

    # 插入新数据
    if new_records:
        for record in new_records:
            db.insert_link(record['Year'], record['Month'], record['Period'], record['URL'])
        print(f"链接更新完成，新增{len(new_records)}条记录")
    else:
        print("没有新链接需要更新")

    return db.get_all_links()


def update_price_data():
    """增量更新价格数据"""
    db = get_db()

    # 获取所有链接
    df_all_links = db.get_all_links()

    if df_all_links.empty:
        print("没有链接数据，请先运行 update_links()")
        return None

    # 抓取新的价格数据
    new_count = 0
    for _, row in df_all_links.iterrows():
        year, month, period, url = int(row['Year']), int(row['Month']), int(row['Period']), row['URL']

        # 检查是否已存在
        if db.period_exists(year, month, period):
            continue

        try:
            price_df = fetch_price_table(url)

            if db.insert_period_prices(year, month, period, price_df, url):
                print(f'已保存: {year}年{month}月第{period}旬')
                new_count += 1
            time.sleep(3)

        except Exception as e:
            print(f'抓取失败: {url}, 错误: {e}')

    print(f"价格数据更新完成，新增{new_count}条记录")

    return db.get_all_periods()


def load_price_data():
    """加载价格数据（返回期次列表）"""
    db = get_db()
    return db.get_all_periods()


def load_links_data():
    """加载链接数据"""
    db = get_db()
    return db.get_all_links()


def get_period_prices(year, month, period):
    """获取指定期次的价格表"""
    db = get_db()
    return db.get_period_prices(year, month, period)
