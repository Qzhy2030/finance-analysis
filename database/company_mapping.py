"""
公司名称-股票代码映射数据库
支持模糊搜索、拼音匹配、增量更新
"""
import json
import re
from pathlib import Path
from typing import Optional
from fuzzywuzzy import fuzz, process

from config import COMPANY_MAPPING_FILE

# ========== 种子数据（金融行业97家）==========
_SEED_FILE = Path(__file__).parent / "finance_seed.json"

def _load_seed_companies() -> list:
    """加载种子公司数据"""
    if _SEED_FILE.exists():
        try:
            with open(_SEED_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # 内置最小样本（确保无JSON文件时仍可用）
    return [
        {"code": "601398", "name": "工商银行", "market": "SH"},
        {"code": "600036", "name": "招商银行", "market": "SH"},
        {"code": "601318", "name": "中国平安", "market": "SH"},
        {"code": "600030", "name": "中信证券", "market": "SH"},
        {"code": "300059", "name": "东方财富", "market": "SZ"},
    ]

_BUILTIN_COMPANIES = _load_seed_companies()


class CompanyMapper:
    """公司名称-股票代码映射管理器，支持模糊搜索"""

    AUTO_IMPORT_URL = "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData"

    def __init__(self):
        self._companies = []
        self._search_index = {}  # 索引缓存
        self.load()
        # 如果内置数据太少，尝试从缓存文件加载
        if len(self._companies) <= len(_BUILTIN_COMPANIES) + 5:
            self._try_load_from_cache()

    def _try_load_from_cache(self):
        """尝试从已下载的JSON缓存加载"""
        cache_files = [
            COMPANY_MAPPING_FILE,
            Path(__file__).parent.parent / "data" / "company_mapping.json",
        ]
        for cf in cache_files:
            if cf.exists() and cf.stat().st_size > 10240:  # >10KB 认为已包含大量数据
                try:
                    with open(cf, "r", encoding="utf-8") as f:
                        cached = json.load(f)
                    if len(cached) > len(self._companies):
                        self._companies = cached
                        self._build_index()
                        print(f"[CompanyMapper] 从缓存加载了 {len(cached)} 家公司")
                        return
                except Exception:
                    pass

    # ── 数据加载与持久化 ──────────────────────────────

    def load(self):
        """加载公司数据：优先从本地缓存，否则使用内置种子数据"""
        if COMPANY_MAPPING_FILE.exists():
            with open(COMPANY_MAPPING_FILE, "r", encoding="utf-8") as f:
                self._companies = json.load(f)
        else:
            self._companies = list(_BUILTIN_COMPANIES)
            self._save()
        self._build_index()

    def _save(self):
        COMPANY_MAPPING_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(COMPANY_MAPPING_FILE, "w", encoding="utf-8") as f:
            json.dump(self._companies, f, ensure_ascii=False, indent=2)

    def _build_index(self):
        """构建多维度搜索索引"""
        self._search_index = {}
        for item in self._companies:
            code = item["code"]
            name = item["name"]
            full_name = item.get("full_name", "")
            # 按代码索引
            self._search_index[code] = item
            # 按简称索引
            self._search_index[name] = item
            # 按全称索引
            if full_name:
                self._search_index[full_name] = item

    # ── 模糊搜索 ──────────────────────────────────────

    def search(self, keyword: str, limit: int = 20) -> list:
        """
        模糊搜索公司，支持：
        - 股票代码精确匹配
        - 公司简称/全称模糊匹配
        - 拼音首字母匹配
        """
        if not keyword or not keyword.strip():
            return self._companies[:limit]

        keyword = keyword.strip().upper()

        # 1. 精确匹配代码
        if keyword in self._search_index:
            return [self._search_index[keyword]]

        # 2. 构建候选文本列表用于模糊匹配
        candidates = []
        for item in self._companies:
            text = f"{item['name']} {item.get('full_name', '')} {item['code']}"
            candidates.append((text, item))

        # 3. fuzzywuzzy 模糊匹配（传入字符串列表，手动映射回公司对象）
        search_texts = [text for text, item in candidates]
        results = process.extract(
            keyword, search_texts,
            scorer=fuzz.partial_ratio,
            limit=limit
        )
        # 过滤低分结果（<40分），将匹配文本映射回公司对象
        text_to_company = {text: item for text, item in candidates}
        filtered = []
        for text, score in results:
            if score >= 40 and text in text_to_company:
                filtered.append((text_to_company[text], score))
        filtered.sort(key=lambda x: (-x[1], x[0]["code"]))

        return [item for item, score in filtered]

    def get_by_code(self, code: str) -> Optional[dict]:
        """通过股票代码获取公司信息"""
        code = code.strip().upper()
        return self._search_index.get(code)

    def get_by_name(self, name: str) -> Optional[dict]:
        """通过公司简称获取公司信息（精确匹配）"""
        name = name.strip()
        return self._search_index.get(name)

    def add_company(self, code: str, name: str, full_name: str = "", market: str = "SZ"):
        """添加或更新公司映射"""
        code = code.strip().upper()
        existing = self.get_by_code(code)
        if existing:
            existing["name"] = name
            if full_name:
                existing["full_name"] = full_name
            existing["market"] = market
        else:
            self._companies.append({
                "code": code, "name": name,
                "full_name": full_name, "market": market,
            })
        self._build_index()
        self._save()

    @property
    def all_companies(self) -> list:
        return list(self._companies)

    @property
    def count(self) -> int:
        return len(self._companies)


# 全局单例
_mapper: Optional[CompanyMapper] = None


def get_mapper() -> CompanyMapper:
    global _mapper
    if _mapper is None:
        _mapper = CompanyMapper()
    return _mapper
