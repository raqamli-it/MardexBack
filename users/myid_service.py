# import requests
# import os
#
# MYID_BASE_URL = os.getenv("MYID_BASE_URL")
# CLIENT_ID = os.getenv("MYID_CLIENT_ID")
# CLIENT_SECRET = os.getenv("MYID_CLIENT_SECRET")
#
# def get_access_token():
#     url = f"{MYID_BASE_URL}/auth/clients/access-token"
#     data = {
#         "client_id": CLIENT_ID,
#         "client_secret": CLIENT_SECRET
#     }
#     res = requests.post(url, json=data)
#     res.raise_for_status()
#     return res.json()["access_token"]
#
#
# def create_session(pass_data=None, birth_date=None, is_resident=True):
#     access_token = get_access_token()
#     url = f"{MYID_BASE_URL}/sdk/sessions"
#     headers = {"Authorization": f"Bearer {access_token}"}
#     data = {
#         "pass_data": pass_data,
#         "birth_date": birth_date,
#         "is_resident": is_resident
#     }
#     res = requests.post(url, json=data, headers=headers)
#     res.raise_for_status()
#     return res.json()["session_id"]
#
#
# def get_user_data(code):
#     access_token = get_access_token()
#     url = f"{MYID_BASE_URL}/sdk/data?code={code}"
#     headers = {"Authorization": f"Bearer {access_token}"}
#     res = requests.get(url, headers=headers)
#     res.raise_for_status()
#     return res.json()
