"""
图文并茂的HTML财报分析报告生成器
使用 ECharts 生成营业收入/净利润趋势图
"""
import json
import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from config import REPORTS_DIR


class ReportGenerator:
    """
    财报分析报告 HTML 生成器
    将AI生成的Markdown报告 + ECharts图表 拼装为完整的HTML
    """

    # ECharts CDN
    ECHARTS_CDN = "https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"

    # HTML 模板
    HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report_title}</title>
    <script src="{echarts_cdn}"></script>
    <style>
        :root {{
            --primary: #1a73e8;
            --primary-light: #e8f0fe;
            --text-primary: #1f2937;
            --text-secondary: #6b7280;
            --bg: #ffffff;
            --bg-card: #f8fafc;
            --border: #e5e7eb;
            --accent-green: #10b981;
            --accent-red: #ef4444;
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                         "Helvetica Neue", Arial, "Noto Sans SC", sans-serif;
            color: var(--text-primary);
            background: var(--bg);
            line-height: 1.8;
        }}

        .container {{
            max-width: 1000px;
            margin: 0 auto;
            padding: 40px 24px;
        }}

        /* 报告头部 */
        .report-header {{
            text-align: center;
            padding: 48px 0 40px;
            border-bottom: 2px solid var(--primary);
            margin-bottom: 40px;
        }}
        .report-header h1 {{
            font-size: 28px;
            color: var(--primary);
            margin-bottom: 8px;
        }}
        .report-header .meta {{
            color: var(--text-secondary);
            font-size: 14px;
        }}

        /* 图表容器 */
        .chart-section {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 32px;
        }}
        .chart-section h2 {{
            font-size: 20px;
            color: var(--text-primary);
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 1px solid var(--border);
        }}
        .chart-box {{
            width: 100%;
            height: 420px;
        }}

        /* 分析报告内容 */
        .report-content {{
            padding: 24px 0;
        }}
        .report-content h2 {{
            font-size: 22px;
            color: var(--primary);
            margin: 32px 0 16px;
            padding-bottom: 8px;
            border-bottom: 2px solid var(--primary-light);
        }}
        .report-content h3 {{
            font-size: 18px;
            margin: 24px 0 12px;
            color: var(--text-primary);
        }}
        .report-content p {{
            margin: 12px 0;
            text-align: justify;
        }}
        .report-content table {{
            width: 100%;
            border-collapse: collapse;
            margin: 16px 0;
            font-size: 14px;
        }}
        .report-content th {{
            background: var(--primary-light);
            color: var(--primary);
            font-weight: 600;
            padding: 10px 12px;
            text-align: center;
            border: 1px solid var(--border);
        }}
        .report-content td {{
            padding: 8px 12px;
            border: 1px solid var(--border);
            text-align: right;
        }}
        .report-content td:first-child {{
            text-align: left;
            font-weight: 500;
        }}
        .report-content ul, .report-content ol {{
            margin: 12px 0;
            padding-left: 24px;
        }}
        .report-content li {{
            margin: 6px 0;
        }}
        .report-content strong {{
            color: var(--primary);
        }}

        /* 数据卡片 */
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 32px;
        }}
        .kpi-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .kpi-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }}
        .kpi-card .label {{
            font-size: 13px;
            color: var(--text-secondary);
            margin-bottom: 8px;
        }}
        .kpi-card .value {{
            font-size: 24px;
            font-weight: 700;
            color: var(--text-primary);
        }}
        .kpi-card .change {{
            font-size: 13px;
            margin-top: 4px;
        }}
        .kpi-card .change.up {{ color: var(--accent-green); }}
        .kpi-card .change.down {{ color: var(--accent-red); }}

        /* 页脚 */
        .report-footer {{
            text-align: center;
            padding: 32px 0;
            color: var(--text-secondary);
            font-size: 13px;
            border-top: 1px solid var(--border);
            margin-top: 48px;
        }}

        @media (max-width: 640px) {{
            .container {{ padding: 20px 12px; }}
            .report-header h1 {{ font-size: 22px; }}
            .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }}
        }}
    </style>
</head>
<body>
    <div class="container">
        {header_html}
        {kpi_html}
        {chart_html}
        <div class="report-content">
            {content_html}
        </div>
        <div class="report-footer">
            <p>本报告由财务数据分析平台自动生成 | 生成时间：{generate_time}</p>
            <p>数据来源：巨潮资讯网、同花顺等公开数据</p>
            <p style="font-size:12px; margin-top:8px; color:#9ca3af;">免责声明：本报告仅供参考，不构成投资建议</p>
        </div>
    </div>

    <script>
        {chart_scripts}
    </script>
