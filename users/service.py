# services/atmos/service.py
import requests
import logging
from django.conf import settings
from requests.adapters import HTTPAdapter, Retry

from users.views import AtmosAPI

logger = logging.getLogger(__name__)


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
