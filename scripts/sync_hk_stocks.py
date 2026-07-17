#!/usr/bin/env python3
"""
同步港股上市金融机构
包含：港股银行、保险、券商、交易所等
"""
import sys, json, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.company_mapping import get_mapper
from database.db_manager import get_db
from scraper.cninfo_scraper import get_cninfo_scraper

# 港股核心金融机构（手工整理）
HK_FINANCE_COMPANIES = [
    # ===== 银行 (6家) =====
    {"code":"00005","name":"汇丰控股","market":"HK","full_name":"香港上海汇丰银行有限公司"},
    {"code":"00011","name":"恒生银行","market":"HK","full_name":"恒生银行有限公司"},
    {"code":"02388","name":"中银香港","market":"HK","full_name":"中银香港(控股)有限公司"},
    {"code":"00023","name":"东亚银行","market":"HK","full_name":"东亚银行有限公司"},
    {"code":"02888","name":"渣打集团","market":"HK","full_name":"渣打集团有限公司"},
    
    # ===== 保险 (6家) =====
    {"code":"01299","name":"友邦保险","market":"HK","full_name":"友邦保险控股有限公司"},
    {"code":"00966","name":"中国太平","market":"HK","full_name":"中国太平保险控股有限公司"},
    {"code":"01508","name":"中国再保险","market":"HK","full_name":"中国再保险(集团)股份有限公司"},
    {"code":"06060","name":"众安在线","market":"HK","full_name":"众安在线财产保险股份有限公司"},
    {"code":"02378","name":"保诚","market":"HK","full_name":"英国保诚集团"},
    
    # ===== 证券/交易所 (9家) =====
    {"code":"00388","name":"香港交易所","market":"HK","full_name":"香港交易及结算所有限公司"},
    {"code":"06886","name":"HTSC","market":"HK","full_name":"华泰证券股份有限公司"},  # H股
    {"code":"06030","name":"中信证券","market":"HK","full_name":"中信证券股份有限公司"},  # H股
    {"code":"06881","name":"中国银河","market":"HK","full_name":"中国银河证券股份有限公司"},  # H股
    {"code":"03908","name":"中金公司","market":"HK","full_name":"中国国际金融股份有限公司"},  # H股
    {"code":"01776","name":"广发证券","market":"HK","full_name":"广发证券股份有限公司"},  # H股
    {"code":"06099","name":"招商证券","market":"HK","full_name":"招商证券股份有限公司"},  # H股
    {"code":"02611","name":"国泰君安","market":"HK","full_name":"国泰君安国际控股有限公司"},  # H股
    {"code":"06837","name":"海通证券","market":"HK","full_name":"海通证券股份有限公司"},  # H股
]

def main():
    mapper = get_mapper()
    db = get_db()
    scraper = get_cninfo_scraper()
    
    print("=" * 60)
    print("🇭🇰 同步港股上市金融机构")
    print("=" * 60)
    
    added = 0
    exists = 0
    has_data = 0
    
    for i, company in enumerate(HK_FINANCE_COMPANIES):
        code = company["code"]
        name = company["name"]
        market = company["market"]
        full_name = company.get("full_name", "")
        
        # 检查是否已存在
        if mapper.get_by_code(code):
            print(f"   [{i+1}/{len(HK_FINANCE_COMPANIES)}] {name}({code}): 已存在 ✅")
            exists += 1
            continue
        
        # 添加到映射
        mapper.add_company(code, name, full_name, market)
        
        # 添加到SQLite
        company_id = db.upsert_company(code, name, full_name, market)
        
        # 尝试获取财务数据（使用mock，因为港股API不通）
        try:
            fin_data = scraper.fetch_ths_financial_data(code)
            highlights = fin_data.get("highlights", [])
            if highlights:
                for h in highlights:
                    db.save_highlights(company_id, h)
                has_data += 1
                print(f"   [{i+1}/{len(HK_FINANCE_COMPANIES)}] {name}({code}): +{len(highlights)}期数据 ✅")
            else:
                print(f"   [{i+1}/{len(HK_FINANCE_COMPANIES)}] {name}({code}): 已添加，无数据 ⚠")
        except Exception as e:
            print(f"   [{i+1}/{len(HK_FINANCE_COMPANIES)}] {name}({code}): 已添加，数据异常 {str(e)[:40]}")
        
        added += 1
    
    # 统计
    print(f"\n{'='*60}")
    print(f"✅ 港股同步完成!")
    
    # 按市场分类
    hk_count = len([c for c in mapper.all_companies if c.get("market") == "HK"])
    sh_count = len([c for c in mapper.all_companies if c.get("market") == "SH"])
    sz_count = len([c for c in mapper.all_companies if c.get("market") == "SZ"])
    bj_count = len([c for c in mapper.all_companies if c.get("market") == "BJ"])
    
    print(f"   新增: {added} | 已存在: {exists}")
    print(f"   数据库总计: {mapper.count} 家")
    print(f"   市场分布: SH={sh_count} SZ={sz_count} BJ={bj_count} HK={hk_count}")
    
    # 分类统计
    banks = [c for c in mapper.all_companies if "银行" in c["name"]]
    insur = [c for c in mapper.all_companies if "保险" in c["name"] or c["name"] in ["中国平安","友邦保险","众安在线","保诚"]]
    sec = [c for c in mapper.all_companies if "证券" in c["name"] or c["name"] in ["香港交易所","HTSC"]]
    print(f"   银行: {len(banks)} | 保险: {len(insur)} | 证券/交易所: {len(sec)}")
    
    # 搜索测试
    print(f"\n🔍 搜索验证:")
    for q in ["汇丰","友邦","港交所","恒生","中金"]:
        r = mapper.search(q, 3)
        names = " | ".join([f'{c["name"]}({c["code"]})' for c in r])
        print(f'   "{q}": {names}')


if __name__ == "__main__":
    main()
