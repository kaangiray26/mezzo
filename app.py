#!env/bin/python3
# -*- coding: utf-8 -*-

import os
import signal
import duckdb
from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify, send_from_directory
import functools
from lib.mezzo import Scanner
from lib.db import create_tables, default_playlists
from uuid import uuid4, UUID

# Flask app
app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app_path = os.path.expanduser("~/.var/app/org.flatpak.mezzo/data")

# Create covers directory
os.makedirs(os.path.join(app_path, "covers"), exist_ok=True)

# Init duckdb
con = duckdb.connect(os.path.join(app_path, "mezzo.db"), config = {'threads': 1})

# Check for tables
tables = con.sql("SHOW TABLES;").fetchall()
if not len(tables):
    for create_table in create_tables:
        con.execute(create_table)

# Update library
count = con.sql("SELECT COUNT(*) FROM songs;").fetchone()[0]
if count == 0:
    # Scan library
    scanner = Scanner(app_path)
    scanner.scan()

    print("Updating library...")
    con.sql(scanner.join_artists())
    con.sql(scanner.join_albums())
    con.sql(scanner.join_songs())
print("Library ready.")

def route_required(func):
    @functools.wraps(func)
    def route(*args, **kwargs):
        if "X-Requested-From" not in request.headers:
            return redirect(url_for("index", path=[request.path]))
        return func(*args, **kwargs)
    return route

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/search")
@route_required
def search():
    return render_template("search.html")

@app.route("/query")
def search_query():
    query = request.args.get("q")
    print("Searching for:", query)
    artists = con.sql(f"SELECT * FROM artists WHERE name ILIKE '%{query}%' ORDER BY name;").fetchall()
    albums = con.sql(f"SELECT albums.id, albums.name, albums.artist, albums.cover, artists.name FROM albums JOIN artists ON albums.artist = artists.id WHERE albums.name ILIKE '%{query}%' ORDER BY albums.name;").fetchall()
    songs = con.sql(f"SELECT songs.id, songs.name, songs.artist, songs.album, artists.name, albums.name FROM songs JOIN artists ON songs.artist = artists.id JOIN albums ON songs.album = albums.id WHERE songs.name ILIKE '%{query}%' ORDER BY songs.name;").fetchall()

    return render_template("results.html", results={
        "artists": artists,
        "albums": albums,
        "songs": songs
    })

@app.route("/albums")
@route_required
def albums():
    # Get albums
    albums = con.sql("SELECT albums.id, albums.name, artists.name FROM albums JOIN artists ON albums.artist = artists.id ORDER BY albums.name;").fetchall()
    return render_template("albums.html", albums=albums)

@app.route("/album/<uuid>")
@route_required
def album(uuid):
    # Get album
    album = con.sql(f"SELECT albums.id, albums.name, artists.name FROM albums JOIN artists ON albums.artist = artists.id WHERE albums.id = '{uuid}';").fetchone()
    songs = con.sql(f"SELECT * FROM songs WHERE album = '{uuid}' ORDER BY discnumber, tracknumber;").fetchall()
    return render_template("album.html", album=album, songs=songs)

@app.route("/album/<uuid>/songs")
def album_songs(uuid):
    # Get songs
    songs = con.sql(f"SELECT id FROM songs WHERE album = '{uuid}' ORDER BY discnumber, tracknumber;").fetchall()
    return {
        "songs": list(map(lambda x: x[0], songs))
    }

@app.route("/artists")
@route_required
def artists():
    # Get artists
    artists = con.sql("SELECT * FROM artists ORDER BY name;").fetchall()
    return render_template("artists.html", artists=artists)

@app.route("/artist/<uuid>")
@route_required
def artist(uuid):
    # Get artist
    artist = con.sql(f"SELECT * FROM artists WHERE id = '{uuid}';").fetchone()
    albums = con.sql(f"SELECT * FROM albums WHERE artist = '{uuid}' ORDER BY name;").fetchall()
    return render_template("artist.html", artist=artist, albums=albums)

