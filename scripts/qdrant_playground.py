from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams,PointStruct, Filter, FieldCondition, MatchValue, PayloadSchemaType
from tqdm import tqdm
from dotenv import load_dotenv
import os
import pprint
from get_acoustic_brainz_data_all import load_tracks_from_cache


def init_qdrant_client():
    load_dotenv()
    return QdrantClient(
        os.getenv("QDRANT_CLUSTER_NAME"),
        api_key=os.getenv("QDRANT_API_KEY"),
    )

# collection creation
def ensure_collection(client, name, vector_size):
    existing_collections = [col.name for col in client.get_collections().collections]
    if name not in existing_collections:
        print(f"Creating collection: {name}")
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

# vectors and payloads preparation
def prepare_points(track_dicts):
    vector_keys = [k for k in track_dicts[0].keys() if k not in {
        'musicbrainz_recordingid', 'title', 'artist', 'album', 'releasecountry'
    }]
    points = []
    for track in track_dicts:
        vector = [track[key] for key in vector_keys]
        payload = {
            "title": track['title'],
            "artist": track['artist'],
            "album": track['album'],
            "musicbrainz_recordingid": track['musicbrainz_recordingid'],
            "releasecountry": track['releasecountry']
        }
        points.append(PointStruct(
            id=track['musicbrainz_recordingid'],
            vector=vector,
            payload=payload
        ))
    return points, len(vector_keys)

# Batch Upload to Qdrant
def upload_batches(client, collection_name, points, batch_size=5000):
    for i in tqdm(range(0, len(points), batch_size), desc="Upserting tracks", unit="batch"):
        batch = points[i:i + batch_size]
        response = client.upsert(collection_name=collection_name, points=batch)
        print(f"Upserted points {i} to {i + len(batch)}")
        print(f"qdrant_response: {response}")
    print("All tracks loaded into Qdrant!")


def main():
    client = init_qdrant_client()
    tracks = load_tracks_from_cache("../cache/acousticbrainz_all.pkl")
    points, vector_size = prepare_points(tracks)
    ensure_collection(client, "tracks", vector_size)
    upload_batches(client, "tracks", points)

if __name__ == "__main__":
    main()
