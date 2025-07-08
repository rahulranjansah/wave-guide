# Wave Guide
Wave Guide creates personalized playlists.

Guide your mood and discover new songs.

1. Choose from songs and moods for the beginning and destination of your playlist
2. Create Playlist
3. Wave Guide will find a path from the beginning to destination, helping you discover new songs that match your tastes.
4. Listen on Spotify

## Example Wave Guide Journeys

### When you can't get a song out of your head
Search for your earworm to begin the playlist.
Choose from one of the moods as your destination.

### When you need to take it down a notch
Begin with the Energized mood.
Choose the Calm mood as your destination.

### When you want to find something new
Search for a song you like to begin the playlist.
Search for a very different song, that you also like, as your destination.

# For Developers

## Running Locally
This project uses a Makefile to run locally.

`make install` will install the python depednecies including gunicorn

`make run` Will start the flask app with a gunicorn server

If you encounter the error `make: gunicorn: No such file or directory` make sure that the python binaries are availalabe in your `$PATH` environment variable.  For example `export PATH=/Library/Frameworks/Python.framework/Versions/3.7/bin:$PATH`

## Supporting Documentation

The `Notes` folder contains information gained through experiments with the spotify API

`backlog.txt` contains future plans for improvement of Wave Guide



## MusicBrainz Developer Documentation Porting Info

As we know, Spotify has locked down most of the API webpoints, so we are building our application around MusicBrainz.

`todo.txt` contains todos for the project

`requirements.txt` contains the dependencies for the project

Set the environment variables in the `.env_sample` file.

How to load the data form MusicBrainz?

```bash
curl -L -O \
  https://data.metabrainz.org/pub/musicbrainz/acousticbrainz/dumps/\
acousticbrainz-sample-json-20220623/\
acousticbrainz-highlevel-sample-json-20220623-0.tar.zst
```

How to untar the file?

```bash
tar -xvf acousticbrainz-highlevel-sample-json-20220623-0.tar.zst
```
How to process the data?

```bash
python3 scripts/acoustic_brainz_data_all.py
```
How to load the data into Qdrant?

```bash
python3 scripts/qdrant_playground.py
```
How to search the data?

```bash
python3 scripts/search_playground.py
```