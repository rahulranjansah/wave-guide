from search_playground import search_qdrant_with_filter, search_qdrant_without_filter
from oauth2_musicbrainz import get_musicbrainz_session
import pprint

# could be done without manual oauth2 becasue musicbrainz api allows it

# TODO: build fallback for ISRC when not found, refer todo.txt

def fetch_isrc(mb_session, mbid):
    """Fetch ISRC(s) for a given MusicBrainz recording ID."""
    url = f"https://musicbrainz.org/ws/2/recording/{mbid}"
    params = {"inc": "isrcs", "fmt": "json"}
    resp = mb_session.get(url, params=params)
    if resp.status_code == 200:
        data = resp.json()
        return data.get("isrcs", [])
    else:
        print(f"Error for {mbid}: {resp.status_code} - {resp.text}")
        return []

def get_isrc_codes_for_search_results():
    results = search_qdrant_with_filter()
    mb = get_musicbrainz_session()

    for hit in results:
        mbid = hit.payload.get("musicbrainz_recordingid")
        title = hit.payload.get("title")
        isrcs = fetch_isrc(mb, mbid)

        print(f"Title: {title}")
        print(f"MBID: {mbid}")
        print(f"ISRC(s): {isrcs if isrcs else 'None found'}")

if __name__ == "__main__":
    get_isrc_codes_for_search_results()
