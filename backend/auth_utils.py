import os
import logging
import requests
import jwt
from typing import Optional

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://ocydnvzzvfucjxdjochw.supabase.co")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")

def verify_supabase_token(token: str) -> Optional[dict]:
    """
    Verifies a Supabase JWT token.
    Tries offline decoding if SUPABASE_JWT_SECRET is set,
    otherwise falls back to online verification via Supabase Auth API.
    """
    if not token:
        return None

    # 1. Try offline verification if secret is provided
    if SUPABASE_JWT_SECRET:
        try:
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_aud": False}  # Supabase aud is 'authenticated'
            )
            return {
                "id": payload.get("sub"),
                "email": payload.get("email"),
                "name": payload.get("user_metadata", {}).get("name") or payload.get("user_metadata", {}).get("full_name") or payload.get("email", "").split("@")[0].capitalize()
            }
        except jwt.PyJWTError as e:
            logger.error(f"Offline JWT verification failed: {e}")
            return None

    # 2. Fall back to online verification
    url = f"{SUPABASE_URL.rstrip('/')}/auth/v1/user"
    headers = {
        "Authorization": f"Bearer {token}",
        "apikey": SUPABASE_ANON_KEY if SUPABASE_ANON_KEY else "dummy"  # postgrest/gotrue requires apikey header
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            user_data = response.json()
            metadata = user_data.get("user_metadata") or {}
            return {
                "id": user_data.get("id"),
                "email": user_data.get("email"),
                "name": metadata.get("name") or metadata.get("full_name") or user_data.get("email", "").split("@")[0].capitalize()
            }
        else:
            logger.warning(f"Online token verification failed: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Online token verification error: {e}")

    return None
