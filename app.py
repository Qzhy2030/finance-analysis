"""
财务数据分析平台 - Streamlit 主应用
功能：公司搜索、财报数据获取、AI分析报告生成、HTML输出
"""
import sys
import os
from pathlib import Path

# 确保项目根目录在导入路径中
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import pandas as pd
from datetime import datetime

from config import PAGE_TITLE, PAGE_ICON, LAYOUT
from database.company_mapping import get_mapper
from database.db_manager import get_db
from scraper.cninfo_scraper import get_cninfo_scraper
from analysis.deepseek_client import get_deepseek
from analysis.report_generator import generate_report

# ── 页面配置 ──────────────────────────────────────────
st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout=LAYOUT,
    initial_sidebar_state="expanded",
)

# ── 初始化全局对象 ────────────────────────────────────
@st.cache_resource
def init_services():
    return {
        "mapper": get_mapper(),
        "db": get_db(),
        "scraper": get_cninfo_scraper(),
        "ai": get_deepseek(),
    }

services = init_services()
mapper = services["mapper"]
db = services["db"]
scraper = services["scraper"]
ai_client = services["ai"]

# ── 侧边栏导航 ────────────────────────────────────────
st.sidebar.markdown(f"""
<div style="text-align:center; padding:20px 0;">
    <h1 style="font-size:24px; margin:0;">📊</h1>
    <h2 style="font-size:18px; margin:8px 0 0;">财务数据分析平台</h2>
    <p style="font-size:12px; color:#888;">{datetime.now().strftime('%Y-%m-%d')}</p>
</div>
""", unsafe_allow_html=True)

# 已缓存的公司数据库统计
company_count = mapper.count
st.sidebar.info(f"📚 已收录 {company_count} 家上市公司")

# 系统状态指示器
with st.sidebar.expander("⚙️ 系统状态", expanded=False):
    st.markdown("**AI引擎:** ✅ DeepSeek已连接")
    st.markdown("**数据源:** 🔄 巨潮资讯/同花顺")
    st.markdown(f"**数据库:** 🗄️ SQLite (可切换PostgreSQL)")
    st.markdown("**报告目录:** 📁 reports/")
    st.markdown("---")
    st.markdown("**一键部署脚本:**")
    st.code("bash deploy/deploy.sh", language="bash")
    st.markdown("**启动定时任务:**")
    st.code("python scripts/scheduler.py", language="bash")

st.sidebar.markdown("---")

page = st.sidebar.radio(
    "功能导航",
    ["🔍 公司查询与财报", "📈 财务数据看板", "🤖 AI分析报告", "📄 报告管理", "🔄 数据同步中心", "⚙️ 数据管理"],
    index=0,
)

st.sidebar.markdown("---")
st.sidebar.caption("数据来源：巨潮资讯网、同花顺 | 技术支持：DeepSeek AI")

