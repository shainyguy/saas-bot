# app/utils/security.py
import hashlib
import hmac
import json
from urllib.parse import parse_qs
from datetime import datetime, timezone
from jose import jwt

from app.config import settings


def validate_webapp_data(init_data: str) -> dict | None:
    """Проверить подпись данных Telegram WebApp."""
    parsed = parse_qs(init_data)
    received_hash = parsed.get("hash", [None])[0]
    if not received_hash:
        return None

    data_pairs = []
    for key, values in sorted(parsed.items()):
        if key != "hash":
            data_pairs.append(f"{key}={values[0]}")
    data_check_string = "\n".join(data_pairs)

    secret_key = hmac.new(
        b"WebAppData", settings.BOT_TOKEN.encode(), hashlib.sha256
    ).digest()
    computed_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        return None

    user_data = parsed.get("user", [None])[0]
    if user_data:
        return json.loads(user_data)
    return {}


def create_api_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "iat": datetime.now(timezone.utc).timestamp(),
        "exp": datetime.now(timezone.utc).timestamp() + 86400,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def verify_api_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return int(payload["sub"])
    except Exception:
        return None