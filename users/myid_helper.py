import time
import requests
from django.conf import settings

_cached_token = None
_token_expiry = 0

def get_myid_access_token():
    global _cached_token, _token_expiry

    now = time.time()
    if _cached_token and now < _token_expiry:
        return _cached_token  # Token hali yaroqli

    url = f"{settings.MYID_BASE_URL}/oauth/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": settings.MYID_CLIENT_ID,
        "client_secret": settings.MYID_CLIENT_SECRET
    }

    res = requests.post(url, data=data)
    if res.status_code != 200:
        raise Exception(f"Token olishda xatolik: {res.text}")

    result = res.json()
    _cached_token = result.get("access_token")
    _token_expiry = now + result.get("expires_in", 3600) - 60  # 1 daqiqa xavfsizlik uchun

    return _cached_token
