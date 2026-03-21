import sys
import time
import importlib
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/bot", tags=["bot"])

bot_start_time = time.time()

@router.get("/status")
async def bot_status():
    return {
        "status": "success",
        "uptime": int(time.time() - bot_start_time),
        "ping": 0,  # Ping simulation or metrics tie-in pending
        "messages": 0
    }

@router.get("/plugins")
async def get_plugins():
    modules = [m for m in sys.modules.keys() if m.startswith("app.plugins.")]
    return {"status": "success", "plugins": modules}

@router.post("/plugins/{plugin_path}/{action}")
async def manage_plugin(plugin_path: str, action: str):
    if action == "reload":
        if plugin_path in sys.modules:
            importlib.reload(sys.modules[plugin_path])
            return {"status": "success", "message": f"{plugin_path} reloaded dynamically."}
        raise HTTPException(status_code=404, detail="Plugin not loaded")
        
    elif action == "unload":
        if plugin_path in sys.modules:
            del sys.modules[plugin_path]
            return {"status": "success", "message": f"{plugin_path} removed from sys.modules."}
            
    elif action == "load":
        importlib.import_module(plugin_path)
        return {"status": "success", "message": f"{plugin_path} loaded dynamically."}
        
    raise HTTPException(status_code=400, detail="Invalid action")
