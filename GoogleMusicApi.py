import sys

class GoogleMusicApi():
    def __init__(self):
        self.main      = sys.modules["__main__"]
        self.storage   = self.main.storage
        self.api       = None
        self.device    = None
        self.login     = None
        
    def getApi(self,nocache=False):
        if self.api == None :
            import GoogleMusicLogin
            self.login = GoogleMusicLogin.GoogleMusicLogin()
            self.login.login(nocache)
            self.api = self.login.getApi()
            self.device = self.login.getDevice()
        return self.api

    def getDevice(self):
        if self.device == None:
            self.getApi()
        return self.device

    def getLogin(self):
        if self.login == None:
            self.getApi()
        return self.login
                
    def getPlaylistSongs(self, playlist_id, forceRenew=False):
        if playlist_id in ('thumbsup','lastadded','mostplayed','freepurchased','feellucky'):
            return self.storage.getAutoPlaylistSongs(playlist_id)

        if not self.storage.isPlaylistFetched(playlist_id) or forceRenew:
            self.updatePlaylistSongs(playlist_id)

        songs = self.storage.getPlaylistSongs(playlist_id)

        return songs

    def getPlaylistsByType(self, playlist_type, forceRenew=False):
        if playlist_type == 'auto':
            return [['thumbsup','Highly Rated'],['lastadded','Last Added'],
                    ['freepurchased','Free and Purchased'],['mostplayed','Most Played']]

        if forceRenew:
            self.updatePlaylists(playlist_type)

        playlists = self.storage.getPlaylists()
        if len(playlists) == 0 and not forceRenew:
            self.updatePlaylists(playlist_type)
            playlists = self.storage.getPlaylists()

        return playlists

    def getSong(self, song_id):
        return self.storage.getSong(song_id)
        
    def loadLibrary(self):
        #gen = self.gmusicapi.get_all_songs(incremental=True)
        #for chunk in gen:
        #    for song in chunk:
                #print song
        #        api_songs.append(song)
        #    break
        #api_songs = [song for chunk in api_songs for song in chunk]
        api_songs = self.getApi().get_all_songs()
        self.main.log("Library Size: "+repr(len(api_songs)))
        #self.main.log("First Song: "+repr(api_songs[0]))
        self.storage.storeApiSongs(api_songs, 'all_songs')

    def updatePlaylistSongs(self, playlist_id):
        self.storage.storePlaylistSongs(self.getApi().get_all_user_playlist_contents())

    def updatePlaylists(self, playlist_type):
        self.storage.storePlaylistSongs(self.getApi().get_all_user_playlist_contents())

    def getSongStreamUrl(self, song_id):
        # using cached cookies fails with all access tracks
        self.getApi()

        stream_url = self.login.getStreamUrl(song_id)
        self.storage.updateSongStreamUrl(song_id, stream_url)
        self.main.log("getSongStreamUrl: "+stream_url)
        return stream_url
        
    def incrementSongPlayCount(self, song_id):
        try:
            self.getApi().increment_song_playcount(song_id)
        except Exception as ex:
            self.main.log("ERROR trying to increment playcount: "+repr(ex))
            pass
        self.storage.incrementSongPlayCount(song_id)

    def getFilterSongs(self, filter_type, filter_criteria, artist):
        return self.storage.getFilterSongs(filter_type, filter_criteria, artist)

    def getCriteria(self, criteria, artist=''):
        return self.storage.getCriteria(criteria,artist)

    def getSearch(self, query):
        tracksAA = []
        tracksLib = self.storage.getSearch(query)
        albums = []
        artists = []
        result = {}
        try:
            aaresult = self.getApi().search_all_access(query)
            for song in aaresult['song_hits']:
                track = song['track']
                self.main.log("RESULT: "+track['artist']+" - "+track['title'])
                tracksAA.append([track['nid'],'',0,0,track['discNumber'],'',0,track['album'],
                               track['title'],track['albumArtist'],track['trackType'],
                               track['trackNumber'],0,0,'',track.get('playCount', 0),0,track['title'],
                               track['artist'],'',0,int(track['durationMillis'])/1000,
                               track['albumArtRef'][0]['url'],track['artist']+" - "+track['title'],''])
            for album in aaresult['album_hits']:
                albums.append([album['album']['name'],album['album']['artist']])
            for artist in aaresult['artist_hits']:
                artists.append(artist['artist']['name'])
        except Exception as e:
            self.main.log("*** NO ALL ACCESS RESULT IN SEARCH *** "+repr(e))
            #tracksAA = self.storage.getAutoPlaylistSongs('thumbsup')
        result['tracksAA'] = tracksAA
        result['tracksLib'] = tracksLib
        result['albums'] = albums
        result['artists']= artists
        return result

    def clearCache(self):
        self.storage.clearCache()
        self.clearCookie()

    def clearCookie(self):
        self.getLogin().clearCookie()

    def getStations(self):
        stations = {}
        try:
            stations = self.getApi().get_all_stations()
            #self.main.log("STATIONS: "+repr(stations))
        except Exception as e:
            self.main.log("*** NO STATIONS *** "+repr(e))
        return stations

    def getStationTracks(self, station_id):
        tracks = {}
        try:
            tracks = self.getApi().get_station_tracks(station_id)
            #self.main.log("TRACKS *** "+repr(tracks))
        except Exception as e:
            self.main.log("*** NO TRACKS *** "+repr(e))
        return tracks

    def addAAtrack(self, song_id):
        self.getApi().add_aa_track(song_id)

    def addToPlaylist(self, playlist_id, song_id):
        entry_id = self.getApi().add_songs_to_playlist(playlist_id, song_id)
        self.storage.addToPlaylist(playlist_id, song_id, entry_id[0])

    def delFromPlaylist(self, playlist_id, song_id):
        entry_id = self.storage.delFromPlaylist(playlist_id, song_id)
        self.getApi().remove_entries_from_playlist(entry_id)
