#!/usr/bin/env python3
"""
批量下载巨潮资讯网年报PDF，并解析核心财务数据存入数据库
使用方式：
    python scripts/batch_download_pdfs.py                  # 下载全部公司最新年报
    python scripts/batch_download_pdfs.py --code 600519    # 下载指定公司
    python scripts/batch_download_pdfs.py --years 3        # 下载近3年年报
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import json
import time
from datetime import datetime
from typing import Optional

from scraper.cninfo_scraper import get_cninfo_scraper
from scraper.pdf_parser import PdfReportParser
from database.company_mapping import get_mapper
from database.db_manager import get_db
from config import DATA_DIR

PDF_CACHE_DIR = DATA_DIR / "pdf_cache"


def ensure_dirs():
    PDF_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def download_and_parse(code: str, name: str, years: int = 1,
                       skip_existing: bool = True) -> dict:
    """
    下载并解析指定公司年报PDF
    返回解析结果
    """
    ensure_dirs()
    scraper = get_cninfo_scraper()
    parser = PdfReportParser()
    db = get_db()

    result = {
        "code": code,
        "name": name,
        "downloaded": 0,
        "parsed": 0,
        "errors": [],
    }

    # 1. 获取年报列表
    reports = scraper.get_annual_reports(code, years=years)
    if not reports:
        print(f"  ⚠ {name}({code}): 未找到年报")
        return result

    print(f"  📄 找到 {len(reports)} 份年报")

    # 2. 下载并解析
    for report in reports:
        year = report["year"]
        pdf_url = report.get("pdf_url", "")
        if not pdf_url:
            continue

        pdf_path = PDF_CACHE_DIR / f"{code}_{year}_annual_report.pdf"

        # 跳过已存在的
        if skip_existing and pdf_path.exists():
            print(f"  - {year}年: 已存在，跳过")
            result["downloaded"] += 1
            result["parsed"] += 1
            continue

        # 下载PDF
        print(f"  - {year}年: 正在下载...", end=" ", flush=True)
        pdf_bytes = scraper.download_pdf(pdf_url, str(pdf_path))
        if not pdf_bytes:
            print("❌ 下载失败")
            result["errors"].append(f"{year}: 下载失败")
            continue
        result["downloaded"] += 1
        print("✅")

        # 解析PDF
        print(f"    -> 正在解析...", end=" ", flush=True)
        try:
            parsed = parser.parse_pdf(str(pdf_path))
            if parsed.get("error"):
                print(f"⚠ {parsed['error']}")
                result["errors"].append(f"{year}: {parsed['error']}")
                continue

            # 提取关键财务数据
            financial_data = parsed.get("financial_data", {})
            highlights = _extract_highlights(financial_data, year)

            if highlights:
                # 存入数据库
                company = db.get_company_by_code(code)
                if not company:
                    company_id = db.upsert_company(code, name)
                else:
                    company_id = company["id"]

                db.save_highlights(company_id, highlights)
                result["parsed"] += 1
                print("✅ 已存入数据库")
            else:
                print("⚠ 未提取到财务数据")
                result["errors"].append(f"{year}: 数据提取为空")

        except Exception as e:
            print(f"❌ 解析异常: {e}")
            result["errors"].append(f"{year}: {e}")

        time.sleep(1)  # 请求间隔，避免被反爬

    return result


def _extract_highlights(financial_data: dict, year: int) -> Optional[dict]:
    """从解析结果中提取关键财务指标"""
    highlights = {
        "report_date": f"{year}-12-31",
        "report_year": year,
    }

    # 从各表中提取
    for report_type, items in financial_data.items():
        for item in items:
            name = item.get("item_name", "")
            amounts = item.get("amounts", {})

            # 取第一个金额值
            value = None
            for _, v in amounts.items():
                value = v
                break

            if value is None:
                continue

            if "营业收入" in name or "营业总收入" in name:
                highlights["revenue"] = value
            elif "净利润" in name:
                if "归属于" in name or name == "净利润":
                    highlights["net_profit"] = value
            elif "总资产" in name or "资产总计" in name:
                highlights["total_assets"] = value
            elif "负债合计" in name:
                highlights["total_liab"] = value
            elif "净资产" in name or "股东权益" in name:
                if "归属于" in name:
                    highlights["equity"] = value
            elif "每股收益" in name:
                highlights["eps"] = value

    # 必须有营收或净利润才算有效
    if "revenue" not in highlights and "net_profit" not in highlights:
        return None

    return highlights


def main():
    parser = argparse.ArgumentParser(
        description="批量下载巨潮资讯网年报PDF并解析财务数据"
    )
    parser.add_argument("--code", type=str, help="指定股票代码")
    parser.add_argument("--name", type=str, help="指定公司名称")
    parser.add_argument("--years", type=int, default=1, help="下载最近N年年报")
    parser.add_argument("--limit", type=int, default=50, help="最多处理公司数")
    parser.add_argument("--no-skip", action="store_true",
                        help="不跳过已下载文件，重新下载")
    args = parser.parse_args()

    start_time = time.time()
    ensure_dirs()
    mapper = get_mapper()

    print("=" * 60)
    print(f"📥 巨潮资讯年报批量下载与解析")
    print(f"   PDF缓存: {PDF_CACHE_DIR}")
    print(f"   年报数量: 最近{args.years}年")
    print("=" * 60)

    # 确定要处理的公司列表
    companies = []
    if args.code:
        company = mapper.get_by_code(args.code)
        if not company:
            # 尝试搜索
            results = mapper.search(args.code, limit=1)
            if results:
                company = results[0]
        if company:
            companies = [company]
        else:
            print(f"❌ 未找到股票代码: {args.code}")
            return
    elif args.name:
        companies = mapper.search(args.name, limit=1)
        if not companies:
            print(f"❌ 未找到公司: {args.name}")
            return
    else:
        companies = mapper.all_companies[:args.limit]

    print(f"\n📊 共 {len(companies)} 家公司待处理\n")

    total_downloaded = 0
    total_parsed = 0
    total_errors = 0

    for i, company in enumerate(companies, 1):
        code = company["code"]
        name = company["name"]
        print(f"\n[{i}/{len(companies)}] {name}({code})")

        result = download_and_parse(
            code, name,
            years=args.years,
            skip_existing=not args.no_skip,
        )

        total_downloaded += result["downloaded"]
        total_parsed += result["parsed"]
        total_errors += len(result["errors"])

        # 进度提示
        if i < len(companies):
            elapsed = time.time() - start_time
            per_item = elapsed / i
            remaining = per_item * (len(companies) - i)
            print(f"   进度: {i}/{len(companies)} | "
                  f"预计剩余: {remaining:.0f}s")

    # 总结
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print("📊 批量处理完成！")
    print(f"   处理公司: {len(companies)} 家")
    print(f"   下载PDF: {total_downloaded} 份")
    print(f"   解析入库: {total_parsed} 条")
    print(f"   错误: {total_errors} 个")
    print(f"   耗时: {elapsed:.1f}s")
    print("=" * 60)


if __name__ == "__main__":
    main()
