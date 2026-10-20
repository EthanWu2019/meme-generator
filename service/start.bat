@echo off
chcp 65001 > nul
set MEME_HOME=%~dp0
set MEME_PORT=8766
set MEME_HOST=127.0.0.1
cd /d %~dp0
"D:\TRSSYUNZAI\MemeService\.venv\Scripts\python.exe" server.py
