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

        # try to detect problem in database creation
        if os.path.isfile(self.path):
            try:
                self.curs.execute("SELECT * FROM songs, library_songs, playlists, playlists_songs LIMIT 1").fetchone()
            except Exception as ex:
                utils.log("Cache database error, clear "+repr(ex))
                self.clearCache()

        # Make sure to initialize database when it does not exist.
        if not os.path.isfile(self.path):
            self.initializeDatabase()
            utils.addon.setSetting("fetched_all_songs","0")

    def clearCache(self):
        if os.path.isfile(self.path):
            if self.conn: self.conn.close()
            try:
                os.remove(self.path)
            except Exception as ex:
                utils.log("Error trying to delete database "+repr(ex))
                self._connect()
        utils.addon.setSetting("fetched_all_songs", "0")

    def getPlaylistSongs(self, playlist_id):
        if playlist_id == 'all_songs':
            query = "SELECT * FROM songs ORDER BY display_name"
        elif playlist_id == 'shuffled_albums':
            query = "WITH albums AS (SELECT DISTINCT album, album_artist FROM songs ORDER BY RANDOM()) "\
                    "SELECT songs.* FROM albums LEFT JOIN songs ON songs.album = albums.album AND songs.album_artist = albums.album_artist "\
                    "ORDER BY albums.rowid, songs.discnumber, songs.tracknumber"
        else:
            query = "SELECT * FROM songs "\
                    "INNER JOIN playlists_songs ON songs.song_id = playlists_songs.song_id "\
                    "WHERE playlists_songs.playlist_id = :id"
        return self.curs.execute(query,{'id':playlist_id}).fetchall()

    def getFilterSongs(self, filter_type, filter_criteria, albumArtist):
        utils.log("### storage getfiltersongs: "+repr(filter_type)+" "+repr(filter_criteria)+" "+repr(albumArtist))

        if albumArtist:
            query = "select * from library_songs where album = :filter and album_artist = :albumArtist "\
                    "order by discnumber asc, tracknumber asc, display_name asc"
        elif filter_type == 'album':
            query = "select * from library_songs where album = :filter "\
                    "order by discnumber asc, tracknumber asc, display_name asc"
        elif filter_type == 'artist':
            query = "select * from library_songs where (artist = :filter or album_artist = :filter) "\
                    "order by album asc, discnumber asc, tracknumber asc, display_name asc"
        elif filter_type == 'genre':
            query = "select * from library_songs where genre = :filter "\
                    "order by album asc, discnumber asc, tracknumber asc, title asc"
        elif filter_type == 'composer':
            query = "select * from library_songs where composer = :filter "\
                    "order by album asc, discnumber asc, tracknumber asc, title asc"

        return self.curs.execute(query,{'filter':filter_criteria,'albumArtist':albumArtist}).fetchall()

    def getCriteria(self, criteria, name):
        utils.log("### storage getcriteria: "+repr(criteria)+" "+repr(name))

        if criteria == 'album':
            query = "select album_artist, album, year, artistart, max(albumart) as arturl, max(creation_date) as date "\
                    "from library_songs where album <> '-???-' group by lower(album_artist), lower(album)"
        elif criteria == 'artist' and not name:
            query = "select album_artist as criteria, max(artistart) as arturl from library_songs group by lower(album_artist)"
        elif criteria == 'artist' and name:
            query = "select album_artist, album, year, artistart,  max(albumart) as arturl, max(creation_date) as date "\
                    "from library_songs where album_artist = :name group by lower(album_artist), lower(album)"
        elif criteria == 'genre' and not name:
            query = "select genre as criteria, max(artistart) as arturl from library_songs group by lower(genre)"
        elif criteria == 'genre' and name:
            query = "select album_artist, album, year, artistart, max(albumart) as arturl , max(creation_date) as date "\
                    "from library_songs where album <> '-???-' and genre=:name group by lower(album_artist), lower(album)"
        elif name:
            query = "select album_artist, album, year, artistart, max(albumart) as arturl, max(creation_date) as date "\
                    "from library_songs where %s=:name group by lower(album_artist), lower(album)" % criteria
        else:
            query = "select %s as criteria, max(albumart) as arturl from library_songs group by lower(%s)" % (criteria, criteria)

        return self.curs.execute(query,{'name':name.decode('utf8')}).fetchall()

    def getPlaylists(self):
        return self.curs.execute("SELECT playlist_id, name, arturl FROM playlists ORDER BY name").fetchall()

    def getAutoPlaylistSongs(self,playlist):
        querys = {'thumbsup':'SELECT * FROM songs WHERE rating > 3 ORDER BY display_name',
                  'lastadded':'SELECT * FROM songs ORDER BY creation_date desc LIMIT 500',
                  'mostplayed':'SELECT * FROM songs ORDER BY playcount desc LIMIT 500',
                  'freepurchased':'SELECT * FROM songs WHERE type = 6 order by creation_date desc',
                  'feellucky':'SELECT * FROM songs ORDER BY random() LIMIT 500',
                  'videos':'SELECT * FROM songs WHERE videoid IS NOT NULL ORDER BY display_name',
                 }
        return self.curs.execute(querys[playlist]).fetchall()

    def getSong(self, song_id):
        return self.curs.execute("SELECT title,artist,album,year,tracknumber,rating,albumart,artistart,stream_url as url "+
                                 "FROM songs WHERE song_id = ? ", (song_id,)).fetchone()

    def getVideo(self, title):
        return self.curs.execute("SELECT videoid FROM songs WHERE display_name like ? ", ('%'+title+'%',)).fetchone()["videoid"]

    def getArtist(self, artist_id):
        artist = self.curs.execute("SELECT artistart FROM artists WHERE artist_id = ? ", (artist_id,)).fetchone()
        return artist['artistart'] if artist else ''

    def setArtist(self, artist_id, artistart):
        self.curs.execute("INSERT OR REPLACE INTO artists VALUES (:artist_id, :artistart)" , (artist_id, artistart))
        self.conn.commit()

    def getSearch(self, query, max_results=10):
        query = '%'+ query.replace('%','') + '%'
        result = {}
        result['artists'] = self.curs.execute("SELECT artist as name, max(artistart) as artistArtRef FROM songs WHERE artist like ? GROUP BY artist LIMIT %s" % max_results, (query,)).fetchall()
        result['tracks'] = self.curs.execute("SELECT * FROM songs WHERE display_name like ? ORDER BY display_name LIMIT %s" % max_results, (query,)).fetchall()
        result['albums'] = self.curs.execute("SELECT album as name, artist, artistart, max(albumart) as albumart FROM songs WHERE album like ? or album_artist like ? GROUP BY album, artist LIMIT %s" % max_results, (query,query)).fetchall()
        return result

    def storePlaylistSongs(self, playlists_songs):
        self.curs.execute("PRAGMA foreign_keys = OFF")

        self.curs.execute("DELETE FROM playlists_songs")
        self.curs.execute("DELETE FROM playlists")

        api_songs = []

        for playlist in playlists_songs:
            #utils.log(repr(playlist))
            playlistId = playlist['id']
            if len(playlist['name']) > 0:
                arturl = utils.addon.getAddonInfo('icon')
                if playlist['tracks']:
                    song = self.getSong(playlist['tracks'][0]['trackId'])
                    if song and song['albumart']:
                        arturl = song['albumart']
                self.curs.execute("INSERT OR REPLACE INTO playlists (name, playlist_id, type, arturl) VALUES (?, ?, 'user', ?)", (playlist['name'], playlistId, arturl) )
                for entry in playlist['tracks']:
                    self.curs.execute("INSERT OR REPLACE INTO playlists_songs (playlist_id, song_id, entry_id ) VALUES (?, ?, ?)", (playlistId, entry['trackId'], entry['id']))
                    if entry.has_key('track'):
                        api_songs.append(entry['track'])

        self.conn.commit()
        self.storeInAllSongs(api_songs)

    def storeInAllSongs(self, api_songs):
        self.curs.execute("PRAGMA foreign_keys = OFF")

        default_albumart  = [{"url": utils.addon.getAddonInfo('icon')}]
        default_artistart = [{"url": utils.addon.getAddonInfo('fanart')}]

        def artists():
          for api_song in api_songs:
              get = api_song.get
              if not get("artistId") or not get("artistArtRef"): continue
              yield {
                  'artist_id': get("artistId")[0],
                  'artistart': get("artistArtRef")[0]['url'],
              }
        self.curs.executemany("INSERT OR REPLACE INTO artists VALUES (:artist_id, :artistart)", artists())

        #for i in range(5):
        def songs():
          for api_song in api_songs:
              get = api_song.get
              yield {
                  'song_id':       get("id", get("storeId", get("trackId"))), #+str(i),
                  'comment':       get("comment", ""),
                  'rating':        get("rating"),
                  'last_played':   get("recentTimestamp"),
                  'discnumber':    get("discNumber"),
                  'composer':      get("composer") if get("composer") else '-???-',
                  'year':          get("year"),
                  'album':         get("album") if get("album") else '-???-',
                  'title':         get("title", get("name","")),
                  'album_artist':  get("albumArtist") if get("albumArtist") else get("artist") if get("artist") else '-???-',
                  'type':          get("trackType"),
                  'tracknumber':   get("trackNumber" ),
                  'total_tracks':  get("totalTrackCount"),
                  'genre':         get("genre", '-???-'),
                  'playcount':     get("playCount"),
                  'creation_date': get("creationTimestamp"),
                  'artist':        get("artist") if get("artist") else get("albumArtist") if get("albumArtist") else '-???-',
                  'total_discs':   get("totalDiscCount"),
                  'duration':      int(get("durationMillis",0))/1000,
                  'albumart':      get("albumArtRef", default_albumart)[0]['url'],
                  'display_name':  self._getSongDisplayName(api_song),
                  'stream_url':    None,
                  'artistart':     get("artistArtRef", default_artistart)[0]["url"],
                  'videoid':       get("primaryVideo",{"id":None})["id"],
              }

        self.curs.executemany("INSERT OR REPLACE INTO songs VALUES ("+
                              ":song_id, :comment, :rating, :last_played, :discnumber, :composer, :year, :album, "+
                              ":title, :album_artist, :type, :tracknumber, :total_tracks, :genre, :playcount, "+
                              ":creation_date, :artist, :total_discs, :duration, :albumart, :display_name, "+
                              ":stream_url, :artistart, :videoid)", songs())

        self.conn.commit()


    def getSongStreamUrl(self, song_id):
        song = self.curs.execute("SELECT stream_url FROM songs WHERE song_id = ?", (song_id,)).fetchone()
        return song[0]

    def incrementSongPlayCount(self, song_id):
        import time
        self.curs.execute("UPDATE songs SET playcount = playcount+1, last_played = ? WHERE song_id = ?", (int(time.time()*1000000), song_id))
        self.conn.commit()

    def addToPlaylist(self, playlist_id, song_id, entry_id):
        self.curs.execute("INSERT OR REPLACE INTO playlists_songs(playlist_id, song_id, entry_id) VALUES (?,?,?)", (playlist_id, song_id, entry_id))
        self.conn.commit()

    def delFromPlaylist(self, playlist_id, song_id):
        entry_id = self.curs.execute("SELECT entry_id FROM playlists_songs WHERE playlist_id=? and song_id=?", (playlist_id, song_id)).fetchone()
        self.curs.execute("DELETE from playlists_songs WHERE entry_id=?", (entry_id[0], ))
        self.conn.commit()
        return entry_id[0]

    def deletePlaylist(self, playlist_id):
        self.curs.execute("DELETE FROM playlists_songs WHERE playlist_id = ?", (playlist_id, ))
        self.curs.execute("DELETE FROM playlists WHERE playlist_id = ?", (playlist_id, ))
        self.conn.commit()

    def createPlaylist(self, name, playlist_id):
        self.curs.execute("INSERT OR REPLACE INTO playlists(playlist_id, name, type) VALUES (?,?,?)", (playlist_id, name, 'user'))
        self.conn.commit()

    def setThumbs(self, song_id, thumbs):
        self.curs.execute("UPDATE songs SET rating = ? WHERE song_id = ?", (thumbs, song_id))
        self.conn.commit()

    def updateSongStreamUrl(self, song_id, stream_url):
        self.curs.execute("UPDATE songs SET stream_url = ? WHERE song_id = ?", (stream_url, song_id))
        self.conn.commit()

    def _connect(self):
        self.conn = sqlite3.connect(self.path)
        self.conn.text_factory = str
        self.conn.row_factory = sqlite3.Row
        self.curs = self.conn.cursor()

    def initializeDatabase(self):
        self._connect()

        self.curs.executescript('''
            CREATE TABLE IF NOT EXISTS songs (
                song_id VARCHAR NOT NULL PRIMARY KEY,      --# 0
                comment VARCHAR,                           --# 1
                rating INTEGER NOT NULL DEFAULT 0,         --# 2
                last_played INTEGER NOT NULL DEFAULT 0,    --# 3
                discnumber INTEGER NOT NULL DEFAULT 0,     --# 4
                composer VARCHAR,                          --# 5
                year INTEGER NOT NULL DEFAULT 0,           --# 6
                album VARCHAR,                             --# 7
                title VARCHAR,                             --# 8
                album_artist VARCHAR,                      --# 9
                type INTEGER NOT NULL DEFAULT 0,           --# 10
                tracknumber INTEGER NOT NULL DEFAULT 0,    --# 11
                total_tracks INTEGER NOT NULL DEFAULT 0,   --# 12
                genre VARCHAR,                             --# 13
                playcount INTEGER NOT NULL DEFAULT 0,      --# 14
                creation_date INTEGER NOT NULL DEFAULT 0,  --# 15
                artist VARCHAR,                            --# 16
                total_discs INTEGER NOT NULL DEFAULT 0,    --# 17
                duration INTEGER NOT NULL DEFAULT 0,       --# 18
                albumart VARCHAR,                          --# 19
                display_name VARCHAR,                      --# 20
                stream_url VARCHAR,                        --# 21
                artistart VARCHAR,                         --# 22
                videoid VARCHAR                            --# 23
            );
            CREATE TABLE IF NOT EXISTS playlists (
                playlist_id VARCHAR NOT NULL PRIMARY KEY,
                name VARCHAR,
                type VARCHAR,
                arturl VARCHAR
            );
            CREATE TABLE IF NOT EXISTS playlists_songs (
                playlist_id VARCHAR,
                song_id VARCHAR,
                entry_id VARCHAR,
                FOREIGN KEY(playlist_id) REFERENCES playlists(playlist_id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS artists (
                artist_id VARCHAR NOT NULL PRIMARY KEY,
                artistart VARCHAR
            );
            CREATE VIEW IF NOT EXISTS library_songs AS SELECT * FROM SONGS WHERE type <> 7;
            CREATE INDEX IF NOT EXISTS playlistindex ON playlists_songs(playlist_id);
            CREATE INDEX IF NOT EXISTS songindex ON playlists_songs(song_id);
            CREATE INDEX IF NOT EXISTS songinfoindex ON songs(album,artist,genre,album_artist,type);
        ''')

        self.conn.commit()

    def _getSongDisplayName(self, api_song):
        displayName = "-???-"
        song_name = api_song.get("title")
        song_artist = api_song.get("artist")

        if song_artist :
            displayName = song_artist.strip()
            if song_name:
                displayName += " - " + song_name.strip()
        elif song_name :
            displayName = song_name.strip()

        return displayName

    def loadKodiLib(self):
        # find last kodi music file db
        import glob
        utils.log("Start local kodi library import")

        lastVersionDb = None
        for file in glob.glob(os.path.join(xbmc.translatePath("special://database"), 'MyMusic*.db')):
            if not lastVersionDb:
                lastVersionDb = file
            elif int(file[-5:-3]) > int(lastVersionDb[-5:-3]):
                lastVersionDb = file
            #utils.log("File: %s , LastDB: %s" % (file, lastVersionDb))

        # load all songs from kodi library
        conn = sqlite3.connect(lastVersionDb)
        conn.text_factory = str
        conn.row_factory = sqlite3.Row

        query = '''SELECT 'kodi'||idSong as song_id, comment, rating, lastplayed as last_played,
                       0 as discNumber, '' as composer, song.iYear as year, strAlbum as album,
                       strTitle as title, album.strArtists as album_artist, '99' as type,
                       iTrack as tracknumber, 0 as total_tracks, song.strGenres as genre,
                       iTimesPlayed as playcount, album.lastScraped as creation_date,
                       song.strArtists as artist, 0 as total_discs, iDuration as duration,
                       a1.url as albumart, strArtist||' - '||strTitle as display_name,
                       strPath||strFileName as stream_url, a2.url as artistart, '' as videoid
                   FROM song, artist, album, path
                       left join art a1 on album.idAlbum = a1.media_id and a1.media_type = 'album'
                       left join art a2 on artist.idArtist = a2.media_id and a2.media_type = 'artist'
                   WHERE song.idalbum = album.idalbum and song.strArtists = artist.strArtist and song.idPath = path.idPath'''
        kodiSongs = conn.cursor().execute(query).fetchall()

        # check for repeated songs (same title, artist and album)
        uniqSongs = []
        uniqQuery = "select 1 from songs where lower(title) = lower(?) and lower(artist) = lower(?) and lower(album) = lower(?)"
        for song in kodiSongs:
            exists = self.curs.execute(uniqQuery, (song['title'], song['artist'], song['album'])).fetchall()
            #utils.log(repr(exists))
            if not exists:
                #utils.log(repr(song))
                uniqSongs.append(song)

        utils.log("%d uniq songs to import from Kodi library" % len(uniqSongs))

        self.curs.executemany("INSERT OR REPLACE INTO songs VALUES ("+
                              ":song_id, :comment, :rating, :last_played, :discnumber, :composer, :year, :album, "+
                              ":title, :album_artist, :type, :tracknumber, :total_tracks, :genre, :playcount, "+
                              ":creation_date, :artist, :total_discs, :duration, :albumart, :display_name, "+
                              ":stream_url, :artistart, :videoid)", uniqSongs)

        self.conn.commit()


storage = GoogleMusicStorage()
