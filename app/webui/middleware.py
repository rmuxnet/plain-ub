import typing
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, RedirectResponse
from .security import verify_session_token

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: typing.Callable):
        if request.url.path in ["/api/auth/login", "/", "/index.html"]:
            return await call_next(request)
            
        if request.url.path.startswith("/static/"):
            return await call_next(request)

        token = request.cookies.get("webui_session")
        if not token or not verify_session_token(token):
            if request.url.path.startswith("/api/"):
                return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
            return RedirectResponse(url="/")
            
        return await call_next(request)
