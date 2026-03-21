import asyncio
import logging
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import WebUIConfig
from .middleware import AuthMiddleware
from .routes import auth_router
from .routes.bot import router as bot_router
from .routes.ws import router as ws_router
from .routes.system import router as system_router
from .plugin_manager import load_all_plugins, get_plugin_manifest

LOGGER = logging.getLogger("WebUI")

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="UB WebUI Dashboard")

app.add_middleware(AuthMiddleware)
app.include_router(auth_router)
app.include_router(bot_router)
app.include_router(ws_router)
app.include_router(system_router)

from fastapi import Request
from fastapi.responses import HTMLResponse

@app.get("/", response_class=HTMLResponse)
@app.get("/index.html", response_class=HTMLResponse)
async def serve_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

load_all_plugins(app)

@app.get("/api/plugins/manifest")
async def plugin_manifest():
    return {"status": "success", "plugins": get_plugin_manifest()}

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


class WebUIServer:
    def __init__(self):
        self.server = None
        self.task = None

    async def start(self):
        if self.task and not self.task.done():
            LOGGER.warning("WebUI Server is already running.")
            return

        config = uvicorn.Config(
            app=app,
            host=WebUIConfig.HOST,
            port=WebUIConfig.PORT,
            log_level="info",
            access_log=False,
            use_colors=True
        )
        self.server = uvicorn.Server(config)
        
        LOGGER.info(f"Starting WebUI ASGI Server on {WebUIConfig.HOST}:{WebUIConfig.PORT}")
        self.task = asyncio.create_task(self.server.serve())

    async def stop(self):
        if self.server:
            LOGGER.info("Stopping WebUI ASGI Server...")
            self.server.should_exit = True
            if self.task:
                await self.task
            self.server = None
            self.task = None
            LOGGER.info("WebUI Server stopped.")

webui_manager = WebUIServer()
