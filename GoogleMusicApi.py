import sys

class GoogleMusicApi():
    def __init__(self):
        self.main      = sys.modules["__main__"]
        self.storage   = self.main.storage
        self.api       = None
        self.device    = None
        self.login     = None
        
    def getApi(self):
        if self.api == None :
            import GoogleMusicLogin
            self.login = GoogleMusicLogin.GoogleMusicLogin()
            self.login.login()
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
        self.main.log("First Song: "+repr(api_songs[0]))
        self.storage.storeApiSongs(api_songs, 'all_songs')

    def updatePlaylistSongs(self, playlist_id):
        if self.getDevice():
            self.storage.storePlaylistSongs(self.api.get_all_user_playlist_contents())
        else:
            self.storage.storeApiSongs(self.api.get_playlist_songs(playlist_id), playlist_id)

    def updatePlaylists(self, playlist_type):
        if self.getDevice():
            self.storage.storePlaylistSongs(self.api.get_all_user_playlist_contents())
        else:
            playlists = self.api.get_all_playlist_ids(playlist_type)
            self.storage.storePlaylists(playlists[playlist_type], playlist_type)

    def getSongStreamUrl(self, song_id):
        device_id = self.getDevice()
        self.main.log("getSongStreamUrl device: "+device_id)

        if device_id:
            stream_url = self.api.get_stream_url(song_id, device_id)
        else:
            streams = self.api.get_stream_urls(song_id)
            if len(streams) > 1:
                self.main.xbmc.executebuiltin("XBMC.Notification("+plugin+",'All Access track not playable')")
                raise Exception('All Access track not playable, no mobile device found in account!')
            stream_url = streams[0]

        self.storage.updateSongStreamUrl(song_id, stream_url)
        self.main.log("getSongStreamUrl: "+stream_url)
        return stream_url

    def getFilterSongs(self, filter_type, filter_criteria):
        return self.storage.getFilterSongs(filter_type, filter_criteria)

    def getCriteria(self, criteria, artist=''):
        return self.storage.getCriteria(criteria,artist)

    def getSearch(self, query):
        return self.storage.getSearch(query)

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