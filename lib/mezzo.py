#-*- coding: utf-8 -*-

import os
import json
import time
import shutil
import mutagen
import requests
from mutagen.easyid3 import EasyID3
from uuid import uuid4
from base64 import b64encode

def escape(string):
    if string is None:
        return ""
    return string.replace("'", "''")

class Scanner:
    def __init__(self):
        # Read config
        with open("config.json", "r") as f:
            self.config = json.load(f)

        # Set variables
        self.library = {
            "artists":{},
            "albums":{},
            "songs":{}
        }
        self.audio_extensions = [".mp3", ".flac", ".ogg", ".wav"]
        self.image_extensions = [".jpg", ".jpeg", ".png"]
        self.library_path = os.path.expanduser(self.config["library_path"])

        # Spotify
        self.last_request = 0
        self.spotify_expires = 0
        self.spotify_access_token = None

    def get_spotify_access_token(self):
        auth = b64encode(f"{self.config['spotify_client_id']}:{self.config['spotify_client_secret']}".encode()).decode()
        with requests.post(
            "https://accounts.spotify.com/api/token",
            data = {
                "grant_type": "client_credentials"
            },
            headers = {
                "Authorization": f"Basic {auth}"
            }
        ) as r:
            data = r.json()
            self.spotify_access_token = data["access_token"]
            self.spotify_expires = time.time() + data["expires_in"]

    def get_artist_cover_from_spotify(self, name):
        if not self.spotify_access_token or time.time() > self.spotify_expires:
            self.get_spotify_access_token()

        # Rate limit: 10 requests per second
        if time.time() - self.last_request < 0.1:
            time.sleep(0.1)

        # Get artist cover from spotify
        url = "https://api.spotify.com/v1/search"
        with requests.get(url, params = {"q": name, "type": "artist", "limit": 1}, headers = {"Authorization": f"Bearer {self.spotify_access_token}"}) as r:
            if r.status_code != 200:
                print("Error:", r.status_code, r.text)
                return None
            # Parse data
            data = r.json()
            image_url = data["artists"]["items"][0]["images"][0]["url"]
            print("Got cover for:", name, image_url)

        # Download image to covers directory
        id = str(uuid4())
        cover_path = os.path.join("covers", id)
        with requests.get(image_url) as r:
            with open(cover_path, "wb") as f:
                f.write(r.content)

        return id

    def get_tags(self, path):
        # Check extension
        if os.path.splitext(path)[1].lower() == ".mp3":
            return EasyID3(path)
        return mutagen.File(path)

    def join_artists(self):
        # Use items
        return "INSERT INTO artists VALUES " +", ".join(map(lambda x: "('{}', '{}', '{}')".format(x[0], escape(x[1]['name']), escape(x[1]['cover'])), self.library["artists"].items()))

    def join_albums(self):
        return "INSERT INTO albums VALUES " + ", ".join(map(lambda x: "('{}', '{}', '{}', '{}')".format(x[0], escape(x[1]['name']), x[1]['artist'], escape(x[1]['cover'])), self.library["albums"].items()))

    def join_songs(self):
        return "INSERT INTO songs VALUES " + ", ".join(map(lambda x: "('{}', '{}', '{}', '{}', '{}', '{}', '{}')".format(x[0], escape(x[1]['name']), escape(x[1]['path']), x[1]['artist'], x[1]['album'], x[1]['discnumber'], x[1]['tracknumber']), self.library["songs"].items()))

    def add_cover(self, album_id, path):
        # Copy cover to covers directory as album_id.extension
        cover_path = os.path.join("covers", album_id)
        shutil.copyfile(path, cover_path)

        # Add cover to library
        self.library["albums"][album_id]["cover"] = cover_path

    def scan(self):
        # Directory structure: {artist}/{album}/{song}
        # Example: /home/user/Music/Airbag/All Rights Removed/06 - Homesick.flac

        print(f"Scanning {self.library_path}...")
        starttime = time.time()

        library = {
            "artists":[],
            "albums":[],
            "songs":[]
        }

        # Iterate over artists
        for artist in os.listdir(self.library_path):
            artist_path = os.path.join(self.library_path, artist)

            # Add artist
            artist_id = str(uuid4())
            self.library["artists"][artist_id] = {
                "name": artist,
                "cover": self.get_artist_cover_from_spotify(artist)
            }

            # Iterate over albums
            for album in os.listdir(artist_path):
                album_path = os.path.join(artist_path, album)

                # Add album
                album_id = str(uuid4())
                self.library["albums"][album_id] = {
                    "name": album,
                    "artist": artist_id,
                    "cover": None
                }

                # Iterate over items
                for item in os.listdir(album_path):
                    item_path = os.path.join(album_path, item)

                    # Check if item is a cover
                    if os.path.splitext(item)[1].lower() in self.image_extensions:
                        self.add_cover(album_id, item_path)
                        continue

                    # Scan for songs in CD (CD1, CD 2, etc.)
                    if os.path.isdir(item_path):
                        for file in os.listdir(item_path):
                            file_path = os.path.join(item_path, file)
                            self.scan_song(file_path, artist, album, artist_id, album_id)
                        continue

                    # Scan for songs
                    self.scan_song(item_path, artist, album, artist_id, album_id)

        endtime = time.time()
        print(f"Scanned {len(self.library['songs'])} songs in {endtime - starttime :.2f} seconds")

    def scan_song(self, file, artist, album, artist_id, album_id):
        # Check if item is a cover
        if os.path.splitext(file)[1].lower() in self.image_extensions:
            self.add_cover(album_id, file)
            return

        # Check if song is a music file
        if os.path.splitext(file)[1].lower() not in self.audio_extensions:
            return

        # Get tags
        tags = self.get_tags(file)

        # Add song
        song_id = str(uuid4())
        try:
            self.library["songs"][song_id] = {
                "name": tags["title"][0],
                "path": file,
                "artist": artist_id,
                "album": album_id,
                "discnumber": tags["discnumber"][0] if "discnumber" in tags else "1",
                "tracknumber": tags["tracknumber"][0]
            }
        except Exception as e:
            raise Exception(f"Error adding song {file}: {e}")

        # Update artist name
        self.library["artists"][artist_id]["name"] = tags["artist"][0]

        # Update album name
        self.library["albums"][album_id]["name"] = tags["album"][0]