# ══════════════════════════════════════════════════════
# 页面1：公司查询与财报
# ══════════════════════════════════════════════════════
if page == "🔍 公司查询与财报":
    st.title("🔍 公司查询与财报数据")

    # 搜索区域
    col1, col2 = st.columns([3, 1])
    with col1:
        search_term = st.text_input(
            "输入公司名称或股票代码（支持模糊搜索）",
            placeholder="例如：贵州茅台、贵州、600519、茅台",
            label_visibility="collapsed",
        )
    with col2:
        search_btn = st.button("🔍 搜索", type="primary", use_container_width=True)

    # 搜索逻辑
    if search_term and search_btn:
        with st.spinner("正在搜索..."):
            results = mapper.search(search_term)

        if not results:
            st.warning(f"未找到匹配 '{search_term}' 的公司，请尝试其他关键词")
        else:
            st.success(f"找到 {len(results)} 个匹配结果")

            # 显示搜索结果表格
            df = pd.DataFrame(results)
            df_display = df[["code", "name", "full_name", "market"]].copy()
            df_display.columns = ["股票代码", "简称", "公司全称", "市场"]
            st.dataframe(df_display, use_container_width=True, hide_index=True)

            # 选择公司
            if len(results) == 1:
                selected = results[0]
            else:
                options = {f"{r['code']} - {r['name']}": r for r in results}
                selected_label = st.selectbox("请选择公司", list(options.keys()))
                selected = options[selected_label]

            # 显示公司详情和操作按钮
            if selected:
                st.markdown("---")
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                with col1:
                    st.subheader(f"{selected['name']} ({selected['code']})")
                    st.caption(selected.get("full_name", ""))
                with col2:
                    fetch_btn = st.button("📥 获取财报数据", type="primary", use_container_width=True)
                with col3:
                    analyze_btn = st.button("🤖 生成分析报告", use_container_width=True)
                with col4:
                    pipeline_btn = st.button("⚡ 全流程执行", use_container_width=True,
                                              help="一键完成：获取数据+AI分析+生成HTML报告")

                # -- 功能1: 获取财务数据 --
                if fetch_btn:
                    with st.spinner(f"正在获取 {selected['name']} 的财务数据..."):
                        company_id = db.upsert_company(
                            stock_code=selected["code"],
                            short_name=selected["name"],
                            full_name=selected.get("full_name", ""),
                            market=selected.get("market", "SZ"),
                        )
                        fin_data = scraper.fetch_ths_financial_data(selected["code"])
                        highlights = fin_data.get("highlights", [])
                        if highlights:
                            for h in highlights:
                                db.save_highlights(company_id, {
                                    "report_date": h["report_date"],
                                    "report_year": h["report_year"],
                                    "revenue": h.get("revenue"),
                                    "net_profit": h.get("net_profit"),
                                    "total_assets": h.get("total_assets"),
                                    "total_liab": h.get("total_liab"),
                                    "equity": h.get("equity"),
                                    "gross_margin": h.get("gross_margin"),
                                    "net_margin": h.get("net_margin"),
                                    "roe": h.get("roe"),
                                    "eps": h.get("eps"),
                                    "bvps": h.get("bvps"),
                                })
                            segments = fin_data.get("segments", [])
                            if segments:
                                db.save_business_segments(company_id, [
                                    {"report_year": h.get("report_year", datetime.now().year - 1),
                                     "segment_name": s["name"],
                                     "revenue_pct": s.get("revenue_pct")}
                                    for s in segments
                                ])
                            st.session_state["current_financial_data"] = fin_data
                            st.session_state["current_company"] = selected
                            st.success(f"✅ {selected['name']} 财务数据获取成功! ({len(highlights)}期数据)")
                            st.rerun()
                        else:
                            st.error("获取财务数据失败，请稍后重试")

                # -- 功能2: 一键全流程（获取+分析+报告） --
                if pipeline_btn:
                    step_status = st.empty()
                    # Step 1: 获取数据
                    step_status.info("⏳ 步骤1/3: 获取财务数据...")
                    company_id = db.upsert_company(
                        stock_code=selected["code"], short_name=selected["name"],
                        full_name=selected.get("full_name", ""), market=selected.get("market", "SZ"),
                    )
                    fin_data = scraper.fetch_ths_financial_data(selected["code"])
                    highlights = fin_data.get("highlights", [])
                    if highlights:
                        for h in highlights:
                            db.save_highlights(company_id, h)
                        st.session_state["current_financial_data"] = fin_data
                        st.session_state["current_company"] = selected

                    # Step 2: AI分析
                    if fin_data and highlights:
                        step_status.info("⏳ 步骤2/3: AI正在生成财务分析报告（约30秒）...")
                        report_md = ai_client.analyze_financial_report(
                            selected["name"], selected["code"], fin_data
                        )
                        if report_md:
                            st.session_state["current_report_md"] = report_md

                            # Step 3: 生成HTML报告
                            step_status.info("⏳ 步骤3/3: 生成图文并茂的HTML报告...")
                            html_path = generate_report(
                                selected["name"], selected["code"], fin_data, report_md
                            )
                            st.session_state["last_html_report"] = html_path
                            st.session_state["report_generated"] = True

                            # 存入数据库
                            db.save_report(
                                company_id,
                                highlights[0]["report_year"], 4,
                                f"{selected['name']} {highlights[0]['report_year']}年度分析报告",
                                open(html_path, "r", encoding="utf-8").read(),
                                report_md[:300],
                            )

                            step_status.empty()
                            st.balloons()
                            st.success("🎉 全流程完成！财务数据已获取 → AI分析已生成 → HTML报告已保存")
                            st.info(f"📄 报告文件: {html_path}")
                            st.rerun()
                        else:
                            step_status.error("AI分析生成失败")
                    else:
                        step_status.error("获取财务数据失败")

                # -- 功能3: 仅生成AI分析报告 --
                if analyze_btn:
                    fin_data = st.session_state.get("current_financial_data")
                    if not fin_data:
                        st.warning("请先获取财务数据再生成报告，或使用「⚡ 全流程执行」一键完成")
                    else:
                        with st.spinner("🤖 AI正在生成财务分析报告（约30秒）..."):
                            report_md = ai_client.analyze_financial_report(
                                selected["name"], selected["code"], fin_data
                            )
                            if report_md:
                                st.session_state["current_report_md"] = report_md
                                html_path = generate_report(
                                    selected["name"], selected["code"],
                                    fin_data, report_md
                                )
                                st.session_state["last_html_report"] = html_path
                                st.session_state["report_generated"] = True
                                st.success("✅ AI分析报告生成完成！")
                                st.rerun()
                            else:
                                st.error("AI分析生成失败，请检查API密钥和网络连接")

    # 显示搜索结果（无搜索时展示热门公司）
    elif not search_term:
        st.markdown("##### 🏛️ 金融行业公司快速选择")
        st.caption("点击公司名称 -> 自动获取数据 -> AI分析 -> 生成HTML报告（全程约40秒）")

        # 金融公司分类展示
        finance_groups = {
            "🏦 银行": ["工商银行","招商银行","建设银行","农业银行","中国银行","交通银行","邮储银行","兴业银行","平安银行","浦发银行","民生银行","中信银行","光大银行","华夏银行","宁波银行","北京银行","上海银行","南京银行","江苏银行","杭州银行","成都银行","长沙银行","贵阳银行","西安银行","郑州银行","青岛银行","苏州银行","兰州银行","重庆银行","浙商银行","沪农商行","渝农商行","青农商行","无锡银行","常熟银行","张家港行","江阴银行","苏农银行","紫金银行","瑞丰银行","厦门银行","齐鲁银行"],
            "🛡️ 保险": ["中国平安","中国人寿","中国太保","中国人保","新华保险","友邦保险","中国太平","中国再保险","众安在线","保诚","阳光保险","中国财险","天茂集团"],
            "📈 证券": ["中信证券","华泰证券","广发证券","国信证券","东方财富","中金公司","国泰君安","海通证券","银河证券","光大证券"],
            "📊 期货/信托/金控": ["永安期货","南华期货","瑞达期货","建元信托","中油资本","越秀资本"],
            "🇭🇰 港股金融": ["汇丰控股","友邦保险","香港交易所","恒生银行","中银香港","渣打集团","东亚银行","中国太平","保诚","众安在线","中国财险","阳光保险","中金公司","HTSC"],
        }

        cols = st.columns(2)
        col_idx = 0
        for group_name, companies in finance_groups.items():
            with cols[col_idx % 2]:
                with st.expander(group_name, expanded=True):
                    for i in range(0, len(companies), 3):
                        row_companies = companies[i:i+3]
                        btn_cols = st.columns(len(row_companies))
                        for j, comp_name in enumerate(row_companies):
                            with btn_cols[j]:
                                # key 加入分组名 + 序号，避免跨分组重名（如友邦保险在保险+港股双组）
                                unique_key = f"q_{group_name}_{i+j}_{comp_name}"
                                if st.button(comp_name, key=unique_key, use_container_width=True):
                                    st.session_state["auto_run_company"] = comp_name
            col_idx += 1

        # ── 自动运行：点击公司按钮后立即全流程执行 ──
        auto_name = st.session_state.pop("auto_run_company", None)
        if auto_name:
            results = mapper.search(auto_name, limit=1)
            if not results:
                st.error(f"未找到公司: {auto_name}")
            else:
                sel = results[0]
                status_area = st.empty()
                progress_bar = st.progress(0, text="⏳ 准备就绪，开始处理...")
                fetch_ok = False
                report_md = None

                # Step 1: 获取财务数据 (0→33%)
                progress_bar.progress(5, text=f"⏳ [1/3] 正在获取 {sel['name']} 财务数据...")
                try:
                    company_id = db.upsert_company(
                        stock_code=sel["code"], short_name=sel["name"],
                        full_name=sel.get("full_name", ""), market=sel.get("market", "SZ"),
                    )
                    progress_bar.progress(15, text="⏳ [1/3] 连接数据源...")
                    fin_data = scraper.fetch_ths_financial_data(sel["code"])
                    highlights = fin_data.get("highlights", [])
                    if highlights:
                        for h in highlights:
                            db.save_highlights(company_id, h)
                        st.session_state["current_financial_data"] = fin_data
                        st.session_state["current_company"] = sel
                        fetch_ok = True
                        progress_bar.progress(33, text=f"✅ [1/3] 财务数据获取完成 ({len(highlights)}期)")
                    else:
                        progress_bar.progress(33, text="❌ [1/3] 获取财务数据失败")
                        status_area.error("❌ 获取财务数据失败（API无返回）")
                except Exception as e:
                    progress_bar.progress(33, text=f"❌ [1/3] 获取数据异常: {e}")
                    status_area.error(f"❌ [1/3] 异常详情: {e}")
                    st.exception(e)

                # Step 2: AI分析 (33→66%)
                if fetch_ok:
                    progress_bar.progress(40, text=f"⏳ [2/3] AI正在分析 {sel['name']} 财务数据（约20秒）...")
                    try:
                        report_md = ai_client.analyze_financial_report(
                            sel["name"], sel["code"], fin_data
                        )
                        if report_md:
                            st.session_state["current_report_md"] = report_md
                            progress_bar.progress(66, text=f"✅ [2/3] AI分析完成 ({len(report_md)}字)")
                        else:
                            progress_bar.progress(66, text="❌ [2/3] AI分析失败")
                            status_area.error("❌ AI分析失败（DeepSeek API无返回）")
                            fetch_ok = False
                    except Exception as e:
                        progress_bar.progress(66, text="❌ [2/3] AI分析异常")
                        status_area.error(f"❌ AI分析异常: {e}")
                        fetch_ok = False

                # Step 3: 生成HTML报告 (66→100%)
                if fetch_ok and report_md:
                    progress_bar.progress(75, text="⏳ [3/3] 生成图文并茂的HTML报告（含ECharts图表）...")
                    try:
                        html_path = generate_report(sel["name"], sel["code"], fin_data, report_md)
                        st.session_state["last_html_report"] = html_path
                        st.session_state["report_generated"] = True
                        progress_bar.progress(90, text="⏳ [3/3] 保存报告到数据库...")
                        year = highlights[0]["report_year"]
                        db.save_report(company_id, year, 4,
                            f"{sel['name']}{year}年度财务分析报告",
                            open(html_path, "r", encoding="utf-8").read(),
                            report_md[:300])

                        # 完成！
                        progress_bar.progress(100, text=f"✅ 全流程完成！{sel['name']} 财务分析报告已就绪")
                        status_area.empty()
                        st.balloons()
                        st.success(f"""
                        ### ✅ 报告生成完毕！
                        | 步骤 | 状态 | 详情 |
                        |------|------|------|
                        | 📊 财务数据 | ✅ | {len(highlights)}期数据已入库 |
                        | 🤖 AI分析 | ✅ | {len(report_md)}字专业报告 |
                        | 📄 HTML报告 | ✅ | 含ECharts图表 + KPI卡片 |
                        | 💾 数据库 | ✅ | 已存储到 analysis_reports |
                        """)
                    except Exception as e:
                        progress_bar.progress(100, text="❌ [3/3] 报告生成异常")
                        status_area.error(f"❌ 报告生成异常: {e}")

