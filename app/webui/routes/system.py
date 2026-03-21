import psutil
from fastapi import APIRouter

router = APIRouter(prefix="/api/system", tags=["system"])

@router.get("/info")
async def system_info():
    return {
        "status": "success",
        "cpu": psutil.cpu_percent(),
        "ram": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage('/').percent,
        "net_sent": psutil.net_io_counters().bytes_sent,
        "net_recv": psutil.net_io_counters().bytes_recv,
    }
