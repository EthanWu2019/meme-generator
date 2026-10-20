@echo off
REM meme-generator Python 版服务(earth-k 那批专属表情)
REM 必须在 MemePy 目录下启动:manager 用 cwd 相对路径计算模块名
cd /d D:\TRSSYUNZAI\MemePy
set PYTHONPATH=D:\TRSSYUNZAI\MemePy
set PYTHONIOENCODING=utf-8
"D:\TRSSYUNZAI\MemePy\.venv\Scripts\python.exe" D:\TRSSYUNZAI\MemePy\legacy_server.py