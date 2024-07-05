import os
import base64
import requests
from flask import (
    redirect,
    url_for,
    )


def get_access_token(refershToken):
    requestData = {
        "grant_type": "refresh_token",
        "refresh_token": refershToken
        }
    authHeader = base64.urlsafe_b64encode(
        (os.getenv("DEUTSCHE_CLIENT_ID")+":"+os.getenv("DEUTSCHE_CLIENT_KEY")).encode()  # noqa: E501
        )
    requestHeaders = {
        "Authorization": "Basic "+authHeader.decode("utf-8")
        }
    res = requests.post('https://simulator-api.db.com/gw/oidc/token', data=requestData, headers=requestHeaders)  # noqa: E501
    if res.status_code != 200:
        return redirect(url_for('deutsche.login_to_bank'))
    print("In Utils file\n", res.json())
    return res.json().get("access_token")
