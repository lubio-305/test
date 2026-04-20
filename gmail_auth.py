"""
用法:
  步驟1 (產生授權網址): python gmail_auth.py
  步驟2 (輸入授權碼):   python gmail_auth.py <授權碼>
"""
import sys
import json
import requests
from urllib.parse import urlencode

CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"

SCOPES = " ".join([
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
])


def load_client_info():
    with open(CREDENTIALS_FILE) as f:
        data = json.load(f)
    info = data.get("installed") or data.get("web")
    return info["client_id"], info["client_secret"]


def generate_auth_url(client_id):
    params = {
        "client_id": client_id,
        "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
    }
    return "https://accounts.google.com/o/oauth2/auth?" + urlencode(params)


def exchange_code(client_id, client_secret, code):
    resp = requests.post("https://oauth2.googleapis.com/token", data={
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
        "grant_type": "authorization_code",
    })
    if resp.status_code != 200:
        print(f"錯誤: {resp.json()}")
        sys.exit(1)

    token = resp.json()
    with open(TOKEN_FILE, "w") as f:
        json.dump({
            "token": token["access_token"],
            "refresh_token": token.get("refresh_token"),
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": client_id,
            "client_secret": client_secret,
            "scopes": SCOPES.split(),
        }, f, indent=2)
    print(f"授權成功！token 已儲存至 {TOKEN_FILE}")


if __name__ == "__main__":
    client_id, client_secret = load_client_info()

    if len(sys.argv) == 1:
        url = generate_auth_url(client_id)
        print("\n請在瀏覽器開啟以下網址進行授權：\n")
        print(url)
        print("\n授權後將頁面上的授權碼執行：")
        print("  python gmail_auth.py <授權碼>\n")
    else:
        code = sys.argv[1]
        exchange_code(client_id, client_secret, code)
