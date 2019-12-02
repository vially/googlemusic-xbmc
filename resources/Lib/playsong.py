import api
import utils
import xbmc
from storage import storage


class PlaySong:

    def __init__(self):
        self.api = api.Api()

    def play(self, params):
        song_id = params.pop('song_id')
        if song_id[0] == 't': song_id = song_id.capitalize()

        params = self.__getSongStreamUrl(song_id, params)
        url = params.pop('url')
        title = params.get('title')
        utils.log("Song: %s - %r " % (title, url))

        li = utils.createItem(title, params.pop('albumart'), params.pop('artistart'))
        li.setInfo(type='music', infoLabels=params)
        li.setPath(url)

        utils.setResolvedUrl(li)

        self.__incrementSongPlayCount(song_id)

        if utils.addon.getSettingBool("prefetch"):
            try:
                self.__prefetchUrl()
            except Exception as ex:
                utils.log("ERROR trying to fetch url: " + repr(ex))

    def __incrementSongPlayCount(self, song_id):
        xbmc.sleep(5000)
        self.api.incrementSongPlayCount(song_id)

    def __getSongStreamUrl(self, song_id, params):
        # try to fetch from memory first
        params['url'] = utils.get_mem_cache(song_id)

        # if no metadata
        if 'title' not in params:
            song = storage.getSong(song_id)
            if not song:
                # fetch from web
                song = self.api.getTrack(song_id)
            params['title'] = song['title']
            params['artist'] = song['artist']
            params['albumart'] = song['albumart']
            params['artistart'] = song['artistart']
            params['tracknumber'] = song['tracknumber']
            params['album'] = song['album']
            params['year'] = song['year']
            params['rating'] = song['rating']

        # check if not expired before returning
        if params['url']:
            import time
            if int(utils.paramsToDict(params['url']).get('expire', 0)) < time.time():
                params['url'] = ''

        if not params['url']:
            # try to fetch from web
            params['url'] = self.api.getSongStreamUrl(song_id, session_token=params.pop('sessiontoken', None),
                                                      wentry_id=params.pop('wentryid', None))

        return params

    def __prefetchUrl(self):
        import json
        jsonGetPlaylistPos = '{"jsonrpc":"2.0", "method":"Player.GetProperties", "params":{"playerid":0,"properties":["playlistid","position","percentage"]},"id":1}'
        jsonGetPlaylistItems = '{"jsonrpc":"2.0", "method":"Playlist.GetItems",    "params":{"playlistid":0,"properties":["file","duration"]}, "id":1}'

        # get song position in playlist
        playerProperties = json.loads(xbmc.executeJSONRPC(jsonGetPlaylistPos))
        while 'result' not in playerProperties or playerProperties['result']['percentage'] > 5:
            # wait for song playing and playlist ready
            xbmc.sleep(1000)
            playerProperties = json.loads(xbmc.executeJSONRPC(jsonGetPlaylistPos))

        position = playerProperties['result']['position']
        utils.log("position:" + str(position) + " percentage:" + str(playerProperties['result']['percentage']))

        # get next song id and fetch url
        playlistItems = json.loads(xbmc.executeJSONRPC(jsonGetPlaylistItems))
        # utils.log("playlistItems:: "+repr(playlistItems))

        if 'items' not in playlistItems['result']:
            utils.log("empty playlist")
            return

        if position + 1 >= len(playlistItems['result']['items']):
            utils.log("playlist end:: position " + repr(position) + " size " + repr(len(playlistItems['result']['items'])))
            return

        song_id_next = utils.paramsToDict(playlistItems['result']['items'][position + 1]['file']).get("song_id")

        stream_url = self.api.getSongStreamUrl(song_id_next)
        utils.set_mem_cache(song_id_next, stream_url)

        # stream url expires in 1 minute, refetch to always have a valid one
        while True:
            xbmc.sleep(50000)

            # test if music changed
            playerProperties = json.loads(xbmc.executeJSONRPC(jsonGetPlaylistPos))
            utils.log("playerProperties:: " + repr(playerProperties))
            if 'result' not in playerProperties or position != playerProperties['result']['position']:
                utils.log("ending:: position " + repr(position) + " " + repr(playerProperties))
                break

            # before the stream url expires we fetch it again
            stream_url = self.api.getSongStreamUrl(song_id_next)
            utils.set_mem_cache(song_id_next, stream_url)
