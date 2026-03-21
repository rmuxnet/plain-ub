import os
import importlib
import logging
from pathlib import Path
from fastapi import FastAPI

LOGGER = logging.getLogger(__name__)

PLUGINS_DIR = Path(__file__).parent.parent / "webui_plugins"

_plugin_manifest = []

def load_all_plugins(app: FastAPI):
    if not PLUGINS_DIR.exists():
        PLUGINS_DIR.mkdir(parents=True, exist_ok=True)

    for plugin_dir in PLUGINS_DIR.iterdir():
        if plugin_dir.is_dir() and not plugin_dir.name.startswith("_"):
            _load_plugin(app, plugin_dir)

def _load_plugin(app: FastAPI, plugin_path: Path):
    plugin_name = plugin_path.name
    api_file = plugin_path / "api.py"
    html_file = plugin_path / "index.html"
    js_file = plugin_path / "script.js"

    if api_file.exists():
        try:
            module_path = f"app.webui_plugins.{plugin_name}.api"
            mod = importlib.import_module(module_path)
            if hasattr(mod, "router"):
                app.include_router(mod.router, prefix=f"/api/plugins/{plugin_name}")
                LOGGER.info(f"Mounted WebUI Plugin router: {plugin_name}")
        except Exception as e:
            LOGGER.error(f"Failed to load plugin router {plugin_name}: {e}")

    html_content = ""
    js_content = ""
    if html_file.exists():
        with open(html_file, "r", encoding="utf-8") as f:
            html_content = f.read()
    if js_file.exists():
        with open(js_file, "r", encoding="utf-8") as f:
            js_content = f.read()

    _plugin_manifest.append({
        "name": plugin_name,
        "html": html_content,
        "script": js_content
    })

def get_plugin_manifest():
    return _plugin_manifest
