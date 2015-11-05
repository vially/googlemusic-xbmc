import os, sqlite3, utils, xbmc

class GoogleMusicStorage():
    def __init__(self):
        self.path = os.path.join(xbmc.translatePath("special://database"), utils.addon.getSetting('sqlite_db'))
        self._connect()

    def checkDbInit(self):
        # check if auto update is enabled
        if os.path.isfile(self.path):
            updatelib = int(utils.addon.getSetting('updatelib'))
            if updatelib != 0:
                import time
                difftime = time.time() - float(utils.addon.getSetting('fetched_all_songs'))

                if difftime > 7 * 24 * 60 * 60: # week
                    self.clearCache()
                elif updatelib == 2 and difftime > 24 * 60 * 60: # day
                    self.clearCache()
                elif updatelib == 3 and difftime > 60 * 60: # hour
                    self.clearCache()

        # Make sure to initialize database when it does not exist.
        if not os.path.isfile(self.path):
            self.initializeDatabase()
            utils.addon.setSetting("fetched_all_songs","0")

    def clearCache(self):
        if os.path.isfile(self.path):
            if self.conn: self.conn.close()
            os.remove(self.path)
        utils.addon.setSetting("fetched_all_songs", "0")

    def getPlaylistSongs(self, playlist_id):
        if playlist_id == 'all_songs':
            result = self.curs.execute("SELECT * FROM songs ORDER BY display_name")
        elif playlist_id == 'shuffled_albums':
            result = self.curs.execute("WITH albums AS (SELECT DISTINCT album, album_artist FROM songs ORDER BY RANDOM()) "+
                                       "SELECT songs.* FROM albums LEFT JOIN songs ON songs.album = albums.album AND songs.album_artist = albums.album_artist "+
									   "ORDER BY albums.rowid, songs.disc, songs.track")
        else:
            result = self.curs.execute("SELECT * FROM songs "+
                                       "INNER JOIN playlists_songs ON songs.song_id = playlists_songs.song_id "+
                                       "WHERE playlists_songs.playlist_id = ?", (playlist_id,))
        songs = result.fetchall()
        return songs

    def getFilterSongs(self, filter_type, filter_criteria, albumArtist):
        #print "### storage getfiltersongs: "+repr(filter_type)+" "+repr(filter_criteria)+" "+repr(albumArtist)

        if albumArtist:
            query = "select * from songs where album = :filter and album_artist = :albumArtist order by disc asc, track asc"
        elif filter_type == 'album':
            query = "select * from songs where album = :filter order by disc asc, track asc"
        elif filter_type == 'artist':
            query = "select * from songs where artist = :filter order by album asc, disc asc, track asc"
        elif filter_type == 'genre':
            query = "select * from songs where genre = :filter order by album asc, disc asc, track asc, title asc"
        elif filter_type == 'composer':
            query = "select * from songs where composer = :filter order by album asc, disc asc, track asc, title asc"

        songs = self.curs.execute(query,{'filter':filter_criteria if filter_criteria else '','albumArtist':albumArtist}).fetchall()

        return songs

    def getCriteria(self, criteria, name):
        #print "### storage getcriteria: "+repr(criteria)+" "+repr(name)

        if criteria == 'album':
            query = "select album_artist, album, year, max(album_art_url), max(creation_date) from songs where album <> '-Unknown-' group by lower(album_artist), lower(album)"
        else:
            #if criteria == 'artist': criteria = 'album_artist'
            if criteria == 'artist' and not name:
                query = "select album_artist, max(artist_art_url) from songs group by lower(album_artist)"
            elif criteria == 'artist' and name:
                query = "select album_artist, album, year, max(album_art_url), max(creation_date) from songs where (artist=:name or album_artist=:name) group by lower(album_artist), lower(album)"
            elif criteria == 'genre' and not name:
                query = "select genre, max(artist_art_url) from songs group by lower(genre)"
            elif criteria == 'genre' and name:
                query = "select genre, album, year, max(album_art_url), max(creation_date) from songs where genre=:name group by lower(genre), lower(album)"
            elif name:
                query = "select album_artist, album, year, max(album_art_url), max(creation_date) from songs where %s=:name group by lower(album_artist), lower(album)" % criteria
            else:
                query = "select %s from songs group by lower(%s)" % (criteria, criteria)

        return self.curs.execute(query,{'name':name.decode('utf8')}).fetchall()

    def getPlaylists(self):
        return self.curs.execute("SELECT playlist_id, name FROM playlists ORDER BY name").fetchall()

    def getAutoPlaylistSongs(self,playlist):
        querys = {'thumbsup':'SELECT * FROM songs WHERE rating > 3 ORDER BY display_name',
                  'lastadded':'SELECT * FROM songs ORDER BY creation_date desc LIMIT 500',
                  'mostplayed':'SELECT * FROM songs ORDER BY play_count desc LIMIT 500',
                  'freepurchased':'SELECT * FROM songs WHERE type <> 0 order by creation_date desc',
                  'feellucky':'SELECT * FROM songs ORDER BY random() LIMIT 500',
                 }
        return self.curs.execute(querys[playlist]).fetchall()

    def getSong(self, song_id):
        return self.curs.execute("SELECT * FROM songs WHERE song_id = ? ", (song_id,)).fetchone()

    def getSearch(self, query):
        query = '%'+ query.replace('%','') + '%'
        result = {}
        result['artists'] = self.curs.execute("SELECT artist, max(artist_art_url) FROM songs WHERE artist like ? GROUP BY artist", (query,)).fetchall()
        result['tracks'] = self.curs.execute("SELECT * FROM songs WHERE display_name like ? ORDER BY display_name", (query,)).fetchall()
        result['albums'] = self.curs.execute("SELECT album, artist, max(album_art_url) FROM songs WHERE album like ? or album_artist like ? GROUP BY album, artist", (query,query)).fetchall()
        return result

    def storePlaylistSongs(self, playlists_songs):
        self.curs.execute("PRAGMA foreign_keys = OFF")

        self.curs.execute("DELETE FROM playlists_songs")
        self.curs.execute("DELETE FROM playlists")

        api_songs = []

        for playlist in playlists_songs:
            #print playlist['name']+' id:'+playlist['id']+' tracks:'+str(len(playlist['tracks']))
            playlistId = playlist['id']
            if len(playlist['name']) > 0:
                self.curs.execute("INSERT INTO playlists (name, playlist_id, type, fetched) VALUES (?, ?, 'user', 1)", (playlist['name'], playlistId) )
                for entry in playlist['tracks']:
                    self.curs.execute("INSERT INTO playlists_songs (playlist_id, song_id, entry_id ) VALUES (?, ?, ?)", (playlistId, entry['trackId'], entry['id']))
                    if entry.has_key('track'):
                        api_songs.append(entry['track'])

        self.conn.commit()
        self.storeInAllSongs(api_songs)

    def storeApiSongs(self, api_songs):
        import time
        utils.addon.setSetting("fetched_all_songs", str(time.time()))
        self.storeInAllSongs(api_songs)

    def storeInAllSongs(self, api_songs):
        self.curs.execute("PRAGMA foreign_keys = OFF")

        #for i in range(5):
        def songs():
          for api_song in api_songs:
              get = api_song.get
              yield {
                  'song_id':       get("id", get("storeId", get("trackId"))), #+str(i),
                  'comment':       get("comment", ""),
                  'rating':        get("rating", 0),
                  'last_played':   get("recentTimestamp", 0),
                  'disc':          get("discNumber", 0),
                  'composer':      get("composer", '-Unknown-'),
                  'year':          get("year", 0),
                  'album':         get("album", '-Unknown-'),
                  'title':         get("title", get("name","")),
                  'album_artist':  get("albumArtist", get("artist", '-Unknown-')),
                  'type':          get("trackType", 0),
                  'track':         get("trackNumber" ,0),
                  'total_tracks':  get("totalTrackCount", 0),
                  'genre':         get("genre", '-Unknown-'),
                  'play_count':    get("playCount", 0),
                  'creation_date': get("creationTimestamp", 0),
                  'name':          get("name", get("title","")),
                  'artist':        get("artist", get("albumArtist", '-Unknown-')),
                  'total_discs':   get("totalDiscCount", 0),
                  'duration':      int(get("durationMillis",0))/1000,
                  'album_art_url': get("albumArtRef")[0]['url'] if get("albumArtRef") else utils.addon.getAddonInfo('icon'),
                  'display_name':  self._getSongDisplayName(api_song),
                  'artist_art_url':get("artistArtRef")[0]['url'] if get("artistArtRef") else utils.addon.getAddonInfo('fanart'),
              }

        self.curs.executemany("INSERT OR REPLACE INTO songs VALUES ("+
                              ":song_id, :comment, :rating, :last_played, :disc, :composer, :year, :album, :title, :album_artist,"+
                              ":type, :track, :total_tracks, NULL, :genre, :play_count, :creation_date, :name, :artist, "+
                              "NULL, :total_discs, :duration, :album_art_url, :display_name, NULL, :artist_art_url)", songs())

        self.conn.commit()


    def getSongStreamUrl(self, song_id):
        song = self.curs.execute("SELECT stream_url FROM songs WHERE song_id = ?", (song_id,)).fetchone()
        return song[0]

    def incrementSongPlayCount(self, song_id):
        import time
        self.curs.execute("UPDATE songs SET play_count = play_count+1, last_played = ? WHERE song_id = ?", (int(time.time()*1000000), song_id))
        self.conn.commit()

    def addToPlaylist(self, playlist_id, song_id, entry_id):
        self.curs.execute("INSERT OR REPLACE INTO playlists_songs(playlist_id, song_id, entry_id) VALUES (?,?,?)", (playlist_id, song_id, entry_id))
        self.conn.commit()

    def delFromPlaylist(self, playlist_id, song_id):
        entry_id = self.curs.execute("SELECT entry_id FROM playlists_songs WHERE playlist_id=? and song_id=?", (playlist_id, song_id)).fetchone()
        self.curs.execute("DELETE from playlists_songs WHERE entry_id=?", (entry_id[0], ))
        self.conn.commit()
        return entry_id[0]

    def updateSongStreamUrl(self, song_id, stream_url):
        self.curs.execute("UPDATE songs SET stream_url = ? WHERE song_id = ?", (stream_url, song_id))
        self.conn.commit()

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
                stream_url VARCHAR,                             --# 24
                artist_art_url VARCHAR                          --# 25
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
                entry_id VARCHAR,
                FOREIGN KEY(playlist_id) REFERENCES playlists(playlist_id) ON DELETE CASCADE,
                FOREIGN KEY(song_id) REFERENCES songs(song_id) ON DELETE CASCADE
        )''')

        self.curs.execute('''CREATE INDEX IF NOT EXISTS playlistindex ON playlists_songs(playlist_id)''')
        self.curs.execute('''CREATE INDEX IF NOT EXISTS songindex ON playlists_songs(song_id)''')

        self.conn.commit()

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

storage = GoogleMusicStorage()