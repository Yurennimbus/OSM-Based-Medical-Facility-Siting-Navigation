"""WebGIS 服务器入口 (无浏览器版)"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backend.config import SERVER_HOST, SERVER_PORT
import uvicorn

uvicorn.run("backend.main:app", host=SERVER_HOST, port=SERVER_PORT, reload=False)
