import sys

class GoogleMusicPlaySong():

    def __init__(self):
        self.xbmcplugin = sys.modules["__main__"].xbmcplugin
        self.xbmcgui = sys.modules["__main__"].xbmcgui
        self.api = sys.modules["__main__"].api

    def play(self, song_id):
        song = self.api.getSong(song_id)
        url = self.api.getSongStreamUrl(song_id)

        li = self.createItem(song)
        li.setPath(url)

        self.xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=True, listitem=li)

    def createItem(self, song):
        coverURL = ""
        if song[22]:
            coverURL = "http:" + song[22]

        infoLabels = {
            'tracknumber': song[11],
            'duration': song[21] / 1000,
            'year': song[6],
            'genre': song[14].encode('utf-8'),
            'album': song[7].encode('utf-8'),
            'artist': song[18].encode('utf-8'),
            'title': song[8].encode('utf-8'),
            'playcount': song[15]
        }

        li = self.xbmcgui.ListItem(label=song[23], iconImage=coverURL, thumbnailImage=coverURL)
        li.setProperty('IsPlayable', 'true')
        li.setProperty('Music', 'true')
        li.setProperty('mimetype', 'audio/mpeg')
        li.setInfo(type='music', infoLabels=infoLabels)

        return li
