artists_table = """
CREATE TABLE IF NOT EXISTS artists (
    id TEXT PRIMARY KEY,
    name TEXT,
    path TEXT,
    cover TEXT
);
"""

albums_table = """
CREATE TABLE IF NOT EXISTS albums (
    id TEXT PRIMARY KEY,
    name TEXT,
    path TEXT,
    cover TEXT,
    artist TEXT,
    FOREIGN KEY (artist) REFERENCES artists(id)
);
"""

songs_table = """
CREATE TABLE IF NOT EXISTS songs (
    id TEXT PRIMARY KEY,
    name TEXT,
    path TEXT,
    artist TEXT,
    album TEXT,
    discnumber INTEGER,
    tracknumber INTEGER,
    FOREIGN KEY (artist) REFERENCES artists(id),
    FOREIGN KEY (album) REFERENCES albums(id)
);
"""

playlists_table = """
CREATE TABLE IF NOT EXISTS playlists (
    id TEXT PRIMARY KEY,
    name TEXT
);
"""

playlist_songs_table = """
CREATE TABLE IF NOT EXISTS playlist_songs (
    playlist TEXT REFERENCES playlists(id),
    song TEXT REFERENCES songs(id),
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

# Create 3 default playlists
# 1. Favorite Songs
# 2. Most Played
# 3. Recently Played
default_playlists = """
INSERT INTO playlists (id, name) VALUES
    ('00000000-0000-0000-0000-000000000001', 'Favorite Songs'),
    ('00000000-0000-0000-0000-000000000002', 'Most Played'),
    ('00000000-0000-0000-0000-000000000003', 'Recently Played');
"""

create_tables = [artists_table, albums_table, songs_table, playlists_table, playlist_songs_table, default_playlists]
