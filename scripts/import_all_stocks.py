#!/usr/bin/env python3
"""
从东方财富批量拉取全部A股上市公司列表，导入公司映射数据库
数据来源：沪深主板 + 创业板 + 科创板 + 北交所
"""
import sys, json, time, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from config import SCRAPER_HEADERS


def fetch_company_list() -> list:
    """
    从东方财富API拉取全部A股上市公司
    返回: [(code, name, market), ...]
    """
    session = requests.Session()
    session.headers.update(SCRAPER_HEADERS)
    session.trust_env = False  # 绕过系统代理，直连

    # 全市场一次性获取（已验证可工作）
    fs_param = "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048"
    page = 1
    page_size = 200  # 减小页大小避免连接断开
    max_pages = 50   # 安全上限

    all_companies = []
    seen_codes = set()

    while page <= max_pages:
        url = "https://push2.eastmoney.com/api/qt/clist/get"
        params = {
            "pn": page,
            "pz": page_size,
            "po": 1,
            "np": 1,
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "fltt": 2,
            "invt": 2,
            "fid": "f3",
            "fs": fs_param,
            "fields": "f12,f14,f20",
        }

        try:
            resp = session.get(url, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("data", {}).get("diff", [])
            total = data.get("data", {}).get("total", 0)

            if not items:
                break

            for item in items:
                code = str(item.get("f12", "")).strip()
                name = str(item.get("f14", "")).strip()
                industry = str(item.get("f20", "")).strip() if item.get("f20") else ""

                if code and name and code not in seen_codes:
                    seen_codes.add(code)
                    if code.startswith("6"):
                        mk = "SH"
                    elif code.startswith(("0", "3")):
                        mk = "SZ"
                    elif code.startswith(("8", "4")):
                        mk = "BJ"
                    else:
                        mk = "SZ"

                    all_companies.append({
                        "code": code, "name": name,
                        "market": mk, "industry": industry,
                    })

            print(f"   第{page}页: {len(items)}条 | 累计: {len(seen_codes)}/{total}", end="\r")

            if len(items) < page_size:
                break
            page += 1
            time.sleep(0.5)

        except Exception as e:
            print(f"\n   ⚠ 第{page}页失败: {e}")
            # 等待后重试一次
            time.sleep(3)
            try:
                resp = session.get(url, params=params, timeout=20)
                data = resp.json()
                items = data.get("data", {}).get("diff", [])
                for item in items:
                    code = str(item.get("f12", "")).strip()
                    name = str(item.get("f14", "")).strip()
                    if code and name and code not in seen_codes:
                        seen_codes.add(code)
                        mk = "SH" if code.startswith("6") else ("SZ" if code.startswith(("0","3")) else "BJ")
                        all_companies.append({"code": code, "name": name, "market": mk, "industry": str(item.get("f20","") or "")})
                page += 1
                print(f"   第{page-1}页(重试成功): {len(items)}条")
            except:
                print(f"   第{page}页重试仍失败，跳过")
                page += 1

    print(f"\n   ✅ 全市场完成: {len(seen_codes)} 家公司")
    return all_companies


def import_to_database(companies: list, batch_size: int = 500):
    """批量导入到公司映射和数据库"""
    from database.company_mapping import get_mapper
    from database.db_manager import get_db

    mapper = get_mapper()
    db = get_db()

    total = len(companies)
    added = 0
    exists = 0

    # 先添加到SQLite数据库
    for i, company in enumerate(companies):
        company_id = db.upsert_company(
            stock_code=company["code"],
            short_name=company["name"],
            full_name="",
            market=company["market"],
            industry=company["industry"],
        )
        if i % 100 == 0:
            print(f"   数据库导入进度: {i+1}/{total}...", end="\r")

    print(f"\n   ✅ 数据库导入完成: {len(companies)} 条记录")

    # 然后更新company_mapping.json
    for i, company in enumerate(companies):
        existing = mapper.get_by_code(company["code"])
        if existing:
            # 更新行业
            if company["industry"]:
                mapper.add_company(
                    company["code"],
                    company["name"],
                    "",
                    company["market"],
                )
            exists += 1
        else:
            mapper.add_company(
                company["code"],
                company["name"],
                company.get("full_name", ""),
                company["market"],
            )
            added += 1

        if i % 200 == 0:
            print(f"   映射导入进度: {i+1}/{total}...", end="\r")

    return added, exists


def main():
    print("=" * 60)
    print("📊 批量导入A股上市公司到映射数据库")
    print("=" * 60)

    # 获取公司列表
    print("\n🔄 正在从东方财富获取全部A股公司列表...")
    companies = fetch_company_list()
    print(f"\n✅ 共获取 {len(companies)} 家上市公司\n")

    # 统计市场分布
    from collections import Counter
    market_count = Counter(c["market"] for c in companies)
    print("📊 市场分布:")
    for mk, cnt in sorted(market_count.items()):
        names = {"SH": "上海主板/科创板", "SZ": "深圳主板/创业板", "BJ": "北交所"}
        print(f"   {names.get(mk, mk)}: {cnt} 家")

    # 导入数据库
    print("\n💾 正在导入数据库...")
    added, exists = import_to_database(companies)

    # 统计结果
    print("\n" + "=" * 60)
    print("✅ 批量导入完成！")
    print(f"   新增: {added} 家")
    print(f"   已存在: {exists} 家")
    print(f"   总计: {exists + added} 家")

    # 验证
    from database.company_mapping import get_mapper
    mapper = get_mapper()
    print(f"\n📊 验证: 映射数据库当前 {mapper.count} 家公司")

    # 搜索测试
    test_queries = ["茅台", "腾讯", "宁德", "中国石油", "工商"]
    print("\n🔍 搜索测试:")
    for q in test_queries:
        r = mapper.search(q, limit=3)
        names = [f"{c['name']}({c['code']})" for c in r]
        print(f"   '{q}': {', '.join(names)}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