# ══════════════════════════════════════════════════════
# 页面2：财务数据看板
# ══════════════════════════════════════════════════════
elif page == "📈 财务数据看板":
    st.title("📈 财务数据看板")

    fin_data = st.session_state.get("current_financial_data")
    company = st.session_state.get("current_company")

    if not fin_data or not company:
        st.info("请先在「公司查询与财报」页面搜索并获取公司财务数据")
    else:
        st.subheader(f"{company['name']} ({company['code']}) 财务概览")

        highlights = fin_data.get("highlights", [])
        if highlights:
            # 指标卡片
            latest = highlights[0]
            cols = st.columns(5)
            metrics = [
                ("营业收入", latest.get("revenue"), "万元"),
                ("净利润", latest.get("net_profit"), "万元"),
                ("总资产", latest.get("total_assets"), "万元"),
                ("ROE", latest.get("roe"), "%"),
                ("EPS", latest.get("eps"), "元"),
            ]
            for col, (label, val, unit) in zip(cols, metrics):
                with col:
                    if val is not None:
                        if unit == "%":
                            display = f"{float(val) * 100:.2f}%"
                        elif float(val) >= 10000:
                            display = f"{float(val) / 10000:.2f}亿"
                        else:
                            display = f"{float(val):,.2f}"
                    else:
                        display = "N/A"
                    st.metric(label, display)

            # 数据表格
            st.markdown("##### 近5年财务数据明细")
            df = pd.DataFrame(highlights)
            # 格式化百分比
            for col in ["gross_margin", "net_margin", "roe"]:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: f"{float(x) * 100:.2f}%" if x else "N/A")
            # 格式化大额数字
            for col in ["revenue", "net_profit", "total_assets", "total_liab", "equity"]:
                if col in df.columns:
                    df[col] = df[col].apply(
                        lambda x: f"{float(x) / 10000:.2f}亿" if x and float(x) >= 10000
                        else (f"{float(x):,.2f}" if x else "N/A"))
            st.dataframe(df, use_container_width=True, hide_index=True)

            # 业务板块
            segments = fin_data.get("segments", [])
            if segments:
                st.markdown("##### 主营业务构成")
                seg_df = pd.DataFrame(segments)
                if "revenue_pct" in seg_df.columns:
                    seg_df["收入占比"] = seg_df["revenue_pct"].apply(
                        lambda x: f"{float(x) * 100:.1f}%" if x else "N/A")
                st.dataframe(seg_df[["name", "收入占比"]], use_container_width=True, hide_index=True)
        else:
            st.warning("暂无财务数据")

