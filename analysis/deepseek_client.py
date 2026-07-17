"""
DeepSeek API 客户端
用于调用大模型生成财报分析报告
"""
import json
from typing import Optional, List, Dict, Any

import httpx

from config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL, DEEPSEEK_MODEL


class DeepSeekClient:
    """DeepSeek API 客户端"""

    def __init__(self, api_key: str = DEEPSEEK_API_KEY):
        self.api_key = api_key
        self.api_url = DEEPSEEK_API_URL
        self.model = DEEPSEEK_MODEL

    def chat(self, messages: List[Dict], temperature: float = 0.7,
             max_tokens: int = 4096) -> Optional[str]:
        """
        调用 DeepSeek Chat API
        :param messages: 对话消息列表 [{"role": "user", "content": "..."}]
        :return: 模型回复文本
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        try:
            with httpx.Client(timeout=120) as client:
                resp = client.post(self.api_url, json=payload, headers=headers)
                resp.raise_for_status()
                result = resp.json()
                return result["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            print(f"[DeepSeek] HTTP错误: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            print(f"[DeepSeek] 调用失败: {e}")
            return None

    def analyze_financial_report(self, company_name: str, stock_code: str,
                                 financial_data: Dict[str, Any]) -> Optional[str]:
        """
        生成公司的财务分析报告
        :param company_name: 公司名称
        :param stock_code: 股票代码
        :param financial_data: 财务数据字典
        :return: Markdown格式的分析报告
        """
        # 构建财务数据摘要文本
        data_summary = self._build_data_summary(company_name, stock_code, financial_data)

        system_prompt = """你是一位资深财务分析师，精通中国A股上市公司财报分析。
请基于提供的财务数据，撰写一份专业的财务分析报告。

报告必须包含以下板块（严格按此结构）：
1. **公司概况** - 公司基本信息、主营业务、行业地位
2. **财务表现分析** - 营业收入、净利润、毛利率、ROE等核心指标的趋势分析
3. **主营业务分析** - 各业务板块的收入构成和盈利能力
4. **新增业务与战略布局** - 公司在拓展哪些新业务领域
5. **在建工程项目** - 重大在建项目的投资规模、进度和未来影响
6. **风险与挑战** - 面临的主要经营风险和财务风险
7. **发展前景与投资价值** - 对公司未来3-5年的发展展望

要求：
- 使用专业、客观的财务分析语言
- 每项分析必须有数据支撑
- 保持中国会计准则的术语规范
- 总字数1500-2000字
- 使用Markdown格式输出
- 数据单位统一为"万元"，大额数据可使用"亿元"\n"""

        user_prompt = f"""请对{company_name}({stock_code})进行全面的财务分析。

以下是该公司的财务数据：

{data_summary}

请根据上述数据，撰写完整的财务分析报告。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        return self.chat(messages, temperature=0.3, max_tokens=8192)

    def _build_data_summary(self, company_name: str, stock_code: str,
                            data: Dict[str, Any]) -> str:
        """构建财务数据摘要字符串"""
        lines = [f"公司名称：{company_name}", f"股票代码：{stock_code}"]

        highlights = data.get("highlights", [])
        if highlights:
            lines.append("\n## 近5年财务数据汇总")
            lines.append("| 年份 | 营业收入(万元) | 净利润(万元) | 总资产(万元) | 净资产(万元) | 毛利率 | 净利率 | ROE | EPS |")
            lines.append("|------|---------------|-------------|-------------|------------|-------|-------|-----|-----|")
            for h in highlights:
                lines.append(
                    f"| {h.get('report_year', '')} "
                    f"| {h.get('revenue', 'N/A')} "
                    f"| {h.get('net_profit', 'N/A')} "
                    f"| {h.get('total_assets', 'N/A')} "
                    f"| {h.get('equity', 'N/A')} "
                    f"| {h.get('gross_margin', 'N/A')} "
                    f"| {h.get('net_margin', 'N/A')} "
                    f"| {h.get('roe', 'N/A')} "
                    f"| {h.get('eps', 'N/A')} |"
                )

        segments = data.get("segments", [])
        if segments:
            lines.append("\n## 主营业务构成")
            for s in segments:
                lines.append(f"- {s.get('segment_name', '')}: "
                             f"收入占比 {s.get('revenue_pct', 'N/A')}")

        projects = data.get("projects", [])
        if projects:
            lines.append("\n## 在建工程项目")
            for p in projects:
                lines.append(
                    f"- {p.get('project_name', '')}: "
                    f"预算 {p.get('budget_amount', 'N/A')}万元, "
                    f"已投入 {p.get('invested_amount', 'N/A')}万元, "
                    f"进度 {p.get('progress_pct', 'N/A')}"
                )

        return "\n".join(lines)


# 全局单例
_client: Optional[DeepSeekClient] = None


def get_deepseek() -> DeepSeekClient:
    global _client
    if _client is None:
        _client = DeepSeekClient()
    return _client
