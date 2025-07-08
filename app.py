import logging
import os
from functools import wraps

from flask import Flask, session, request, redirect, render_template, jsonify
import spotipy
from werkzeug.exceptions import abort
import git
import hmac
import hashlib
import json

from recommendation_engine import playlist
from recommendation_engine.mood_track_finder import MoodTrackFinder
from search.autocomplete import search_tracks
from utils.validators import validate_new_playlist_request

# Top level entry point for wave-guide flask application

# App setup =================================
# ===========================================


def create_app():
    app = Flask(__name__)
    cache_handler = spotipy.cache_handler.FlaskSessionCacheHandler(session)
    scopes = ["user-read-private",
              "user-read-email",
              "playlist-modify-public",
              "playlist-modify-private",
              "playlist-read-private",
              "playlist-read-collaborative",
              "playlist-modify-public",
              ]

    # .env file loaded in wsgi.py
    # NOTE: THIS IS CASE SENSITIVE

    # THE USER MUST INPUT THEIR EMAIL THE SAME AS IT LOOKS ON SPOTIFY DEVELOPER DASHBOARD
    redirect_uri = os.getenv('SPOTIPY_REDIRECT_URI')
    app.logger.debug(f"Using redirect URI: {redirect_uri}")
    auth_manager = spotipy.oauth2.SpotifyOAuth(
        cache_handler=cache_handler,
        client_id=os.getenv('SPOTIPY_CLIENT_ID'),
        client_secret=os.getenv('SPOTIPY_CLIENT_SECRET'),
        redirect_uri=redirect_uri,
        scope=scopes,
        open_browser=False,
    )
    spotify = spotipy.Spotify(auth_manager=auth_manager, requests_timeout=45, retries=0)
    app.cache_handler = cache_handler
    app.auth_manager = auth_manager
    app.spotify = spotify
    app.config["SECRET_KEY"] = os.urandom(64)
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["SESSION_FILE_DIR"] = "./.flask_session/"

    # setup logging
    app.logger.setLevel(logging.DEBUG)
    app.logger.info("created app")
    return app


app = create_app()


# App logic =================================
# ===========================================


def validate_token():
    token = app.cache_handler.get_cached_token()
    if not token:
        app.logger.debug("No token found")
        return False

    if not app.auth_manager.validate_token(token):
        app.logger.debug("Token validation failed")
        return False

    app.logger.debug(f"Token scopes: {token.get('scope', 'no scopes')}")
    return True

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not validate_token():
            return jsonify({"message": "User not logged in"}), 403
        return f(*args, **kwargs)
    return decorated_function

@app.route("/")
def index():
    app.logger.debug("Entering index route")
    if request.args.get("code"):
        app.logger.debug(f"Received authorization code: {request.args.get('code')}")
        try:
            token_info = app.auth_manager.get_access_token(request.args.get("code"))
            app.logger.debug(f"Successfully obtained access token: {token_info}")
            return redirect("/")
        except Exception as e:
            app.logger.error(f"Error getting access token: {str(e)}")
            app.logger.debug(f"Request URL: {request.url}")
            app.logger.debug(f"Request args: {request.args}")
            return f"Error during authentication: {str(e)}. Please try again. If the issue persists, check that the redirect URI in your Spotify Developer Dashboard exactly matches: {redirect_uri}"

    if not validate_token():
        app.logger.debug("No valid token, generating auth URL")
        try:
            auth_url = app.auth_manager.get_authorize_url()
            app.logger.debug(f"Generated auth URL: {auth_url}")
            return render_template("login.html", auth_url=auth_url)
        except Exception as e:
            app.logger.error(f"Error generating auth URL: {str(e)}")
            return f"Error initializing authentication: {str(e)}. Please try again. If the issue persists, check that the redirect URI in your Spotify Developer Dashboard exactly matches: {redirect_uri}"

    # Step 3. Signed in, display data
    app.spotify = spotipy.Spotify(auth_manager=app.auth_manager)
    user_name = session.get('user_name')

    if not user_name:
        app.logger.debug("calling spotify.me()")
        try:
            user_name = app.spotify.me()["display_name"]
        except spotipy.exceptions.SpotifyException as e:
            if e.http_status == 403:
                app.logger.info("User not in beta access group")
                return render_template("beta_access_needed.html")
            # Re-raise any other Spotify exceptions
            raise

        session['user_name'] = user_name
        app.logger.info(f"user {user_name} logged in")

    return render_template("index.html", user_name=user_name)


@app.route("/callback", methods=["GET"])
def callback():
    app.logger.debug("Handling Spotify callback")
    app.logger.debug(f"Request URL: {request.url}")
    app.logger.debug(f"Request args: {request.args}")
    if request.args.get("error"):
        error = request.args.get("error")
        app.logger.error(f"Spotify authorization error: {error}")
        return f"Authorization error: {error}. Please try again."

    if not request.args.get("code"):
        app.logger.error("No authorization code received from Spotify")
        return "No authorization code received. Please try again."

    try:
        code = request.args.get("code")
        app.logger.debug(f"Received authorization code: {code}")
        token_info = app.auth_manager.get_access_token(code)
        app.logger.debug("Successfully obtained access token")
        return redirect("/")
    except Exception as e:
        app.logger.error(f"Error handling callback: {str(e)}")
        return f"Error during callback handling: {str(e)}. Please try again."

@app.route("/log_out")
def log_out():
    session.pop("token_info", None)
    return redirect("/")



# Pure API endpoints that do not return HTML
# ===========================================