# ══════════════════════════════════════════════════════
# 页面3：AI分析报告
# ══════════════════════════════════════════════════════
elif page == "🤖 AI分析报告":
    st.title("🤖 AI财务分析报告")

    company = st.session_state.get("current_company")
    report_md = st.session_state.get("current_report_md")

    if not company:
        st.info("请先在「公司查询与财报」页面搜索公司并生成报告")
    else:
        st.subheader(f"{company['name']} ({company['code']})")

        # 生成报告按钮（如果还没有报告）
        if not report_md:
            if st.button("🔄 重新生成分析报告", type="primary"):
                fin_data = st.session_state.get("current_financial_data")
                if fin_data:
                    with st.spinner("🤖 AI正在深度分析财务数据..."):
                        report_md = ai_client.analyze_financial_report(
                            company["name"], company["code"], fin_data
                        )
                        if report_md:
                            st.session_state["current_report_md"] = report_md
                            st.rerun()
                        else:
                            st.error("生成失败，请检查API配置")
        else:
            # 展示报告
            st.markdown(report_md)

            # 操作按钮
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("🔄 重新生成", use_container_width=True):
                    st.session_state.pop("current_report_md", None)
                    st.rerun()
            with col2:
                # 生成HTML报告
                fin_data = st.session_state.get("current_financial_data")
                if fin_data:
                    if st.button("📄 导出HTML报告", use_container_width=True):
                        html_path = generate_report(
                            company["name"], company["code"],
                            fin_data, report_md
                        )
                        st.session_state["last_html_report"] = html_path
                        st.success(f"✅ HTML报告已生成!")
                        st.rerun()
            with col3:
                last_html = st.session_state.get("last_html_report")
                if last_html and Path(last_html).exists():
                    with open(last_html, "r", encoding="utf-8") as f:
                        st.download_button(
                            label="📥 下载HTML报告",
                            data=f,
                            file_name=Path(last_html).name,
                            mime="text/html",
                            use_container_width=True,
                        )

    # 预览最新生成的HTML报告
    last_html = st.session_state.get("last_html_report")
    if last_html and Path(last_html).exists():
        st.markdown("---")
        st.markdown("##### 📋 最新生成的图文报告预览")
        with open(last_html, "r", encoding="utf-8") as f:
            html_content = f.read()
        st.components.v1.html(html_content, height=600, scrolling=True)

