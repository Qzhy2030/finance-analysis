@echo off
chcp 65001 >nul
title 财务数据分析平台

echo ==========================================
echo   📊 财务数据分析平台 - 启动脚本
echo ==========================================
echo.

:: 激活虚拟环境
call venv\Scripts\activate.bat

:: 检查数据库
echo [1/3] 检查数据库...
python -c "from database.db_manager import get_db; get_db(); print('  ✅ 数据库就绪')"

:: 初始化公司映射数据
echo [2/3] 加载公司映射...
python -c "from database.company_mapping import get_mapper; m=get_mapper(); print(f'  ✅ {m.count} 家公司已加载')"

:: 启动 Streamlit
echo [3/3] 启动 Web 服务...
echo.
echo   🌐 访问地址: http://localhost:8501
echo.
streamlit run app.py --server.port=8501 --server.headless=true

pause
