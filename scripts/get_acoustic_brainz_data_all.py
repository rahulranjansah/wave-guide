from pathlib import Path
import pprint
import json
import pickle
import os
from tqdm import tqdm

def ingest_json(root_dir: str):
    """
    Recursively load every .json under root_dir,
    Returns a list of flattened track dicts.
    """
    root = Path(root_dir)
    # 1) build the full list of files
    all_json = list(root.rglob("*.json"))
    tracks = []

    # 2) iterate with tqdm for a nice progress bar
    for json_path in tqdm(all_json, desc="Reading JSON files", unit="file"):
        try:
            data = json.loads(json_path.read_text())
        except Exception as e:
            tqdm.write(f"Skipping {json_path.name}: {e}")
            continue

        # if the top‐level is None or not even a dict, skip it
        if not isinstance(data, dict):
            tqdm.write(f"Skipping {json_path.name}: top-level is {data!r}")
            continue

        metadata = data.get('metadata') or {}
        tags     = metadata.get('tags')   or {}
        high     = data.get('highlevel')  or {}

        # if tags is empty, skip entirely
        if not tags:
            tqdm.write(f"Skipping {json_path.name}: no tags")
            continue

        # base track info
        track = {
            'musicbrainz_recordingid': tags.get('musicbrainz_recordingid', [""])[0],
            'title': tags.get('title', [""])[0],
            'artist': tags.get('artist', [""])[0],
            'album': tags.get('album', [""])[0],
            'releasecountry': tags.get('releasecountry', [""])[0]
        }

        # flatten every highlevel feature
        for feat_name, feat_block in high.items():
            flat = feat_block.get('all', {})
            for subname, val in flat.items():
                key = f"{feat_name}_{subname}"
                track[key] = float(val)

            # wanna store label & prob?
            # if 'value' in feat_block and 'probability' in feat_block:
            #     track[f"{feat_name}_value"] = feat_block['value']
            #     track[f"{feat_name}_prob"] = float(feat_block['probability'])

        tracks.append(track)

    return tracks

# cache file, load_tracks unchanged
CACHE_FILE = "../cache/acousticbrainz_all.pkl"

def load_tracks_from_cache(path):
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "rb") as f:
            return pickle.load(f)

    tracks = ingest_json(path)
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(tracks, f, protocol=pickle.HIGHEST_PROTOCOL)
    return tracks

if __name__ == "__main__":
    all_tracks = load_tracks_from_cache(
        "../acousticbrainz-highlevel-sample-json-20220623/highlevel/"
    )
    print(f"Loaded {len(all_tracks)} tracks")
    # pprint.pprint(all_tracks[0])
