#!/usr/bin/env python3
"""One-time helper: sign in with Google and print a Gmail refresh token.

Run this on YOUR computer (not on the server):

    python tools/get_gmail_refresh_token.py          # narrowest scope: send to yourself only
    python tools/get_gmail_refresh_token.py --full   # fallback: gmail.send

It asks for the OAuth client ID and secret (Desktop app type) from Google
Cloud, opens your browser so you can approve "send email" access for your
Gmail account, and prints a refresh token. Put that token into Render as
GMAIL_REFRESH_TOKEN. Nothing is written to disk and nothing is sent anywhere
except to Google.

Standard library only.
"""
import argparse
import getpass
import http.server
import json
import secrets
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

# Narrowest option: the app can only send email to the account owner (the contact
# form only ever emails you). Neither scope lets the app read your mailbox.
SCOPE_SELF = "https://www.googleapis.com/auth/gmail.send.self"
# Fallback if Google's send endpoint rejects the .self scope: send as you, to anyone.
SCOPE_FULL = "https://www.googleapis.com/auth/gmail.send"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
PORT = 8765
REDIRECT_URI = f"http://127.0.0.1:{PORT}"


def wait_for_redirect(expected_state):
    """Run a tiny local web server until Google redirects back with a code."""
    result = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if "code" in query or "error" in query:
                if query.get("state", [""])[0] == expected_state:
                    result.update({k: v[0] for k, v in query.items()})
                else:
                    result["error"] = "state_mismatch"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"<h2>Done - you can close this tab and go back to the terminal.</h2>"
            )

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", PORT), Handler)
    try:
        while not result:
            server.handle_request()
    finally:
        server.server_close()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--full", action="store_true",
                        help="request gmail.send instead of the narrower gmail.send.self")
    args = parser.parse_args()
    scope = SCOPE_FULL if args.full else SCOPE_SELF
    print(f"Requesting scope: {scope}")

    client_id = input("OAuth client ID: ").strip()
    client_secret = getpass.getpass("OAuth client secret (typing is hidden): ").strip()

    state = secrets.token_urlsafe(16)
    auth_url = AUTH_URL + "?" + urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": scope,
        "access_type": "offline",   # needed to get a refresh token
        "prompt": "consent",        # forces Google to issue a refresh token
        "state": state,
    })
    print("\nOpening your browser. If it does not open, paste this link into it:\n")
    print(auth_url, "\n")
    webbrowser.open(auth_url)

    result = wait_for_redirect(state)
    if "code" not in result:
        raise SystemExit(f"Authorisation failed: {result.get('error', 'unknown error')}")

    data = urllib.parse.urlencode({
        "code": result["code"],
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode("utf-8")
    try:
        with urllib.request.urlopen(urllib.request.Request(TOKEN_URL, data=data), timeout=15) as resp:
            tokens = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"Google rejected the code: {exc.read().decode('utf-8', 'replace')}")

    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        raise SystemExit(
            "Google did not return a refresh token. Remove this app at "
            "https://myaccount.google.com/permissions and run the script again."
        )
    print("Success! Add this in Render as GMAIL_REFRESH_TOKEN (keep it secret):\n")
    print(refresh_token)


if __name__ == "__main__":
    main()
