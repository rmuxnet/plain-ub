import os
import secrets
from pathlib import Path

import pyotp

SECRET_FILE = Path(__file__).parent / ".totp_secret"

_active_sessions = set()

def get_or_create_totp_secret() -> tuple[str, str, bool]:
    if SECRET_FILE.exists():
        with open(SECRET_FILE, "r") as f:
            secret = f.read().strip()
        return secret, "", False
    
    secret = pyotp.random_base32()
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name="WebUI", issuer_name="UB_Core")
    
    with open(SECRET_FILE, "w") as f:
        f.write(secret)
        
    try:
        if os.name == 'posix':
            os.chmod(SECRET_FILE, 0o600)
    except Exception:
        pass
        
    return secret, uri, True

def verify_totp(code: str) -> bool:
    if not SECRET_FILE.exists():
        return False
    with open(SECRET_FILE, "r") as f:
        secret = f.read().strip()
    totp = pyotp.TOTP(secret)
    return totp.verify(code)

def create_session_token() -> str:
    token = secrets.token_urlsafe(64)
    _active_sessions.add(token)
    return token

def verify_session_token(token: str) -> bool:
    return token in _active_sessions

def revoke_session_token(token: str) -> None:
    _active_sessions.discard(token)
