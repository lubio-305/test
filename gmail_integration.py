import os
import base64
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]

CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"


def get_gmail_service():
    """Authenticate and return Gmail API service."""
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"找不到 {CREDENTIALS_FILE}，請先從 Google Cloud Console 下載 OAuth2 憑證檔案"
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def list_messages(service, user_id="me", max_results=10, query=""):
    """List emails in inbox."""
    try:
        result = service.users().messages().list(
            userId=user_id, maxResults=max_results, q=query
        ).execute()
        messages = result.get("messages", [])
        return messages
    except HttpError as e:
        print(f"列出郵件失敗: {e}")
        return []


def get_message(service, msg_id, user_id="me"):
    """Get a specific email by ID."""
    try:
        msg = service.users().messages().get(userId=user_id, id=msg_id, format="full").execute()
        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}

        body = ""
        payload = msg["payload"]
        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain":
                    data = part["body"].get("data", "")
                    body = base64.urlsafe_b64decode(data).decode("utf-8")
                    break
        elif "body" in payload and payload["body"].get("data"):
            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")

        return {
            "id": msg_id,
            "subject": headers.get("Subject", "(無主旨)"),
            "from": headers.get("From", ""),
            "to": headers.get("To", ""),
            "date": headers.get("Date", ""),
            "body": body,
            "snippet": msg.get("snippet", ""),
        }
    except HttpError as e:
        print(f"取得郵件失敗: {e}")
        return None


def send_message(service, to, subject, body, user_id="me"):
    """Send an email."""
    try:
        msg = MIMEText(body)
        msg["to"] = to
        msg["subject"] = subject

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        result = service.users().messages().send(
            userId=user_id, body={"raw": raw}
        ).execute()
        print(f"郵件已送出，ID: {result['id']}")
        return result
    except HttpError as e:
        print(f"寄送郵件失敗: {e}")
        return None


def send_html_message(service, to, subject, html_body, user_id="me"):
    """Send an HTML email."""
    try:
        msg = MIMEMultipart("alternative")
        msg["to"] = to
        msg["subject"] = subject
        msg.attach(MIMEText(html_body, "html"))

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        result = service.users().messages().send(
            userId=user_id, body={"raw": raw}
        ).execute()
        print(f"HTML 郵件已送出，ID: {result['id']}")
        return result
    except HttpError as e:
        print(f"寄送 HTML 郵件失敗: {e}")
        return None


def mark_as_read(service, msg_id, user_id="me"):
    """Mark a message as read."""
    try:
        service.users().messages().modify(
            userId=user_id, id=msg_id, body={"removeLabelIds": ["UNREAD"]}
        ).execute()
    except HttpError as e:
        print(f"標記已讀失敗: {e}")


def get_profile(service, user_id="me"):
    """Get Gmail account profile."""
    try:
        profile = service.users().getProfile(userId=user_id).execute()
        return profile
    except HttpError as e:
        print(f"取得個人資料失敗: {e}")
        return None


if __name__ == "__main__":
    print("正在連接 Gmail API...")
    service = get_gmail_service()

    profile = get_profile(service)
    if profile:
        print(f"登入帳號: {profile['emailAddress']}")
        print(f"郵件總數: {profile['messagesTotal']}")

    print("\n最新 5 封郵件:")
    messages = list_messages(service, max_results=5)
    for i, msg_meta in enumerate(messages, 1):
        msg = get_message(service, msg_meta["id"])
        if msg:
            print(f"\n[{i}] 主旨: {msg['subject']}")
            print(f"    寄件人: {msg['from']}")
            print(f"    日期: {msg['date']}")
            print(f"    摘要: {msg['snippet'][:80]}...")