# ══════════════════════════════════════════════════════
# 页面4：报告管理
# ══════════════════════════════════════════════════════
elif page == "📄 报告管理":
    st.title("📄 报告管理")

    reports_dir = Path(__file__).parent / "reports"
    if not reports_dir.exists():
        reports_dir.mkdir(parents=True)

    html_files = sorted(reports_dir.glob("*.html"), key=os.path.getmtime, reverse=True)

    if not html_files:
        st.info("暂无已生成的报告，请先在「AI分析报告」页面生成")
    else:
        st.success(f"共找到 {len(html_files)} 份报告")

        for i, html_file in enumerate(html_files):
            stat = html_file.stat()
            size_kb = stat.st_size / 1024
            modified = datetime.fromtimestamp(stat.st_mtime)

            with st.expander(f"📄 {html_file.name}  ({size_kb:.0f}KB · {modified.strftime('%Y-%m-%d %H:%M')})"):
                with open(html_file, "r", encoding="utf-8") as f:
                    html_content = f.read()

                # 预览和下载
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.components.v1.html(html_content, height=400, scrolling=True)
                with col2:
                    st.download_button(
                        label="📥 下载",
                        data=html_content,
                        file_name=html_file.name,
                        mime="text/html",
                        use_container_width=True,
                    )
                    if st.button(f"🗑️ 删除", key=f"del_{i}", use_container_width=True):
                        html_file.unlink()
                        st.rerun()

