# self-note: Rahul - check your old oauth redditstyle form barebones to fix issues

import time
import os, json, threading
from dotenv import load_dotenv
from requests_oauthlib import OAuth2Session
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Load your credentials
load_dotenv()
CLIENT_ID     = os.getenv("MUSICBRAINZ_CLIENT_ID")
CLIENT_SECRET = os.getenv("MUSICBRAINZ_CLIENT_SECRET")
REDIRECT_URI  = os.getenv("MUSICBRAINZ_REDIRECT_URI")

# OAuth endpoints & scopes
AUTH_URL  = "https://musicbrainz.org/oauth2/authorize"
TOKEN_URL = "https://musicbrainz.org/oauth2/token"
SCOPES    = ["profile", "tag", "rating"]

# Token file (dynamic tokens live here)
TOKEN_FILE = os.path.expanduser("~/.musicbrainz_token.json")

def _save_token(token):
    with open(TOKEN_FILE, "w") as f:
        json.dump(token, f)


def _load_token():
    if os.path.exists(TOKEN_FILE):
        token = json.load(open(TOKEN_FILE))
        # Add safety margin
        if time.time() >= token.get("expires_at", 0) - 5:
            print("Token expired, triggering re-auth...")
            return None
        return token
    return None

# musicbrainz oauth2 do not have auto refresh, so we need to manually refresh the token every 1 hour
def get_musicbrainz_session():
    token = _load_token()
    mb = OAuth2Session(
        client_id=CLIENT_ID,
        redirect_uri=REDIRECT_URI,
        scope=SCOPES,
        token=token,
        # auto_refresh_url=TOKEN_URL,
        # auto_refresh_kwargs={
        #     "client_id": CLIENT_ID,
        #     "client_secret": CLIENT_SECRET,
        # },
        # token_updater=_save_token
    )
    mb.headers.update({
        "User-Agent": "wave-guide/0.1",
        "From": "f1rahulranjan@gmail.com"
        })

    # If no token, do the auth flow
    if token is None:
        # tiny server to catch the code
        class CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                qs   = parse_qs(urlparse(self.path).query)
                code = qs.get("code", [None])[0]
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Authorized-thanks!")
                CallbackHandler.authorization_code = code

        httpd = HTTPServer(("localhost", 8888), CallbackHandler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()

        auth_url, _ = mb.authorization_url(AUTH_URL)
        print("Open this URL:\n", auth_url)

        # wait for redirect
        while not hasattr(CallbackHandler, "authorization_code"):
            pass
        httpd.shutdown()
        code = CallbackHandler.authorization_code

        token = mb.fetch_token(
            TOKEN_URL,
            client_secret=CLIENT_SECRET,
            code=code
        )
        _save_token(token)
        print("Token fetched and saved.")

    return mb

# DO the auth dance, will you?
if __name__ == "__main__":
    get_musicbrainz_session()
    print("Session is ready—use this module from your other scripts.")
