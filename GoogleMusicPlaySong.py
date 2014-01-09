import sys, time

class GoogleMusicPlaySong():

    def __init__(self):
        self.main       = sys.modules["__main__"]
        self.xbmcgui    = self.main.xbmcgui

    def play(self, song_id, params={}):
        song = self.main.storage.getSong(song_id)
        prefetch = self.main.settings.getSetting( "prefetch" )

        if song:
            if prefetch=="false" or not song[24] or int(self.main.parameters_string_to_dict(song[24]).get('expire'))  < time.time():
                 self.main.log("Prefetch disabled or URL invalid or expired :")
                 url = self.__getSongStreamUrl(song_id)
            else:
                 url = song[24]

            li = self.createItem(song)
        else:
            self.main.log("Track not in library :: "+repr(params))
            if params:
                label=params.get('title')
            li = self.xbmcgui.ListItem(label)
            li.setProperty('IsPlayable', 'true')
            li.setProperty('Music', 'true')
            url = self.__getSongStreamUrl(song_id)

        self.main.log("URL :: "+repr(url))

        li.setPath(url)
        self.main.xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=True, listitem=li)

        if prefetch=="true":
            try:
                self.__prefetchUrl()
            except Exception as ex:
                self.main.log("ERROR trying to fetch url: "+repr(ex))
                #raise

    def __getSongStreamUrl(self,song_id):
        import GoogleMusicApi
        self.api = GoogleMusicApi.GoogleMusicApi()
        return self.api.getSongStreamUrl(song_id)

    def createItem(self, song, label=None):
        infoLabels = {
            'tracknumber': song[11],
            'duration': song[21],
            'year': song[6],
            'genre': song[14],
            'album': song[7],
            'artist': song[18],
            'title': song[8],
            'playcount': song[15]
        }

        if not label:
            label = song[23]

        if song[22]:
            li = self.xbmcgui.ListItem(label, iconImage=song[22], thumbnailImage=song[22])
        else:
            li = self.xbmcgui.ListItem(label)
        li.setProperty('IsPlayable', 'true')
        li.setProperty('Music', 'true')
        li.setProperty('mimetype', 'audio/mpeg')
        li.setInfo(type='music', infoLabels=infoLabels)

        return li

    def __prefetchUrl(self):
        import gmusicapi.compat as compat
        loadJson = compat.json.loads
        xbmc     = self.main.xbmc
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
            self.main.log("playlist end:: position "+repr(position)+" size "+len(playlistItems['result']['items']))
            return

        song_id_next = self.main.parameters_string_to_dict(playlistItems['result']['items'][position+1]['file']).get("song_id")
        self.__getSongStreamUrl(song_id_next)

        # get playing song duration
        duration = playlistItems['result']['items'][position]['duration']

        # stream url expires in 1 minute, refetch to always have a valid one
        while duration > 50:
            xbmc.sleep(50000)
            duration = duration - 50

            # test if music changed
            playerProperties = loadJson(xbmc.executeJSONRPC(jsonGetPlaylistPos))
            if not 'result' in playerProperties or position != playerProperties['result']['position']:
                self.main.log("ending:: position "+repr(position)+" "+repr(playerProperties))
                break

            # before the stream url expires we fetch it again
            self.__getSongStreamUrl(song_id_next)