# ══════════════════════════════════════════════════════
# 页面5：数据同步中心
# ══════════════════════════════════════════════════════
elif page == "🔄 数据同步中心":
    st.title("🔄 数据同步中心")
    st.caption("管理公司财务数据同步 — 去重检测 · 一键批量同步 · 进度追踪")

    # ── 加载同步概览 ──
    summary = db.get_sync_summary()
    all_status = db.get_all_companies_sync_status()
    unsynced_list = db.get_unsynced_companies()
    synced_codes = db.get_synced_company_codes()

    # ── 概览卡片 ──
    st.markdown("##### 📊 同步概览")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("总公司数", summary["total_companies"])
    c2.metric("✅ 已同步", summary["synced_companies"])
    c3.metric("⚠️ 未同步", summary["unsynced_companies"])
    c4.metric("📋 财务记录", summary["total_records"])

    # 行业维度
    if summary["by_industry"]:
        with st.expander("📈 按行业查看同步进度", expanded=False):
            for ind in summary["by_industry"]:
                ind_name = ind["industry"] or "未分类"
                total_i = ind["total"]
                synced_i = ind["synced"] or 0
                pct = synced_i / total_i * 100 if total_i > 0 else 0
                st.progress(pct / 100, text=f"{ind_name}: {synced_i}/{total_i} ({pct:.0f}%)")

    st.markdown("---")

    # ── Tab: 未同步公司 + 一键同步 ──
    tab1, tab2, tab3 = st.tabs(["⚠️ 未同步公司", "📋 全部公司状态", "📝 同步日志"])

    with tab1:
        if not unsynced_list:
            st.success("🎉 所有公司均已同步！数据库中的财务数据已是最新。")
        else:
            st.warning(f"共 **{len(unsynced_list)}** 家公司尚未同步财务数据")

            # ── 按行业分组显示 ──
            from collections import defaultdict
            grouped = defaultdict(list)
            for co in unsynced_list:
                ind = co.get("industry") or "未分类"
                grouped[ind].append(co)

            # 全选/取消全选
            all_codes = [co["stock_code"] for co in unsynced_list]
            select_all = st.checkbox("全选/取消全选", value=True, key="sync_select_all")
            selected_codes = set()
            if select_all:
                selected_codes = set(all_codes)
            else:
                selected_codes = set()

            for ind_name, companies in sorted(grouped.items()):
                st.markdown(f"**{ind_name}** ({len(companies)}家)")
                cols = st.columns(4)
                for i, co in enumerate(companies):
                    with cols[i % 4]:
                        key = f"sync_{co['stock_code']}"
                        if select_all:
                            checked = st.checkbox(
                                f"{co['short_name']}", value=True, key=key
                            )
                        else:
                            checked = st.checkbox(
                                f"{co['short_name']}", value=False, key=key
                            )
                        if checked and not select_all:
                            selected_codes.add(co["stock_code"])
                        st.caption(co["stock_code"])

            st.markdown("---")

            # ── 一键同步按钮 ──
            sync_col1, sync_col2 = st.columns([2, 1])
            with sync_col1:
                sync_btn = st.button(
                    f"🚀 一键同步选中的 {len(selected_codes)} 家公司",
                    type="primary", use_container_width=True,
                    disabled=len(selected_codes) == 0
                )
            with sync_col2:
                sync_size = st.selectbox("每批数量", [3, 5, 10, 20], index=1)

            if sync_btn and selected_codes:
                # ── 去重：再次确认哪些仍需同步 ──
                to_sync = []
                for code in selected_codes:
                    if db.is_company_synced(code):
                        continue  # 已经同步了，跳过
                    to_sync.append(code)

                if not to_sync:
                    st.info("所选公司均已有数据，无需重复同步 ✅")
                else:
                    st.info(f"去重后需同步 {len(to_sync)} 家（已跳过 {len(selected_codes)-len(to_sync)} 家已同步）")
                    progress_bar = st.progress(0.0)
                    status_col1, status_col2 = st.columns(2)
                    log_lines = []

                    success_cnt = 0
                    fail_cnt = 0
                    skipped_cnt = len(selected_codes) - len(to_sync)
                    total = len(to_sync)

                    for i, code in enumerate(to_sync):
                        # 再次确认去重（同步期间可能被其他操作影响）
                        if db.is_company_synced(code):
                            skipped_cnt += 1
                            log_lines.append(f"⏭️ {code} — 已同步,跳过")
                            progress_bar.progress((i + 1) / max(total, 1),
                                text=f"⏭️ [{i+1}/{total}] {code} 已有数据,跳过")
                            continue

                        company = db.get_company_by_code(code)
                        name = company["short_name"] if company else code
                        progress_bar.progress((i + 0.3) / max(total, 1),
                            text=f"⏳ [{i+1}/{total}] 正在获取 {name} 数据...")

                        try:
                            fin_data = scraper.fetch_ths_financial_data(code)
                            highlights = fin_data.get("highlights", [])
                            if highlights:
                                cid = company["id"] if company else db.upsert_company(
                                    stock_code=code, short_name=name,
                                    full_name=company.get("full_name", ""),
                                    market=company.get("market", "SZ"),
                                )
                                for h in highlights:
                                    db.save_highlights(cid, h)
                                db.log_scraper("batch_sync", cid, "年报",
                                    status="success", records=len(highlights))
                                success_cnt += 1
                                log_lines.append(f"✅ {name} ({code}) — {len(highlights)}期数据")
                            else:
                                fail_cnt += 1
                                log_lines.append(f"❌ {name} ({code}) — API无数据")
                        except Exception as e:
                            fail_cnt += 1
                            log_lines.append(f"❌ {code} — {str(e)[:60]}")

                        progress_bar.progress((i + 1) / max(total, 1),
                            text=f"{'✅' if success_cnt > fail_cnt else '⏳'} [{i+1}/{total}] {name}")

                        # 实时显示最近5条日志
                        with status_col1:
                            for line in log_lines[-5:]:
                                st.caption(line)

                    progress_bar.progress(1.0, text=f"✅ 同步完成！成功 {success_cnt} / 失败 {fail_cnt} / 跳过 {skipped_cnt}")
                    st.success(f"### ✅ 批量同步完成\n| 成功 | 失败 | 跳过(去重) |\n|------|------|------------|\n| {success_cnt} | {fail_cnt} | {skipped_cnt} |")
                    st.balloons()
                    st.rerun()

            # ── 单独同步按钮 ──
            with st.expander("🔧 单公司同步", expanded=False):
                single_code = st.text_input("输入股票代码", placeholder="例如：601318")
                if st.button("📥 同步该公司", disabled=not single_code):
                    if db.is_company_synced(single_code.strip()):
                        detail = db.get_company_sync_detail(single_code.strip())
                        st.warning(f"⚠️ 该公司已同步（{detail['records']}条记录，覆盖年份：{detail['years']}）")
                        if st.button("🔄 仍然重新同步"):
                            st.rerun()
                    else:
                        with st.spinner(f"正在同步 {single_code}..."):
                            fin_data = scraper.fetch_ths_financial_data(single_code.strip())
                            highlights = fin_data.get("highlights", [])
                            if highlights:
                                co = db.get_company_by_code(single_code.strip())
                                if co:
                                    cid = co["id"]
                                else:
                                    cid = db.upsert_company(
                                        stock_code=single_code.strip(),
                                        short_name=single_code.strip(),
                                    )
                                for h in highlights:
                                    db.save_highlights(cid, h)
                                db.log_scraper("manual_sync", cid, "年报",
                                    status="success", records=len(highlights))
                                st.success(f"✅ {single_code} 同步成功！({len(highlights)}期)")
                                st.rerun()
                            else:
                                st.error(f"❌ {single_code} API无数据返回")

    with tab2:
        st.markdown("##### 📋 全部公司同步状态")
        if all_status:
            import pandas as pd
            df_all = pd.DataFrame(all_status)
            df_all["status"] = df_all["record_count"].apply(
                lambda x: "✅ 已同步" if x > 0 else "⚠️ 未同步"
            )
            df_display = df_all[["stock_code", "short_name", "industry", "status",
                                  "record_count", "last_sync"]].copy()
            df_display.columns = ["代码", "简称", "行业", "状态", "记录数", "最近同步"]
            # 格式处理
            df_display["最近同步"] = df_display["最近同步"].fillna("从未同步")
            st.dataframe(df_display, use_container_width=True, hide_index=True,
                         column_config={
                             "状态": st.column_config.Column(width="small"),
                             "记录数": st.column_config.Column(width="small"),
                         })
        else:
            st.info("暂无公司数据")

    with tab3:
        st.markdown("##### 📝 最近同步日志")
        try:
            cursor = db.conn.cursor()
            cursor.execute("""
                SELECT sl.*, c.short_name, c.stock_code
                FROM scraper_logs sl
                LEFT JOIN companies c ON sl.company_id = c.id
                ORDER BY sl.created_at DESC LIMIT 30
            """)
            logs = [dict(r) for r in cursor.fetchall()]
            if logs:
                for log in logs:
                    icon = "✅" if log["status"] == "success" else "❌"
                    name = log.get("short_name") or log.get("stock_code") or "N/A"
                    st.caption(
                        f"{icon} {log['created_at'][:16]} | {name} | "
                        f"{log.get('records_count', 0)}条 | 来源: {log['source']}"
                    )
            else:
                st.info("暂无同步日志")
        except Exception as e:
            st.caption(f"日志加载失败: {e}")

        # 清除日志按钮
        if st.button("🗑️ 清空同步日志", type="secondary"):
            cursor = db.conn.cursor()
            cursor.execute("DELETE FROM scraper_logs")
            db.conn.commit()
            st.success("日志已清空")
            st.rerun()