</body>
</html>"""

    def generate(self, company_name: str, stock_code: str,
                 financial_data: Dict[str, Any],
                 analysis_markdown: str) -> str:
        """
        生成完整的HTML财报分析报告
        :return: HTML字符串
        """
        highlights = financial_data.get("highlights", [])

        # 1. 报告标题
        latest_year = highlights[0]["report_year"] if highlights else datetime.now().year
        report_title = f"{company_name}({stock_code}) {latest_year}年度财务分析报告"

        # 2. 头部
        header_html = f"""
        <div class="report-header">
            <h1>{company_name}（{stock_code}）财务分析报告</h1>
            <div class="meta">{latest_year}年度 | 数据来源：巨潮资讯网、同花顺</div>
        </div>
        """

        # 3. KPI 卡片
        kpi_html = self._build_kpi_cards(highlights)

        # 4. ECharts 图表
        chart_html, chart_scripts = self._build_charts(company_name, highlights)

        # 5. 内容：Markdown 转 HTML
        content_html = self._markdown_to_html(analysis_markdown)

        # 6. 拼装
        return self.HTML_TEMPLATE.format(
            report_title=report_title,
            header_html=header_html,
            kpi_html=kpi_html,
            chart_html=chart_html,
            content_html=content_html,
            chart_scripts=chart_scripts,
            generate_time=datetime.now().strftime("%Y-%m-%d %H:%M"),
            echarts_cdn=self.ECHARTS_CDN,
        )

    def save(self, html: str, filename: Optional[str] = None) -> str:
        """保存HTML报告到文件"""
        if not filename:
            filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        save_path = str(REPORTS_DIR / filename)
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"[报告] 已保存: {save_path}")
        return save_path

    # ── 内部方法 ──────────────────────────────────────

    def _build_kpi_cards(self, highlights: List[Dict]) -> str:
        """构建KPI指标卡片"""
        if not highlights:
            return ""

        latest = highlights[0]
        prev = highlights[1] if len(highlights) > 1 else None

        cards = []

        def format_val(val, unit="万元"):
            if val is None:
                return "N/A"
            val_f = float(val)
            if val_f >= 10000:
                return f"{val_f / 10000:.2f}亿"
            return f"{val_f:,.2f}"

        def format_change(current, previous):
            if current is None or previous is None or previous == 0:
                return "", ""
            change = (float(current) / float(previous) - 1) * 100
            cls = "up" if change >= 0 else "down"
            return f"{cls}", f"{change:+.1f}%"

        kpis = [
            ("营业收入", "revenue", format_val(latest.get("revenue"))),
            ("净利润", "net_profit", format_val(latest.get("net_profit"))),
            ("总资产", "total_assets", format_val(latest.get("total_assets"))),
            ("净资产", "equity", format_val(latest.get("equity"))),
            ("毛利率", "gross_margin",
             f"{float(latest.get('gross_margin', 0)) * 100:.1f}%" if latest.get("gross_margin") else "N/A"),
            ("ROE", "roe",
             f"{float(latest.get('roe', 0)) * 100:.1f}%" if latest.get("roe") else "N/A"),
        ]

        for label, key, value in kpis:
            change_cls, change_text = "", ""
            if prev and latest.get(key) and prev.get(key):
                change_cls, change_text = format_change(latest[key], prev[key])

            change_html = ""
            if change_text:
                change_html = f'<div class="change {change_cls}">{change_text} 同比</div>'

            cards.append(f"""
            <div class="kpi-card">
                <div class="label">{label}</div>
                <div class="value">{value}</div>
                {change_html}
            </div>""")

        return f'<div class="kpi-grid">{"".join(cards)}</div>'

    def _build_charts(self, company_name: str, highlights: List[Dict]) -> tuple:
        """构建ECharts收入/利润趋势图"""
        if not highlights or len(highlights) < 2:
            return "", ""

        # 按年份排序
        sorted_data = sorted(highlights, key=lambda x: x["report_year"])
        years = [str(h["report_year"]) for h in sorted_data]
        revenues = [float(h.get("revenue", 0)) / 10000 for h in sorted_data]  # 转换为亿元
        profits = [float(h.get("net_profit", 0)) / 10000 for h in sorted_data]

        chart_id = "trendChart"

        chart_html = f"""
        <div class="chart-section">
            <h2>📈 {company_name} 营业收入与净利润趋势</h2>
            <div id="{chart_id}" class="chart-box"></div>
        </div>
        """

        chart_script = f"""
        (function() {{
            var chart = echarts.init(document.getElementById('{chart_id}'));
            var option = {{
                tooltip: {{
                    trigger: 'axis',
                    axisPointer: {{ type: 'cross' }},
                    formatter: function(params) {{
                        var result = params[0].axisValue + '<br/>';
                        params.forEach(function(p) {{
                            result += p.marker + ' ' + p.seriesName + ': '
                                   + p.value.toFixed(2) + ' 亿元<br/>';
                        }});
                        return result;
                    }}
                }},
                legend: {{
                    data: ['营业收入', '净利润'],
                    top: 0,
                    textStyle: {{ fontSize: 14 }}
                }},
                grid: {{
                    left: '3%', right: '4%', bottom: '3%',
                    containLabel: true
                }},
                xAxis: {{
                    type: 'category',
                    data: {json.dumps(years)},
                    axisLabel: {{ fontSize: 13 }},
                    axisLine: {{ lineStyle: {{ color: '#e5e7eb' }} }}
                }},
                yAxis: {{
                    type: 'value',
                    name: '亿元',
                    nameTextStyle: {{ fontSize: 13 }},
                    splitLine: {{ lineStyle: {{ type: 'dashed', color: '#e5e7eb' }} }}
                }},
                series: [
                    {{
                        name: '营业收入',
                        type: 'bar',
                        data: {json.dumps(revenues)},
                        itemStyle: {{
                            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                                {{ offset: 0, color: '#1a73e8' }},
                                {{ offset: 1, color: '#83b3f3' }}
                            ]),
                            borderRadius: [4, 4, 0, 0]
                        }},
                        emphasis: {{
                            itemStyle: {{ color: '#1557b0' }}
                        }}
                    }},
                    {{
                        name: '净利润',
                        type: 'line',
                        data: {json.dumps(profits)},
                        smooth: true,
                        symbol: 'circle',
                        symbolSize: 8,
                        lineStyle: {{ width: 3, color: '#10b981' }},
                        itemStyle: {{ color: '#10b981' }},
                        areaStyle: {{
                            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                                {{ offset: 0, color: 'rgba(16, 185, 129, 0.3)' }},
                                {{ offset: 1, color: 'rgba(16, 185, 129, 0.03)' }}
                            ])
                        }}
                    }}
                ]
            }};
            chart.setOption(option);
            window.addEventListener('resize', function() {{ chart.resize(); }});
        }})();
        """

        return chart_html, chart_script

    def _markdown_to_html(self, md: str) -> str:
        """简易Markdown转HTML"""
        if not md:
            return "<p>暂无分析内容</p>"

        html = md

        # 代码块（优先处理）
        html = re.sub(r'```(\w*)\n(.*?)```', r'<pre><code>\2</code></pre>', html, flags=re.DOTALL)

        # 标题
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)

        # 表格
        html = re.sub(
            r'\|(.+)\|\n\|[-| ]+\|\n((?:\|.+\|\n?)*)',
            self._convert_table,
            html,
            flags=re.MULTILINE
        )

        # 加粗
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)

        # 列表
        html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        html = re.sub(r'(<li>.*</li>\n?)+', r'<ul>\g<0></ul>', html, flags=re.DOTALL)

        # 段落
        paragraphs = []
        for line in html.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith(('<h', '<li', '<ul', '<pre', '<table')):
                paragraphs.append(line)
            else:
                paragraphs.append(f"<p>{line}</p>")

        return "\n".join(paragraphs)

    def _convert_table(self, match) -> str:
        """转换Markdown表格为HTML表格"""
        lines = match.group(0).strip().split("\n")
        if len(lines) < 2:
            return match.group(0)

        # 表头
        header_cells = [c.strip() for c in lines[0].strip("|").split("|")]
        html = "<table><thead><tr>"
        for cell in header_cells:
            html += f"<th>{cell}</th>"
        html += "</tr></thead><tbody>"

        # 数据行
        for line in lines[2:]:
            cells = [c.strip() for c in line.strip("|").split("|")]
            html += "<tr>"
            for cell in cells:
                html += f"<td>{cell}</td>"
            html += "</tr>"

        html += "</tbody></table>"
        return html


def generate_report(company_name: str, stock_code: str,
                    financial_data: Dict[str, Any],
                    analysis_markdown: str) -> str:
    """快捷生成并保存报告"""
    gen = ReportGenerator()
    html = gen.generate(company_name, stock_code, financial_data, analysis_markdown)
    return gen.save(html)
