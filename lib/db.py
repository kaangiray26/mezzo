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
    name VARCHAR,
    songs UUID[]
);
"""

# Create 3 default playlists
# 1. Favorite Songs
# 2. Most Played
# 3. Recently Played
default_playlists = """
INSERT INTO playlists (id, name, songs) VALUES
    ('00000000-0000-0000-0000-000000000001', 'Favorite Songs', ARRAY[]::UUID[]),
    ('00000000-0000-0000-0000-000000000002', 'Most Played', ARRAY[]::UUID[]),
    ('00000000-0000-0000-0000-000000000003', 'Recently Played', ARRAY[]::UUID[]);
"""

create_tables = [artists_table, albums_table, songs_table, playlists_table, default_playlists]
