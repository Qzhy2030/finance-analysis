"""
扩充保险类公司 —— 新增港股核心险企 + A股保险科技概念股
1. 更新 finance_seed.json
2. 更新 SQLite 数据库
3. 从新浪/东方财富拉取行情数据
"""
import json
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_manager import get_db
from database.company_mapping import get_mapper

SEED_PATH = Path(__file__).parent.parent / "database" / "finance_seed.json"

# ── 新增的公司 ──────────────────────────────────────────
NEW_INSURANCE_COMPANIES = [
    # === 港股核心保险公司 ===
    {
        "code": "00376",
        "name": "云锋金融",
        "market": "HK",
        "full_name": "云锋金融集团有限公司(旗下万通保险)"
    },
    {
        "code": "00945",
        "name": "宏利金融-S",
        "market": "HK",
        "full_name": "宏利金融有限公司(全球保险巨头)"
    },
    # === A股保险科技 / 保险概念 ===
    {
        "code": "300085",
        "name": "银之杰",
        "market": "SZ",
        "full_name": "深圳市银之杰科技股份有限公司(互联网保险)"
    },
    {
        "code": "300399",
        "name": "天利科技",
        "market": "SZ",
        "full_name": "江西天利科技股份有限公司(保险科技)"
    },
    {
        "code": "300773",
        "name": "拉卡拉",
        "market": "SZ",
        "full_name": "拉卡拉支付股份有限公司(保险经纪)"
    },
    {
        "code": "002315",
        "name": "焦点科技",
        "market": "SZ",
        "full_name": "焦点科技股份有限公司(保险电商平台)"
    },
]


# ── Step 1: 更新 JSON 种子文件 ─────────────────────────
def update_seed_json():
    with open(SEED_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    existing_codes = {c["code"] for c in data}
    added = 0
    skipped = 0
    
    for company in NEW_INSURANCE_COMPANIES:
        if company["code"] in existing_codes:
            print(f"  ⏭ 已存在: {company['name']} ({company['code']})")
            skipped += 1
        else:
            data.append(company)
            print(f"  ✅ 新增: {company['name']} ({company['code']}) - {company['full_name']}")
            added += 1
    
    if added > 0:
        with open(SEED_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n种子文件更新完成: 新增 {added} 家, 跳过 {skipped} 家, 总计 {len(data)} 家")
    return added


# ── Step 2: 写入数据库 ──────────────────────────────────
def sync_to_database():
    db = get_db()
    count_new = 0
    count_existing = 0
    
    for company in NEW_INSURANCE_COMPANIES:
        try:
            # 检查是否已存在
            existing = db.get_company_by_code(company["code"])
            if existing:
                print(f"  📌 数据库已存在: {company['name']} ({company['code']})")
                count_existing += 1
            else:
                db.upsert_company(
                    stock_code=company["code"],
                    short_name=company["name"],
                    market=company["market"],
                    full_name=company.get("full_name", ""),
                    industry="保险"
                )
                print(f"  💾 写入数据库: {company['name']} ({company['code']})")
                count_new += 1
        except Exception as e:
            print(f"  ❌ 失败 {company['name']}: {e}")
    
    print(f"\n数据库同步完成: 新增 {count_new} 条, 已存在 {count_existing} 条")
    return count_new


# ── Step 3: 更新公司映射缓存 ────────────────────────────
def refresh_mapper():
    print("🔄 刷新公司映射缓存...")
    mapper = get_mapper()
    mapper.load()  # 重新加载种子数据并重建索引
    print(f"  ✅ 映射索引重建完成，共 {len(mapper._companies)} 家公司")


# ── Step 4: 验证数据库 ────────────────────────────────
def verify_database():
    print("\n📋 验证数据库中的保险类公司...")
    db = get_db()
    
    for company in NEW_INSURANCE_COMPANIES:
        row = db.get_company_by_code(company["code"])
        if row:
            print(f"  ✅ {company['name']} ({company['code']}) - ID: {row.get('id', '?')}")
        else:
            print(f"  ❌ {company['name']} ({company['code']}) - 未找到!")
    
    # 统计总数
    import sqlite3
    cursor = db.conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM companies")
    total = cursor.fetchone()[0]
    print(f"\n📊 数据库公司总数: {total}")


# ── Main ────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  保险类公司扩充 —— 同步数据")
    print("=" * 60)
    
    print(f"\n新增 {len(NEW_INSURANCE_COMPANIES)} 家公司:")
    for c in NEW_INSURANCE_COMPANIES:
        tag = "🇭🇰" if c["market"] == "HK" else "🇨🇳"
        print(f"  {tag} {c['name']} ({c['code']}.{c['market']}) - {c.get('full_name','')}")
    
    print("\n── Step 1/4 ── 更新种子JSON...")
    added = update_seed_json()
    
    print("\n── Step 2/4 ── 同步SQLite数据库...")
    db_added = sync_to_database()
    
    print("\n── Step 3/4 ── 刷新公司映射索引...")
    refresh_mapper()
    
    print("\n── Step 4/4 ── 验证数据库完整性...")
    verify_database()
    
    print("\n" + "=" * 60)
    print(f"  ✨ 全部完成！新增 {added} 家保险相关公司")
    print(f"  💡 提示: 通过Streamlit App点击公司即可自动拉取行情数据")
    print("=" * 60)
