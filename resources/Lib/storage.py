import os
import sqlite3
import utils
import xbmc


class Storage:
    def __init__(self):
        self.path = os.path.join(xbmc.translatePath(utils.addon.getAddonInfo('profile')).decode('utf-8'), 'gpmusic.db')
        self._connect()

    def clearCache(self):
        if os.path.isfile(self.path):
            if self.conn: self.conn.close()
            try:
                os.remove(self.path)
            except Exception as ex:
                utils.log("Error trying to delete database " + repr(ex))
                self._connect()
        utils.addon.setSettingInt("fetched_time", 0)

    def getPlaylistSongs(self, playlist_id):
        if playlist_id == 'all_songs':
            query = "SELECT * FROM songs ORDER BY display_name"
        elif playlist_id == 'shuffled_albums':
            self.curs.execute(
                'CREATE TABLE shuffled_albums AS SELECT album, album_artist FROM songs GROUP BY album, album_artist ORDER BY RANDOM()')
            res = self.curs.execute('''
                SELECT songs.* FROM shuffled_albums LEFT JOIN songs ON songs.album = shuffled_albums.album AND songs.album_artist = shuffled_albums.album_artist
                ORDER BY shuffled_albums.rowid, songs.discnumber, songs.tracknumber
            ''').fetchall()

            self.curs.execute('DROP TABLE shuffled_albums')
            return res
        else:
            query = "SELECT * FROM songs " \
                    "INNER JOIN playlists_songs ON songs.song_id = playlists_songs.song_id " \
                    "WHERE playlists_songs.playlist_id = :id"
        return self.curs.execute(query, {'id': playlist_id}).fetchall()

    def getFilterSongs(self, filter_type, filter_criteria, albumArtist):
        query = ""
        utils.log("### storage getfiltersongs: " + repr(filter_type) + " " + repr(filter_criteria) + " " + repr(albumArtist))

        if albumArtist:
            query = "select * from library_songs where album = :filter and album_artist = :albumArtist " \
                    "order by discnumber asc, tracknumber asc, display_name asc"
        elif filter_type == 'album':
            query = "select * from library_songs where album = :filter " \
                    "order by discnumber asc, tracknumber asc, display_name asc"
        elif filter_type == 'artist':
            query = "select * from library_songs where (artist = :filter or album_artist = :filter) " \
                    "order by album asc, discnumber asc, tracknumber asc, display_name asc"
        elif filter_type == 'genre':
            query = "select * from library_songs where genre = :filter " \
                    "order by album asc, discnumber asc, tracknumber asc, title asc"
        elif filter_type == 'composer':
            query = "select * from library_songs where composer = :filter " \
                    "order by album asc, discnumber asc, tracknumber asc, title asc"

        return self.curs.execute(query, {'filter': filter_criteria, 'albumArtist': albumArtist}).fetchall()

    def getCriteria(self, criteria, name):
        utils.log("### storage get criteria: " + repr(criteria) + " " + repr(name))

        if criteria == 'album':
            query = "select album_artist, album, year, artistart, max(albumart) as arturl, max(creation_date) as date " \
                    "from library_songs where album <> '-???-' and length(album)>1 group by lower(album_artist), lower(album)"
        elif criteria == 'artist' and not name:
            query = "select album_artist as criteria, max(artistart) as arturl from library_songs "\
                    "where length(album_artist)>1 group by lower(album_artist)"
        elif criteria == 'artist' and name:
            query = "select album_artist, album, year, artistart,  max(albumart) as arturl, max(creation_date) as date " \
                    "from library_songs where album_artist = :name group by lower(album_artist), lower(album)"
        elif criteria == 'genre' and not name:
            query = "select genre as criteria, max(artistart) as arturl from library_songs " \
                    "where length(genre)>1 group by lower(genre)"
        elif criteria == 'genre' and name:
            query = "select album_artist, album, year, artistart, max(albumart) as arturl , max(creation_date) as date " \
                    "from library_songs where album <> '-???-' and genre=:name group by lower(album_artist), lower(album)"
        elif name:
            query = "select album_artist, album, year, artistart, max(albumart) as arturl, max(creation_date) as date " \
                    "from library_songs where %s=:name group by lower(album_artist), lower(album)" % criteria
        else:
            query = "select %s as criteria, max(albumart) as arturl from library_songs group by lower(%s)" % (criteria, criteria)

        return self.curs.execute(query, {'name': name.decode('utf8')}).fetchall()

    def getPlaylists(self):
        return self.curs.execute("SELECT playlist_id, name, arturl, token, recent FROM playlists ORDER BY name").fetchall()

    def getRecentPlaylists(self):
        return self.curs.execute("SELECT playlist_id, name, arturl, token, recent FROM playlists ORDER BY recent desc LIMIT 10").fetchall()

    def getAutoPlaylistSongs(self, playlist):
        querys = {'thumbsup': 'SELECT * FROM songs WHERE rating > 3 ORDER BY display_name',
                  'lastadded': 'SELECT * FROM songs ORDER BY creation_date desc LIMIT 500',
                  'mostplayed': 'SELECT * FROM songs ORDER BY playcount desc LIMIT 500',
                  'freepurchased': 'SELECT * FROM songs WHERE type = 6 order by creation_date desc',
                  'feellucky': 'SELECT * FROM songs ORDER BY random() LIMIT 500',
                  'videos': 'SELECT * FROM songs WHERE videoid IS NOT NULL ORDER BY display_name',
                  }
        return self.curs.execute(querys[playlist]).fetchall()

    def getSong(self, song_id):
        return self.curs.execute("SELECT title,artist,album,year,tracknumber,rating,albumart,artistart " +
                                 "FROM songs WHERE song_id = ? ", (song_id,)).fetchone()

    def getVideo(self, title):
        videoid = self.curs.execute("SELECT videoid FROM songs WHERE display_name like ? ", ('%' + title + '%',)).fetchone()
        return videoid['videoid'] if videoid else ''

    def getArtist(self, artist_id):
        artist = self.curs.execute("SELECT artistart FROM artists WHERE artist_id = ? ", (artist_id,)).fetchone()
        return artist['artistart'] if artist else ''

    def setArtist(self, artist_id, artistart):
        self.curs.execute("INSERT OR REPLACE INTO artists VALUES (:artist_id, :artistart)", (artist_id, artistart))
        self.conn.commit()

    def getSearch(self, query, max_results=10):
        query = '%' + query.replace('%', '') + '%'
        result = {
            'artists': self.curs.execute(
                "SELECT artist as name, max(artistart) as artistArtRef FROM songs WHERE artist like ? " +
                "GROUP BY artist LIMIT %s" % max_results, (query,)).fetchall(),
            'tracks': self.curs.execute(
                "SELECT * FROM songs WHERE display_name like ? ORDER BY display_name LIMIT %s" % max_results, (query,)).fetchall(),
            'albums': self.curs.execute(
                "SELECT album as name, artist, artistart, max(albumart) as albumart FROM songs " +
                "WHERE album like ? or album_artist like ? GROUP BY album, artist LIMIT %s" % max_results, (query, query)).fetchall()}
        return result

    def storePlaylistSongs(self, playlists_songs):
        self.curs.execute("PRAGMA foreign_keys = OFF")

        self.curs.execute("DELETE FROM playlists_songs")
        self.curs.execute("DELETE FROM playlists")

        insert1 = "INSERT OR REPLACE INTO playlists (name, playlist_id, type, arturl, token, recent) VALUES (?, ?, 'user', ?, ?, ?)"
        insert2 = "INSERT OR REPLACE INTO playlists_songs (playlist_id, song_id, entry_id ) VALUES (?, ?, ?)"

        api_songs = []

        for playlist in playlists_songs:
            # utils.log(repr(playlist))
            playlistId = playlist['id']
            if len(playlist['name']) > 0:
                arturl = utils.addon.getAddonInfo('icon')
                # if playlist['tracks']:
                for track in playlist['tracks']:
                    song = self.getSong(track['trackId'])
                    if song and song['albumart']:
                        arturl = song['albumart']
                        break
                self.curs.execute(insert1, (playlist['name'], playlistId, arturl, playlist.get('shareToken'), playlist.get('recentTimestamp')))
                for entry in playlist['tracks']:
                    self.curs.execute(insert2, (playlistId, entry['trackId'], entry['id']))
                    if entry.has_key('track'):
                        api_songs.append(entry['track'])

        self.conn.commit()
        self.storeInAllSongs(api_songs)

    def storeInAllSongs(self, api_songs):
        self.curs.execute("PRAGMA foreign_keys = OFF")

        default_albumart = [{"url": utils.addon.getAddonInfo('icon')}]
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

        def songs():
            for api_song in api_songs:
                get = api_song.get
                yield {
                    'song_id': get("id", get("storeId", get("trackId"))),
                    'comment': get("comment", ""),
                    'rating': get("rating"),
                    'last_played': get("recentTimestamp"),
                    'discnumber': get("discNumber"),
                    'composer': get("composer", '-???-'),
                    'year': get("year"),
                    'album': get("album", '-???-'),
                    'title': get("title", get("name", "")),
                    'album_artist': get("albumArtist", get("artist", '-???-')),
                    'type': get("trackType"),
                    'tracknumber': get("trackNumber"),
                    'genre': get("genre", '-???-'),
                    'playcount': get("playCount"),
                    'creation_date': get("creationTimestamp"),
                    'artist': get("artist", get("albumArtist", '-???-')),
                    'duration': int(get("durationMillis", 0)) / 1000,
                    'albumart': get("albumArtRef", default_albumart)[0]['url'],
                    'display_name': self._get_display_name(api_song),
                    'artistart': get("artistArtRef", default_artistart)[0]["url"],
                    'videoid': get("primaryVideo", {"id": None})["id"],
                }

        self.curs.executemany("INSERT OR REPLACE INTO songs VALUES (" +
                              ":song_id, :comment, :rating, :last_played, :discnumber, :composer, :year, :album, " +
                              ":title, :album_artist, :type, :tracknumber, :genre, :playcount, " +
                              ":creation_date, :artist,  :duration, :albumart, :display_name, " +
                              ":artistart, :videoid)", songs())

        self.conn.commit()
        # utils.log("Songs Stored: "+repr(len(api_songs)))

    def incrementSongPlayCount(self, song_id):
        import time
        self.curs.execute("UPDATE songs SET playcount = playcount+1, last_played = ? WHERE song_id = ?",
                          (int(time.time() * 1000000), song_id))
        self.conn.commit()

    def addToPlaylist(self, playlist_id, song_id, entry_id):
        self.curs.execute("INSERT OR REPLACE INTO playlists_songs(playlist_id, song_id, entry_id) VALUES (?,?,?)",
                          (playlist_id, song_id, entry_id))
        self.conn.commit()

    def delFromPlaylist(self, playlist_id, song_id):
        entry_id = self.curs.execute("SELECT entry_id FROM playlists_songs WHERE playlist_id=? and song_id=?",
                                     (playlist_id, song_id)).fetchone()
        self.curs.execute("DELETE from playlists_songs WHERE entry_id=?", (entry_id[0],))
        self.conn.commit()
        return entry_id[0]

    def deletePlaylist(self, playlist_id):
        self.curs.execute("DELETE FROM playlists_songs WHERE playlist_id = ?", (playlist_id,))
        self.curs.execute("DELETE FROM playlists WHERE playlist_id = ?", (playlist_id,))
        self.conn.commit()

    def createPlaylist(self, name, playlist_id):
        self.curs.execute("INSERT OR REPLACE INTO playlists(playlist_id, name, type) VALUES (?,?,?)",
                          (playlist_id, name, 'user'))
        self.conn.commit()

    def setThumbs(self, song_id, thumbs):
        self.curs.execute("UPDATE songs SET rating = ? WHERE song_id = ?", (thumbs, song_id))
        self.conn.commit()

    def _connect(self):
        self.conn = sqlite3.connect(self.path)
        self.conn.text_factory = str
        self.conn.row_factory = sqlite3.Row
        self.curs = self.conn.cursor()

    def init_database(self):
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
                genre VARCHAR,                             --# 12
                playcount INTEGER NOT NULL DEFAULT 0,      --# 13
                creation_date INTEGER NOT NULL DEFAULT 0,  --# 14
                artist VARCHAR,                            --# 15
                duration INTEGER NOT NULL DEFAULT 0,       --# 16
                albumart VARCHAR,                          --# 17
                display_name VARCHAR,                      --# 18
                artistart VARCHAR,                         --# 19
                videoid VARCHAR                            --# 20
            );
            CREATE TABLE IF NOT EXISTS playlists (
                playlist_id VARCHAR NOT NULL PRIMARY KEY,
                name VARCHAR,
                type VARCHAR,
                arturl VARCHAR,
                token VARCHAR,
                recent INTEGER
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
        ''')

        self.conn.commit()

    def init_indexes(self):
        self.curs.executescript('''
            CREATE VIEW IF NOT EXISTS library_songs AS SELECT * FROM SONGS WHERE type <> 7;
            CREATE INDEX IF NOT EXISTS playlistindex ON playlists_songs(playlist_id);
            CREATE INDEX IF NOT EXISTS songindex ON playlists_songs(song_id);
            CREATE INDEX IF NOT EXISTS songinfoindex ON songs(album,artist,genre,album_artist,type);
        ''')
        self.conn.commit()

    def _get_display_name(self, api_song):
        displayName = "-???-"
        song_name = api_song.get("title")
        song_artist = api_song.get("artist")

        if song_artist:
            displayName = song_artist.strip()
            if song_name:
                displayName += " - " + song_name.strip()
        elif song_name:
            displayName = song_name.strip()

        return displayName


storage = Storage()