@app.route("/artist/<uuid>/songs")
def artist_songs(uuid):
    # Get random songs
    songs = con.sql(f"SELECT id FROM songs WHERE artist = '{uuid}' ORDER BY RANDOM() LIMIT 12;").fetchall()
    return {
        "songs": list(map(lambda x: x[0], songs))
    }

@app.route("/playlists")
@route_required
def playlists():
    return render_template("playlists.html")

@app.route("/playlists/select/<uuid>")
def playlists_select(uuid):
    # Get playlists
    playlists = con.sql("SELECT id, name FROM playlists ORDER BY name;").fetchall()
    return render_template("select_playlist.html", playlists=playlists, song=uuid)

@app.route("/playlist/add/", methods=["POST"])
def playlist_add():
    # Get playlist and song from body
    data = request.json
    song_id = data["song"]
    playlist_id = data["playlist"]

    # Get songs from playlist
    playlist = con.sql(f"SELECT * FROM playlists WHERE id = '{playlist_id}';").fetchone()

    # Add song to playlist
    playlist[2].append(song_id)

    # Delete playlist
    con.sql(f"DELETE FROM playlists WHERE id = '{playlist_id}';")

    # Insert playlist
    con.execute("INSERT INTO playlists (id, name, songs) VALUES (?, ?, ?);", (playlist[0], playlist[1], playlist[2]))

    return {
        "status": "success"
    }

@app.route("/playlist/<uuid>")
def playlist(uuid):
    # Get playlist
    playlist = con.sql(f"SELECT * FROM playlists WHERE id = '{uuid}';").fetchone()

    if not len(playlist[2]):
        return render_template("playlist.html", playlist=playlist, songs=[])

    # Get songs from playlist
    st = str(tuple(map(str, playlist[2])))
    songs = con.sql("SELECT songs.id, songs.name, songs.artist, songs.album, artists.name, albums.name FROM songs JOIN artists ON songs.artist = artists.id JOIN albums ON songs.album = albums.id WHERE songs.id IN " + st + ";").fetchall()

    return render_template("playlist.html", playlist=playlist, songs=songs)

@app.route("/playlist/<uuid>/songs")
def playlist_songs(uuid):
    # Get playlist
    songs = con.sql(f"SELECT songs FROM playlists WHERE id = '{uuid}';").fetchone()

    return {
        "songs": list(map(lambda x: x, songs[0]))
    }

@app.route("/stream/<uuid>")
def stream(uuid):
    # Get song
    song = con.sql(f"SELECT * FROM songs WHERE id = '{uuid}';").fetchone()
    return send_file(song[2])

@app.route("/stream/<uuid>/basic")
def stream_basic(uuid):
    # Get song
    song = con.sql(f"SELECT songs.id, songs.name, songs.album, artists.name, albums.name FROM songs JOIN artists ON songs.artist = artists.id JOIN albums ON songs.album = albums.id WHERE songs.id = '{uuid}';").fetchone()
    # Return as JSON with column names
    columns = ["id", "name", "cover", "artist", "album"]
    return dict(zip(columns, song))

@app.route("/cover/<uuid>")
def cover(uuid):
    # Send cover
    return send_from_directory(os.path.join(app_path, "covers"), uuid);

@app.route("/queue", methods=["POST"])
def queue():
    # Get queue
    queue = request.json

    if not queue:
        return render_template("queue.html", songs=[])

    # Get songs
    # Without backslashes
    arr = ','.join(map(lambda x: repr(str(x)), queue))
    songs = con.sql(f"SELECT * FROM songs WHERE id IN ({arr})").fetchall()

    # Sort songs by queue
    songs = sorted(songs, key=lambda x: queue.index(str(x[0])))
    return render_template("queue.html", songs=songs)

@app.route("/exit", methods=["POST"])
def exit():
    # Create signal.SIGINT
    os.kill(os.getpid(), signal.SIGINT)
    return {
        "data": "Goodbye!"
    }
