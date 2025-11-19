# services/atmos/service.py
import requests
import time
import logging
from django.conf import settings
from typing import Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from django.core.cache import cache

logger = logging.getLogger(__name__)


# ATMOS API uchun umumiy class
class AtmosAPI:
    TOKEN_CACHE_KEY = "atmos_access_token"
    TOKEN_EXPIRES_IN_FALLBACK = 3500  # fallback value if provider doesn't return expires_in
    TIMEOUT = 5  # seconds for requests
    _SESSION: Optional[requests.Session] = None
    _CACHE_LOCK_KEY = "atmos_token_lock"
    _CACHE_LOCK_TTL = 10  # seconds to avoid deadlock

    @classmethod
    def _get_session(cls) -> requests.Session:
        """Return a configured requests.Session with retry/backoff and connection pooling."""
        if cls._SESSION is None:
            session = requests.Session()
            # Retry strategy: backoff, retry on 502/503/504 and connection errors
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
        """
        Try to acquire a simple cache-based lock.
        Uses cache.add which is atomic in most backends (Redis/memcached).
        Returns True if lock acquired, False otherwise.
        """
        try:
            return cache.add(cls._CACHE_LOCK_KEY, "1", timeout=cls._CACHE_LOCK_TTL)
        except Exception:
            # If cache backend doesn't support add/atomic, fallback to False (no lock).
            logger.warning("Cache add failed while acquiring token lock; continuing without lock.")
            return False

    @classmethod
    def _release_lock(cls) -> None:
        try:
            cache.delete(cls._CACHE_LOCK_KEY)
        except Exception:
            logger.warning("Cache delete failed for token lock.")

    @classmethod
    def get_access_token(cls) -> str:
        """
        Return cached access token or fetch new one from ATMOS.
        Implements:
          - cache with expiry based on provider's expires_in
          - simple cache lock to avoid race conditions
          - retries and timeouts via requests.Session
          - safe JSON parsing and sanitized logging
        Raises Exception on failure.
        """
        # 1) Quick return if cached
        token_data = cache.get(cls.TOKEN_CACHE_KEY)
        if token_data:
            # token_data is dict {"access_token": "...", "expires_at": 1234567890}
            access_token = token_data.get("access_token")
            if access_token:
                return access_token

        # 2) Try to acquire lock; if we can't, wait a bit and re-check cache
        lock_acquired = cls._acquire_lock()
        if not lock_acquired:
            # Another process likely fetching token — wait short time and re-read cache
            time.sleep(0.5)
            token_data = cache.get(cls.TOKEN_CACHE_KEY)
            if token_data and token_data.get("access_token"):
                return token_data["access_token"]
            # If still nothing, attempt to fetch token ourselves (best-effort)

        session = cls._get_session()
        url = f"{settings.ATMOS['BASE_URL'].rstrip('/')}/oauth/token"

        try:
            # Use auth via client id/secret in body as currently used.
            response = session.post(
                url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": settings.ATMOS["CLIENT_ID"],
                    "client_secret": settings.ATMOS["CLIENT_SECRET"],
                },
                timeout=cls.TIMEOUT,
                verify=True,  # ensure SSL verification
            )
        except requests.RequestException as exc:
            logger.exception("ATMOS token request failed at network level")
            # release lock if we owned it
            if lock_acquired:
                cls._release_lock()
            raise Exception("Failed to connect to ATMOS for token") from exc

        # parse JSON safely
        try:
            data = response.json()
        except ValueError:
            logger.error("ATMOS token response is not valid JSON; status=%s text=%s", response.status_code, response.text[:1000])
            if lock_acquired:
                cls._release_lock()
            raise Exception("Invalid response from ATMOS token endpoint")

        # verify response and content
        if response.status_code != 200 or "access_token" not in data:
            # DO NOT log secrets - log only non-sensitive fields
            logger.error("ATMOS token fetch failed; status=%s, body_keys=%s", response.status_code, list(data.keys()) if isinstance(data, dict) else None)
            if lock_acquired:
                cls._release_lock()
            raise Exception("ATMOS token fetch failed")

        access_token = data["access_token"]

        # compute expiry: use provider's expires_in if available, fallback to class default
        expires_in = data.get("expires_in") or cls.TOKEN_EXPIRES_IN_FALLBACK
        # set a safety margin (e.g., 5 seconds) and cache slightly less than real TTL
        ttl = max(int(expires_in) - 5, 60)

        # store structured token data in cache to avoid ambiguity
        try:
            cache.set(cls.TOKEN_CACHE_KEY, {"access_token": access_token, "expires_at": int(time.time()) + ttl}, ttl)
        except Exception:
            # if cache set fails, still release lock and return token
            logger.warning("Failed to write token to cache; continuing without cache persistence.")

        # release lock if we acquired it
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
        url = f"{settings.ATMOS['BASE_URL']}/merchant/pay/pre-apply"
        return AtmosService.send_request("POST", url, payload)

    @staticmethod
    def apply(payload):
        url = f"{settings.ATMOS['BASE_URL']}/merchant/pay/apply"
        return AtmosService.send_request("POST", url, payload)

    @staticmethod
    def check_status(order_id):
        url = f"{settings.ATMOS['BASE_URL']}/merchant/pay/status/{order_id}"
        return AtmosService.send_request("GET", url)

    @staticmethod
    def confirm_payment(payload):
        # Same as apply(), so reuse it
        return AtmosService.apply(payload)

    @staticmethod
    def cancel_transaction(payload):
        url = f"{settings.ATMOS['BASE_URL']}/merchant/pay/reverse"
        return AtmosService.send_request("POST", url, payload)
