"""
WebGIS — 数据初始化脚本
首次运行或 config.yaml 变更后执行
用法: python init.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from backend.database import init_db
    from backend.importer import import_all_configured_cities
except ImportError as e:
    print(f"错误: 缺少依赖包 ({e})")
    print("请先安装: pip install fastapi uvicorn sqlalchemy geopandas networkx scipy pyproj shapely pydantic pyyaml")
    sys.exit(1)

print("=" * 50)
print("  WebGIS 数据初始化")
print("=" * 50)

print("\n[1/2] 初始化数据库...")
init_db()
print("  数据库就绪")

print("\n[2/2] 导入已配置城市...")
results = import_all_configured_cities()
for r in results:
    layers_info = ", ".join(f"{k}({v['feature_count']})" for k, v in r.get("layers", {}).items())
    print(f"  {r['city_name']} ({r['schema_name']}): {len(r['layers'])} 图层 [{layers_info}]")
    print(f"    设施容量记录: {r.get('capacity_imported', 0)} 条")

print(f"\n完成 — 共 {len(results)} 个城市已就绪")
print("  运行 python run.py 启动服务")
