#!/usr/bin/env python3
"""
补全银行和保险公司数据
从新浪API批量拉取所有A股银行/保险，并补充财务数据
"""
import sys, json, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from config import DATA_DIR
from database.company_mapping import get_mapper
from database.db_manager import get_db
from scraper.cninfo_scraper import get_cninfo_scraper


# 已知缺失但重要的银行/保险（手工确认）
MISSING_BANK_INSURANCE = [
    {"code":"600000", "name":"浦发银行", "market":"SH", "full_name":"上海浦东发展银行股份有限公司"},
    {"code":"601825", "name":"沪农商行", "market":"SH", "full_name":"上海农村商业银行股份有限公司"},
    {"code":"601077", "name":"渝农商行", "market":"SH", "full_name":"重庆农村商业银行股份有限公司"},
    {"code":"002958", "name":"青农商行", "market":"SZ", "full_name":"青岛农村商业银行股份有限公司"},
    {"code":"002839", "name":"张家港行", "market":"SZ", "full_name":"江苏张家港农村商业银行股份有限公司"},
    {"code":"601528", "name":"瑞丰银行", "market":"SH", "full_name":"浙江绍兴瑞丰农村商业银行股份有限公司"},
    {"code":"601860", "name":"紫金银行", "market":"SH", "full_name":"江苏紫金农村商业银行股份有限公司"},
    {"code":"603323", "name":"苏农银行", "market":"SH", "full_name":"江苏苏州农村商业银行股份有限公司"},
]


def fetch_all_bank_insurance():
    """从新浪全量拉取所有银行/保险股"""
    session = requests.Session()
    session.trust_env = False
    session.headers.update({"User-Agent": "Mozilla/5.0", "Referer": "https://finance.sina.com.cn"})

    all_finance = {}
    for page in range(1, 60):
        url = "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData"
        params = {"page": page, "num": 100, "sort": "symbol", "asc": 1, "node": "hs_a", "symbol": "", "_s_r_a": "init"}
        try:
            resp = session.get(url, params=params, timeout=10)
            data = resp.json()
            if not data:
                break
            for item in data:
                sym = item.get("symbol", "")
                name = item.get("name", "")
                code = sym.replace("sh","").replace("sz","").replace("bj","")
                if "银行" in name or "保险" in name:
                    mk = "SH" if sym.startswith("sh") else ("SZ" if sym.startswith("sz") else "BJ")
                    all_finance[code] = {"code": code, "name": name, "market": mk}
            if len(data) < 100:
                break
            time.sleep(0.15)
        except:
            break
    return list(all_finance.values())


def main():
    mapper = get_mapper()
    db = get_db()
    scraper = get_cninfo_scraper()

    print("=" * 60)
    print("🏦 补全银行与保险公司数据")
    print("=" * 60)

    # Step 1: 从新浪全量拉取
    print("\n[1/3] 从新浪拉取全部银行/保险股...")
    sina_list = fetch_all_bank_insurance()
    print(f"   新浪返回 {len(sina_list)} 家")

    # Step 2: 合并缺失的公司
    print("\n[2/3] 合并缺失公司...")
    to_add = list(MISSING_BANK_INSURANCE)  # 手工确认的

    # 检查新浪还有哪些缺失的
    seen_codes = {c["code"] for c in mapper.all_companies}
    for c in sina_list:
        if c["code"] not in seen_codes:
            to_add.append(c)
            seen_codes.add(c["code"])

    # 去重
    seen = set()
    unique_add = []
    for c in to_add:
        if c["code"] not in seen:
            seen.add(c["code"])
            unique_add.append(c)

    print(f"   需要新增: {len(unique_add)} 家")

    if not unique_add:
        print("   无需新增，数据库已完备")
        return

    for c in unique_add:
        print(f"   + {c['code']} {c['name']} ({c['market']})")

    # Step 3: 写入数据库
    print("\n[3/3] 写入数据库并获取财务数据...")
    for i, c in enumerate(unique_add):
        # 添加到映射
        mapper.add_company(c["code"], c["name"], c.get("full_name", ""), c["market"])
        # 添加到SQLite
        company_id = db.upsert_company(
            c["code"], c["name"], c.get("full_name", ""), c["market"]
        )
        # 获取财务数据
        try:
            fin_data = scraper.fetch_ths_financial_data(c["code"])
            highlights = fin_data.get("highlights", [])
            if highlights:
                for h in highlights:
                    db.save_highlights(company_id, h)
                print(f"   {i+1}/{len(unique_add)} {c['name']}: {len(highlights)}期 ✅")
            else:
                print(f"   {i+1}/{len(unique_add)} {c['name']}: 无财务数据 ⚠")
        except Exception as e:
            print(f"   {i+1}/{len(unique_add)} {c['name']}: 数据异常 {e}")

    # 总结
    print(f"\n{'='*60}")
    banks = [c for c in mapper.all_companies if "银行" in c["name"]]
    insur = [c for c in mapper.all_companies if "保险" in c["name"] or c["name"] in ["中国平安"]]
    print(f"✅ 补全完成!")
    print(f"  银行: {len(banks)} 家")
    print(f"  保险: {len(insur)} 家")
    print(f"  数据库总计: {mapper.count} 家")

    # 验证浦发银行
    r = mapper.get_by_code("600000")
    print(f"  浦发银行: {'✅' if r else '❌'}")


if __name__ == "__main__":
    main()
