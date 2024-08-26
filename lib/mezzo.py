#-*- coding: utf-8 -*-

import os
import glob
import json
import time
import shutil
import mutagen
import requests
import hashlib
from mutagen.easyid3 import EasyID3
from uuid import uuid4
from base64 import b64encode
from lib.data import config

def escape(string):
    if string is None:
        return ""
    return string.replace("'", "''")

class Scanner:
    def __init__(self, app_path):
        # Set variables
        self.app_path = app_path
        self.library = {
            "artists":{},
            "albums":{},
            "songs":{}
        }

        self.deleted_paths = []

        self.audio_extensions = [".mp3", ".flac", ".ogg", ".wav"]
        self.image_extensions = [".jpg", ".jpeg", ".png"]
        self.library_path = os.path.expanduser(config["library_path"])

        # Spotify
        self.last_request = 0
        self.spotify_expires = 0
        self.spotify_access_token = None

    def get_library_state(self):
        files = glob.glob(self.library_path + "/**/*", recursive=True)
        string = "".join(files)
        hash = hashlib.md5(string.encode()).hexdigest()
        return hash, files

    def save_library_state(self, hash, files):
        with open(os.path.join(self.app_path, "library.json"), "w", encoding="utf-8") as f:
            json.dump({"hash": hash, "files": files}, f, ensure_ascii=False)

    def load_library_state(self):
        with open(os.path.join(self.app_path, "library.json"), "r", encoding="utf-8") as f:
            data = json.load(f)
            return data["hash"], data["files"]

    def get_spotify_access_token(self):
        auth = b64encode(f"{config['spotify_client_id']}:{config['spotify_client_secret']}".encode()).decode()
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
        print(f"Checking cover for: {name}...")
        url = "https://api.spotify.com/v1/search"
        with requests.get(url, params = {"q": name, "type": "artist", "limit": 1}, headers = {"Authorization": f"Bearer {self.spotify_access_token}"}) as r:
            if r.status_code != 200:
                print("Error:", r.status_code, r.text)
                return None
            # Parse data
            data = r.json()
            image_url = data["artists"]["items"][0]["images"][0]["url"]

        # Check if image is already downloaded
        spotify_id = image_url.split("/")[-1]
        if not os.path.exists(os.path.join(self.app_path, "covers", spotify_id)):
            # Download image to covers directory
            cover_path = os.path.join(self.app_path, "covers", spotify_id)
            with requests.get(image_url) as r:
                with open(cover_path, "wb") as f:
                    f.write(r.content)

        return spotify_id

    def get_tags(self, path):
        # Check extension
        if os.path.splitext(path)[1].lower() == ".mp3":
            return EasyID3(path)
        return mutagen.File(path)

    async def remove_deleted_files(self, db):
        if not len(self.deleted_paths):
            return

        print(f"Removing {len(self.deleted_paths)} deleted files from database...")
        await db.execute("DELETE FROM artists WHERE path IN (" + ",".join(["?" for _ in self.deleted_paths]) + ");", self.deleted_paths)
        await db.execute(f"DELETE FROM albums WHERE path IN (" + ",".join(["?" for _ in self.deleted_paths]) + ");", self.deleted_paths)
        await db.execute(f"DELETE FROM songs WHERE path IN (" + ",".join(["?" for _ in self.deleted_paths]) + ");", self.deleted_paths)
        await db.commit()

    async def insert_added_files(self, db):
        if not any([len(self.library["artists"]), len(self.library["albums"]), len(self.library["songs"])]):
            return

        await db.executemany(*self.get_artists())
        await db.executemany(*self.get_albums())
        await db.executemany(*self.get_songs())
        await db.commit()

    def get_artists(self):
        # Get artists
        # Example: (id, name, path, cover)
        artists = list(map(lambda x: (x[0], x[1]["name"], x[1]["path"], x[1]["cover"]), self.library["artists"].items()))
        return "INSERT INTO artists(id, name, path, cover) VALUES (?, ?, ?, ?)", artists

    def get_albums(self):
        # Get albums
        # Example: (id, name, path, cover, artist)
        albums = list(map(lambda x: (x[0], x[1]["name"], x[1]["path"], x[1]["cover"], x[1]["artist"]), self.library["albums"].items()))
        return "INSERT INTO albums(id, name, path, cover, artist) VALUES (?, ?, ?, ?, ?)", albums

    def get_songs(self):
        # Get songs
        # Example: (id, name, path, artist, album, discnumber, tracknumber)
        songs = list(map(lambda x: (x[0], x[1]["name"], x[1]["path"], x[1]["artist"], x[1]["album"], x[1]["discnumber"], x[1]["tracknumber"]), self.library["songs"].items()))
        return "INSERT INTO songs(id, name, path, artist, album, discnumber, tracknumber) VALUES (?, ?, ?, ?, ?, ?, ?)", songs

    def add_cover(self, album_id, path):
        # Copy cover to covers directory as album_id.extension
        cover_path = os.path.join(self.app_path, "covers", album_id)
        shutil.copyfile(path, cover_path)

        # Add cover to library
        self.library["albums"][album_id]["cover"] = cover_path

    def scan(self):
        # Directory structure: {artist}/{album}/{song}
        # Example: /home/user/Music/Airbag/All Rights Removed/06 - Homesick.flac

        print(f"Scanning {self.library_path}...")
        starttime = time.time()

        # Iterate over artists
        for artist in os.listdir(self.library_path):
            artist_path = os.path.join(self.library_path, artist)

            # Add artist
            artist_id = str(uuid4())
            self.library["artists"][artist_id] = {
                "name": artist,
                "path": artist_path,
                "cover": self.get_artist_cover_from_spotify(artist)
            }

            # Iterate over albums
            for album in os.listdir(artist_path):
                album_path = os.path.join(artist_path, album)

                # Add album
                album_id = str(uuid4())
                self.library["albums"][album_id] = {
                    "name": album,
                    "path": album_path,
                    "cover": None,
                    "artist": artist_id,
                }

                # Iterate over items
                for item in os.listdir(album_path):
                    item_path = os.path.join(album_path, item)

                    # Scan for songs in CD (CD1, CD 2, etc.)
                    if os.path.isdir(item_path):
                        for file in os.listdir(item_path):
                            file_path = os.path.join(item_path, file)
                            self.scan_song(file_path, artist_id, album_id)
                        continue

                    # Scan for songs
                    self.scan_song(item_path, artist_id, album_id)

        endtime = time.time()
        print(f"Scanned {len(self.library['songs'])} songs in {endtime - starttime :.2f} seconds")

    def scan_song(self, file, artist_id, album_id):
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

    async def find_artist_id(self, db, path, artist_id=None):
        if artist_id:
            return artist_id

        try:
            cursor = await db.execute("SELECT id FROM artists WHERE path = ?;", [path])
            artist = await cursor.fetchone()
            return artist[0]
        except Exception as e:
            raise Exception(f"Error finding artist id: {path}")

    async def find_album_id(self, db, path, album_id=None):
        if album_id:
            return album_id

        cursor = await db.execute(f"SELECT id FROM albums WHERE path = ?;", [path])
        album = await cursor.fetchone()
        return album[0]

    # Add artist to library
    def add_artist_to_library(self, artist, path) -> str:
        # Add artist
        artist_id = str(uuid4())
        self.library["artists"][artist_id] = {
            "name": artist,
            "path": path,
            "cover": self.get_artist_cover_from_spotify(artist)
        }
        return artist_id

    def add_album_to_library(self, album, path, artist_id) -> str:
        # Add album
        album_id = str(uuid4())
        self.library["albums"][album_id] = {
            "name": album,
            "path": path,
            "cover": None,
            "artist": artist_id,
        }
        return album_id

    async def scan_for_changes(self, db):
        starttime = time.time()

        # Load library state
        hash, files = self.load_library_state()

        # Get new library state
        new_hash, new_files = self.get_library_state()

        if hash == new_hash:
            endtime = time.time()
            # print(f"No changes detected. Took {endtime - starttime :.2f} seconds.")
            return

        # Find deleted files
        self.deleted_paths = [f for f in files if f not in new_files]

        # Add new files
        for artist in os.listdir(self.library_path):
            artist_id = None
            artist_path = os.path.join(self.library_path, artist)
            if artist_path not in files:
                artist_id = self.add_artist_to_library(artist, artist_path)

            # Iterate over albums
            for album in os.listdir(artist_path):
                album_id = None
                album_path = os.path.join(artist_path, album)
                if album_path not in files:
                    artist_id = await self.find_artist_id(db, artist_path, artist_id)
                    album_id = self.add_album_to_library(album, album_path, artist_id)

                # Get artist_id and album_id
                artist_id = await self.find_artist_id(db, artist_path, artist_id)
                album_id = await self.find_album_id(db, album_path, album_id)

                # Iterate over items
                for item in os.listdir(album_path):
                    item_path = os.path.join(album_path, item)

                    # item is a directory
                    if os.path.isdir(item_path):
                        for file in os.listdir(item_path):
                            # Check if file is in files
                            file_path = os.path.join(item_path, file)
                            if file_path not in files:
                                self.scan_song(file_path, artist_id, album_id)
                        continue

                    # item is a file
                    if item_path not in files:
                        self.scan_song(item_path, artist_id, album_id)

        # done
        endtime = time.time()
        print(f"Found {len(self.library['songs'])} new songs in {endtime - starttime :.2f} seconds")
