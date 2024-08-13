artists_table = """
CREATE TABLE IF NOT EXISTS artists (
    id UUID PRIMARY KEY,
    name VARCHAR,
    cover VARCHAR
);
"""

albums_table = """
CREATE TABLE IF NOT EXISTS albums (
    id UUID PRIMARY KEY,
    name VARCHAR,
    artist UUID,
    cover VARCHAR,
    FOREIGN KEY (artist) REFERENCES artists(id)
);
"""

songs_table = """
CREATE TABLE IF NOT EXISTS songs (
    id UUID PRIMARY KEY,
    name VARCHAR,
    path VARCHAR,
    artist UUID,
    album UUID,
    discnumber INTEGER,
    tracknumber INTEGER,
    FOREIGN KEY (artist) REFERENCES artists(id),
    FOREIGN KEY (album) REFERENCES albums(id)
);
"""

playlists_table = """
CREATE TABLE IF NOT EXISTS playlists (
    id UUID PRIMARY KEY,
    title VARCHAR,
    songs UUID[]
);
"""

library_table = """
CREATE TABLE IF NOT EXISTS library(
    id UUID PRIMARY KEY,
    items VARCHAR[]
);
"""

create_tables = [artists_table, albums_table, songs_table, playlists_table, library_table]
