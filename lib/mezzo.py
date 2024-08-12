#-*- coding: utf-8 -*-

import os
import json
import time
import mutagen
from uuid import uuid4

class Scanner:
    def __init__(self):
        self.library = {
            "artists":set(),
            "albums":set(),
            "songs":set()
        }
        self.extensions = [".mp3", ".flac", ".ogg", ".wav"]

    def save(self):
        with open("library.json", "w", encoding="utf-8") as f:
            json.dump(self.library, f, indent=4, default=tuple, ensure_ascii=False)

    def add_song(self, path, tags):
        # Get tags
        title = tags["title"][0]
        album = tags["album"][0]
        artist = tags["artist"][0]

        # Add artist
        # (name)
        self.library["artists"].add(artist)

        # Check if album exists
        # (title, artist)
        self.library["albums"].add((album, artist))

        # Add song to library
        # (title, artist, album, path)
        self.library["songs"].add((title, artist, album, path))

    def scan(self, path):
        library_path = os.path.expanduser(path)
        starttime = time.time()
        for root, dirs, files in os.walk(library_path):
            for file in files:
                # Check if file is a music file
                if os.path.splitext(file)[1] not in self.extensions:
                    continue
                path = os.path.join(root, file)
                try:
                    self.add_song(path, mutagen.File(path).tags)
                except Exception as e:
                    # print(f"Cant read tags for {path}: {e}")
                    continue
        endtime = time.time()
        print(f"Scanned {len(self.library['songs'])} songs in {endtime - starttime :.2f} seconds")
        # self.save()
        return self.library
