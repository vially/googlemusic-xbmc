import GoogleMusicApi, utils, xbmc
from GoogleMusicStorage import storage

class GoogleMusicPlaySong():

    def __init__(self):
        self.api   = GoogleMusicApi.GoogleMusicApi()

    def play(self, params):
        song_id = params.pop('song_id')
        if song_id[0] == 't': song_id = song_id.capitalize()

        params = self.__getSongStreamUrl(song_id, params)
        url    = params.pop('url')
        title  = params.get('title')
        utils.log("Song: %s - %r " % (title, url))

        li = utils.createItem(title, params.pop('albumart'))
        li.setInfo(type='music', infoLabels=params)
        li.setPath(url)

        utils.setResolvedUrl(li)

        self.__incrementSongPlayCount(song_id)

        if utils.addon.getSetting( "prefetch" ) == "true":
            try:
                self.__prefetchUrl()
            except Exception as ex:
                utils.log("ERROR trying to fetch url: "+repr(ex))
                #raise

    def __incrementSongPlayCount(self, song_id):
        xbmc.sleep(5000)
        self.api.incrementSongPlayCount(song_id)

    def __getSongStreamUrl(self, song_id, params):
        # try to fetch from library first
        song = storage.getSong(song_id)
        if song:
            # if no metadata
            if not 'title' in params:
                params['title'] = song[17]
                params['artist'] = song[18]
                params['albumart'] = song[22]
            # if url in library check if not expired before returning
            if song[24]:
                import time
                if int(utils.paramsToDict(song[24]).get('expire')) > time.time():
                    params['url'] = song[24]
                    return params
        # try to fetch from web
        params['url'] = self.api.getSongStreamUrl(song_id)
        # if no metadata
        if not 'title' in params:
            trackinfo = self.api.getTrack(song_id)
            params['title'] = trackinfo[17]
            params['artist'] = trackinfo[18]
            params['albumart'] = trackinfo[22]

        return params

    def __prefetchUrl(self):
        import gmusicapi.compat as compat
        loadJson = compat.json.loads
        jsonGetPlaylistPos   = '{"jsonrpc":"2.0", "method":"Player.GetProperties", "params":{"playerid":0,"properties":["playlistid","position","percentage"]},"id":1}'
        jsonGetPlaylistItems = '{"jsonrpc":"2.0", "method":"Playlist.GetItems",    "params":{"playlistid":0,"properties":["file","duration"]}, "id":1}'

        # get song position in playlist
        playerProperties = loadJson(xbmc.executeJSONRPC(jsonGetPlaylistPos))
        while not 'result' in playerProperties or playerProperties['result']['percentage'] > 5:
          #wait for song playing and playlist ready
          xbmc.sleep(1000)
          playerProperties = loadJson(xbmc.executeJSONRPC(jsonGetPlaylistPos))

        position = playerProperties['result']['position']
        utils.log("position:"+str(position)+" percentage:"+str(playerProperties['result']['percentage']))

        # get next song id and fetch url
        playlistItems = loadJson(xbmc.executeJSONRPC(jsonGetPlaylistItems))
        #utils.log("playlistItems:: "+repr(playlistItems))

        if not 'items' in playlistItems['result']:
            utils.log("empty playlist")
            return

        if position+1 >= len(playlistItems['result']['items']):
            utils.log("playlist end:: position "+repr(position)+" size "+repr(len(playlistItems['result']['items'])))
            return

        song_id_next = utils.paramsToDict(playlistItems['result']['items'][position+1]['file']).get("song_id")
        stream_url = self.api.getSongStreamUrl(song_id_next)
        storage.updateSongStreamUrl(song_id_next, stream_url)

        # stream url expires in 1 minute, refetch to always have a valid one
        while True:
            xbmc.sleep(50000)

            # test if music changed
            playerProperties = loadJson(xbmc.executeJSONRPC(jsonGetPlaylistPos))
            if not 'result' in playerProperties or position != playerProperties['result']['position']:
                utils.log("ending:: position "+repr(position)+" "+repr(playerProperties))
                break

            # before the stream url expires we fetch it again
            stream_url = self.api.getSongStreamUrl(song_id_next)
            storage.updateSongStreamUrl(song_id_next, stream_url)
