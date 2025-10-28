import base64
import requests
from django.conf import settings

def _get_auth_header():
    auth_str = f"{settings.MYID_CLIENT_ID}:{settings.MYID_CLIENT_SECRET}"
    base64_auth = base64.b64encode(auth_str.encode()).decode()
    return {"Authorization": f"Basic {base64_auth}"}

def start_verification(data):
    """MyID bilan shaxsni tekshirishni boshlaydi"""
    url = f"{settings.MYID_BASE_URL}/start-verification"
    headers = {"Content-Type": "application/json", **_get_auth_header()}

    payload = {
        "document_series": data["passport_seria"],
        "document_number": data["passport_number"],
        "birth_date": data["birth_date"],  # "YYYY-MM-DD"
        "pinfl": data["jshshir"],
        "citizenship": data["citizenship"],  # "UZ" yoki "FOREIGN"
        "redirect_url": settings.MYID_REDIRECT_URL
    }

    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()

def get_verification_result(verification_id):
    """Tasdiqlashdan keyingi natijani olish"""
    url = f"{settings.MYID_BASE_URL}/verification-result/{verification_id}"
    headers = _get_auth_header()
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()
