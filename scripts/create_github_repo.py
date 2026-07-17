"""创建 GitHub 仓库并推送代码（token 从环境变量读取）"""
import requests
import subprocess
import sys
import os

TOKEN = os.environ.get("GH_TOKEN", "")
if not TOKEN:
    print("❌ 请设置环境变量 GH_TOKEN")
    sys.exit(1)

REPO_NAME = "finance-analysis"
USERNAME = "Qzhy2030"
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

headers = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

print("🚀 正在创建 GitHub 仓库...")
resp = requests.post("https://api.github.com/user/repos", headers=headers, json={
    "name": REPO_NAME,
    "description": "财务数据分析平台 - AI驱动财报分析 | Streamlit + DeepSeek",
    "private": False,
})

if resp.status_code == 201:
    print(f"✅ 仓库创建成功: {resp.json()['html_url']}")
else:
    print(f"失败: {resp.status_code} {resp.text[:200]}")
