from dataclasses import dataclass
import spotipy
from typing import Dict, Any, Optional, List
import pprint

COUNTRY = "US"  # TODO: get this from user metadata


@dataclass
class BookendSeedsTrackFinder:
    """Core recommendaiton function of app.
    Takes in starting and ending parameters
    then creates a list of tracks"""

    sp: spotipy.Spotify
    seed_track: Dict[str, Any]  # Spotify Get Track response
    destination_track: Dict[str, Any]  # Spotify Get Track response

    # num_tracks: int hard coded to 5 to simplify seed track logic for now

    # target_min_multiplier definesv how much we will allow the min features to dip below the target
    # for each call to the recommend endpoint
    # 1 sets the target as min,
    # 0 or missing feature key will not set a minimum
    target_min_multiplier: Optional[Dict[str, float]] = None
    # target_max_multiplier defines how much we will allow the max features to go above the target
    # for each call to the recommend endpoint
    # 1 sets the target as max,
    # 0 or missing feature key will not set a maximum
    # 2, for example, would set double the target as the max
    target_max_multiplier: Optional[Dict[str, float]] = None

    def __init__(
        self,
        sp: spotipy.Spotify,
        seed_track: Dict[str, Any],
        destination_track: Dict[str, Any],
        # TODO: maybe abstract this inside of the actual
        # class since this one is not used by other recommenders
        target_min_multiplier: Optional[Dict[str, float]] = None,
        target_max_multipler: Optional[Dict[str, float]] = None,
    ):
        self.sp = sp
        self.seed_track = seed_track
        self.destination_track = destination_track
        self.target_min_multiplier = target_min_multiplier
        self.target_max_multipler = target_max_multipler
        self.num_tracks = 5

        # TODO: remove API call from __init__??
        bookendFeatures = self.sp.audio_features([self.seed_track["id"], self.destination_track["id"]])

        # slim down to currently supported features of energy, danceability, and valence
        source_features = bookendFeatures[0]
        self.source_features = {}
        self.source_features["energy"] = source_features["energy"]
        self.source_features["danceability"] = source_features["danceability"]
        self.source_features["valence"] = source_features["valence"]

        destination_features = bookendFeatures[1]
        self.destination_features = {}
        self.destination_features["energy"] = destination_features["energy"]
        self.destination_features["danceability"] = destination_features["danceability"]
        self.destination_features["valence"] = destination_features["valence"]

    # TODO: break into helper functions for readability
    def recommend(self):
        pp = pprint.PrettyPrinter(indent=4, width=120)
        # tracks that will be returned from the function
        # [seed, r0, r1, r2, r3, r4, destination]
        playlist_tracks = [self.seed_track, None, None, None, None, None, self.destination_track]
        # keep track of names of songs to prevent a playlist full of remakes
        track_names = [self.seed_track["name"].lower(), self.destination_track["name"].lower()]
        # TODO: handle multiple artists for more diveserity?
        # keep track of artists to prevent duplicates for more diversity
        artist_ids = [self.seed_track["artists"][0]["id"], self.destination_track["artists"][0]["id"]]
        # TODO: experiment with adding/not adding more seed tracks as you go

        source_features = self.source_features
        destination_features = self.destination_features

        # list of kwargs for each slot in the playlist
        iterations_recommendation_kwargs = []

        step_size = self.num_tracks
        for i in range(self.num_tracks):
            recommendation_kwargs = {}
            for feature in source_features:
                target_key = f"target_{feature}"
                target = source_features[feature] + (
                    (destination_features[feature] - source_features[feature]) / step_size
                )
                source_features[feature] = target
                recommendation_kwargs[target_key] = target

                if self.target_min_multiplier is not None:
                    min_key = f"min_{feature}"
                    min_feature = target * self.target_min_multiplier.get(feature, 0)
                    recommendation_kwargs[min_key] = min_feature

                if self.target_max_multiplier is not None and self.target_max_multiplier.get(feature, 0) != 0:
                    max_key = f"max_{feature}"
                    max_feature = target * self.target_max_multiplier
                    recommendation_kwargs[max_key] = max_feature

                iterations_recommendation_kwargs.append(recommendation_kwargs)

        recommendation_pool_size = 4

        # getting recommendations that utilize bookended seeds
        # r0
        recommendation_kwargs = iterations_recommendation_kwargs[0]
        seed_tracks = [self.seed_track["id"]]
        recs = self.sp.recommendations(
            limit=recommendation_pool_size, seed_tracks=seed_tracks, country=COUNTRY, **recommendation_kwargs,
        )
        next_track = self.skip_duplicate_titles_and_artists(recs, track_names, artist_ids)
        track_names.append(next_track["name"].lower())
        artist_ids.append(next_track["artists"][0]["id"])
        playlist_tracks[1] = next_track

        # r2
        recommendation_kwargs = iterations_recommendation_kwargs[2]
        seed_tracks = [self.seed_track["id"], self.destination_track["id"]]
        recs = self.sp.recommendations(
            limit=recommendation_pool_size, seed_tracks=seed_tracks, country=COUNTRY, **recommendation_kwargs,
        )
        next_track = self.skip_duplicate_titles_and_artists(recs, track_names, artist_ids)
        track_names.append(next_track["name"].lower())
        artist_ids.append(next_track["artists"][0]["id"])
        playlist_tracks[3] = next_track

        # r4
        recommendation_kwargs = iterations_recommendation_kwargs[4]
        seed_tracks = [self.destination_track["id"]]
        recs = self.sp.recommendations(
            limit=recommendation_pool_size, seed_tracks=seed_tracks, country=COUNTRY, **recommendation_kwargs,
        )
        next_track = self.skip_duplicate_titles_and_artists(recs, track_names, artist_ids)
        track_names.append(next_track["name"].lower())
        artist_ids.append(next_track["artists"][0]["id"])
        playlist_tracks[5] = next_track

        # getting recommendations that use recommended tracks as seeds
        # hoping this will blend continuity and diversity
        # r1
        recommendation_kwargs = iterations_recommendation_kwargs[1]
        seed_tracks = [playlist_tracks[1]["id"], playlist_tracks[3]["id"]]
        recs = self.sp.recommendations(
            limit=recommendation_pool_size, seed_tracks=seed_tracks, country=COUNTRY, **recommendation_kwargs,
        )
        next_track = self.skip_duplicate_titles_and_artists(recs, track_names, artist_ids)
        track_names.append(next_track["name"].lower())
        artist_ids.append(next_track["artists"][0]["id"])
        playlist_tracks[2] = next_track

        # r3
        recommendation_kwargs = iterations_recommendation_kwargs[3]
        seed_tracks = [playlist_tracks[5]["id"], playlist_tracks[3]["id"]]
        recs = self.sp.recommendations(
            limit=recommendation_pool_size, seed_tracks=seed_tracks, country=COUNTRY, **recommendation_kwargs,
        )
        next_track = self.skip_duplicate_titles_and_artists(recs, track_names, artist_ids)
        track_names.append(next_track["name"].lower())
        artist_ids.append(next_track["artists"][0]["id"])
        playlist_tracks[4] = next_track

        return playlist_tracks

    @staticmethod
    # if there are only duplicates available in the recommendation pool,
    # return the first track
    # track_names should be all lowercase
    def skip_duplicate_titles_and_artists(recs: Dict[str, Any], track_names: List[str], artist_ids: List[str]):
        track_name_set = {track.lower() for track in track_names}
        artist_id_set = {artist_id for artist_id in artist_ids}
        for recommended_track in recs["tracks"]:
            recommended_track_name = recommended_track["name"].lower()
            recommended_track_artist_id = recommended_track["artists"][0]["id"]
            if recommended_track_name in track_name_set or recommended_track_artist_id in artist_id_set:
                continue
            return recommended_track
        return recs["tracks"][0]
