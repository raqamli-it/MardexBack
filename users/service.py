# services/atmos/service.py
import requests
import time
import logging
from config import settings
from typing import Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from django.core.cache import cache

logger = logging.getLogger(__name__)


# ATMOS API uchun umumiy class
class AtmosAPI:
    TOKEN_CACHE_KEY = "atmos_access_token"
    TOKEN_EXPIRES_IN_FALLBACK = 3500  # fallback if provider doesn't return expires_in
    TIMEOUT = 5  # seconds for HTTP requests
    _SESSION: Optional[requests.Session] = None
    _CACHE_LOCK_KEY = "atmos_token_lock"
    _CACHE_LOCK_TTL = 10  # seconds

    @classmethod
    def _get_session(cls) -> requests.Session:
        if cls._SESSION is None:
            session = requests.Session()
            retries = Retry(
                total=3,
                backoff_factor=0.5,
                status_forcelist=(500, 502, 503, 504),
                allowed_methods=frozenset(["POST", "GET", "PUT", "DELETE", "OPTIONS"])
            )
            adapter = HTTPAdapter(max_retries=retries, pool_maxsize=10, pool_connections=10)
            session.mount("https://", adapter)
            session.mount("http://", adapter)
            cls._SESSION = session
        return cls._SESSION

    @classmethod
    def _acquire_lock(cls) -> bool:
        try:
            return cache.add(cls._CACHE_LOCK_KEY, "1", timeout=cls._CACHE_LOCK_TTL)
        except Exception:
            logger.warning("Cache lock acquisition failed.")
            return False

    @classmethod
    def _release_lock(cls) -> None:
        try:
            cache.delete(cls._CACHE_LOCK_KEY)
        except Exception:
            logger.warning("Cache lock release failed.")

    @classmethod
    def get_access_token(cls) -> str:
        # 1) Check cache
        token_data = cache.get(cls.TOKEN_CACHE_KEY)
        if token_data:
            access_token = token_data.get("access_token")
            if access_token:
                return access_token

        # 2) Acquire lock
        lock_acquired = cls._acquire_lock()
        if not lock_acquired:
            time.sleep(0.5)
            token_data = cache.get(cls.TOKEN_CACHE_KEY)
            if token_data and token_data.get("access_token"):
                return token_data["access_token"]

        session = cls._get_session()
        url = f"{settings.ATMOS_BASE_URL.rstrip('/')}/token"

        payload = {
            "grant_type": "client_credentials",
            "client_id": settings.ATMOS_CONSUMER_KEY,
            "client_secret": settings.ATMOS_CONSUMER_SECRET,
        }

        try:
            response = session.post(url, data=payload, timeout=cls.TIMEOUT, verify=True)
        except requests.RequestException as exc:
            logger.exception("ATMOS token request failed at network level")
            if lock_acquired:
                cls._release_lock()
            raise Exception("Failed to connect to ATMOS for token") from exc

        try:
            data = response.json()
        except ValueError:
            logger.error("ATMOS token response is not valid JSON; status=%s text=%s", response.status_code, response.text[:1000])
            if lock_acquired:
                cls._release_lock()
            raise Exception("Invalid response from ATMOS token endpoint")

        if response.status_code != 200 or "access_token" not in data:
            logger.error("ATMOS token fetch failed; status=%s, body=%s", response.status_code, data)
            if lock_acquired:
                cls._release_lock()
            raise Exception("ATMOS token fetch failed")

        access_token = data["access_token"]
        expires_in = data.get("expires_in") or cls.TOKEN_EXPIRES_IN_FALLBACK
        ttl = max(int(expires_in) - 5, 60)

        try:
            cache.set(cls.TOKEN_CACHE_KEY, {"access_token": access_token, "expires_at": int(time.time()) + ttl}, ttl)
        except Exception:
            logger.warning("Failed to cache token; continuing without cache.")

        if lock_acquired:
            cls._release_lock()

        return access_token

    @classmethod
    def make_headers(cls) -> dict:
        return {
            "Authorization": f"Bearer {cls.get_access_token()}",
            "Content-Type": "application/json",
        }


class AtmosService:
    """
    Secure, optimized, production-ready service class
    for interacting with ATMOS API.
    """

    # General request sender
    @staticmethod
    def send_request(method, url, payload=None):
        headers = AtmosAPI.make_headers()

        # Retry strategy
        retry = Retry(
            total=3,
            backoff_factor=0.3,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["POST", "GET"]
        )

        adapter = HTTPAdapter(max_retries=retry)
        session = requests.Session()
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        try:
            if method == "POST":
                response = session.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=AtmosAPI.TIMEOUT
                )
            else:
                response = session.get(
                    url,
                    headers=headers,
                    timeout=AtmosAPI.TIMEOUT
                )

            # Log API response
            logger.info("ATMOS API [%s] %s → %s", method, url, response.status_code)

            # Validate response structure
            try:
                data = response.json()
            except Exception:
                logger.error("Invalid JSON from ATMOS: %s", response.text)
                return {"error": "Invalid JSON response"}, 500

            return data, response.status_code

        except requests.RequestException as e:
            logger.exception("ATMOS Request Failed: %s", str(e))
            return {"error": "ATMOS connection error"}, 500

    # Specific methods
    @staticmethod
    def pre_apply(payload):
        url = f"{settings.ATMOS_BASE_URL['BASE_URL']}/merchant/pay/pre-apply"
        return AtmosService.send_request("POST", url, payload)

    @staticmethod
    def apply(payload):
        url = f"{settings.ATMOS_BASE_URL['BASE_URL']}/merchant/pay/apply"
        return AtmosService.send_request("POST", url, payload)

    @staticmethod
    def check_status(order_id):
        url = f"{settings.ATMOS_BASE_URL['BASE_URL']}/merchant/pay/status/{order_id}"
        return AtmosService.send_request("GET", url)

    @staticmethod
    def confirm_payment(payload):
        # Same as apply(), so reuse it
        return AtmosService.apply(payload)

    @staticmethod
    def cancel_transaction(payload):
        url = f"{settings.ATMOS_BASE_URL['BASE_URL']}/merchant/pay/reverse"
        return AtmosService.send_request("POST", url, payload)
