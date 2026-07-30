@echo off
cd /d "%~dp0"
python fetch_shopee.py >> data\shopee_sync_stdout.log 2>&1
