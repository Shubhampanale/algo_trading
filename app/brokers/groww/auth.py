import time
import uuid
import hashlib
import requests
import pyotp
from datetime import datetime, timedelta

from growwapi import GrowwAPI
from growwapi.groww.exceptions import BaseGrowwException


def fetch_token_and_profile(
    api_key: str,
    totp_secret: str | None = None,
    api_secret: str | None = None,
    otp_token: str | None = None,
) -> tuple[str | None, dict]:
    """
    Attempt to obtain a Groww access token + user profile.

    Priority:
      1. TOTP Flow  — api_key (long key) + totp_secret  → GrowwAPI.get_access_token
      2. Legacy Flow — api_key + api_secret              → REST checksum endpoint
    """
    clean_key = str(api_key).strip() if api_key else None
    clean_secret = str(totp_secret).replace(" ", "").upper() if totp_secret else None

    # ── Flow 1: TOTP ─────────────────────────────────────────────────────────
    if clean_secret and clean_key:
        try:
            key_preview = (
                f"{clean_key[:6]}...{clean_key[-4:]}" if len(clean_key) > 50 else "N/A"
            )
            print(f"[AUTH] 🚀 TOTP Flow — api_key={key_preview}")

            otp_now = pyotp.TOTP(clean_secret).now()
            print(f"[AUTH] 🔢 Generated OTP: {otp_now}")

            token = GrowwAPI.get_access_token(api_key=clean_key, totp=otp_now)
            if token:
                print(f"[AUTH] ✅ Token received (len={len(token)})")
                temp_client = GrowwAPI(token)
                profile = temp_client.get_user_profile() or {}
                return token, profile

            print("[AUTH] ❌ No token returned from TOTP flow")
        except Exception as exc:
            import traceback
            print(f"[AUTH] ❌ TOTP Flow error: {exc}")
            traceback.print_exc()

    # ── Flow 2: Legacy API Key / Secret ──────────────────────────────────────
    if api_secret and clean_key:
        print("[AUTH] 🕯️ Falling back to Legacy Key/Secret flow")
        base_url = "https://api.groww.in/v1/token/api/access"
        headers = {
            "x-request-id": str(uuid.uuid4()),
            "Authorization": f"Bearer {clean_key}",
            "Content-Type": "application/json",
            "x-api-version": "1.0",
        }
        timestamp = int(time.time())
        checksum = hashlib.sha256(
            (str(api_secret) + str(timestamp)).encode()
        ).hexdigest()
        body: dict = {"key_type": "approval", "checksum": checksum, "timestamp": timestamp}

        resp = requests.post(base_url, headers=headers, json=body, timeout=15)

        if resp.status_code != 200:
            otp_code = otp_token or (pyotp.TOTP(totp_secret).now() if totp_secret else None)
            if otp_code:
                body["otp"] = otp_code
                resp = requests.post(base_url, headers=headers, json=body, timeout=15)

        if resp.status_code == 200:
            data = resp.json() or {}
            return data.get("token"), data.get("user", {})

    print("[AUTH] ❌ All authentication flows failed")
    return None, {}


def init_sdk_client(auth_token: str) -> GrowwAPI | None:
    """Return an initialised GrowwAPI client or None on failure."""
    try:
        return GrowwAPI(auth_token)
    except BaseGrowwException as err:
        print(f"[AUTH] SDK init failed: {err}")
        return None