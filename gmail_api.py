"""Send email through the Gmail API over HTTPS (no SMTP).

Render's free tier blocks outbound SMTP ports (25/465/587), so Flask-Mail with
smtp.gmail.com cannot connect there. The Gmail API talks HTTPS (port 443),
which is allowed, and the mail still goes out from your own Google account.

Required environment variables:
    GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN

Get the refresh token once with tools/get_gmail_refresh_token.py.
Only the standard library is used, so no new dependency is needed.
"""
import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from email.message import EmailMessage

TOKEN_URL = "https://oauth2.googleapis.com/token"
SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
_REQUIRED = ("GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN")

# Access tokens live ~1 hour; keep one around instead of asking Google each time.
_cache = {"token": None, "expires_at": 0.0}


def is_configured():
    return all(os.getenv(name) for name in _REQUIRED)


def _clean(value):
    """Strip line breaks so visitor input can never inject extra headers."""
    return " ".join(str(value).splitlines()).strip()


def _post(url, data, headers, what):
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        raise RuntimeError(f"{what} failed: HTTP {exc.code} {detail}") from exc


def _access_token(force_refresh=False):
    if not force_refresh and _cache["token"] and time.time() < _cache["expires_at"] - 60:
        return _cache["token"]
    data = urllib.parse.urlencode({
        "client_id": os.getenv("GMAIL_CLIENT_ID"),
        "client_secret": os.getenv("GMAIL_CLIENT_SECRET"),
        "refresh_token": os.getenv("GMAIL_REFRESH_TOKEN"),
        "grant_type": "refresh_token",
    }).encode("utf-8")
    payload = _post(TOKEN_URL, data,
                    {"Content-Type": "application/x-www-form-urlencoded"},
                    "Gmail token refresh")
    _cache["token"] = payload["access_token"]
    _cache["expires_at"] = time.time() + int(payload.get("expires_in", 3600))
    return _cache["token"]


def send_email(to, subject, body, reply_to=None, sender=None):
    """Send a plain-text email. The Gmail account that authorised the refresh
    token is the real sender; `sender` should be that same address."""
    msg = EmailMessage()
    msg["To"] = _clean(to)
    msg["From"] = _clean(sender or to)
    msg["Subject"] = _clean(subject)
    if reply_to:
        msg["Reply-To"] = _clean(reply_to)
    msg.set_content(body)
    payload = json.dumps(
        {"raw": base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")}
    ).encode("utf-8")

    for attempt in (1, 2):
        headers = {
            "Authorization": f"Bearer {_access_token(force_refresh=attempt == 2)}",
            "Content-Type": "application/json",
        }
        try:
            return _post(SEND_URL, payload, headers, "Gmail send")
        except RuntimeError as exc:
            # A 401 on the first try means the cached token expired: refresh once.
            if attempt == 1 and "HTTP 401" in str(exc):
                continue
            raise
