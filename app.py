#!env/bin/python3
# -*- coding: utf-8 -*-

import os
import time
import signal
import asyncio
import aiosqlite
from quart import Quart, request, render_template, redirect, url_for, send_file, jsonify, send_from_directory, g
from functools import wraps
from lib.mezzo import Scanner
from lib.db import create_tables, default_playlists
from uuid import uuid4, UUID

# Quart app
app = Quart(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app_path = os.path.expanduser("~/.var/app/org.flatpak.mezzo/data")

# Create covers directory
os.makedirs(os.path.join(app_path, "covers"), exist_ok=True)

# Watch library changes every 5 seconds
async def watch_library_changes():
    while True:
        await asyncio.sleep(5)
        db = await _get_db()

        # Scan for changes
        scanner = Scanner(app_path)
        await scanner.scan_for_changes(db)

        # Remove deleted files
        await scanner.remove_deleted_files(db)

        # Update library
        await scanner.insert_added_files(db)

        # Save library state
        hash, files = scanner.get_library_state()
        scanner.save_library_state(hash, files)

async def _connect_db():
    return await aiosqlite.connect(os.path.join(app_path, "mezzo.db"))

async def _get_db():
    if not hasattr(g, "db"):
        g.db = await _connect_db()
    return g.db

def route_required(func):
    @wraps(func)
    async def route(*args, **kwargs):
        if "X-Requested-From" not in request.headers:
            return redirect(url_for("index", path=[request.path]))
        return await func(*args, **kwargs)
    return route

@app.before_serving
async def startup():
    async with aiosqlite.connect(os.path.join(app_path, "mezzo.db")) as db:
        # Check for tables
        cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = await cursor.fetchall()

        if not len(tables):
            print("Creating tables...")
            for create_table in create_tables:
                await db.execute(create_table)
            await db.commit()

        cursor = await db.execute("SELECT COUNT(*) FROM songs;")
        count = await cursor.fetchone()

        # Check if songs table is empty
        if count[0] == 0:
            # Scan library
            scanner = Scanner(app_path)
            scanner.scan()

            # Update library
            await scanner.insert_added_files(db)

            # Save library state
            hash, files = scanner.get_library_state()
            scanner.save_library_state(hash, files)

    # Add watcher for library changes
    app.add_background_task(watch_library_changes)
    print("Library ready.")

@app.after_serving
async def shutdown():
    pass

@app.route("/")
async def index():
    return await render_template("index.html")

@app.route("/search")
@route_required
async def search():
    return await render_template("search.html")

@app.route("/query")
async def search_query():
    query = request.args.get("q")
    db = await _get_db()

    # Get artist results
    cursor = await db.execute(f"SELECT * FROM artists WHERE name LIKE '%{query}%' ORDER BY name;")
    artists = await cursor.fetchall()

    # Get album results
    cursor = await db.execute(f"SELECT albums.id, albums.name, albums.artist, albums.cover, artists.name FROM albums JOIN artists ON albums.artist = artists.id WHERE albums.name LIKE '%{query}%' ORDER BY albums.name;")
    albums = await cursor.fetchall()

    # Get song results
    cursor = await db.execute(f"SELECT songs.id, songs.name, songs.artist, songs.album, artists.name, albums.name FROM songs JOIN artists ON songs.artist = artists.id JOIN albums ON songs.album = albums.id WHERE songs.name LIKE '%{query}%' ORDER BY songs.name;")
    songs = await cursor.fetchall()

    return await render_template("results.html", results={
        "artists": artists,
        "albums": albums,
        "songs": songs
    })

@app.route("/albums")
@route_required
async def albums():
    db = await _get_db()

    # Get albums
    cursor = await db.execute("SELECT albums.id, albums.name, artists.name FROM albums JOIN artists ON albums.artist = artists.id ORDER BY albums.name COLLATE NOCASE;")
    albums = await cursor.fetchall()
    return await render_template("albums.html", albums=albums)

@app.route("/album/<uuid>")
@route_required
async def album(uuid):
    db = await _get_db()

    # Get album
    cursor = await db.execute(f"SELECT albums.id, albums.name, artists.name FROM albums JOIN artists ON albums.artist = artists.id WHERE albums.id = '{uuid}';")
    album = await cursor.fetchone()

    # Get songs
    cursor = await db.execute(f"SELECT * FROM songs WHERE album = '{uuid}' ORDER BY discnumber, tracknumber;")
    songs = await cursor.fetchall()
    return await render_template("album.html", album=album, songs=songs)

@app.route("/album/<uuid>/songs")
async def album_songs(uuid):
    db = await _get_db()

    # Get songs
    cursor = await db.execute(f"SELECT id FROM songs WHERE album = '{uuid}' ORDER BY discnumber, tracknumber;")
    songs = await cursor.fetchall()
    return {
        "songs": list(map(lambda x: x[0], songs))
    }

@app.route("/artists")
@route_required
async def artists():
    db = await _get_db()

    # Get artists
    cursor = await db.execute("SELECT * FROM artists ORDER BY name COLLATE NOCASE;")
    artists = await cursor.fetchall()
    return await render_template("artists.html", artists=artists)

@app.route("/artist/<uuid>")
@route_required
async def artist(uuid):
    db = await _get_db()

    # Get artist
    cursor = await db.execute(f"SELECT * FROM artists WHERE id = '{uuid}';")
    artist = await cursor.fetchone()

    # Get albums
    cursor = await db.execute(f"SELECT * FROM albums WHERE artist = '{uuid}' ORDER BY name;")
    albums = await cursor.fetchall()
    return await render_template("artist.html", artist=artist, albums=albums)

@app.route("/artist/<uuid>/songs")
async def artist_songs(uuid):
    db = await _get_db()

    # Get random songs
    cursor = await db.execute(f"SELECT id FROM songs WHERE artist = '{uuid}' ORDER BY RANDOM() LIMIT 12;")
    songs = await cursor.fetchall()
    return {
        "songs": list(map(lambda x: x[0], songs))
    }

@app.route("/playlists")
@route_required
async def playlists():
    return await render_template("playlists.html")

@app.route("/playlists/select/<uuid>")
async def playlists_select(uuid):
    db = await _get_db()

    # Get playlists
    cursor = await db.execute("SELECT id, name FROM playlists ORDER BY name;")
    playlists = await cursor.fetchall()
    return await render_template("select_playlist.html", playlists=playlists, song=uuid)

@app.route("/playlist/add", methods=["POST"])
async def playlist_add():
    # Get playlist and song from body
    data = await request.get_json()
    song_id = data["song"]
    playlist_id = data["playlist"]

    db = await _get_db()

    # Add song to playlist
    cursor = await db.execute("INSERT INTO playlist_songs (playlist, song) VALUES (?, ?) ON CONFLICT DO NOTHING;", (playlist_id, song_id))
    await db.commit()

    return {
        "status": "success"
    }

@app.route("/playlist/<uuid>")
async def playlist(uuid):
    db = await _get_db()

    # Get playlist
    cursor = await db.execute(f"SELECT * FROM playlists WHERE id = '{uuid}';")
    playlist = await cursor.fetchone()

    # Get songs
    cursor = await db.execute(f"SELECT songs.id, songs.name, songs.artist, songs.album, artists.name, albums.name FROM songs JOIN artists ON songs.artist = artists.id JOIN albums ON songs.album = albums.id JOIN playlist_songs ON songs.id = playlist_songs.song WHERE playlist_songs.playlist = '{uuid}' ORDER BY playlist_songs.timestamp ASC;")

    songs = await cursor.fetchall()

    return await render_template("playlist.html", playlist=playlist, songs=songs)

@app.route("/playlist/<uuid>/songs")
async def playlist_songs(uuid):
    db = await _get_db()

    # Get playlist songs
    cursor = await db.execute(f"SELECT song FROM playlist_songs WHERE playlist = '{uuid}' ORDER BY timestamp ASC;")
    songs = await cursor.fetchall()

    return {
        "songs": list(map(lambda x: x[0], songs))
    }

@app.route("/stream/<uuid>")
async def stream(uuid):
    db = await _get_db()

    # Get song path
    cursor = await db.execute(f"SELECT path FROM songs WHERE id = '{uuid}';")
    song = await cursor.fetchone()
    return await send_file(song[0])

@app.route("/stream/<uuid>/basic")
async def stream_basic(uuid):
    db = await _get_db()

    # Get song
    cursor = await db.execute(f"SELECT songs.id, songs.name, songs.album, artists.name, albums.name FROM songs JOIN artists ON songs.artist = artists.id JOIN albums ON songs.album = albums.id WHERE songs.id = '{uuid}';")
    song = await cursor.fetchone()

    # Return as JSON with column names
    columns = ["id", "name", "cover", "artist", "album"]
    return dict(zip(columns, song))

@app.route("/cover/<uuid>")
async def cover(uuid):
    # Send cover
    return await send_from_directory(os.path.join(app_path, "covers"), uuid);

@app.route("/queue", methods=["POST"])
async def queue():
    # Get queue
    queue = await request.get_json()

    if not len(queue):
        return await render_template("queue.html", songs=[])

    db = await _get_db()

    # Get songs
    cursor = await db.execute("SELECT * FROM songs WHERE id IN (" + ",".join(["?" for _ in queue]) + ");", queue)
    songs = await cursor.fetchall()

    # Sort songs by queue
    songs = sorted(songs, key=lambda x: queue.index(x[0]))
    return await render_template("queue.html", songs=songs)

@app.route("/exit", methods=["POST"])
async def exit():
    print("Exiting...")
    # Create signal.SIGTERM
    os.kill(os.getpid(), signal.SIGTERM)
    return {
        "data": "Goodbye!"
    }
