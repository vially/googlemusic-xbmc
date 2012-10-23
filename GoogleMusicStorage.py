import os
import sys
import sqlite3

class GoogleMusicStorage():
    def __init__(self):
        self.xbmc = sys.modules["__main__"].xbmc
        self.xbmcvfs = sys.modules["__main__"].xbmcvfs
        self.settings = sys.modules["__main__"].settings
        self.path = os.path.join(self.xbmc.translatePath("special://database"), self.settings.getSetting('sqlite_db'))

		# Make sure to initialize database when it does not exist.
        if ((not os.path.isfile(self.path)) or
            (not settings.getSetting("firstrun"))):
            storage.initializeDatabase()
            settings.setSetting("firstrun", "1")

    def getPlaylistSongs(self, playlist_id):
        self._connect()

        result = []
        if playlist_id == 'all_songs':
            result = self.curs.execute("SELECT * FROM songs")
        else:
            result = self.curs.execute("SELECT * FROM songs INNER JOIN playlists_songs ON songs.song_id = playlists_songs.song_id WHERE playlists_songs.playlist_id = ?", (playlist_id,))

        songs = result.fetchall()
        self.conn.close()

        return songs

    def getPlaylistsByType(self, playlist_type):
        self._connect()
        result = self.curs.execute("SELECT * FROM playlists WHERE playlists.type = ?", (playlist_type,))
        playlists = result.fetchall()
        self.conn.close()

        return playlists

    def getSong(self, song_id):
        self._connect()
        result = self.curs.execute("SELECT * FROM songs WHERE song_id = ?", (song_id,)).fetchone()
        self.conn.close()

        return result

    def storeApiSongs(self, api_songs, playlist_id = 'all_songs'):
        new_songs = []
        playlists_songs = []

        self._connect()
        self._clearPlaylist(playlist_id, api_songs)

        for api_song in api_songs:
            song = {
                'song_id': api_song["id"],
                'comment': api_song["comment"],
                'rating': api_song["rating"],
                'last_played': api_song["lastPlayed"],
                'disc': api_song["disc"],
                'composer': api_song["composer"],
                'year': api_song["year"],
                'album': api_song["album"],
                'title': api_song["title"],
                'album_artist': api_song["albumArtist"],
                'type': api_song["type"],
                'track': api_song["track"],
                'total_tracks': api_song["totalTracks"],
                'beats_per_minute': api_song["beatsPerMinute"],
                'genre': api_song["genre"],
                'play_count': api_song["playCount"],
                'creation_date': api_song["creationDate"],
                'name': api_song["name"],
                'artist': api_song["artist"],
                'url': api_song["url"],
                'total_discs': api_song["totalDiscs"],
                'duration_millis': api_song["durationMillis"],
                'album_art_url': api_song.get("albumArtUrl", None),
                'display_name': self._getSongDisplayName(api_song)
            }

            existing_song = self.curs.execute("SELECT * FROM songs WHERE song_id = ?", (api_song["id"],)).fetchone()
            if existing_song is not None:
                self.curs.execute("UPDATE songs SET comment=:comment, rating=:rating, last_played=:last_played, disc=:disc, composer=:composer, year=:year, album=:album, title=:title, album_artist=:album_artist, type=:type, track=:track, total_tracks=:total_tracks, beats_per_minute=:beats_per_minute, genre=:genre, play_count=:play_count, creation_date=:creation_date, name=:name, artist=:artist, url=:url, total_discs=:total_discs, duration_millis=:duration_millis, album_art_url=:album_art_url, display_name=:display_name WHERE song_id=:song_id", song)
            else:
                new_songs.append(song)

            playlist_song = (playlist_id, api_song["id"])
            playlists_songs.append(playlist_song)

        self.curs.executemany("INSERT INTO songs VALUES (:song_id, :comment, :rating, :last_played, :disc, :composer, :year, :album, :title, :album_artist, :type, :track, :total_tracks, :beats_per_minute, :genre, :play_count, :creation_date, :name, :artist, :url, :total_discs, :duration_millis, :album_art_url, :display_name, NULL)", new_songs)
        if playlist_id != 'all_songs':
            self.curs.execute("UPDATE playlists SET fetched = 1 WHERE playlist_id = ?", (playlist_id,))
            self.curs.executemany("INSERT INTO playlists_songs VALUES (?, ?)", playlists_songs)
        else:
            self.settings.setSetting("fetched_all_songs", "1")

        self.conn.commit()
        self.conn.close()

    def storePlaylists(self, playlists, playlist_type):
        all_playlists = []
        all_ids = [playlist_type]
        for playlist_name, playlist_ids in playlists.iteritems():
            for playlist_id in playlist_ids:
                playlist = (playlist_id, playlist_name)
                all_playlists.append(playlist)
                all_ids.append(playlist_id)

        self._connect()
        self.curs.execute("DELETE FROM playlists_songs WHERE playlists_songs.playlist_id IN (SELECT playlist_id FROM playlists WHERE type = ? AND playlist_id NOT IN (%s))" % ','.join('?' * (len(all_ids) - 1)), all_ids)
        self.curs.execute("DELETE FROM playlists WHERE type = ? and playlist_id NOT IN (%s)" % ','.join('?' * (len(all_ids) - 1)), all_ids)
        self.conn.commit()

        result = self.curs.execute("SELECT playlist_id FROM playlists WHERE type = ? AND playlist_id IN (%s)" % ','.join('?' * (len(all_ids) - 1)), all_ids)
        existing_playlists = []
        for playlist_id, in result:
            existing_playlists.append(playlist_id)

        for (playlist_id, playlist_name) in all_playlists:
            if playlist_id in existing_playlists:
                self.curs.execute("UPDATE playlists SET name = ? WHERE playlist_id = ?", (playlist_name, playlist_id))
            else:
                self.curs.execute("INSERT INTO playlists VALUES (?, ?, ?, 0)", (playlist_id, playlist_name, playlist_type))
        self.conn.commit()
        self.conn.close()

    def getSongStreamUrl(self, song_id):
        self._connect()
        song = self.curs.execute("SELECT stream_url FROM songs WHERE song_id = ?", (song_id,)).fetchone()
        stream_url = song[0]
        self.conn.close()

        return stream_url

    def isPlaylistFetched(self, playlist_id):
        fetched = False
        if playlist_id == 'all_songs':
            fetched = bool(self.settings.getSetting("fetched_all_songs"))
        else:
            self._connect()
            playlist = self.curs.execute("SELECT fetched FROM playlists WHERE playlist_id = ?", (playlist_id,)).fetchone()
            fetched = bool(playlist[0])
            self.conn.close()

        return fetched

    def updateSongStreamUrl(self, song_id, stream_url):
        self._connect()
        self.curs.execute("UPDATE songs SET stream_url = ? WHERE song_id = ?", (stream_url, song_id))
        self.conn.commit()
        self.conn.close()

    def _clearPlaylist(self, playlist_id, api_songs):
        if playlist_id == 'all_songs':
            song_ids = []
            for api_song in api_songs:
                song_ids.append(api_song["id"])

            self.curs.execute("DELETE FROM playlists_songs WHERE song_id NOT IN (%s)" % ','.join('?' * len(song_ids)), song_ids) # this may not be necessary
            self.curs.execute("DELETE FROM songs WHERE song_id NOT IN (%s)" % ','.join('?' * len(song_ids)), song_ids)
        else:
            self.curs.execute("DELETE FROM playlists_songs WHERE playlist_id = ?", (playlist_id,))

        self.conn.commit()

    def _connect(self):
        self.conn = sqlite3.connect(self.path)
        self.curs = self.conn.cursor()

    def initializeDatabase(self):
        self._connect()

        self.curs.execute('''CREATE TABLE songs (
                song_id VARCHAR NOT NULL PRIMARY KEY,           --# 0
                comment VARCHAR,                                --# 1
                rating INTEGER,                                 --# 2
                last_played INTEGER,                            --# 3
                disc INTEGER,                                   --# 4
                composer VARCHAR,                               --# 5
                year INTEGER,                                   --# 6
                album VARCHAR,                                  --# 7
                title VARCHAR,                                  --# 8
                album_artist VARCHAR,                           --# 9
                type INTEGER,                                   --# 10
                track INTEGER,                                  --# 11
                total_tracks INTEGER,                           --# 12
                beats_per_minute INTEGER,                       --# 13
                genre VARCHAR,                                  --# 14
                play_count INTEGER,                             --# 15
                creation_date INTEGER,                          --# 16
                name VARCHAR,                                   --# 17
                artist VARCHAR,                                 --# 18
                url VARCHAR,                                    --# 19
                total_discs INTEGER,                            --# 20
                duration_millis INTEGER,                        --# 21
                album_art_url VARCHAR,                          --# 22
                display_name VARCHAR,                           --# 23
                stream_url VARCHAR                              --# 24
        )''')

        self.curs.execute('''CREATE TABLE playlists (
                playlist_id VARCHAR NOT NULL PRIMARY KEY,
                name VARCHAR,
                type VARCHAR,
                fetched BOOLEAN
        )''')

        self.curs.execute('''CREATE TABLE playlists_songs (
                playlist_id VARCHAR,
                song_id VARCHAR,
                FOREIGN KEY(playlist_id) REFERENCES playlists(playlist_id) ON DELETE CASCADE,
                FOREIGN KEY(song_id) REFERENCES songs(song_id) ON DELETE CASCADE
        )''')

        self.curs.execute('''CREATE INDEX playlistindex ON playlists_songs(playlist_id)''')
        self.curs.execute('''CREATE INDEX songindex ON playlists_songs(song_id)''')

        self.conn.commit()
        self.conn.close()

    def _getSongDisplayName(self, api_song):
        displayName = ""
        song = api_song.get
        song_name = song("name").strip()
        song_artist = song("artist").strip()

        if ( (len(song_artist) == 0) and (len(song_name) == 0)):
            displayName = "UNKNOWN"
        elif (len(song_artist) > 0):
            displayName += song_artist
            if (len(song_name) > 0):
                displayName += " - " + song_name
        else:
            displayName += song_name

        return displayName

    def _encodeApiSong(self, api_song):
        encoding_keys = ["id", "comment", "composer", "album", "title", "albumArtist", "titleNorm", "albumArtistNorm", "genre", "name", "albumNorm", "artist", "url", "artistNorm", "albumArtUrl"]

        song = {}
        for key in api_song:
            key = key.encode('utf-8')
            if key in encoding_keys:
                song[key] = api_song[key].encode('utf-8')
            else:
                song[key] = api_song[key]

        return song
