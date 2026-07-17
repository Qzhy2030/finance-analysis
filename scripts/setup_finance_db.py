#!/usr/bin/env python3
"""
金融行业公司数据库初始化
只保留银行、保险、证券、信托、期货、金融科技等金融公司
并优化报告生成流程
"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DATA_DIR


FINANCE_COMPANIES = [
    # ===== 银行 (37家) =====
    {"code":"601398","name":"工商银行","market":"SH","full_name":"中国工商银行股份有限公司"},
    {"code":"601939","name":"建设银行","market":"SH","full_name":"中国建设银行股份有限公司"},
    {"code":"601288","name":"农业银行","market":"SH","full_name":"中国农业银行股份有限公司"},
    {"code":"601328","name":"交通银行","market":"SH","full_name":"交通银行股份有限公司"},
    {"code":"600036","name":"招商银行","market":"SH","full_name":"招商银行股份有限公司"},
    {"code":"601166","name":"兴业银行","market":"SH","full_name":"兴业银行股份有限公司"},
    {"code":"600015","name":"华夏银行","market":"SH","full_name":"华夏银行股份有限公司"},
    {"code":"600016","name":"民生银行","market":"SH","full_name":"中国民生银行股份有限公司"},
    {"code":"600908","name":"无锡银行","market":"SH","full_name":"无锡农村商业银行股份有限公司"},
    {"code":"600919","name":"江苏银行","market":"SH","full_name":"江苏银行股份有限公司"},
    {"code":"600926","name":"杭州银行","market":"SH","full_name":"杭州银行股份有限公司"},
    {"code":"600928","name":"西安银行","market":"SH","full_name":"西安银行股份有限公司"},
    {"code":"601009","name":"南京银行","market":"SH","full_name":"南京银行股份有限公司"},
    {"code":"601128","name":"常熟银行","market":"SH","full_name":"江苏常熟农村商业银行股份有限公司"},
    {"code":"601169","name":"北京银行","market":"SH","full_name":"北京银行股份有限公司"},
    {"code":"601187","name":"厦门银行","market":"SH","full_name":"厦门银行股份有限公司"},
    {"code":"601229","name":"上海银行","market":"SH","full_name":"上海银行股份有限公司"},
    {"code":"601528","name":"瑞丰银行","market":"SH","full_name":"浙江绍兴瑞丰农村商业银行股份有限公司"},
    {"code":"601577","name":"长沙银行","market":"SH","full_name":"长沙银行股份有限公司"},
    {"code":"601658","name":"邮储银行","market":"SH","full_name":"中国邮政储蓄银行股份有限公司"},
    {"code":"601665","name":"齐鲁银行","market":"SH","full_name":"齐鲁银行股份有限公司"},
    {"code":"601818","name":"光大银行","market":"SH","full_name":"中国光大银行股份有限公司"},
    {"code":"601838","name":"成都银行","market":"SH","full_name":"成都银行股份有限公司"},
    {"code":"601860","name":"紫金银行","market":"SH","full_name":"江苏紫金农村商业银行股份有限公司"},
    {"code":"601916","name":"浙商银行","market":"SH","full_name":"浙商银行股份有限公司"},
    {"code":"601963","name":"重庆银行","market":"SH","full_name":"重庆银行股份有限公司"},
    {"code":"601988","name":"中国银行","market":"SH","full_name":"中国银行股份有限公司"},
    {"code":"601997","name":"贵阳银行","market":"SH","full_name":"贵阳银行股份有限公司"},
    {"code":"601998","name":"中信银行","market":"SH","full_name":"中信银行股份有限公司"},
    {"code":"603323","name":"苏农银行","market":"SH","full_name":"江苏苏州农村商业银行股份有限公司"},
    {"code":"000001","name":"平安银行","market":"SZ","full_name":"平安银行股份有限公司"},
    {"code":"001227","name":"兰州银行","market":"SZ","full_name":"兰州银行股份有限公司"},
    {"code":"002142","name":"宁波银行","market":"SZ","full_name":"宁波银行股份有限公司"},
    {"code":"002807","name":"江阴银行","market":"SZ","full_name":"江苏江阴农村商业银行股份有限公司"},
    {"code":"002936","name":"郑州银行","market":"SZ","full_name":"郑州银行股份有限公司"},
    {"code":"002948","name":"青岛银行","market":"SZ","full_name":"青岛银行股份有限公司"},
    {"code":"002966","name":"苏州银行","market":"SZ","full_name":"苏州银行股份有限公司"},

    # ===== 保险 (5家) =====
    {"code":"601318","name":"中国平安","market":"SH","full_name":"中国平安保险(集团)股份有限公司"},
    {"code":"601628","name":"中国人寿","market":"SH","full_name":"中国人寿保险股份有限公司"},
    {"code":"601601","name":"中国太保","market":"SH","full_name":"中国太平洋保险(集团)股份有限公司"},
    {"code":"601319","name":"中国人保","market":"SH","full_name":"中国人民保险集团股份有限公司"},
    {"code":"601336","name":"新华保险","market":"SH","full_name":"新华人寿保险股份有限公司"},

    # ===== 证券 (34家) =====
    {"code":"600030","name":"中信证券","market":"SH","full_name":"中信证券股份有限公司"},
    {"code":"600109","name":"国金证券","market":"SH","full_name":"国金证券股份有限公司"},
    {"code":"600369","name":"西南证券","market":"SH","full_name":"西南证券股份有限公司"},
    {"code":"600906","name":"财达证券","market":"SH","full_name":"财达证券股份有限公司"},
    {"code":"600909","name":"华安证券","market":"SH","full_name":"华安证券股份有限公司"},
    {"code":"600918","name":"中泰证券","market":"SH","full_name":"中泰证券股份有限公司"},
    {"code":"600958","name":"东方证券","market":"SH","full_name":"东方证券股份有限公司"},
    {"code":"601059","name":"信达证券","market":"SH","full_name":"信达证券股份有限公司"},
    {"code":"601108","name":"财通证券","market":"SH","full_name":"财通证券股份有限公司"},
    {"code":"601136","name":"首创证券","market":"SH","full_name":"首创证券股份有限公司"},
    {"code":"601162","name":"天风证券","market":"SH","full_name":"天风证券股份有限公司"},
    {"code":"601198","name":"东兴证券","market":"SH","full_name":"东兴证券股份有限公司"},
    {"code":"601236","name":"红塔证券","market":"SH","full_name":"红塔证券股份有限公司"},
    {"code":"601375","name":"中原证券","market":"SH","full_name":"中原证券股份有限公司"},
    {"code":"601377","name":"兴业证券","market":"SH","full_name":"兴业证券股份有限公司"},
    {"code":"601555","name":"东吴证券","market":"SH","full_name":"东吴证券股份有限公司"},
    {"code":"601688","name":"华泰证券","market":"SH","full_name":"华泰证券股份有限公司"},
    {"code":"601696","name":"中银证券","market":"SH","full_name":"中银国际证券股份有限公司"},
    {"code":"601788","name":"光大证券","market":"SH","full_name":"光大证券股份有限公司"},
    {"code":"601878","name":"浙商证券","market":"SH","full_name":"浙商证券股份有限公司"},
    {"code":"601901","name":"方正证券","market":"SH","full_name":"方正证券股份有限公司"},
    {"code":"601990","name":"南京证券","market":"SH","full_name":"南京证券股份有限公司"},
    {"code":"000686","name":"东北证券","market":"SZ","full_name":"东北证券股份有限公司"},
    {"code":"000728","name":"国元证券","market":"SZ","full_name":"国元证券股份有限公司"},
    {"code":"000750","name":"国海证券","market":"SZ","full_name":"国海证券股份有限公司"},
    {"code":"000776","name":"广发证券","market":"SZ","full_name":"广发证券股份有限公司"},
    {"code":"000783","name":"长江证券","market":"SZ","full_name":"长江证券股份有限公司"},
    {"code":"002500","name":"山西证券","market":"SZ","full_name":"山西证券股份有限公司"},
    {"code":"002670","name":"国盛金控","market":"SZ","full_name":"国盛金融控股集团股份有限公司"},
    {"code":"002673","name":"西部证券","market":"SZ","full_name":"西部证券股份有限公司"},
    {"code":"002736","name":"国信证券","market":"SZ","full_name":"国信证券股份有限公司"},
    {"code":"002926","name":"华西证券","market":"SZ","full_name":"华西证券股份有限公司"},
    {"code":"002939","name":"长城证券","market":"SZ","full_name":"长城证券股份有限公司"},
    {"code":"002945","name":"华林证券","market":"SZ","full_name":"华林证券股份有限公司"},

    # ===== 期货 (4家) =====
    {"code":"600927","name":"永安期货","market":"SH","full_name":"永安期货股份有限公司"},
    {"code":"603093","name":"南华期货","market":"SH","full_name":"南华期货股份有限公司"},
    {"code":"001236","name":"弘业期货","market":"SZ","full_name":"弘业期货股份有限公司"},
    {"code":"002961","name":"瑞达期货","market":"SZ","full_name":"瑞达期货股份有限公司"},

    # ===== 信托 (1家) =====
    {"code":"600816","name":"建元信托","market":"SH","full_name":"建元信托股份有限公司"},

    # ===== 金融科技/金控/其他 (16家) =====
    {"code":"300059","name":"东方财富","market":"SZ","full_name":"东方财富信息股份有限公司"},
    {"code":"300033","name":"同花顺","market":"SZ","full_name":"浙江核新同花顺网络信息股份有限公司"},
    {"code":"600061","name":"国投资本","market":"SH","full_name":"国投资本股份有限公司"},
    {"code":"600095","name":"湘财股份","market":"SH","full_name":"湘财股份有限公司"},
    {"code":"600120","name":"浙江东方","market":"SH","full_name":"浙江东方金融控股集团股份有限公司"},
    {"code":"600155","name":"华创云信","market":"SH","full_name":"华创云信数字技术股份有限公司"},
    {"code":"600390","name":"五矿资本","market":"SH","full_name":"五矿资本股份有限公司"},
    {"code":"600517","name":"国网英大","market":"SH","full_name":"国网英大股份有限公司"},
    {"code":"600621","name":"华鑫股份","market":"SH","full_name":"上海华鑫股份有限公司"},
    {"code":"600643","name":"爱建集团","market":"SH","full_name":"上海爱建集团股份有限公司"},
    {"code":"600864","name":"哈投股份","market":"SH","full_name":"哈尔滨投资股份有限公司"},
    {"code":"000532","name":"华金资本","market":"SZ","full_name":"珠海华金资本股份有限公司"},
    {"code":"000567","name":"海德股份","market":"SZ","full_name":"海南海德资本管理股份有限公司"},
    {"code":"000617","name":"中油资本","market":"SZ","full_name":"中国石油集团资本股份有限公司"},
    {"code":"000987","name":"越秀资本","market":"SZ","full_name":"广州越秀资本控股集团股份有限公司"},
    {"code":"002423","name":"中粮资本","market":"SZ","full_name":"中粮资本控股股份有限公司"},
]


def main():
    # 去重
    seen = set()
    unique = []
    for c in FINANCE_COMPANIES:
        if c["code"] not in seen:
            seen.add(c["code"])
            unique.append(c)

    # 1. 写入 company_mapping.json
    mapping_file = DATA_DIR / "company_mapping.json"
    with open(mapping_file, "w", encoding="utf-8") as f:
        json.dump(unique, f, ensure_ascii=False, indent=2)
    print(f"[1/4] company_mapping.json: {len(unique)} 家金融公司")

    # 2. 重新初始化 CompanyMapper
    from database.company_mapping import get_mapper
    mapper = get_mapper()
    print(f"[2/4] CompanyMapper 已加载: {mapper.count} 家")

    # 3. 重建 SQLite 数据库
    from database.db_manager import get_db
    db = get_db()
    # 清空旧数据（注意外键顺序）
    cursor = db.conn.cursor()
    cursor.execute("PRAGMA foreign_keys=OFF")
    for table in ["analysis_reports", "financial_highlights", "business_segments",
                   "construction_projects", "financial_statements", "scraper_logs", "companies"]:
        cursor.execute(f"DELETE FROM {table}")
    cursor.execute("PRAGMA foreign_keys=ON")
    db.conn.commit()

    for c in unique:
        db.upsert_company(
            stock_code=c["code"],
            short_name=c["name"],
            full_name=c.get("full_name", ""),
            market=c.get("market", "SZ"),
        )
    print(f"[3/4] SQLite数据库重建: {len(unique)} 条记录")

    # 4. 验证搜索
    print(f"\n[4/4] 搜索验证:")
    tests = ["工商银行", "中国平安", "招商银行", "中信证券", "东方财富"]
    for q in tests:
        r = mapper.search(q, limit=3)
        names = " | ".join([f'{c["name"]}({c["code"]})' for c in r])
        print(f'   "{q}": {names}')

    # 分类统计
    print(f"\n=== 金融公司分类统计 ===")
    banks = [c for c in unique if "银行" in c["name"]]
    insur_comp = [c for c in unique if c["name"] in ["中国平安","中国人寿","中国太保","中国人保","新华保险"]]
    sec   = [c for c in unique if "证券" in c["name"]]
    fut   = [c for c in unique if "期货" in c["name"]]
    trust = [c for c in unique if "信托" in c["name"]]
    other = [c for c in unique if c not in banks and c not in insur_comp and c not in sec and c not in fut and c not in trust]
    print(f"  银行: {len(banks)}家  保险: {len(insur_comp)}家  证券: {len(sec)}家")
    print(f"  期货: {len(fut)}家  信托: {len(trust)}家  金控/其他: {len(other)}家")
    print(f"  总计: {len(unique)}家")


if __name__ == "__main__":
    main()
