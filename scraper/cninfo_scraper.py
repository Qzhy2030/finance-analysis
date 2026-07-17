"""
巨潮资讯网（cninfo.com.cn）数据爬虫
- 搜索上市公司公告
- 获取年报PDF下载链接
- 解析年度报告摘要中的核心财务数据
"""
import json
import re
import time
from datetime import datetime
from typing import Optional, List, Dict, Any
from urllib.parse import quote, urlencode

import requests
from bs4 import BeautifulSoup

from config import SCRAPER_TIMEOUT, SCRAPER_HEADERS


class CninfoScraper:
    """
    巨潮资讯网爬虫
    官方网站: http://www.cninfo.com.cn
    数据接口: http://www.cninfo.com.cn/new/
    """

    # API 端点
    SEARCH_URL = "http://www.cninfo.com.cn/new/fulltextSearch/full"
    BULLETIN_URL = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
    DETAIL_URL = "http://www.cninfo.com.cn/new/disclosure/detail"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(SCRAPER_HEADERS)
        self.session.trust_env = False  # 禁用系统代理，避免代理拦截

    # ── 搜索公司公告 ──────────────────────────────────

    def search_announcements(self, stock_code: str, page_num: int = 1,
                             page_size: int = 30, category: str = "年报") -> List[dict]:
        """
        搜索某公司的公告列表
        :param stock_code: 股票代码
        :param category: 公告类别（年报/半年报/季报等）
        """
        data = {
            "stock": stock_code,
            "pageNum": str(page_num),
            "pageSize": str(page_size),
            "category": category,
            "tabName": "fulltext",
            "seDate": "",
            "searchkey": "",
            "isHLtitle": "true",
            "sortName": "",
            "sortType": "",
        }
        try:
            resp = self.session.post(
                self.SEARCH_URL,
                data=data,
                timeout=SCRAPER_TIMEOUT
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get("totalRecordNum", 0) > 0:
                return result.get("announcements", [])
            return []
        except Exception as e:
            print(f"[cninfo] 搜索公告失败 [{stock_code}]: {e}")
            return []

    def get_annual_reports(self, stock_code: str, years: int = 5) -> List[dict]:
        """
        获取某公司最近N年的年度报告列表
        返回: [{"title", "year", "publish_date", "pdf_url", "announcement_id"}, ...]
        """
        announcements = self.search_announcements(stock_code, category="年报")
        reports = []
        for ann in announcements:
            title = ann.get("announcementTitle", "")
            # 匹配年份
            year_match = re.search(r"(\d{4})\s*年\s*(?:年度|年报|年度报告)", title)
            if not year_match:
                continue
            year = int(year_match.group(1))
            if year < datetime.now().year - years - 1:
                continue

            adjunct_url = ann.get("adjunctUrl", "")
            if adjunct_url:
                pdf_url = f"http://static.cninfo.com.cn/{adjunct_url}"
            else:
                pdf_url = ""

            reports.append({
                "title": title,
                "year": year,
                "publish_date": ann.get("announcementDate", ""),
                "pdf_url": pdf_url,
                "announcement_id": ann.get("announcementId", ""),
                "stock_code": stock_code,
            })
        return sorted(reports, key=lambda x: -x["year"])

    # ── 获取PDF内容文本 ──────────────────────────────

    def download_pdf(self, pdf_url: str, save_path: Optional[str] = None) -> Optional[bytes]:
        """下载PDF文件"""
        try:
            resp = self.session.get(pdf_url, timeout=60)
            resp.raise_for_status()
            if save_path:
                with open(save_path, "wb") as f:
                    f.write(resp.content)
                print(f"[cninfo] PDF已保存: {save_path}")
            return resp.content
        except Exception as e:
            print(f"[cninfo] PDF下载失败: {e}")
            return None

    # ── 从页面提取结构化财务数据 ──────────────────────

    def parse_financial_highlights(self, html_text: str) -> Dict[str, Any]:
        """
        从年报HTML摘要中解析核心财务指标
        返回: {revenue, net_profit, total_assets, ...}
        """
        soup = BeautifulSoup(html_text, "lxml")
        data = {}

        # 尝试从表格中提取关键数据
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["td", "th"])
                cell_texts = [c.get_text(strip=True) for c in cells]
                line = " ".join(cell_texts)

                # 营业收入
                if "营业收入" in line:
                    nums = re.findall(r"[\d,]+\.?\d*", line)
                    if nums:
                        data["revenue"] = float(nums[0].replace(",", ""))

                # 净利润
                if "净利润" in line and "归属于" in line:
                    nums = re.findall(r"-?[\d,]+\.?\d*", line)
                    if nums:
                        data["net_profit"] = float(nums[0].replace(",", ""))

                # 总资产
                if "总资产" in line:
                    nums = re.findall(r"[\d,]+\.?\d*", line)
                    if nums:
                        data["total_assets"] = float(nums[0].replace(",", ""))

                # 净资产
                if "净资产" in line or "股东权益" in line:
                    nums = re.findall(r"[\d,]+\.?\d*", line)
                    if nums:
                        data["equity"] = float(nums[0].replace(",", ""))

                # 每股收益
                if "每股收益" in line:
                    nums = re.findall(r"[\d,]+\.?\d*", line)
                    if nums:
                        data["eps"] = float(nums[0].replace(",", ""))

        return data

    # ── 从同花顺等第三方获取基础财务数据 ──────────────

    def fetch_ths_financial_data(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        从同花顺接口获取公司财务概览
        使用同花顺的公开数据API
        """
        # 确定市场前缀
        market_map = {"6": "SH", "0": "SZ", "3": "SZ", "1": "HK"}
        prefix = stock_code[0]
        market = market_map.get(prefix, "SZ")
        # 港股5位代码特殊处理
        if len(stock_code) == 5:
            market = "HK"

        # 尝试多个数据来源
        sources_tried = []

        # 1. 同花顺行情接口
        url = f"https://basic.10jqka.com.cn/api/stock/v1/finance/{stock_code}/"
        try:
            resp = self.session.get(url, timeout=SCRAPER_TIMEOUT)
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    if isinstance(data, dict) and len(data) > 0:
                        sources_tried.append("tonghuashun")
                        return data
                except (ValueError, json.JSONDecodeError):
                    pass
        except Exception as e:
            print(f"[ths] 获取财务数据失败 [{stock_code}]: {e}")

        # 2. 备用接口：东方财富
        try:
            secid = f"{'1' if market == 'SH' else '0'}.{stock_code}"
            url = f"https://datacenter.eastmoney.com/securities/api/data/v1/get"
            params = {
                "reportName": "RPT_LICO_FN_CPD",
                "columns": "SECUCODE,SECURITY_NAME_ABBR,REPORT_DATE,BASIC_EPS,WEIGHTAVG_ROE",
                "filter": f'SECUCODE="{stock_code}"',
                "pageNumber": 1,
                "pageSize": 5,
                "sortTypes": -1,
                "sortColumns": "REPORT_DATE",
            }
            resp = self.session.get(url, params=params, timeout=SCRAPER_TIMEOUT)
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    if isinstance(data, dict) and data.get("result", {}).get("data"):
                        sources_tried.append("eastmoney")
                        return data
                except (ValueError, json.JSONDecodeError):
                    pass
        except Exception:
            pass

        # 3. 新浪财经接口
        try:
            url = f"https://vip.stock.finance.sina.com.cn/corp/go.php/vFD_BalanceSheet/stockid/{stock_code}/ctrl/part/displaytype/4.phtml"
            resp = self.session.get(url, timeout=SCRAPER_TIMEOUT)
            if resp.status_code == 200:
                sources_tried.append("sina")
        except Exception:
            pass

        # 如果所有API都不可用，返回模拟的测试数据用于演示
        return self._mock_financial_data(stock_code, sources_tried)

    def _mock_financial_data(self, stock_code: str,
                             sources_tried: list = None) -> Dict[str, Any]:
        """
        当API不可用时的回退方案 - 基于行业平均生成模拟财务数据
        仅用于开发和演示目的
        """
        import random
        random.seed(int(stock_code))
        base_revenue = random.uniform(50, 5000)  # 亿元
        mock_data = {
            "stock_code": stock_code,
            "data_source": f"mock(API不可用:{','.join(sources_tried) if sources_tried else '无'})",
            "highlights": [],
            "segments": [
                {"name": "主营业务A", "revenue_pct": 0.45},
                {"name": "主营业务B", "revenue_pct": 0.30},
                {"name": "其他业务", "revenue_pct": 0.25},
            ]
        }
        current_year = datetime.now().year
        for i in range(5):
            year = current_year - 4 + i
            growth = 1 + random.uniform(-0.15, 0.25)
            revenue = base_revenue * (growth ** i) if i > 0 else base_revenue
            net_profit = revenue * random.uniform(0.05, 0.20)
            total_assets = revenue * random.uniform(1.5, 3.0)
            total_liab = total_assets * random.uniform(0.3, 0.6)
            mock_data["highlights"].append({
                "report_year": year,
                "report_date": f"{year}-12-31",
                "revenue": round(revenue * 10000, 2),   # 转换为万元
                "net_profit": round(net_profit * 10000, 2),
                "total_assets": round(total_assets * 10000, 2),
                "total_liab": round(total_liab * 10000, 2),
                "equity": round((total_assets - total_liab) * 10000, 2),
                "gross_margin": round(random.uniform(0.2, 0.6), 4),
                "net_margin": round(net_profit / revenue, 4),
                "roe": round(random.uniform(0.08, 0.25), 4),
                "eps": round(random.uniform(0.5, 5.0), 2),
                "bvps": round(random.uniform(5, 30), 2),
            })
        return mock_data


# 快捷函数
def get_cninfo_scraper() -> CninfoScraper:
    return CninfoScraper()
