import sys, time

class GoogleMusicPlaySong():

    def __init__(self):
        self.main       = sys.modules["__main__"]

    def play(self, params):
        prefetch = self.main.settings.getSetting( "prefetch" )
        song_id = params.pop('song_id')
        song = []
        if prefetch == "true":
            song = self.main.storage.getSong(song_id)

        if not song or not song[0] or int(self.main.parameters_string_to_dict(song[0]).get('expire'))  < time.time():
            self.main.log("Prefetch disabled or URL invalid or expired :")
            url = self.__getSongStreamUrl(song_id)
        else:
            url = song[0]

        params.pop('action')
        li = self.main.xbmcgui.ListItem(params.get('title'))
        li.setProperty('IsPlayable', 'true')
        li.setProperty('Music', 'true')
        li.setProperty('mimetype', 'audio/mpeg')
        li.setInfo(type='music', infoLabels=params)

        self.main.log("URL :: "+repr(url))

        li.setPath(url)
        self.main.xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=True, listitem=li)

        self.__incrementSongPlayCount(song_id)

        if prefetch == "true":
            try:
                self.__prefetchUrl()
            except Exception as ex:
                self.main.log("ERROR trying to fetch url: "+repr(ex))
                #raise

    def __incrementSongPlayCount(self, song_id):
        import xbmc
        xbmc.sleep(2000)
        import GoogleMusicApi
        api = GoogleMusicApi.GoogleMusicApi()
        api.incrementSongPlayCount(song_id)

    def __getSongStreamUrl(self, song_id):
        import GoogleMusicApi
        api = GoogleMusicApi.GoogleMusicApi()
        return api.getSongStreamUrl(song_id)

    def __prefetchUrl(self):
        import gmusicapi.compat as compat, xbmc
        loadJson = compat.json.loads
        jsonGetPlaylistPos  = '{"jsonrpc":"2.0", "method":"Player.GetProperties", "params":{"playerid":0,"properties":["playlistid","position","percentage"]},"id":1}'
        jsonGetSongDuration = '{"jsonrpc":"2.0", "method":"Playlist.GetItems",    "params":{"playlistid":0, "properties":["file","duration"]}, "id":1}'

        # get song position in playlist
        playerProperties = loadJson(xbmc.executeJSONRPC(jsonGetPlaylistPos))
        while not 'result' in playerProperties:
          #wait for song playing and playlist ready
          xbmc.sleep(1000)
          playerProperties = loadJson(xbmc.executeJSONRPC(jsonGetPlaylistPos))

        while playerProperties['result']['percentage'] > 5:
          #wait for new song playing
          xbmc.sleep(1000)
          playerProperties = loadJson(xbmc.executeJSONRPC(jsonGetPlaylistPos))

        position = playerProperties['result']['position']
        self.main.log("position:"+str(position)+" percentage:"+str(playerProperties['result']['percentage']))

        # get next song id and fetch url
        playlistItems = loadJson(xbmc.executeJSONRPC(jsonGetSongDuration))
        #self.main.log("playlistItems:: "+repr(playlistItems))

        if position+1 >= len(playlistItems['result']['items']):
            self.main.log("playlist end:: position "+repr(position)+" size "+repr(len(playlistItems['result']['items'])))
            return

        song_id_next = self.main.parameters_string_to_dict(playlistItems['result']['items'][position+1]['file']).get("song_id")
        self.__getSongStreamUrl(song_id_next)

        # stream url expires in 1 minute, refetch to always have a valid one
        while True:
            xbmc.sleep(50000)

            # test if music changed
            playerProperties = loadJson(xbmc.executeJSONRPC(jsonGetPlaylistPos))
            if not 'result' in playerProperties or position != playerProperties['result']['position']:
                self.main.log("ending:: position "+repr(position)+" "+repr(playerProperties))
                break

            # before the stream url expires we fetch it again
            self.__getSongStreamUrl(song_id_next)