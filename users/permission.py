from rest_framework.permissions import BasePermission
import requests
from django.conf import settings

class IsMyIDTokenValid(BasePermission):
    def has_permission(self, request, view):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            return False
        res = requests.get(f"{settings.MYID_BASE_URL}/sdk/validate-token", headers={"Authorization": f"Bearer {token}"})
        return res.status_code == 200
