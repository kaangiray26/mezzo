#!env/bin/python3
# -*- coding: utf-8 -*-

import duckdb
from queue import Queue, Empty
from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify
import functools
from threading import Thread
from lib.mezzo import Scanner
from lib.db import create_tables
from uuid import uuid4

# Flask app
app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Tasks
tasks = Queue()

# Config
config = {
    "library_path": "~/Music",
}

# Init duckdb
con = duckdb.connect("mezzo.db", config = {'threads': 1})

# Check for tables
for create_table in create_tables:
    con.execute(create_table)

def route_required(func):
    @functools.wraps(func)
    def route(*args, **kwargs):
        if "X-Requested-From" not in request.headers:
            return redirect(url_for("index", path=[request.path]))
        return func(*args, **kwargs)
    return route

@app.route("/")
def index():
    return render_template("index.html", config=config)

@app.route("/albums")
@route_required
def albums():
    # Get albums
    albums = con.sql("SELECT * FROM albums ORDER BY title;").fetchall()
    return render_template("albums.html", albums=albums)

@app.route("/album/<uuid>")
@route_required
def album(uuid):
    # Get album
    album = con.sql(f"SELECT * FROM albums WHERE id = '{uuid}';").fetchone()
    tracks = con.sql(f"SELECT * FROM songs WHERE album = '{album[1]}';").fetchall()
    return render_template("album.html", album=album, tracks=tracks)

@app.route("/artists")
@route_required
def artists():
    # Get artists
    artists = con.sql("SELECT * FROM artists ORDER BY name;").fetchall()
    return render_template("artists.html", artists=artists)

@app.route("/playlists")
@route_required
def playlists():
    return render_template("playlists.html")

@app.route("/stream/<uuid>")
def stream(uuid):
    # Get song
    song = con.sql(f"SELECT * FROM songs WHERE id = '{uuid}';").fetchone()
    return send_file(song[4])

@app.route("/stream/<uuid>/basic")
def stream_basic(uuid):
    # Get song
    song = con.sql(f"SELECT * FROM songs WHERE id = '{uuid}';").fetchone()

    # Return as JSON with column names
    columns = ["id", "title", "artist", "album", "path"]
    return dict(zip(columns, song))

def update_library():
    # Check for song count
    count = con.sql("SELECT COUNT(*) FROM songs;").fetchone()[0]
    if count > 0:
        print("Library already exists.")
        return

    # Scan library
    scanner = Scanner()
    scanner.scan(config["library_path"])

    print("Updating library...")
    con.sql(scanner.join_artists())
    con.sql(scanner.join_albums())
    con.sql(scanner.join_songs())
    print("Library updated.")

if __name__ == "__main__":
    try:
        update_library()
        app.run()
    except KeyboardInterrupt:
        print("Exiting...")
        con.close()
        exit(0)
