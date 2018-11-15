import xbmc, xbmcplugin, utils
import GoogleMusicApi
import time
from urllib import unquote_plus, urlencode
from xbmcgui import ListItem

class GoogleMusicNavigation():
    def __init__(self):
        self.lang = utils.addon.getLocalizedString
        self.api  = GoogleMusicApi.GoogleMusicApi()

        self.main_menu = (
            {'title':self.lang(30211), 'params':{'path':"ifl"},                      'user':['library','subscriber']},
            {'title':self.lang(30219), 'params':{'path':"listennow"},                'user':['subscriber','free']},
            {'title':self.lang(30220), 'params':{'path':"topcharts"},                'user':['subscriber']},
            {'title':self.lang(30221), 'params':{'path':"newreleases"},              'user':['subscriber']},
            {'title':self.lang(30209), 'params':{'path':"library"},                  'user':['library']},
            {'title':self.lang(30222), 'params':{'path':"browse_stations"},          'user':['subscriber','free']},
            {'title':self.lang(30204), 'params':{'path':"playlists", 'type':"auto"}, 'user':['library','subscriber']},
            {'title':self.lang(30202), 'params':{'path':"playlists", 'type':"user"}, 'user':['library','subscriber']},
            {'title':self.lang(30208), 'params':{'path':"search"},                   'user':['library','subscriber']}
        )
        self.lib_menu = (
            {'title':self.lang(30203), 'params':{'path':"playlists",'type':"radio"}},
            {'title':self.lang(30210), 'params':{'path':"playlist", 'playlist_id':"feellucky"}},
            {'title':self.lang(30214), 'params':{'path':"playlist", 'playlist_id':"shuffled_albums"}},
            {'title':self.lang(30201), 'params':{'path':"playlist", 'playlist_id':"all_songs"}},
            {'title':self.lang(30205), 'params':{'path':"filter", 'criteria':"artist"}},
            {'title':self.lang(30206), 'params':{'path':"filter", 'criteria':"album"}},
            {'title':self.lang(30207), 'params':{'path':"filter", 'criteria':"genre"}},
            {'title':self.lang(30212), 'params':{'path':"filter", 'criteria':"composer"}},
        )

    def listMenu(self, params={}):
        get   = params.get
        path  = get("path", "root")
        utils.log("PATH: "+path)

        listItems = []
        view_mode_id = ''
        content = ''
        sortMethods = [xbmcplugin.SORT_METHOD_UNSORTED]

        if path == "root":
            # assemble menu depending on user info
            subscriber = int(utils.addon.getSetting('subscriber')) == 1
            library    = utils.addon.getSetting('library_songs') and int(utils.addon.getSetting('library_songs')) > 0
            utils.log("Assembling menu for subscriber=%r and library=%r" % (subscriber,library))

            for item in self.main_menu:
                user = item.pop('user')
                if (subscriber and 'subscriber' in user) or \
                   (library and 'library' in user) or \
                   (not subscriber and 'free' in user):
                    listItems.append(item)

            listItems = self.getMenuItems(listItems)

        elif path == "ifl":
            listItems = self.addSongsFromLibrary(self.api.getStationTracks("IFL"), 'library')
            content = "songs"

        elif path == "library":
            listItems = self.getMenuItems(self.lib_menu)

        elif path == "playlist":
            listItems = self.listPlaylistSongs(get("playlist_id"))
            if get("playlist_id")=='all_songs':
                sortMethods = [xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE]
            content = "songs"

        elif path == "station":
            listItems = self.addSongsFromLibrary(self.api.getStationTracks(get('id')), 'library')
            content = "songs"

        elif path == "playlists":
            listItems = self.getPlaylists(get('type'))
            view_mode_id = utils.addon.getSetting('playlists_viewid')

        elif path == "filter" and 'album' == get('criteria'):
            listItems = self.listAlbums(get('criteria'))
            sortMethods = [xbmcplugin.SORT_METHOD_ALBUM_IGNORE_THE, xbmcplugin.SORT_METHOD_VIDEO_YEAR,
                           xbmcplugin.SORT_METHOD_ARTIST, xbmcplugin.SORT_METHOD_ALBUM, xbmcplugin.SORT_METHOD_DATE]
            content = "albums"

        elif path in ["artist", "genre"] and get('name'):
            album_name = unquote_plus(get('name'))
            listItems = self.listAlbums(path, album_name)
            paramsAllSongs = {'path':"allcriteriasongs",'criteria':path,'name':album_name}
            listItems.insert(0,self.createFolder('* '+self.lang(30201), paramsAllSongs))
            sortMethods = [xbmcplugin.SORT_METHOD_ALBUM_IGNORE_THE, xbmcplugin.SORT_METHOD_VIDEO_YEAR,
                           xbmcplugin.SORT_METHOD_ARTIST, xbmcplugin.SORT_METHOD_ALBUM, xbmcplugin.SORT_METHOD_DATE]
            content = "albums"

        elif path == "filter":
            listItems = self.getCriteria(get('criteria'))
            sortMethods = [xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE]

        elif path == "allcriteriasongs":
            listItems = self.listAllCriteriaSongs(get('criteria'), get('name'))
            sortMethods = [xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE]
            content = "songs"

        elif path in ["genre", "artist", "album", "composer"]:
            songs = self.api.getFilterSongs(path, unquote_plus(get('album')), unquote_plus(get('artist','')))
            listItems = self.addSongsFromLibrary(songs, 'library')
            sortMethods = [xbmcplugin.SORT_METHOD_TRACKNUM,  xbmcplugin.SORT_METHOD_TITLE_IGNORE_THE,
                           xbmcplugin.SORT_METHOD_PLAYCOUNT, xbmcplugin.SORT_METHOD_SONG_RATING]
            content = "songs"

        elif path == "search":
            listItems.append(self.createFolder(self.lang(30223),{'path':'search_new'}))
            history = utils.addon.getSetting('search-history').split('|')
            for item in history:
                if item:
                    listItems.append(self.createFolder(item,{'path':'search_query','query':item}))

        elif path == "search_new":
            keyboard = xbmc.Keyboard('', self.lang(30208))
            keyboard.doModal()
            if keyboard.isConfirmed() and keyboard.getText():
                listItems = self.getSearch(keyboard.getText())
                history = utils.addon.getSetting('search-history')
                history = keyboard.getText()+('|'+history if history else '')
                if len(history.split('|')) > 10:
                    history = '|'.join(history.split('|')[0:-1])
                utils.addon.setSetting('search-history',history)
                content = "songs"
            else: return

        elif path == "search_query":
            listItems = self.getSearch(url2pathname(get("query")))
            content = "songs"

        elif path == "search_result":
            utils.log("SEARCH_RESULT: "+get('query'))
            listItems = self.getSearch(params)
            content = "songs"

        elif path == "listennow":
            listItems = self.getListennow(self.api.getApi().get_listen_now_items())
            content = "albums"

        elif path == "topcharts":
            listItems.append(self.createFolder(self.lang(30206),{'path':'topcharts_albums'}))
            listItems.append(self.createFolder(self.lang(30213),{'path':'topcharts_songs'}))

        elif path == "topcharts_songs":
            listItems = self.addSongsFromLibrary(self.api.getTopcharts(), 'library')
            content = "songs"

        elif path == "topcharts_albums":
            listItems = self.createAlbumFolder(self.api.getTopcharts(content_type='albums'))
            content = "albums"

        elif path == "newreleases":
            listItems = self.createAlbumFolder(self.api.getNewreleases())
            content = "albums"

        elif path == "browse_stations":
            listItems = self.browseStations(get('category'))

        elif path == "get_stations":
            listItems = self.getCategoryStations(self.api.getApi().get_stations(get('subcategory')))
            view_mode_id = utils.addon.getSetting('stations_viewid')

        elif path == "create_station":
            if utils.addon.getSetting('subscriber') == "0":
                xbmc.executebuiltin("XBMC.Notification(%s,%s,5000,%s)" % (utils.plugin, utils.tryEncode("Song skipping is limited!"), utils.addon.getAddonInfo('icon')))
            utils.playAll(self.api.startRadio(unquote_plus(get('name')),artist_id=get('artistid'), genre_id=get('genreid'), curated_station_id=get('curatedid'), track_id=get('trackid')))
            return

        elif path == "genres":
            listItems = self.getGenres(self.api.getApi().get_top_chart_genres())

        elif path == "store_album":
            utils.log("ALBUM: "+get('albumid'))
            listItems = self.addSongsFromLibrary(self.api.getAlbum(get('albumid')), 'library')
            content = "songs"

        elif path == "artist_topsongs":
            listItems = self.addSongsFromLibrary(self.api.getArtistInfo(get('artistid'))['tracks'], 'library')
            content = "songs"

        elif path == "related_artists":
            listItems = []
            items = self.api.getArtistInfo(get('artistid'), False, 0, relartists=10)['relartists']
            for item in items:
                params = {'path':'artist_topsongs', 'artistid':item['artistId']}
                artist_art = item['artistArtRef'] if 'artistArtRef' in item else utils.addon.getAddonInfo('icon')
                listItems.append(self.createFolder(item['name'], params, arturl=artist_art))

        else:
            utils.log("Invalid path: " + get("path"))
            return

        utils.setDirectory(listItems, content, sortMethods, view_mode_id)


    def getMenuItems(self, items):
        ''' Build the plugin root menu. '''
        menuItems = []
        for menu_item in items:
            params = menu_item['params']
            cm = []
            if 'playlist_id' in params:
                cm = self.getPlayAllContextMenuItems(menu_item['title'], params['playlist_id'])
            elif 'type' in params:
                cm = self.getPlaylistsContextMenuItems(menu_item['title'], params['type'])
            elif params['path'] == 'library':
                cm.append((self.lang(30314), "XBMC.RunPlugin(%s?action=export_library)" % utils.addon_url))
                cm.append((self.lang(30305), "XBMC.RunPlugin(%s?action=update_library)" % utils.addon_url))
                cm.append((self.lang(30306), "XBMC.RunPlugin(%s?action=add_favourite&path=library&title=%s)" % (utils.addon_url,menu_item['title'])))
            elif 'criteria' in params:
                cm.append((self.lang(30306), "XBMC.RunPlugin(%s?action=add_favourite&path=filter&criteria=%s&title=%s)" % (utils.addon_url,params['criteria'],menu_item['title'])))
            menuItems.append(self.createFolder(menu_item['title'], params, cm))
        return menuItems

    def listPlaylistSongs(self, playlist_id):
        utils.log("Loading playlist: " + playlist_id)
        songs = self.api.getPlaylistSongs(playlist_id)
        if playlist_id == 'videos':
            return self.addVideosFromLibrary(songs)
        if playlist_id in ('thumbsup','lastadded','mostplayed','freepurchased','feellucky','all_songs','shuffled_albums'):
            return self.addSongsFromLibrary(songs, 'library')
        return self.addSongsFromLibrary(songs, 'playlist'+playlist_id)

    def addVideosFromLibrary(self, library):
        listItems = []
        append = listItems.append

        for song in library:
            li = ListItem(song['display_name'])
            li.setArt({'thumb':song['albumart'], 'fanart': song['artistart']})
            li.setProperty('IsPlayable', 'true')
            li.setProperty('Video', 'true')
            append(["plugin://plugin.video.youtube/play/?video_id=%s" % song['videoid'], li])

        return listItems

    def addSongsFromLibrary(self, library, song_type):
        listItems = []
        append = listItems.append
        createItem = self.createItem

        for song in library:
            append([utils.getUrl(song), createItem(song, song_type)])

        return listItems

    def listAllCriteriaSongs(self, filter_type, filter_criteria):
        songs      = self.api.getFilterSongs(filter_type, unquote_plus(filter_criteria), '')
        listItems  = []
        append     = listItems.append
        createItem = self.createItem

        # add album name when showing all artist songs
        for song in songs:
            songItem = createItem(song, 'library')
            songItem.setLabel("".join(['[',song['album'],'] ',song['title']]))
            songItem.setLabel2(song['album'])
            append([utils.getUrl(song), songItem])

        return listItems

    def getPlaylists(self, playlist_type):
        utils.log("Getting playlists of type: " + playlist_type)
        listItems = []
        append    = listItems.append
        addFolder = self.createFolder

        if playlist_type == 'radio':
            icon = utils.addon.getAddonInfo('icon')
            for rs in self.api.getStations():
                #utils.log(repr(rs))
                image = rs['compositeArtRefs'][0]['url'] if 'compositeArtRefs' in rs else rs['imageUrls'][0]['url'] if 'imageUrls' in rs else icon
                cm = self.getRadioContextMenuItems(rs['name'], rs['id'])
                append(addFolder(rs['name'], {'path':"station",'id':rs['id']}, cm, image))

        elif playlist_type == 'auto':
            icon = utils.addon.getAddonInfo('icon')
            auto = [['thumbsup',self.lang(30215),icon],['lastadded',self.lang(30216),icon],
                    ['freepurchased',self.lang(30217),icon],['mostplayed',self.lang(30218),icon],
                    ['videos','Videos',icon]]
            for pl_id, pl_name, pl_arturl in auto:
                cm = self.getPlayAllContextMenuItems(pl_name, pl_id)
                append(addFolder(pl_name, {'path':"playlist", 'playlist_id':pl_id}, cm, pl_arturl))

        else:
            for pl_id, pl_name, pl_arturl, pl_token in self.api.getPlaylistsByType(playlist_type):
                cm = self.getPlayAllContextMenuItems(pl_name, pl_id, pl_token)
                append(addFolder(pl_name, {'path':"playlist", 'playlist_id':pl_id}, cm, pl_arturl))

        return listItems

    def listAlbums(self, criteria, name=''):
        utils.log("LISTALBUMS: "+repr(criteria)+" "+repr(name))
        listItems = []
        append    = listItems.append
        addFolder = self.createFolder
        getCm     = self.getFilterContextMenuItems
        items     = self.api.getCriteria(criteria, name)

        for item in items:
            #utils.log(repr(item))
            album  = item['album']
            artist = item['album_artist']
            params = {'path':criteria,'album':album,'artist':artist}
            folder = addFolder(album, params, getCm(criteria, album, artist), item['arturl'], artist, item['artistart'])
            folder[1].setInfo(type='music', infoLabels={
                   'year':item['year'], 'artist':artist, 'album':album,
                   'date':time.strftime('%d.%m.%Y', time.gmtime(item['date']/1000000)),
                   'mediatype':'album'})
            append(folder)

        return listItems

    def getCriteria(self, criteria):
        utils.log("CRITERIA: "+repr(criteria))
        listItems = []
        append    = listItems.append
        addFolder = self.createFolder
        getCm     = self.getFilterContextMenuItems
        items     = self.api.getCriteria(criteria)

        if criteria in ('artist','genre'):
            for item in items:
                append( addFolder(item['criteria'], {'path':criteria,'name':item['criteria']}, getCm(criteria, item['criteria']), item['arturl'], fanarturl=item['arturl']))

        else:
            for item in items:
                append( addFolder(item['criteria'], {'path':criteria,'album':item['criteria']}, getCm(criteria, item['criteria'])))

        return listItems

    def getListennow(self, items):
        listItems    = []
        default_art  = utils.addon.getAddonInfo('icon')

        for item in items:
            suggestion = item.get('suggestion_text')
            image = item['images'][0]['url'] if 'images' in item else default_art

            if item['type'] == '1':
                album = item['album']
                listItems.extend(self.createAlbumFolder([{
                    'name'        :album['title']+' ('+suggestion+')',
                    'artist'      :album['artist_name'],
                    'albumArtRef' :image,
                    'albumId'     :album['id']['metajamCompactKey']}]))

            elif item['type'] == '3':
                radio  = item['radio_station']
                params = {'path':'create_station', 'name':utils.tryEncode('Radio %s (%s)'%(radio['title'], suggestion))}
                params.update(self.getStationSeed(radio['id']['seeds'][0]))
                listItems.append(self.createFolder(params['name'], params, arturl=image))

            else: utils.log("ERROR item type unknown "+repr(item['type']))

        return listItems

    def browseStations(self, index=None):
        listItems = []
        items = self.api.getApi().get_station_categories()
        #utils.log("INDEX:"+repr(index)+"\n"+repr(items))
        if index:
            # list subcategories from category index
            items = items[int(index)]['subcategories']
            params = {'path':'get_stations'}
        else:
            # list stations categories
            params = {'path':'browse_stations'}
        for item in items:
            # populate with categories or subcategories
            params['category'] = items.index(item)
            params['subcategory'] = item['id']
            listItems.append(self.createFolder(item['display_name'], params))
        return listItems

    def getCategoryStations(self, items):
        listItems = []

        default_thumb  = utils.addon.getAddonInfo('icon')
        default_fanart = utils.addon.getAddonInfo('fanart')

        for item in items:
            #utils.log("STATION: "+repr(item))
            params = {'path':'create_station','name':utils.tryEncode(item['name'])}
            params.update(self.getStationSeed(item['seed']))
            url1 = item['compositeArtRefs'][0]['url'] if 'compositeArtRefs' in item and item['compositeArtRefs'] else default_thumb
            url2 = item['imageUrls'][0]['url'] if 'imageUrls' in item and item['imageUrls'] else default_fanart
            folder = self.createFolder(item['name'], params, arturl=url1, fanarturl=url2)
            folder[1].setInfo(type='Music', infoLabels={'comment':item.get('description','No description'),
                            'date':time.strftime('%d.%m.%Y', time.gmtime(item.get('recentTimestamp',0)/1000000))})
            listItems.append(folder)
        return listItems

    def getStationSeed(self, seed):
        seed_id = {}
        if seed['seedType'] == '3':
            seed_id['artistid'] = seed['artistId']
        elif seed['seedType'] == '5':
            seed_id['genreid'] = seed['genreId']
        elif seed['seedType'] == '2':
            seed_id['trackid'] = seed['trackId']
        elif seed['seedType'] == '9':
            seed_id['curatedid'] = seed['curatedStationId']
        else: utils.log("ERROR seedtype unknown "+repr(seed['seedType']))
        return seed_id

    def createAlbumFolder(self, items):
        listItems = []
        for item in items:
            params = {'path':'store_album', 'albumid':item['albumId']}
            cm = [(self.lang(30301), "XBMC.RunPlugin(%s?action=play_all&album_id=%s)" % (utils.addon_url, item['albumId'])),
                  (self.lang(30309), "XBMC.RunPlugin(%s?action=add_album_library&album_id=%s)" % (utils.addon_url, item['albumId'])),
                  (self.lang(30315), "XBMC.RunPlugin(%s?action=add_to_queue&album_id=%s)" % (utils.addon_url, item['albumId']))]
            folder = self.createFolder("[%s] %s"%(item['artist'], item['name']), params, cm, item.get('albumArtRef',''), fanarturl=item.get('artistArtRef',''))
            folder[1].setInfo(type='Music', infoLabels={'artist':item['artist'], 'album':item['name'], 'mediatype':'album'})
            listItems.append(folder)
        #print repr(items)
        return listItems

    def createFolder(self, name, params, contextMenu=[], arturl='', name2='*', fanarturl=utils.addon.getAddonInfo('fanart')):
        li = ListItem(label=name, label2=name2)
        li.setArt({'thumb':arturl, 'fanart':fanarturl})
        li.addContextMenuItems(contextMenu)
        return "?".join([utils.addon_url, urlencode(params, doseq=True)]), li, "true"

    def createItem(self, song, song_type):
        infoLabels = {
            'tracknumber': song['tracknumber'], 'duration':   song['duration'],
            'year':        song['year'],        'genre':      song['genre'],
            'album':       song['album'],       'artist':     song['artist'],
            'title':       song['title'],       'playcount':  song['playcount'],
            'rating':      song['rating'],      'discnumber': song['discnumber'],
            'mediatype':   'song'
        }

        li = utils.createItem(song['display_name'], song['albumart'], song['artistart'])
        li.setInfo(type='music', infoLabels=infoLabels)
        li.addContextMenuItems(self.getSongContextMenu(song['song_id'], song['display_name'], song_type))
        return li

    def getSongContextMenu(self, song_id, title, song_type):
        cm = []
        if song_id.startswith('T'):
            cm.append((self.lang(30309), "XBMC.RunPlugin(%s?action=add_library&song_id=%s)" % (utils.addon_url,song_id)))
            cm.append((self.lang(30319), "XBMC.RunPlugin(%s?action=artist_topsongs&song_id=%s)" % (utils.addon_url,song_id)))
            cm.append((self.lang(30320), "XBMC.RunPlugin(%s?action=related_artists&song_id=%s)" % (utils.addon_url,song_id)))
        if song_type == 'library':
            cm.append((self.lang(30307),"XBMC.RunPlugin(%s?action=add_playlist&song_id=%s)" % (utils.addon_url,song_id)))
        elif song_type.startswith('playlist'):
            pl_id = song_type[8:]
            cm.append((self.lang(30322), "XBMC.RunPlugin(%s?action=play_all&from_here=%s&playlist_id=%s)" % (utils.addon_url, song_id, pl_id)))
            cm.append((self.lang(30308), "XBMC.RunPlugin(%s?action=del_from_playlist&song_id=%s&playlist_id=%s)" % (utils.addon_url, song_id, pl_id)))
        cm.append((self.lang(30409), "XBMC.RunPlugin(%s?action=set_thumbs&song_id=%s)" % (utils.addon_url, song_id)))
        cm.append((self.lang(30313), "XBMC.RunPlugin(%s?action=play_yt&title=%s)" % (utils.addon_url, title)))
        cm.append((self.lang(30311), "XBMC.RunPlugin(%s?action=search_yt&title=%s)" % (utils.addon_url, title)))
        cm.append((self.lang(30310), "XBMC.RunPlugin(%s?action=start_radio&song_id=%s)" % (utils.addon_url,song_id)))
        return cm

    def getRadioContextMenuItems(self, name, radio_id):
        cm = []
        cm.append((self.lang(30301), "XBMC.RunPlugin(%s?action=play_all&radio_id=%s)" % (utils.addon_url, radio_id)))
        cm.append((self.lang(30302), "XBMC.RunPlugin(%s?action=play_all&radio_id=%s&shuffle=true)" % (utils.addon_url, radio_id)))
        cm.append((self.lang(30312), "XBMC.RunPlugin(%s?action=play_all_yt&radio_id=%s)" % (utils.addon_url, radio_id)))
        cm.append((self.lang(30321), "XBMC.RunPlugin(%s?action=play_all_yt&radio_id=%s&shuffle=true)" % (utils.addon_url, radio_id)))
        cm.append((self.lang(30306), "XBMC.RunPlugin(%s?action=add_favourite&path=playlist&radio_id=%s&title=%s)" % (utils.addon_url, radio_id, name)))
        cm.append((self.lang(30315), "XBMC.RunPlugin(%s?action=add_to_queue&radio_id=%s)" % (utils.addon_url, radio_id)))
        cm.append((self.lang(30318), "XBMC.RunPlugin(%s?action=delete_station&radio_id=%s&title=%s)" % (utils.addon_url, radio_id, name)))
        return cm

    def getPlayAllContextMenuItems(self, name, playlist, token=None):
        cm = []
        cm.append((self.lang(30301), "XBMC.RunPlugin(%s?action=play_all&playlist_id=%s)" % (utils.addon_url, playlist)))
        cm.append((self.lang(30302), "XBMC.RunPlugin(%s?action=play_all&playlist_id=%s&shuffle=true)" % (utils.addon_url, playlist)))
        cm.append((self.lang(30312), "XBMC.RunPlugin(%s?action=play_all_yt&playlist_id=%s)" % (utils.addon_url, playlist)))
        cm.append((self.lang(30321), "XBMC.RunPlugin(%s?action=play_all_yt&playlist_id=%s&shuffle=true)" % (utils.addon_url, playlist)))
        cm.append((self.lang(30306), "XBMC.RunPlugin(%s?action=add_favourite&path=playlist&playlist_id=%s&title=%s)" % (utils.addon_url, playlist, name)))
        cm.append((self.lang(30314), "XBMC.RunPlugin(%s?action=export_playlist&playlist_id=%s&title=%s)" % (utils.addon_url, playlist, name)))
        cm.append((self.lang(30315), "XBMC.RunPlugin(%s?action=add_to_queue&playlist_id=%s)" % (utils.addon_url, playlist)))
        cm.append((self.lang(30317), "XBMC.RunPlugin(%s?action=delete_playlist&playlist_id=%s&title=%s)" % (utils.addon_url, playlist, name)))
        if token:
            cm.append((self.lang(30310), "XBMC.RunPlugin(%s?action=start_radio&token=%s&title=%s)" % (utils.addon_url, token, name)))
        return cm

    def getFilterContextMenuItems(self, filter_type, filter_criteria, artist=''):
        cm = []
        cm.append((self.lang(30306), "XBMC.RunPlugin(%s?action=add_favourite&path=%s&name=%s&title=%s)" % (utils.addon_url, filter_type, filter_criteria, filter_criteria)))
        cm.append((self.lang(30301), "XBMC.RunPlugin(%s?action=play_all&filter_type=%s&filter_criteria=%s&artist=%s)" % (utils.addon_url, filter_type, filter_criteria, artist)))
        cm.append((self.lang(30302), "XBMC.RunPlugin(%s?action=play_all&filter_type=%s&filter_criteria=%s&shuffle=true&artist=%s)" % (utils.addon_url, filter_type, filter_criteria, artist)))
        cm.append((self.lang(30312), "XBMC.RunPlugin(%s?action=play_all_yt&filter_type=%s&filter_criteria=%s&artist=%s)" % (utils.addon_url, filter_type, filter_criteria, artist)))
        cm.append((self.lang(30321), "XBMC.RunPlugin(%s?action=play_all_yt&filter_type=%s&filter_criteria=%s&shuffle=true&artist=%s)" % (utils.addon_url, filter_type, filter_criteria, artist)))
        cm.append((self.lang(30208), "XBMC.RunPlugin(%s?action=search&filter_type=%s&filter_criteria=%s&artist=%s)" % (utils.addon_url, filter_type, filter_criteria, artist)))
        cm.append((self.lang(30315), "XBMC.RunPlugin(%s?action=add_to_queue&filter_type=album&filter_criteria=%s&artist=%s)" % (utils.addon_url, filter_criteria, artist)))
        return cm

    def getPlaylistsContextMenuItems(self, name, playlist_type):
        cm = []
        cm.append((self.lang(30304), "XBMC.RunPlugin(%s?action=update_playlists&playlist_type=%s)" % (utils.addon_url, playlist_type)))
        cm.append((self.lang(30306), "XBMC.RunPlugin(%s?action=add_favourite&path=playlists&playlist_type=%s&title=%s)" % (utils.addon_url, playlist_type, name)))
        cm.append((self.lang(30316), "XBMC.RunPlugin(%s?action=create_playlist)" % utils.addon_url))
        return cm

    def getSearch(self, query):
        listItems = []

        def listAlbumsResults():
            for album in result['albums']:
                if 'albumId' in album:
                    listItems.extend(self.createAlbumFolder([album]))
                else:
                    params = {'path':'album','album':utils.tryEncode(album['name']),'artist':utils.tryEncode(album['artist'])}
                    cm = self.getFilterContextMenuItems('album',album['name'])
                    listItems.append(self.createFolder("[%s] %s"%(album['artist'], album['name']), params, cm, album['albumart'], album['artistart']))

        def listArtistsResults():
            cm = []
            for artist in result['artists']:
                params = {'path':'artist','name':utils.tryEncode(artist['name'])}
                if 'artistId' in artist:
                    params = {'path':'search_result','artistid':artist['artistId'],'query':utils.tryEncode(artist['name'])}
                    cm = [(self.lang(30301), "XBMC.RunPlugin(%s?action=play_all&artist_id=%s)" % (utils.addon_url, artist['artistId']))]
                art = artist['artistArtRef'] if 'artistArtRef' in artist else utils.addon.getAddonInfo('icon')
                listItems.append(self.createFolder(artist['name'], params, cm, arturl=art, fanarturl=art))

        if isinstance(query,basestring):
            result = self.api.getSearch(query)
            if result['artists']:
                listItems.append(self.createFolder('[COLOR orange]*** '+self.lang(30205)+' ***[/COLOR] +>',{'path':'search_result','type':'artist','query':query}))
                listArtistsResults()
            if result['albums']:
                listItems.append(self.createFolder('[COLOR orange]*** '+self.lang(30206)+' ***[/COLOR] +>',{'path':'search_result','type':'album','query':query}))
                listAlbumsResults()
            if result['tracks']:
                listItems.append(self.createFolder('[COLOR orange]*** '+self.lang(30213)+' ***[/COLOR] +>',{'path':'search_result','type':'track','query':query}))
                listItems.extend(self.addSongsFromLibrary(result['tracks'], 'library'))
            if result['stations']:
                listItems.append(self.createFolder('[COLOR orange]*** '+self.lang(30203)+' ***[/COLOR]',{'path':'none'}))
                listItems.extend(self.getCategoryStations(result['stations']))
            if result['videos']:
                listItems.append(self.createFolder('[COLOR orange]*** Youtube ***[/COLOR]',{'path':'none'}))
                for video in result['videos']:
                    listItems.append(self.createFolder(video['title'],{'action':'play_yt','display_name':video['title']}))

        elif 'artistid' in query:
            result = self.api.getArtistInfo(query['artistid'], True, 20, 0)
            if result['albums']:
                listItems.append(self.createFolder('[COLOR orange]*** '+self.lang(30206)+' ***[/COLOR]',{'path':'none'}))
                listAlbumsResults()
            listItems.append(self.createFolder('[COLOR orange]*** '+self.lang(30213)+' ***[/COLOR]',{'path':'none'}))
            listItems.extend(self.addSongsFromLibrary(result['tracks'], 'library'))

        elif 'type' in query:
            result = self.api.getSearch(query['query'], max_results=50)
            if query['type'] == 'artist':
                listArtistsResults()
            elif query['type'] == 'album':
                listAlbumsResults()
            elif query['type'] == 'track':
                listItems.extend(self.addSongsFromLibrary(result['tracks'], 'library'))

        else:
            #listItems.extend(self.addSongsFromLibrary(self.api.getSearch(unquote_plus(query['query']))['tracks'], 'library'))
            listItems.extend(self.getSearch(unquote_plus(query['query'])))

        return listItems



