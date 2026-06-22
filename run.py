"""
WebGIS — Medical Facility Site Selection & Navigation
启动脚本：启动服务器并自动打开浏览器
用法: python run.py
"""
import os
import sys
import time
import webbrowser
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_CONDA_PYTHON = r"E:\Miniconda3\python.exe"
_current_python = sys.executable

try:
    import uvicorn
except ImportError:
    if os.path.exists(_CONDA_PYTHON) and _current_python != _CONDA_PYTHON:
        print(f"[!] 当前 Python 缺少依赖，切换到 Conda 环境...")
        print(f"    {_current_python} -> {_CONDA_PYTHON}")
        os.execv(_CONDA_PYTHON, [_CONDA_PYTHON] + sys.argv)
    else:
        print("错误: 缺少依赖包。请运行:")
        print("  pip install fastapi uvicorn sqlalchemy geopandas networkx scipy pyproj shapely pydantic pyyaml")
        sys.exit(1)

from backend.config import SERVER_HOST, SERVER_PORT


def open_browser():
    time.sleep(3)
    url = f"http://localhost:{SERVER_PORT}"
    webbrowser.open(url)
    print(f"\n>>> 浏览器已打开: {url}\n")


if __name__ == "__main__":
    print("=" * 56)
    print("  WebGIS — 医疗设施选址与导航系统")
    print(f"  启动地址: http://localhost:{SERVER_PORT}")
    print("  按 Ctrl+C 停止服务")
    print("=" * 56)

    threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run(
        "backend.main:app",
        host=SERVER_HOST,
        port=SERVER_PORT,
        reload=False,
        log_level="info",
    )
