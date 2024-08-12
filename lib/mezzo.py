#-*- coding: utf-8 -*-

import os
import json
import time
import shutil
import mutagen
from mutagen.easyid3 import EasyID3
from uuid import uuid4

def escape(string):
    if string is None:
        return ""
    return string.replace("'", "''")

class Scanner:
    def __init__(self):
        self.library = {
            "artists":{},
            "albums":{},
            "songs":{}
        }

        self.old_library = {
            "artists":set(),
            "albums":set(),
            "songs":set()
        }
        self.audio_extensions = [".mp3", ".flac", ".ogg", ".wav"]
        self.image_extensions = [".jpg", ".jpeg", ".png"]

    def get_tags(self, path):
        # Check extension
        if os.path.splitext(path)[1].lower() == ".mp3":
            return EasyID3(path)
        return mutagen.File(path)

    def join_artists(self):
        # Use items
        return "INSERT INTO artists VALUES " +", ".join(map(lambda x: "('{}', '{}')".format(x[0], escape(x[1]['name'])), self.library["artists"].items()))

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

    def add_song(self, path, tags):
        print(tags)

        # Get tags
        title = tags["title"][0]
        album = tags["album"][0]
        artist = tags["artist"][0]

        # Add artist
        # (name)
        self.old_library["artists"].add(artist)

        # Check if album exists
        # (title, artist)
        self.old_library["albums"].add((album, artist))

        # Add song to library
        # (title, artist, album, path)
        self.old_library["songs"].add((title, artist, album, path))

    def save(self):
        with open("library.json", "w") as file:
            json.dump(self.old_library, file)

    def old_scan(self, path):
        print(f"Scanning {path}...")
        library_path = os.path.expanduser(path)
        starttime = time.time()
        for root, dirs, files in os.walk(library_path):
            for file in files:
                # Check if file is a music file
                if os.path.splitext(file)[1] not in self.audio_extensions:
                    continue
                path = os.path.join(root, file)
                try:
                    self.add_song(path, mutagen.File(path).tags)
                except Exception as e:
                    # print(f"Cant read tags for {path}: {e}")
                    continue
        endtime = time.time()
        print(f"Scanned {len(self.old_library['songs'])} songs in {endtime - starttime :.2f} seconds")

    def scan(self, path):
        # Directory structure: {artist}/{album}/{song}
        # Example: /home/user/Music/Airbag/All Rights Removed/06 - Homesick.flac

        print(f"Scanning {path}...")
        library_path = os.path.expanduser(path)
        starttime = time.time()

        library = {
            "artists":[],
            "albums":[],
            "songs":[]
        }

        # Iterate over artists
        for artist in os.listdir(library_path):
            # Add artist
            artist_id = str(uuid4())
            self.library["artists"][artist_id] = {
                "name": artist
            }

            # Iterate over albums
            for album in os.listdir(os.path.join(library_path, artist)):
                # Add album
                album_id = str(uuid4())
                self.library["albums"][album_id] = {
                    "name": album,
                    "artist": artist_id,
                    "cover": None
                }

                # Iterate over files in album
                for file in os.listdir(os.path.join(library_path, artist, album)):
                    # Check if file is a cover
                    if os.path.splitext(file)[1].lower() in self.image_extensions:
                        self.add_cover(album_id, os.path.join(library_path, artist, album, file))
                        continue

                    # Check if song is a music file
                    if os.path.splitext(file)[1].lower() not in self.audio_extensions:
                        continue

                    # Get tags
                    tags = self.get_tags(os.path.join(library_path, artist, album, file))

                    # Add song
                    song_id = str(uuid4())
                    try:
                        self.library["songs"][song_id] = {
                            "name": tags["title"][0],
                            "path": os.path.join(library_path, artist, album, file),
                            "artist": artist_id,
                            "album": album_id,
                            "discnumber": tags["discnumber"][0] if "discnumber" in tags else "1",
                            "tracknumber": tags["tracknumber"][0]
                        }
                    except Exception as e:
                        raise Exception(f"Error adding song {os.path.join(library_path, artist, album, file)}: {e}")

                    # Update artist name
                    self.library["artists"][artist_id]["name"] = tags["artist"][0]

                    # Update album name
                    self.library["albums"][album_id]["name"] = tags["album"][0]

        endtime = time.time()
        print(f"Scanned {len(self.library['songs'])} songs in {endtime - starttime :.2f} seconds")
