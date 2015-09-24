import os, xbmc, xbmcgui, utils
import GoogleMusicApi

class GoogleMusicActions():
    def __init__(self):
        self.icon      = utils.addon.getAddonInfo('icon')
        self.song_url  = utils.addon_url+"?action=play_song&song_id=%s&title=%s&artist=%s&albumart=%s"
        self.api       = GoogleMusicApi.GoogleMusicApi()
        self.lang      = utils.addon.getLocalizedString

    def executeAction(self, action, params):
        if (action == "play_all"):
            self.playAll(params)
        elif (action == "play_all_yt"):
            titles = [song[23] for song in self._getSongs(params)]
            self.playYoutube(titles)
        elif (action == "update_playlists"):
            self.api.getPlaylistsByType(params["playlist_type"], True)
        elif (action == "clear_cache"):
            try: self.api.clearCache()
            except Exception as e:
                utils.log(repr(e))
                self.notify(self.lang(30106))
        elif (action == "clear_cookie"):
            self.api.clearCookie()
        elif (action == "add_favourite"):
            self.addFavourite(params.pop("title"),params)
        elif (action == "add_library"):
            self.api.addAAtrack(params["song_id"])
            self.notify(self.lang(30103))
        elif (action == "add_album_library"):
            for track in self.api.getAlbum(params["album_id"]):
                self.api.addAAtrack(track[0])
            self.notify(self.lang(30103))
        elif (action == "add_playlist"):
            self.addToPlaylist(params["song_id"])
        elif (action == "del_from_playlist"):
            self.api.delFromPlaylist(params["playlist_id"], params["song_id"])
        elif (action == "update_library"):
            try: self.api.clearCache()
            except Exception as e:
                utils.log(repr(e))
                self.notify(self.lang(30106))
            xbmc.executebuiltin("XBMC.RunPlugin(%s)" % utils.addon_url)
        elif (action == "reload_library"):
            self.api.loadLibrary();
        elif (action == "export_library"):
            if utils.addon.getSetting('export_path'):
                self.exportLibrary(utils.addon.getSetting('export_path'))
                self.notify(self.lang(30107))
            else:
                self.notify(self.lang(30108))
                utils.addon.openSettings()
        elif (action == "start_radio"):
            keyboard = xbmc.Keyboard(self.api.getSong(params["song_id"])[8], self.lang(30402))
            keyboard.doModal()
            if keyboard.isConfirmed() and keyboard.getText():
                self.playAll({'radio_id': self.api.startRadio(keyboard.getText(), params["song_id"])})
                xbmc.executebuiltin("ActivateWindow(10500)")
                #xbmc.executebuiltin("XBMC.RunPlugin(%s?path=station&id=%s)" % (sys.argv[0],radio_id))
        elif (action == "search_yt"):
            xbmc.executebuiltin("ActivateWindow(10025,plugin://plugin.video.youtube/search/?q=%s)" % params['title'])
        elif (action == "play_yt"):
            self.playYoutube([params.get('title')])
        elif (action == "search"):
            xbmc.executebuiltin("ActivateWindow(10501,%s/?path=search_result&query=%s)" % (utils.addon_url, params.get('filter_criteria')))
        else:
            utils.log("Invalid action: " + action)

    def notify(self, text):
        xbmc.executebuiltin("XBMC.Notification(%s,%s,5000,%s)" % (utils.plugin, utils.tryEncode(text), self.icon))

    def playAll(self, params={}):
        songs = self._getSongs(params)

        player = xbmc.Player()
        if (player.isPlaying()):
            player.stop()

        playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
        playlist.clear()

        for song in songs:
            playlist.add(self.song_url % (song[0], song[8], song[18], song[22]), utils.createItem(song[23], song[22]))

        if params.get("shuffle"):
            playlist.shuffle()

        xbmc.executebuiltin('playlist.playoffset(music , 0)')

    def playYoutube(self, titles):
        #print repr(titles)

        player = xbmc.Player()
        if (player.isPlaying()):
            player.stop()

        playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        playlist.clear()

        dp = None
        if len(titles) > 1:
            dp = xbmcgui.DialogProgress();
            dp.create('Fetching video IDs', str(len(titles))+' '+self.lang(30213).lower(), self.lang(30404))

        ytaddonurl = "plugin://plugin.video.youtube/play/?video_id=%s"
        for videoid, title in self._getVideoIDs(titles, dp):
            playlist.add(ytaddonurl % videoid, xbmcgui.ListItem(title))

        xbmc.executebuiltin('playlist.playoffset(video , 0)')

    def addToPlaylist (self, song_id):
        playlists = self.api.getPlaylistsByType('user')
        plist = [pl_name for pl_id, pl_name in playlists]
        selected = xbmcgui.Dialog().select(self.lang(30401) , plist)
        if selected > 0:
            self.api.addToPlaylist(playlists[selected][0], song_id)

    def addFavourite(self, name, params):
        import fileinput
        path = os.path.join(xbmc.translatePath("special://masterprofile"), "favourites.xml")

        url = ''
        for k,v in params.iteritems():
            url = url+'&'+unicode(k)+'='+unicode(v)

        fav = '\t<favourite name="%s" thumb="%s">ActivateWindow(10501,&quot;%s?%s&quot;,return)</favourite>'
        fav = fav % (name, xbmc.translatePath(self.icon), utils.addon_url, url[1:])

        for line in fileinput.input(path, inplace=1):
            if line.startswith('</favourites>'):
                print fav
            print line,

    def exportLibrary(self, path):
        songs = self.api.getPlaylistSongs('all_songs')
        dp = xbmcgui.DialogProgress();
        dp.create(self.lang(30403), str(len(songs))+' '+self.lang(30213).lower(), self.lang(30404))
        count = 0
        if not os.path.exists(path):
            os.mkdir(path)
        for song in songs:
            count = count + 1
            artist = self._sanitizePath(song[18])
            album  = self._sanitizePath(song[7])
            if not os.path.exists(os.path.join(path,artist)):
                os.mkdir(os.path.join(path,artist))
            if not os.path.exists(os.path.join(path,artist,album)):
                os.mkdir(os.path.join(path,artist,album))
            if not os.path.isfile(os.path.join(path,artist,'artist.nfo')) and song[25]:
                with open(os.path.join(path,artist,'artist.nfo'), "w") as nfo:
                    nfo.write('<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n')
                    nfo.write('<artist>\n\t<name>%s</name>\n\t<thumb>%s</thumb>\n</artist>' % (song[18],song[25]))
            if not os.path.isfile(os.path.join(path,artist,album,'album.nfo')) and song[22]:
                with open(os.path.join(path,artist,album,'album.nfo'), "w") as nfo:
                    nfo.write('<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n')
                    nfo.write('<album>\n\t<title>%s</title>\n\t<artist>%s</artist>\n\t<thumb>%s</thumb>\n</album>' % (song[7],song[18],song[25]))
            with open(os.path.join(path,artist,album,str(song[11])+'-'+self._sanitizePath(song[8])+'.strm'), "w") as strm:
                strm.write(self.song_url % (song[0], song[8], song[18], song[22]))
                dp.update(int(count * 100 / len(songs)))

    def _sanitizePath(self, name):
        name = "".join(i for i in name if i not in "\/:*?<>|,;$%\"\'.`")
        if len(name) > 50: name = name[:50]
        return utils.tryEncode(name).strip()

    def _getSongs(self, params):
        get = params.get

        if get('playlist_id'):
            utils.log("Loading playlist: " + get('playlist_id'))
            songs = self.api.getPlaylistSongs(get('playlist_id'))
        elif get('album_id'):
            utils.log("Loading album: " + get('album_id'))
            songs = self.api.getAlbum(get('album_id'))
        elif get('share_token'):
            import urllib
            utils.log("Loading shared playlist: " + get('share_token'))
            songs = self.api.getSharedPlaylist(urllib.unquote_plus(get('share_token')))
        elif get('artist_id'):
            utils.log("Loading artist top tracks: " + get('artist_id'))
            songs = self.api.getArtist(get('artist_id'))
        elif get('radio_id'):
            utils.log("Loading radio: " + get('radio_id'))
            songs = self.api.getStationTracks(get('radio_id'))
        else:
            songs = self.api.getFilterSongs(get('filter_type'), get('filter_criteria'), albums='')

        return songs

    def _getVideoIDs(self, titles, progress_dialog=None):
        import urllib, urllib2
        import gmusicapi.compat as compat
        loadJson = compat.json.loads

        headers = {'Host': 'www.googleapis.com',
                   'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.36 Safari/537.36',
                   #'Authorization': 'Bearer %s' % utils.addon.getSetting('mastertoken')
                   }
        params = {'part': 'id',
                  'maxResults': 1,
                  'type': 'video', #'order': 'rating', #'regionCode':'us',
                  'videoDefinition': { '0':'high','1':'standard','2':'any' } [utils.addon.getSetting('youtube.video.quality')],
                  'key': 'AIzaSyCpYQnhH6BA_wGBB79agx_32kuoq7WwTZg'
                  }
        videoids = []
        url = 'https://www.googleapis.com/youtube/v3/search?%s'
        count = 0
        for title in titles:
            if progress_dialog:
                if progress_dialog.iscanceled():
                    progress_dialog.close()
                    return videoids
                count = count +1
                progress_dialog.update(int(count * 100 / len(titles)))
            params['q'] = '%s -interview -cover -remix -album' % title.lower()
            req = urllib2.Request(url % urllib.urlencode(params), headers=headers)
            response = urllib2.urlopen(req).read()
            print repr(response)
            searchresults = loadJson(response)['items']
            if searchresults:
                videoids.append([searchresults[0]['id']['videoId'], title])

        return videoids