# ══════════════════════════════════════════════════════
# 页面6：数据管理
# ══════════════════════════════════════════════════════
elif page == "⚙️ 数据管理":
    st.title("⚙️ 数据管理")

    tab1, tab2, tab3 = st.tabs(["📊 数据库状态", "🔄 数据同步", "💡 关于"])

    with tab1:
        st.markdown("##### 数据库概览")

        # 统计信息
        try:
            cursor = db.conn.cursor()
            stats = {}
            for table in ["companies", "financial_highlights", "financial_statements",
                          "business_segments", "analysis_reports"]:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                stats[table] = cursor.fetchone()[0]

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("上市公司数", stats.get("companies", 0))
                st.metric("业务板块记录", stats.get("business_segments", 0))
            with col2:
                st.metric("财务指标记录", stats.get("financial_highlights", 0))
                st.metric("分析报告数", stats.get("analysis_reports", 0))
            with col3:
                st.metric("明细科目记录", stats.get("financial_statements", 0))

            st.caption(f"数据库路径：{db.db_path}")
        except Exception as e:
            st.error(f"数据库读取失败: {e}")

    with tab2:
        st.markdown("##### 🤖 DeepSeek API 测试")
        test_col1, test_col2 = st.columns([3, 1])
        with test_col1:
            test_prompt = st.text_area("测试Prompt", "请用一句话解释什么是ROE（净资产收益率）", height=80)
        with test_col2:
            if st.button("🧪 测试API连接", type="primary", use_container_width=True):
                with st.spinner("正在调用DeepSeek API..."):
                    resp = ai_client.chat([
                        {"role": "user", "content": test_prompt}
                    ], temperature=0.3, max_tokens=200)
                    if resp:
                        st.success("✅ API连接成功！")
                        st.info(resp)
                    else:
                        st.error("❌ API调用失败，请检查网络和密钥配置")

        st.markdown("---")
        st.markdown("##### 批量数据同步")
        st.markdown("从巨潮资讯网批量获取热门公司的财报数据")

        col1, col2 = st.columns(2)
        with col1:
            batch_size = st.number_input("同步数量", min_value=5, max_value=50, value=10)
        with col2:
            if st.button("🚀 开始批量同步", type="primary", use_container_width=True):
                companies = mapper.all_companies[:batch_size]
                progress_bar = st.progress(0)
                status_text = st.empty()

                success_count = 0
                for i, company in enumerate(companies):
                    try:
                        status_text.text(f"正在处理 {company['name']} ({i+1}/{batch_size})...")
                        fin_data = scraper.fetch_ths_financial_data(company["code"])
                        highlights = fin_data.get("highlights", [])
                        if highlights:
                            company_id = db.upsert_company(
                                stock_code=company["code"],
                                short_name=company["name"],
                                full_name=company.get("full_name", ""),
                                market=company.get("market", "SZ"),
                            )
                            for h in highlights:
                                db.save_highlights(company_id, h)
                            success_count += 1
                    except Exception as e:
                        st.error(f"{company['name']} 同步失败: {e}")
                    progress_bar.progress((i + 1) / batch_size)

                status_text.text("")
                st.success(f"✅ 批量同步完成！成功：{success_count}/{batch_size} 家公司")

        st.markdown("##### 公司映射管理")
        new_code = st.text_input("股票代码", placeholder="例如：600519", max_chars=6)
        new_name = st.text_input("公司简称", placeholder="例如：贵州茅台")
        new_full = st.text_input("公司全称（可选）", placeholder="例如：贵州茅台酒股份有限公司")
        if st.button("➕ 添加/更新公司映射") and new_code and new_name:
            mapper.add_company(new_code, new_name, new_full)
            st.success(f"已添加 {new_name}({new_code})")
            st.rerun()

    with tab3:
        st.markdown("""
        ### 💡 关于本平台

        **技术栈：**
        - **前端框架**：Streamlit
        - **数据源**：巨潮资讯网、同花顺
        - **AI引擎**：DeepSeek Chat API
        - **可视化**：ECharts
        - **数据库**：SQLite（开发）/ PostgreSQL（生产）

        **功能特色：**
        - 🔍 支持中英文模糊搜索、拼音匹配
        - 📊 营收/利润趋势图表自动生成
        - 🤖 AI驱动的深度财务分析报告
        - 📄 图文并茂的HTML报告导出
        - ⚡ 支持批量数据同步

        **法律声明：**
        - 所有数据来源于公开市场信息
        - 分析报告仅供参考，不构成投资建议
        """)

# ── 页脚 ──────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.caption("v1.0.0 | Built with ❤️ by Senior Developer")
