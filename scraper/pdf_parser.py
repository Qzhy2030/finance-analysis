"""
PDF年报解析器
从巨潮资讯下载的PDF年报中提取核心财务数据
支持：资产负债表、利润表、现金流量表关键科目
"""
import re
import io
from typing import Optional, Dict, List, Any
from datetime import datetime

import pdfplumber


class PdfReportParser:
    """
    PDF年报解析器
    使用 pdfplumber 提取表格和文本数据
    """

    # 关键财务科目关键词（支持模糊匹配）
    KEY_ITEMS = {
        "营业收入": "revenue",
        "营业总收入": "revenue",
        "净利润": "net_profit",
        "归属于上市公司股东的净利润": "net_profit_parent",
        "总资产": "total_assets",
        "资产总计": "total_assets",
        "负债合计": "total_liabilities",
        "归属于上市公司股东的净资产": "equity_parent",
        "净资产": "equity",
        "基本每股收益": "eps",
        "加权平均净资产收益率": "roe",
        "经营活动产生的现金流量净额": "operate_cashflow",
        "投资活动产生的现金流量净额": "invest_cashflow",
        "筹资活动产生的现金流量净额": "finance_cashflow",
        "研发投入": "rd_expense",
        "毛利率": "gross_margin",
    }

    def __init__(self):
        self.current_year = datetime.now().year

    def parse_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        解析PDF年报文件，提取关键财务数据
        :param pdf_path: PDF文件路径
        :return: {company_info, financial_data, segments, projects}
        """
        result = {
            "company_info": {},
            "financial_data": {},
            "year": None,
            "segments": [],
            "projects": [],
            "raw_tables_count": 0,
        }

        try:
            with pdfplumber.open(pdf_path) as pdf:
                result["raw_tables_count"] = len(pdf.pages)

                # 从首页提取公司名称和年份
                first_page = pdf.pages[0]
                first_text = first_page.extract_text() or ""
                result["company_info"] = self._parse_company_info(first_text)
                result["year"] = self._detect_year(first_text)

                # 遍历所有页面提取表格
                all_tables = []
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables:
                        if table:
                            all_tables.append(table)

                # 从表格中提取财务数据
                for table in all_tables:
                    self._extract_financial_data(table, result)

                # 尝试提取业务板块
                full_text = ""
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"
                result["segments"] = self._parse_segments(full_text)
                result["projects"] = self._parse_projects(full_text)

        except Exception as e:
            print(f"[PDF解析] 错误: {e}")
            result["error"] = str(e)

        return result

    def _parse_company_info(self, text: str) -> Dict[str, str]:
        """从首页提取公司基本信息"""
        info = {}
        patterns = {
            "company_name": r"(?:公司名称|公司全称)[：:]\s*(.+)",
            "stock_code": r"(?:股票代码|证券代码)[：:]\s*(\d{6})",
            "stock_short": r"(?:股票简称|证券简称)[：:]\s*(.+)",
        }
        for key, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                info[key] = match.group(1).strip()
        return info

    def _detect_year(self, text: str) -> Optional[int]:
        """检测报告年份"""
        patterns = [
            r"(\d{4})\s*年\s*(?:年度|年报|年度报告)",
            r"(\d{4})\s*年度报告",
            r"二〇(\d{2})年年度报告",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    return int(f"20{match.group(1)}")
        return None

    def _extract_financial_data(self, table: List[List], result: Dict[str, Any]):
        """从表格中提取财务数据"""
        if not table or len(table) < 2:
            return

        # 获取表头（第一行）
        header = [str(c or "").strip() for c in table[0]]
        header_text = " ".join(header)

        # 判断表格类型
        is_balance = any(k in header_text for k in ["资产", "负债", "权益"])
        is_income = any(k in header_text for k in ["营业收入", "营业成本", "利润"])
        is_cashflow = any(k in header_text for k in ["现金流量", "经营活动"])

        report_type = ""
        if is_balance:
            report_type = "balance"
        elif is_income:
            report_type = "income"
        elif is_cashflow:
            report_type = "cashflow"

        if not report_type:
            return

        # 确保 financial_data 中有该类型
        if report_type not in result["financial_data"]:
            result["financial_data"][report_type] = []

        # 找到金额所在的列索引
        amount_cols = []
        for i, h in enumerate(header):
            if re.search(r"(\d{4})", h):  # 包含年份
                amount_cols.append(i)
        if not amount_cols:
            amount_cols = [-1]  # 最后一列

        # 解析数据行
        for row in table[1:]:
            if not row or len(row) < 2:
                continue
            item_name = str(row[0] or "").strip()
            if not item_name or len(item_name) > 50:
                continue

            # 提取金额
            amounts = {}
            for col_idx in amount_cols:
                if col_idx >= 0 and col_idx < len(row):
                    val = self._parse_amount(str(row[col_idx] or "0"))
                    year_label = header[col_idx] if col_idx < len(header) else str(col_idx)
                    amounts[year_label] = val

            result["financial_data"][report_type].append({
                "item_name": item_name,
                "amounts": amounts,
            })

    def _parse_amount(self, text: str) -> Optional[float]:
        """解析金额字符串"""
        text = text.replace(",", "").replace(" ", "")
        # 匹配数字（可能是负数）
        match = re.search(r"-?[\d]+\.?\d*", text)
        if match:
            val = float(match.group())
            # 如果是万元单位的数据，通常财报以元为单位
            return val
        return None

    def _parse_segments(self, text: str) -> List[Dict]:
        """解析主营业务板块"""
        segments = []
        # 查找"主营业务"相关段落
        section_start = re.search(r"(?:主营业务|营业收入.*构成|分[产品行业]?).*", text)
        if not section_start:
            return segments

        # 尝试从表格模式中提取
        lines = text.split("\n")
        in_segment = False
        for line in lines:
            if re.search(r"(主营业务|营业收入.*构成|分[产品行业])", line):
                in_segment = True
                continue
            if in_segment:
                # 匹配"XX业务 XX万元 XX%"
                match = re.match(r"(.{2,20}?)\s+([\d,]+\.?\d*)\s*万?\s*(\d+\.?\d*%)?", line)
                if match:
                    segments.append({
                        "segment_name": match.group(1).strip(),
                        "revenue": float(match.group(2).replace(",", "")),
                        "revenue_pct": self._parse_pct(match.group(3)),
                    })
                elif re.search(r"^(?:合计|总计|报告期内)", line):
                    break
        return segments

    def _parse_projects(self, text: str) -> List[Dict]:
        """解析在建工程项目"""
        projects = []
        section = re.search(r"在\s*建\s*工\s*程.*?(?=\n\n|\Z)", text, re.DOTALL)
        if not section:
            return projects

        lines = section.group().split("\n")
        for line in lines:
            match = re.match(r"(.{4,40}?)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+(\d+\.?\d*)%?", line)
            if match:
                projects.append({
                    "project_name": match.group(1).strip(),
                    "budget_amount": float(match.group(2).replace(",", "")),
                    "invested_amount": float(match.group(3).replace(",", "")),
                    "progress_pct": float(match.group(4)) / 100,
                })
        return projects

    @staticmethod
    def _parse_pct(text: Optional[str]) -> Optional[float]:
        if not text:
            return None
        match = re.search(r"([\d.]+)%", text)
        return float(match.group(1)) / 100 if match else None


def parse_pdf_report(pdf_path: str) -> Dict[str, Any]:
    """快捷解析函数"""
    parser = PdfReportParser()
    return parser.parse_pdf(pdf_path)
