"""
https://data.metabrainz.org/pub/musicbrainz/acousticbrainz/dumps/acousticbrainz-highlevel-json-20220623/
https://github.com/CDrummond/music-similarity/blob/master/lib/essentia_analysis.py
https://github.com/metabrainz/acousticbrainz-server/blob/master/db/similarity.py
https://acousticbrainz.readthedocs.io/dev/similarity.html
"""

# import zstandard
# import tarfile
# import os
from pathlib import Path
import pprint
import json
import pickle
import tarfile
import os


# Data processing step 1
# decompress and extract the tar.zst file (if required)
def decompress_and_extract(input_file_path, output_dir=None):
    """
    Decompress a .tar.zst file and extract its contents

    Args:
        input_file_path (str): Path to the .tar.zst file
        output_dir (str, optional): Directory to extract contents to. Defaults to current directory.
    """
    input_path = Path(input_file_path)

    if not input_path.exists():
        print(f"Error: File {input_file_path} not found")
        return

    # Create temporary .tar file name
    tar_path = input_path.with_suffix('')  # Remove .zst extension

    try:
        # Decompress .zst to .tar
        print(f"Decompressing {input_path.name}...")
        with open(input_path, 'rb') as input_file:
            dctx = zstandard.ZstdDecompressor()
            with open(tar_path, 'wb') as output_file:
                dctx.copy_stream(input_file, output_file)

        # Extract .tar file
        print(f"Extracting {tar_path.name}...")
        with tarfile.open(tar_path, 'r') as tar:
            tar.extractall(path=output_dir)

        print("Extraction complete!")

    except Exception as e:
        print(f"An error occurred: {str(e)}")

    finally:
        # Clean up: remove temporary .tar file
        if tar_path.exists():
            os.remove(tar_path)
            print(f"Cleaned up temporary file: {tar_path.name}")


# Data processing step 2: what features do we need?
# def ingest_json(input_dir: str):
#     input_dir = Path(input_dir)
#     tracks = []
#     for file in input_dir.iterdir():
#         with open(file, 'r') as f:
#             data = json.load(f)
#             # pprint.pprint(data)
#             track = {
#                 'musicbrainz_recordingid': data['metadata']['tags']['musicbrainz_recordingid'][0],
#                 'title': data['metadata']['tags'].get('title', [""])[0],
#                 'artist': data['metadata']['tags'].get('artist', [""])[0],
#                 'album': data['metadata']['tags'].get('album', [""])[0],
#                 # 'bpm': int(data['metadata']['tags'].get('bpm', [])[0]),

#                 'danceable': float(data['highlevel']['danceability']['all']['danceable']),
#                 'not_danceable': float(data['highlevel']['danceability']['all']['not_danceable']),

#                 'aggressive': float(data['highlevel']['mood_aggressive']['all']['aggressive']),
#                 'electronic': float(data['highlevel']['mood_electronic']['all']['electronic']),
#                 'acoustic': float(data['highlevel']['mood_acoustic']['all']['acoustic']),
#                 'happy': float(data['highlevel']['mood_happy']['all']['happy']),
#                 'party': float(data['highlevel']['mood_party']['all']['party']),
#                 'relaxed': float(data['highlevel']['mood_relaxed']['all']['relaxed']),
#                 'sad': float(data['highlevel']['mood_sad']['all']['sad']),
#                 'dark': float(data['highlevel']['timbre']['all']['dark']),
#                 'tonal': float(data['highlevel']['tonal_atonal']['all']['tonal']),
#                 'voice': float(data['highlevel']['voice_instrumental']['all']['voice']),
#                 'releasecountry': data['metadata']['tags'].get('releasecountry', [""])[0]
#             }
#             tracks.append(track)
#     return tracks


def ingest_json(input_dir: str):
    input_dir = Path(input_dir)
    tracks = []
    for file in input_dir.iterdir():
        data = json.loads(file.read_text())
        tags = data['metadata']['tags']
        high = data['highlevel']

        # start with your basic metadata
        track = {
            'musicbrainz_recordingid': tags['musicbrainz_recordingid'][0],
            'title': tags.get('title', [""])[0],
            'artist': tags.get('artist', [""])[0],
            'album': tags.get('album', [""])[0],
            'releasecountry': tags.get('releasecountry', [""])[0],
        }

        # now loop over every highlevel feature category
        for feat_name, feat_block in high.items():

            # feat_block['all'] is a dict of e.g. {'danceable': 0.75, 'not_danceable': 0.24}
            flat = feat_block.get('all', {})
            for subname, val in flat.items():

                # e.g. 'danceability' -> 'danceability_danceable'
                key = f"{feat_name}_{subname}"
                track[key] = float(val)

            # # if you also want the top‐label and probability:
            # if 'value' in feat_block and 'probability' in feat_block:
            #     track[f"{feat_name}_value"] = feat_block['value']
            #     track[f"{feat_name}_prob"] = float(feat_block['probability'])

        tracks.append(track)
    return tracks


# Data processing step 3: pikcle caching for later time speed ups

# pikcle caching for later time speed ups
CACHE_FILE = "/mnt/hardisk/summer/wave_guide/cache/dummy_acousticbrainz_data.pkl"

def load_tracks(path):
    # cached before, just load the pickle
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "rb") as f:
            return pickle.load(f)

    # .. or, parse the JSON and write cache for next time
    tracks = ingest_json(path)
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(tracks, f, protocol=pickle.HIGHEST_PROTOCOL)
    return tracks

if __name__ == "__main__":
    # note these files are really big
    # https://data.metabrainz.org/pub/musicbrainz/acousticbrainz/dumps/

    # input_file = 'acousticbrainz-highlevel-json-20220623-29.tar.zst'
    # output_dir = "."

    # decompress_and_extract(input_file, output_dir)
    tracks = load_tracks("/mnt/hardisk/summer/wave_guide/acousticbrainz-highlevel-sample-json-20220623/highlevel/00/0/")
    pprint.pprint(tracks)