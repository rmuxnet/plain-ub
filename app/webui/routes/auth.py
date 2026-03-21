from fastapi import APIRouter, Response, Request, HTTPException
from pydantic import BaseModel
from ..security import verify_totp, create_session_token, revoke_session_token

router = APIRouter(prefix="/api/auth", tags=["auth"])

class LoginRequest(BaseModel):
    code: str

@router.post("/login")
async def login(req: LoginRequest, response: Response):
    if verify_totp(req.code):
        token = create_session_token()
        response.set_cookie(
            key="webui_session",
            value=token,
            httponly=True,
            samesite="strict",
            path="/"
        )
        return {"status": "success", "message": "Authenticated"}
    
    raise HTTPException(status_code=401, detail="Invalid TOTP Code")

@router.post("/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get("webui_session")
    if token:
        revoke_session_token(token)
    response.delete_cookie("webui_session", path="/")
    return {"status": "success", "message": "Logged out"}
