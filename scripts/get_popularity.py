
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os
from dotenv import load_dotenv

# --- Configuration ---

# script directory and loads the .env file one level up
script_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(os.path.dirname(script_dir), '.env')
load_dotenv(dotenv_path=dotenv_path)

CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")

songs_to_check = [
    "Blinding Lights The Weeknd",
    "As It Was Harry Styles",
    "Jaago by Lifafa",
    "Hosh waalon Jagjit",
    "bad guy Billie Eilish",
    "a non-existent song 12345" # Example of a song not found
]

def get_popularity_scores():
    """
    Authenticates with the Spotify API and fetches popularity scores for songs and artists.
    """

    # Set up authentication
    client_credentials_manager = SpotifyClientCredentials(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET
    )
    sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

    print("--- Spotify Popularity Checker ---")

    for query in songs_to_check:
        print(f"\nSearching for: '{query}'")

        # Search for the track
        # The 'limit=1' parameter gets the most likely result.
        results = sp.search(q=query, type='track', limit=1)
        tracks = results['tracks']['items']

        if not tracks:
            print("Song not found on Spotify.")
            continue

        # --- Track Information ---
        track = tracks[0]
        track_name = track['name']
        track_popularity = track['popularity']

        # Artists can be multiple, so we'll collect their names
        artist_names = [artist['name'] for artist in track['artists']]

        print(f"Song: '{track_name}' by {', '.join(artist_names)}")
        print(f"Song Popularity: {track_popularity}/100")

        # --- Artist Information ---
        # We'll get the popularity of the primary artist on the track
        primary_artist_id = track['artists'][0]['id']
        artist_info = sp.artist(primary_artist_id)
        artist_name = artist_info['name']
        artist_popularity = artist_info['popularity']

        print(f" Main Artist ('{artist_name}') Popularity: {artist_popularity}/100")



if __name__ == '__main__':
        get_popularity_scores()