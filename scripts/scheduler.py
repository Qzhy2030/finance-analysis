#!/usr/bin/env python3
"""
定时任务调度器
用于自动更新财务数据和生成分析报告

运行方式：
    python scripts/scheduler.py                    # 启动定时任务
    python scripts/scheduler.py --once             # 立即执行一次
    python scripts/scheduler.py --report-only      # 只生成报告，不更新数据
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import json
import logging
import time
from datetime import datetime
from typing import Optional

import schedule

from database.company_mapping import get_mapper
from database.db_manager import get_db
from scraper.cninfo_scraper import get_cninfo_scraper
from analysis.deepseek_client import get_deepseek
from analysis.report_generator import generate_report

# 日志配置
LOG_DIR = Path(__file__).parent.parent / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / f"scheduler_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# 统计数据文件
STATS_FILE = Path(__file__).parent.parent / "data" / "scheduler_stats.json"


def load_stats() -> dict:
    if STATS_FILE.exists():
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"total_runs": 0, "total_companies": 0, "total_reports": 0,
            "last_run": None, "errors": []}


def save_stats(stats: dict):
    STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)


def update_financial_data(limit: int = 20) -> int:
    """
    更新财务数据
    :param limit: 最多更新的公司数
    :return: 成功更新的公司数
    """
    mapper = get_mapper()
    scraper = get_cninfo_scraper()
    db = get_db()

    companies = mapper.all_companies[:limit]
    success = 0

    for company in companies:
        code = company["code"]
        name = company["name"]
        try:
            logger.info(f"更新 {name}({code})...")

            company_id = db.upsert_company(
                stock_code=code,
                short_name=name,
                full_name=company.get("full_name", ""),
                market=company.get("market", "SZ"),
            )

            fin_data = scraper.fetch_ths_financial_data(code)
            highlights = fin_data.get("highlights", [])
            if highlights:
                for h in highlights:
                    db.save_highlights(company_id, h)
                success += 1
                logger.info(f"  ✅ {name}: {len(highlights)} 条指标已更新")
            else:
                logger.warning(f"  ⚠ {name}: 无数据返回")

            time.sleep(2)  # 请求间隔

        except Exception as e:
            logger.error(f"  ❌ {name}: {e}")

    return success


def generate_reports_for_all(limit: int = 10) -> int:
    """
    为有数据的公司批量生成AI分析报告
    :param limit: 最多生成报告数
    :return: 成功生成数
    """
    mapper = get_mapper()
    db = get_db()
    ai_client = get_deepseek()

    companies = mapper.all_companies[:limit]
    generated = 0

    for company in companies:
        code = company["code"]
        name = company["name"]
        try:
            company_obj = db.get_company_by_code(code)
            if not company_obj:
                logger.info(f"  ⚠ {name}: 数据库无记录，跳过")
                continue

            highlights = db.get_highlights(company_obj["id"])
            if not highlights:
                logger.info(f"  ⚠ {name}: 无财务数据，跳过")
                continue

            logger.info(f"生成 {name}({code}) 分析报告...")

            financial_data = {
                "highlights": [dict(h) for h in highlights],
                "segments": [],
                "projects": [],
            }

            report_md = ai_client.analyze_financial_report(
                name, code, financial_data
            )

            if report_md:
                html_path = generate_report(name, code, financial_data, report_md)
                # 存入数据库
                latest_year = highlights[0]["report_year"]
                db.save_report(
                    company_obj["id"], latest_year, 4,
                    f"{name}{latest_year}年度财务分析报告",
                    open(html_path, "r", encoding="utf-8").read(),
                    report_md[:500],
                )
                generated += 1
                logger.info(f"  ✅ {name}: 报告已生成")
            else:
                logger.warning(f"  ⚠ {name}: AI分析失败")

        except Exception as e:
            logger.error(f"  ❌ {name}: {e}")

    return generated


def run_once(update_limit: int = 20, report_limit: int = 10):
    """立即执行一次完整流程"""
    logger.info("=" * 60)
    logger.info("🚀 定时任务 - 立即执行")
    logger.info("=" * 60)

    stats = load_stats()
    stats["total_runs"] += 1
    stats["last_run"] = datetime.now().isoformat()

    # 1. 更新财务数据
    logger.info("\n📥 阶段1: 更新财务数据")
    updated = update_financial_data(limit=update_limit)
    stats["total_companies"] += updated

    # 2. 生成分析报告
    logger.info("\n🤖 阶段2: 生成AI分析报告")
    reports = generate_reports_for_all(limit=report_limit)
    stats["total_reports"] += reports

    # 总结
    logger.info("\n" + "=" * 60)
    logger.info(f"✅ 执行完成!")
    logger.info(f"   更新公司: {updated}")
    logger.info(f"   生成报告: {reports}")
    logger.info(f"   总运行次数: {stats['total_runs']}")
    logger.info("=" * 60)

    save_stats(stats)


def start_scheduler(update_hour: int = 9, report_hour: int = 18):
    """启动定时任务调度器"""
    logger.info("=" * 60)
    logger.info("⏰ 定时任务调度器已启动")
    logger.info(f"   数据更新: 每天 {update_hour}:00")
    logger.info(f"   报告生成: 每天 {report_hour}:00")
    logger.info("=" * 60)

    # 数据更新 - 每天上午
    schedule.every().day.at(f"{update_hour:02d}:00").do(
        run_once, update_limit=30, report_limit=0
    )

    # 报告生成 - 每天下午
    schedule.every().day.at(f"{report_hour:02d}:00").do(
        run_once, update_limit=0, report_limit=15
    )

    # 每周日进行全面更新
    schedule.every().sunday.at("10:00").do(
        run_once, update_limit=100, report_limit=30
    )

    logger.info("\n已注册的定时任务:")
    for job in schedule.get_jobs():
        logger.info(f"  - {job}")

    # 循环执行
    while True:
        schedule.run_pending()
        time.sleep(60)


def main():
    parser = argparse.ArgumentParser(description="财务数据定时更新调度器")
    parser.add_argument("--once", action="store_true",
                        help="立即执行一次然后退出")
    parser.add_argument("--report-only", action="store_true",
                        help="只生成报告")
    parser.add_argument("--update-only", action="store_true",
                        help="只更新数据")
    parser.add_argument("--daemon", action="store_true",
                        help="以守护进程模式运行")
    parser.add_argument("--update-limit", type=int, default=20,
                        help="每次更新的公司数")
    parser.add_argument("--report-limit", type=int, default=10,
                        help="每次生成的报告数")
    args = parser.parse_args()

    if args.once:
        run_once(update_limit=args.update_limit,
                 report_limit=args.report_limit)
    elif args.report_only:
        logger.info("📝 仅生成报告")
        generated = generate_reports_for_all(limit=args.report_limit)
        logger.info(f"✅ 生成 {generated} 份报告")
    elif args.update_only:
        logger.info("📥 仅更新数据")
        updated = update_financial_data(limit=args.update_limit)
        logger.info(f"✅ 更新 {updated} 家公司")
    else:
        # 守护模式
        if args.daemon:
            import daemon
            with daemon.DaemonContext():
                start_scheduler()
        else:
            start_scheduler()


if __name__ == "__main__":
    main()
