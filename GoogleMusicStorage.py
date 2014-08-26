import os
import sys
import sqlite3
import time


class GoogleMusicStorage():
    def __init__(self):
        self.xbmc     = sys.modules["__main__"].xbmc
        self.settings = sys.modules["__main__"].settings
        self.path     = os.path.join(self.xbmc.translatePath("special://database"), self.settings.getSetting('sqlite_db'))

    def checkDbInit(self):
        # check if auto update is enabled
        if os.path.isfile(self.path):
            updatelib = int(self.settings.getSetting('updatelib'))
            if updatelib != 0:
                #difftime = datetime.datetime.now() - datetime.datetime.fromtimestamp(os.path.getctime(self.path))
                difftime = time.time() - float(self.settings.getSetting('fetched_all_songs'))

                if difftime > 7 * 24 * 60 * 60: # week
                    self.clearCache()
                elif updatelib == 2 and difftime > 24 * 60 * 60: # day
                    self.clearCache()
                elif updatelib == 3 and difftime > 60 * 60: # hour
                    self.clearCache()
                
        # Make sure to initialize database when it does not exist.
        if not os.path.isfile(self.path):
            self.initializeDatabase()
            self.settings.setSetting("fetched_all_songs","0")

    def clearCache(self):
        if os.path.isfile(self.path):
            os.remove(self.path)
        self.settings.setSetting("fetched_all_songs", "0")

    def getPlaylistSongs(self, playlist_id):
        self._connect()
        if playlist_id == 'all_songs':
            result = self.curs.execute("SELECT * FROM songs ORDER BY display_name")
        else:
            result = self.curs.execute("SELECT * FROM songs INNER JOIN playlists_songs ON songs.song_id = playlists_songs.song_id "+
                                       "WHERE playlists_songs.playlist_id = ?", (playlist_id,))

        songs = result.fetchall()
        self.conn.close()

        return songs

    def getFilterSongs(self, filter_type, filter_criteria, artist):
        #print "storage getfiltersongs: "+filter_type+" "+repr(filter_criteria)+" "+repr(artist)
        
        if filter_type == 'album':
            if artist:
                query = "select * from songs where album = :filter and artist = :artist order by disc asc, track asc"
            else:
                query = "select * from songs where album = :filter order by disc asc, track asc"
        elif filter_type == 'artist':
            query = "select * from songs where artist = :filter order by album asc, disc asc, track asc"
        else:
            query = "select * from songs where genre = :filter order by title asc"
            
        self._connect()
        songs = self.curs.execute(query,{'filter':filter_criteria if filter_criteria else '','artist':artist}).fetchall()
        self.conn.close()

        return songs

    def getCriteria(self, criteria, artist_name):
        self._connect()
        if (criteria == 'artist'):
            result = self.curs.execute("select artist, year, max(album_art_url) from songs group by artist")
        elif (criteria == 'album'):
            if artist_name:
               result = self.curs.execute("select album, year, album_artist, max(album_art_url) from songs where artist=? group by album",(artist_name.decode('utf8'),))
            else:
               result = self.curs.execute("select album, year, album_artist, max(album_art_url) from songs group by album")
        else:
            result = self.curs.execute("select genre from songs group by genre")

        criterias = result.fetchall()
        self.conn.close()

        return criterias

    def getPlaylists(self):
        self._connect()
        playlists = self.curs.execute("SELECT playlist_id, name FROM playlists ORDER BY name").fetchall()
        self.conn.close()
        return playlists

    def getAutoPlaylistSongs(self,playlist):
        querys = {'thumbsup':'SELECT * FROM songs WHERE rating = 5 ORDER BY display_name',
                  'lastadded':'SELECT * FROM songs ORDER BY creation_date desc LIMIT 500',
                  'mostplayed':'SELECT * FROM songs ORDER BY play_count desc LIMIT 500',
                  'freepurchased':'SELECT * FROM songs WHERE type = 0 OR type = 1',
                  'feellucky':'SELECT * FROM songs ORDER BY random() LIMIT 500',
                 }
        self._connect()
        result = self.curs.execute(querys[playlist]).fetchall()
        self.conn.close()
        return result

    def getSong(self, song_id):
        self._connect()
        #result = self.curs.execute("SELECT * FROM songs WHERE song_id = ? ", (song_id,)).fetchone()
        result = self.curs.execute("SELECT stream_url FROM songs WHERE song_id = ? ", (song_id,)).fetchone()
        self.conn.close()
        return result

    def getSearch(self, query):
        query = '%'+ query.replace('%','') + '%'
        self._connect()
        result = self.curs.execute("SELECT * FROM songs WHERE name like ? OR artist like ? ORDER BY display_name", (query,query,)).fetchall()
        self.conn.close()
        return result

    def storePlaylistSongs(self, playlists_songs):
        self._connect()
        self.curs.execute("PRAGMA foreign_keys = OFF")

        self.curs.execute("DELETE FROM playlists_songs")
        self.curs.execute("DELETE FROM playlists")

        api_songs = []

        for playlist in playlists_songs:
            print playlist['name']+' id:'+playlist['id']+' tracks:'+str(len(playlist['tracks']))
            playlistId = playlist['id']
            if len(playlist['name']) > 0:
                self.curs.execute("INSERT INTO playlists (name, playlist_id, type, fetched) VALUES (?, ?, 'user', 1)", (playlist['name'], playlistId) )
                for entry in playlist['tracks']:
                    self.curs.execute("INSERT INTO playlists_songs (playlist_id, song_id) VALUES (?, ?)", (playlistId, entry['trackId']))
                    if entry.has_key('track'):
                        api_songs.append(entry['track'])

        self.conn.commit()
        self.conn.close()

        self.storeInAllSongs(api_songs)

    def storeApiSongs(self, api_songs, playlist_id = 'all_songs'):
        self._connect()
        self.curs.execute("PRAGMA foreign_keys = OFF")

        if playlist_id == 'all_songs':
            self.curs.execute("DELETE FROM songs")
        else:
            self.curs.execute("DELETE FROM songs WHERE song_id IN (SELECT song_id FROM playlists_songs WHERE playlist_id = ?)", (playlist_id,))
            self.curs.execute("DELETE FROM playlists_songs WHERE playlist_id = ?", (playlist_id,))
            self.curs.executemany("INSERT INTO playlists_songs (playlist_id, song_id) VALUES (?, ?)", [(playlist_id, s["track_id"]) for s in api_songs])

        if playlist_id == 'all_songs':
            self.settings.setSetting("fetched_all_songs", str(time.time()))
        else:
            self.curs.execute("UPDATE playlists SET fetched = 1 WHERE playlist_id = ?", (playlist_id,))

        self.conn.commit()
        self.conn.close()

        self.storeInAllSongs(api_songs)

    def storeInAllSongs(self, api_songs):
        self._connect()
        self.curs.execute("PRAGMA foreign_keys = OFF")

        def songs():
          for api_song in api_songs:
              get = api_song.get
              yield {
                  'song_id':       get("id", get("storeId", get("trackId"))), #+str(i),
                  'comment':       get("comment", ""),
                  'rating':        get("rating", 0),
                  'last_played':   get("lastPlayed", get("recentTimestamp", 0)),
                  'disc':          get("disc", get("discNumber", 0)),
                  'composer':      get("composer", 0),
                  'year':          get("year", 0),
                  'album':         api_song["album"] if api_song["album"] else '-Unknown-',
                  'title':         api_song["title"],
                  'album_artist':  get("albumArtist") if get("albumArtist") else api_song["artist"] if api_song["artist"] else '-Unknown-',
                  'type':          get("type", 0),
                  'track':         get("track", get("trackNumber" ,0)),
                  'total_tracks':  get("total_tracks", get("totalTrackCount", 0)),
                  'beats_per_minute': get("beatsPerMinute", 0),
                  'genre':         api_song["genre"] if api_song["genre"] else '-Unknown-',
                  'play_count':    get("playCount", 0),
                  'creation_date': get("creationDate", get("creationTimestamp", 0)),
                  'name':          get("name", api_song["title"]),
                  'artist':        api_song["artist"] if api_song["artist"] else '-Unknown-',
                  'url':           get("url", None),
                  'total_discs':   get("total_discs", get("totalDiscCount", 0)),
                  'duration':      int(api_song["durationMillis"])/1000,
                  'album_art_url': self._getAlbumArtUrl(api_song),
                  'display_name':  self._getSongDisplayName(api_song),
              }

        self.curs.executemany("INSERT OR REPLACE INTO songs VALUES ("+
                              ":song_id, :comment, :rating, :last_played, :disc, :composer, :year, :album, :title, :album_artist,"+
                              ":type, :track, :total_tracks, :beats_per_minute, :genre, :play_count, :creation_date, :name, :artist, "+
                              ":url, :total_discs, :duration, :album_art_url, :display_name, NULL)", songs())

        self.conn.commit()
        self.conn.close()

    def storePlaylists(self, playlists, playlist_type):
        self._connect()
        self.curs.execute("PRAGMA foreign_keys = OFF")

        # (deletes will not cascade due to pragma)
        self.curs.execute("DELETE FROM playlists WHERE type = ?", (playlist_type,))

        # rebuild table
        def playlist_rows():
          for playlist_name, playlist_ids in playlists.iteritems():
             for playlist_id in playlist_ids:
                yield (playlist_name, playlist_id, playlist_type)

        self.curs.executemany("INSERT INTO playlists (name, playlist_id, type, fetched) VALUES (?, ?, ?, 0)", playlist_rows())

        # clean up dangling songs
        self.curs.execute("DELETE FROM playlists_songs WHERE playlist_id NOT IN (SELECT playlist_id FROM playlists)")
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
            if self.settings.getSetting("fetched_all_songs"):
                fetched = (self.settings.getSetting("fetched_all_songs") != "0")
                #print "Fetched "+repr(fetched)+" "+self.settings.getSetting("fetched_all_songs")
        else:
            self._connect()
            playlist = self.curs.execute("SELECT fetched FROM playlists WHERE playlist_id = ?", (playlist_id,)).fetchone()
            fetched = bool(playlist[0])
            self.conn.close()

        return fetched

    def incrementSongPlayCount(self, song_id):
        self._connect()
        self.curs.execute("UPDATE songs SET play_count = play_count+1 WHERE song_id = ?", (song_id,))
        self.conn.commit()
        self.conn.close()
        
    def updateSongStreamUrl(self, song_id, stream_url):
        self._connect()
        self.curs.execute("UPDATE songs SET stream_url = ? WHERE song_id = ?", (stream_url, song_id))
        self.conn.commit()
        self.conn.close()

    def _connect(self):
        self.conn = sqlite3.connect(self.path)
        self.conn.text_factory = str
        self.curs = self.conn.cursor()

    def initializeDatabase(self):
        self._connect()

        self.curs.execute('''CREATE TABLE IF NOT EXISTS songs (
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
                duration INTEGER,                               --# 21
                album_art_url VARCHAR,                          --# 22
                display_name VARCHAR,                           --# 23
                stream_url VARCHAR                              --# 24
        )''')

        self.curs.execute('''CREATE TABLE IF NOT EXISTS playlists (
                playlist_id VARCHAR NOT NULL PRIMARY KEY,
                name VARCHAR,
                type VARCHAR,
                fetched BOOLEAN
        )''')

        self.curs.execute('''CREATE TABLE IF NOT EXISTS playlists_songs (
                playlist_id VARCHAR,
                song_id VARCHAR,
                FOREIGN KEY(playlist_id) REFERENCES playlists(playlist_id) ON DELETE CASCADE,
                FOREIGN KEY(song_id) REFERENCES songs(song_id) ON DELETE CASCADE
        )''')

        self.curs.execute('''CREATE INDEX IF NOT EXISTS playlistindex ON playlists_songs(playlist_id)''')
        self.curs.execute('''CREATE INDEX IF NOT EXISTS songindex ON playlists_songs(song_id)''')

        self.conn.commit()
        self.conn.close()

    def _getSongDisplayName(self, api_song):
        displayName = "-Unknown-"
        song_name = api_song.get("title")
        song_artist = api_song.get("artist")

        if song_artist :
            displayName = song_artist.strip()
            if song_name:
                displayName += " - " + song_name.strip()
        elif song_name :
            displayName = song_name.strip()

        return displayName

    def _getAlbumArtUrl(self, api_song):
        url = ""
        if "albumArtUrl" in api_song:
            url = "http:"+api_song["albumArtUrl"]
        elif "albumArtRef" in api_song:
            url = api_song["albumArtRef"][0]["url"]
        return url