# TODO: rename to /search or maybe /track_search, /tracks/search
@app.route("/autocomplete", methods=["POST"])
@login_required
def autocomplete():
    if not request.json or "query" not in request.json:
        return jsonify({"message": "Include a query parameter"}), 400
    query = request.json["query"]
    limit = 4
    suggestions = search_tracks(app.spotify, query, limit)
    if not suggestions:
        return jsonify({"message": "No suggestions found"}), 404
    return jsonify(suggestions)


@app.route("/new_playlist/", methods=["POST"])
@login_required
def new_playlist():
    validate_new_playlist_request(request.json)
    try:
        resp = playlist.create_playlist(request, app.spotify, session)
    except spotipy.exceptions.SpotifyException as e:
        app.logger.error(f"Spotify API error: {str(e)}")
        return jsonify({"error": str(e)}), 500
    return jsonify(resp)

# utility to update pythonanywhere code with latest main branch ===
# =================================================================
# https://medium.com/@aadibajpai/deploying-to-pythonanywhere-via-github-6f967956e664
def is_valid_signature(x_hub_signature, data, private_key):
    hash_algorithm, github_signature = x_hub_signature.split('=', 1)
    algorithm = hashlib.__dict__.get(hash_algorithm)
    encoded_key = bytes(private_key, 'latin-1')
    mac = hmac.new(encoded_key, msg=data, digestmod=algorithm)
    return hmac.compare_digest(mac.hexdigest(), github_signature)

@app.route('/update_server', methods=['POST'])
def webhook():
    if request.method != 'POST':
        return 'OK'
    else:
        abort_code = 418
        # Do initial validations on required headers
        if 'X-Github-Event' not in request.headers:
            abort(abort_code)
        if 'X-Github-Delivery' not in request.headers:
            abort(abort_code)
        if 'X-Hub-Signature' not in request.headers:
            abort(abort_code)
        if not request.is_json:
            abort(abort_code)
        if 'User-Agent' not in request.headers:
            abort(abort_code)
        ua = request.headers.get('User-Agent')
        if not ua.startswith('GitHub-Hookshot/'):
            abort(abort_code)

        event = request.headers.get('X-GitHub-Event')
        if event == "ping":
            return json.dumps({'msg': 'Hi!'})

        x_hub_signature = request.headers.get('X-Hub-Signature')
        w_secret = os.getenv('PYTHONANYWHERE_DEPLOYMENT_SECRET')
        if not is_valid_signature(x_hub_signature, request.data, w_secret):
            print('Deploy signature failed: {sig}'.format(sig=x_hub_signature))
            abort(abort_code)

        payload = request.get_json()
        if payload is None:
            print('Deploy payload is empty: {payload}'.format(
                payload=payload))
            abort(abort_code)

        if payload['action'] != "closed":
            return json.dumps({'msg': "Wrong event type"})
            abort(abort_code)

        repo = git.Repo('/home/waveguide/wave_guide')
        origin = repo.remotes.origin

        pull_info = origin.pull(refspec='main', progress=None)

        if len(pull_info) == 0:
            return json.dumps({'msg': "Didn't pull any information from remote!"})
        if pull_info[0].flags > 128:
            return json.dumps({'msg': "Didn't pull any information from remote!"})

        commit_hash = pull_info[0].commit.hexsha
        build_commit = f'build_commit = "{commit_hash}"'
        print(f'{build_commit}')
        return 'Updated PythonAnywhere server to commit {commit}'.format(commit=commit_hash)

# Test utility to experiment with feature paramaters =================================
# ====================================================================================
@app.route("/tracks", methods=["GET"])
@login_required
def get_tracks():
    mood = request.args.get('mood')
    if not mood:
        abort(400, "Include a mood query paramater. Example: /tracks?mood=calm")
    track_finder = MoodTrackFinder(app.spotify, mood, 3)
    recs = track_finder.find()
    wg_resp = {}
    track_ids = []
    for track in recs:
        simplified_track = {
            "name": track["name"],
            "artist": track["artists"][0]["name"],
            "url": track["external_urls"]["spotify"]
        }
        wg_resp[track["id"]] = simplified_track
        track_ids.append(track["id"])
    print("getting track features")
    track_features = app.spotify.audio_features(track_ids)
    print("got features")
    for features in track_features:
        wg_resp[features["id"]]["features"] = {
            "acousticness": features["acousticness"],
            "danceability": features["danceability"],
            "energy": features["energy"],
            "instrumentalness": features["instrumentalness"],
            "valence": features["valence"],
            "key": features["key"],
            "liveness": features["liveness"],
            "loudness": features["loudness"],
            "mode": features["mode"],
            "speechiness": features["speechiness"],
            "tempo": features["tempo"],
        }

    return jsonify(wg_resp)


# @app.route("/tracks", methods=["GET"])
# @login_required
# def get_tracks():
#     mood = request.args.get('mood')
#     if not mood:
#         abort(400, "Include a mood query parameter. Example: /tracks?mood=calm")
#     track_finder = MoodTrackFinder(app.spotify, mood, 3)
#     recs = track_finder.find()

#     # === UPDATED: use metadata_spotify for audio features ===
#     track_ids = [t['id'] for t in recs]
#     features = app.metadata_spotify.audio_features(track_ids)

#     wg_resp = {}
#     for track, feats in zip(recs, features):
#         wg_resp[track['id']] = {
#             "name": track["name"],
#             "artist": track["artists"][0]["name"],
#             "url": track["external_urls"]["spotify"],
#             "features": feats or {}
#         }
#     return jsonify(wg_resp)
