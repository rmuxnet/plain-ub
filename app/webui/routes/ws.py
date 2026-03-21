import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["ws"])

class LogTailer:
    clients = []

    @classmethod
    async def broadcast(cls, message: str):
        for client in cls.clients:
            try:
                await client.send_text(message)
            except Exception:
                pass


@router.websocket("/api/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await websocket.accept()
    LogTailer.clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in LogTailer.clients:
            LogTailer.clients.remove(websocket)


class WsLogHandler(logging.Handler):
    def emit(self, record):
        msg = self.format(record)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(LogTailer.broadcast(msg))
        except RuntimeError:
            pass

ws_handler = WsLogHandler()
ws_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logging.getLogger().addHandler(ws_handler)
