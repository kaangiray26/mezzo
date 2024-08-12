#!env/bin/python3
# -*- coding: utf-8 -*-

import duckdb
from queue import Queue, Empty
from flask import Flask, render_template
from threading import Thread
from lib.mezzo import Scanner
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
con.execute("CREATE TABLE IF NOT EXISTS artists (id UUID PRIMARY KEY, name VARCHAR);")
con.execute("CREATE TABLE IF NOT EXISTS albums (id UUID PRIMARY KEY, title VARCHAR, artist VARCHAR);")
con.execute("CREATE TABLE IF NOT EXISTS playlists (id UUID PRIMARY KEY, title VARCHAR, songs INTEGER[]);")
con.execute("CREATE TABLE IF NOT EXISTS songs (id UUID PRIMARY KEY, title VARCHAR, artist VARCHAR, album VARCHAR, path VARCHAR);")
con.execute("CREATE TABLE IF NOT EXISTS library(id UUID PRIMARY KEY, items VARCHAR[]);")

@app.route("/")
def index():
    return render_template("index.html", config=config)

@app.route("/albums")
def albums():
    # Get albums
    albums = con.execute("SELECT * FROM albums ORDER BY title;").fetchall()
    return render_template("albums.html", albums=albums)

@app.route("/artists")
def artists():
    # Get artists
    artists = con.execute("SELECT * FROM artists ORDER BY name;").fetchall()
    return render_template("artists.html", artists=artists)

@app.route("/playlists")
def playlists():
    return render_template("playlists.html")

def update_library():
    # Load data into duckdb from `library.json`
    library = Scanner().scan(config["library_path"])
    print("Library updated.")

if __name__ == "__main__":
    try:
        update_library()
        app.run()
    except KeyboardInterrupt:
        print("Exiting...")
        con.close()
        exit(0)
