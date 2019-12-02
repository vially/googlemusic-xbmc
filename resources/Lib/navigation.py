import time
from urllib import quote_plus, urlencode

import api
import utils
import xbmc
import xbmcplugin
from xbmcgui import ListItem

fanart = utils.addon.getAddonInfo('fanart')


class Navigation:
    def __init__(self):
        self.lang = utils.addon.getLocalizedString
        self.api = api.Api()
        self.contextmenu_action = "XBMC.RunPlugin("+utils.addon_url+"?action=%s&%s)"

        self.main_menu = (
            {'title': self.lang(30224), 'params': {'path': "home_menu"}, 'user': ['library', 'subscriber']},
            {'title': self.lang(30219), 'params': {'path': "listennow"}, 'user': ['subscriber', 'free']},
            {'title': self.lang(30220), 'params': {'path': "topcharts"}, 'user': ['subscriber']},
            {'title': self.lang(30221), 'params': {'path': "newreleases"}, 'user': ['subscriber']},
            {'title': self.lang(30209), 'params': {'path': "library"}, 'user': ['library']},
            {'title': self.lang(30202), 'params': {'path': "playlists_menu"}, 'user': ['library', 'subscriber']},
            {'title': self.lang(30222), 'params': {'path': "browse_stations"}, 'user': ['subscriber', 'free']},
            {'title': self.lang(30208), 'params': {'path': "search"}, 'user': ['library', 'subscriber']}
        )
        self.lib_menu = (
            {'title': self.lang(30203), 'params': {'path': "playlists", 'type': "radio"}},
            {'title': self.lang(30210), 'params': {'path': "playlist", 'playlist_id': "feellucky"}},
            {'title': self.lang(30214), 'params': {'path': "playlist", 'playlist_id': "shuffled_albums"}},
            {'title': self.lang(30201), 'params': {'path': "playlist", 'playlist_id': "all_songs"}},
            {'title': self.lang(30205), 'params': {'path': "filter", 'criteria': "artist"}},
            {'title': self.lang(30206), 'params': {'path': "filter", 'criteria': "album"}},
            {'title': self.lang(30207), 'params': {'path': "filter", 'criteria': "genre"}},
            {'title': self.lang(30212), 'params': {'path': "filter", 'criteria': "composer"}},
        )
        self.playlists_menu = (
            {'title': self.lang(30225), 'params': {'path': "playlists", 'type': "recent"}, 'user': ['library', 'subscriber']},
            {'title': self.lang(30204), 'params': {'path': "playlists", 'type': "auto"}, 'user': ['library', 'subscriber']},
            {'title': self.lang(30202), 'params': {'path': "playlists", 'type': "user"}, 'user': ['library', 'subscriber']},
        )
        self.home_menu = (
            {'title': self.lang(30211), 'params': {'path': "ifl"}, 'user': ['library', 'subscriber']},
            {'title': self.lang(30225), 'params': {'path': "home_recents"}, 'user': ['library', 'subscriber']},
        )

    def listMenu(self, params):
        get = params.get
        path = get("path", "root")
        utils.log("PATH: " + path)

        listItems = []
        content = ''
        sortMethods = [xbmcplugin.SORT_METHOD_UNSORTED]

        if path == "root":
            # assemble menu depending on user info
            subscriber = utils.addon.getSettingBool('subscriber')
            library = utils.addon.getSettingInt('fetched_count') > 0
            utils.log("Assembling menu for subscriber=%r and library=%r" % (subscriber, library))

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

        elif path == "home_menu":
            listItems = self.getMenuItems(self.home_menu)
            listItems.extend(self.get_situations())
            content = "albums"

        elif path == "situation_items":
            listItems = self.get_situations_items(get('situation_id'))
            content = "albums"

        elif path == "library":
            listItems = self.getMenuItems(self.lib_menu)

        elif path == "playlists_menu":
            listItems = self.getMenuItems(self.playlists_menu)

        elif path == "playlist":
            listItems = self.listPlaylistSongs(get("playlist_id"))
            if get("playlist_id") == 'all_songs':
                sortMethods = [xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE]
            content = "songs"

        elif path == "station":
            listItems = self.addSongsFromLibrary(self.api.getStationTracks(get('id')), 'library')
            content = "songs"

        elif path == "playlists":
            listItems = self.getPlaylists(get('type'))

        elif path == "filter" and 'album' == get('criteria'):
            listItems = self.listAlbums(get('criteria'))
            sortMethods = [xbmcplugin.SORT_METHOD_ALBUM_IGNORE_THE, xbmcplugin.SORT_METHOD_VIDEO_YEAR,
                           xbmcplugin.SORT_METHOD_ARTIST, xbmcplugin.SORT_METHOD_ALBUM, xbmcplugin.SORT_METHOD_DATE]
            content = "albums"

        elif path in ["artist", "genre"] and get('name'):
            album_name = get('name')
            paramsAllSongs = {'path': "allcriteriasongs", 'criteria': path, 'name': album_name}
            listItems.insert(0, self.createFolder('* ' + self.lang(30201), paramsAllSongs))
            listItems.extend(self.listAlbums(path, album_name))
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
            songs = self.api.getFilterSongs(path, get('album'), get('artist', ''))
            listItems = self.addSongsFromLibrary(songs, 'library')
            sortMethods = [xbmcplugin.SORT_METHOD_TRACKNUM, xbmcplugin.SORT_METHOD_TITLE_IGNORE_THE,
                           xbmcplugin.SORT_METHOD_PLAYCOUNT, xbmcplugin.SORT_METHOD_SONG_RATING]
            content = "songs"

        elif path == "search":
            listItems.append(self.createFolder(self.lang(30223), {'path': 'search_new'}))
            history = utils.addon.getSetting('search-history').split('|')
            for item in history:
                if item:
                    listItems.append(self.createFolder(item, {'path': 'search_query', 'query': item}))

        elif path == "search_new":
            keyboard = xbmc.Keyboard('', self.lang(30208))
            keyboard.doModal()
            if keyboard.isConfirmed() and keyboard.getText():
                listItems = self.getSearch(keyboard.getText())
                history = utils.addon.getSetting('search-history')
                history = keyboard.getText() + ('|' + history if history else '')
                if len(history.split('|')) > 10:
                    history = '|'.join(history.split('|')[0:-1])
                utils.addon.setSetting('search-history', history)
                content = "songs"
            else:
                return

        elif path == "search_query":
            listItems = self.getSearch(get("query"))
            content = "songs"

        elif path == "search_result":
            utils.log("SEARCH_RESULT: " + get('query'))
            listItems = self.getSearch(params)
            content = "songs"

        elif path == "listennow":
            listItems = self.getListennow(self.api.getApi().get_listen_now_items())
            content = "albums"

        elif path == "topcharts":
            listItems.append(self.createFolder(self.lang(30206), {'path': 'topcharts_albums'}))
            listItems.append(self.createFolder(self.lang(30213), {'path': 'topcharts_songs'}))

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

        elif path == "create_station":
            if not utils.addon.getSettingBool('subscriber'):
                xbmc.executebuiltin("XBMC.Notification(%s,%s,5000,%s)" % (
                     utils.plugin, utils.tryEncode("Song skipping is limited!"), utils.addon.getAddonInfo('icon')))
            tracks = self.api.startRadio(get('name'), artist_id=get('artistid'), genre_id=get('genreid'),
                                         curated_station_id=get('curatedid'), track_id=get('trackid'))
            listItems = self.addSongsFromLibrary(tracks, 'library')
            content = "songs"
            # utils.playAll(tracks)
            # utils.setResolvedUrl(listItems[0][1])

        elif path == "genres":
            listItems = self.getGenres(self.api.getApi().get_top_chart_genres())

        elif path == "store_album":
            utils.log("ALBUM: " + get('album_id'))
            listItems = self.addSongsFromLibrary(self.api.getAlbum(get('album_id')), 'library')
            content = "songs"

        elif path == "artist_topsongs":
            listItems = self.addSongsFromLibrary(self.api.getArtistInfo(get('artistid'))['tracks'], 'library')
            content = "songs"

        elif path == "related_artists":
            listItems = []
            items = self.api.getArtistInfo(get('artistid'), False, 0, relartists=10)['relartists']
            for item in items:
                params = {'path': 'artist_topsongs', 'artistid': item['artistId']}
                listItems.append(self.createFolder(item['name'], params, arturl=item['artistArtRef']))

        elif path == "home_recents":
            listItems = self.get_recents()
            content = "album"

        else:
            utils.log("Invalid path: " + get("path"))
            return

        utils.setDirectory(listItems, content, sortMethods)

    def getMenuItems(self, items):
        menuItems = []
        for menu_item in items:
            params = menu_item['params']
            cm = []
            if 'playlist_id' in params:
                cm = self.getPlayAllContextMenu(menu_item['title'], params['playlist_id'])
            elif 'type' in params:
                cm.append(self.create_menu(30304, "update_playlists", {'playlist_type': params['type']}))
                cm.append(self.create_menu(30306, "add_favourite", {'path': 'playlists', 'playlist_type': params['type'], 'title': menu_item['title']}))
                cm.append(self.create_menu(30316, "create_playlist"))
            elif params['path'] == 'library':
                cm.append(self.create_menu(30305, "update_library"))
                cm.append(self.create_menu(30306, "add_favourite", {'path': 'library', 'title': menu_item['title']}))
            elif 'criteria' in params:
                cm.append(self.create_menu(30306, "add_favourite", {'path': 'filter', 'criteria': params['criteria'], 'title': menu_item['title']}))
            menuItems.append(self.createFolder(menu_item['title'], params, cm))
        return menuItems

    def listPlaylistSongs(self, playlist_id):
        utils.log("Loading playlist: " + playlist_id)
        songs = self.api.getPlaylistSongs(playlist_id)
        if playlist_id == 'videos':
            return self.addVideosFromLibrary(songs)
        if playlist_id in ('thumbsup', 'lastadded', 'mostplayed', 'freepurchased', 'feellucky', 'all_songs', 'shuffled_albums'):
            return self.addSongsFromLibrary(songs, 'library')
        return self.addSongsFromLibrary(songs, 'playlist' + playlist_id)

    def addVideosFromLibrary(self, library):
        listItems = []

        for song in library:
            li = ListItem(song['display_name'], offscreen=True)
            li.setArt({'thumb': song['albumart'], 'fanart': song['artistart']})
            li.setProperties({'IsPlayable': 'true', 'Video': 'true'})
            listItems.append(["plugin://plugin.video.youtube/play/?video_id=%s" % song['videoid'], li])

        return listItems

    def addSongsFromLibrary(self, library, song_type):
        return [[utils.getUrl(song), self.createItem(song, song_type)] for song in library]

    def listAllCriteriaSongs(self, filter_type, filter_criteria):
        songs = self.api.getFilterSongs(filter_type, filter_criteria, '')
        listItems = []

        # add album name when showing all artist songs
        for song in songs:
            songItem = self.createItem(song, 'library')
            songItem.setLabel("".join(['[', song['album'], '] ', song['title']]))
            songItem.setLabel2(song['album'])
            listItems.append([utils.getUrl(song), songItem])

        return listItems

    def createItem(self, song, song_type):
        infoLabels = {
            'tracknumber': song['tracknumber'], 'duration': song['duration'], 'year': song['year'],
            'genre': song['genre'], 'album': song['album'], 'artist': song['artist'], 'title': song['title'],
            'playcount': song['playcount'], 'rating': song['rating'], 'discnumber': song['discnumber'],
            'mediatype': 'song'
        }
        li = utils.createItem(song['display_name'], song['albumart'], song['artistart'])
        li.setInfo(type='Music', infoLabels=infoLabels)
        li.addContextMenuItems(self.getSongContextMenu(song['song_id'], song['display_name'], song_type))
        return li

    def getPlaylists(self, playlist_type):
        utils.log("Getting playlists of type: " + playlist_type)
        listItems = []
        append = listItems.append
        addFolder = self.createFolder

        if playlist_type == 'radio':
            for rs in self.api.getStations():
                # utils.log(repr(rs))
                image = rs['compositeArtRefs'][0]['url'] if 'compositeArtRefs' in rs else rs['imageUrls'][0]['url'] if 'imageUrls' in rs else None
                cm = self.getRadioContextMenu(rs['name'], rs['id'])
                append(addFolder(rs['name'], {'path': "station", 'id': rs['id']}, cm, image))

        elif playlist_type == 'auto':
            auto = [['thumbsup', self.lang(30215)], ['lastadded', self.lang(30216)],
                    ['freepurchased', self.lang(30217)], ['mostplayed', self.lang(30218)],
                    ['videos', 'Videos']]
            for pl_id, pl_name in auto:
                cm = self.getPlayAllContextMenu(pl_name, pl_id)
                append(addFolder(pl_name, {'path': "playlist", 'playlist_id': pl_id}, cm))

        else:
            for pl_id, pl_name, pl_arturl, pl_token, pl_recent in self.api.getPlaylistsByType(playlist_type):
                cm = self.getPlayAllContextMenu(pl_name, pl_id, pl_token)
                append(addFolder(pl_name, {'path': "playlist", 'playlist_id': pl_id}, cm, pl_arturl))

        return listItems

    def listAlbums(self, criteria, name=''):
        utils.log("LIST ALBUMS: " + repr(criteria) + " " + repr(name))
        listItems = []
        getCm = self.getFilterContextMenu
        items = self.api.getCriteria(criteria, name)

        for item in items:
            # utils.log(repr(item))
            album = item['album']
            artist = item['album_artist']
            params = {'path': criteria, 'album': album, 'artist': artist}
            folder = self.createFolder(album, params, getCm(criteria, album, artist), item['arturl'], artist, item['artistart'])
            folder[1].setInfo(type='Music', infoLabels={'year': item['year'], 'artist': artist, 'album': album,
                              'date': time.strftime('%d.%m.%Y', time.gmtime(item['date'] / 1000000)), 'mediatype': 'album'})
            listItems.append(folder)

        return listItems

    def getCriteria(self, criteria):
        utils.log("CRITERIA: " + repr(criteria))
        folder = self.createFolder
        getCm = self.getFilterContextMenu
        items = self.api.getCriteria(criteria)

        if criteria in ('artist', 'genre'):
            return [folder(item['criteria'], {'path': criteria, 'name': item['criteria']},
                           getCm(criteria, item['criteria']), item['arturl'], fanarturl=item['arturl']) for item in items]
        else:
            return [folder(item['criteria'], {'path': criteria, 'album': item['criteria']},
                           getCm(criteria, item['criteria'])) for item in items]

    def get_recents(self):
        listItems = []
        dictItems = {}
        addFolder = self.createFolder

        for pl_id, pl_name, pl_arturl, pl_token, pl_recent in self.api.getPlaylistsByType('user'):
            cm = self.getPlayAllContextMenu(pl_name, pl_id, pl_token)
            dictItems[int(pl_recent)] = addFolder(pl_name+" (Playlist)", {'path': 'playlist', 'playlist_id': pl_id}, cm, pl_arturl)

        from datetime import datetime, timedelta
        filtertime = ((datetime.today() - timedelta(40)) - datetime(1970,1,1)).total_seconds() * 1000000
        for rs in self.api.getStations():
            if int(rs['lastModifiedTimestamp']) < filtertime:
                continue
            image = rs['compositeArtRefs'][0]['url'] if 'compositeArtRefs' in rs else rs['imageUrls'][0]['url'] if 'imageUrls' in rs else None
            cm = self.getRadioContextMenu(rs['name'], rs['id'])
            if rs['seed']['seedType'] == '3':
                rs['name'] = rs['name'] + " Radio"
            dictItems[int(rs['recentTimestamp'])] = addFolder(rs['name'], {'path': 'station', 'id': rs['id']}, cm, image)

        #for song in self.api.getRecent():
        #    cm = self.getFilterContextMenu("album", song['album'], song['artist'])
        #    dictItems[song['recent']] = addFolder(song['album'], {'path': 'album', 'album': song['album'], 'artist': song['artist']}, cm, song['albumart'])

        for key in sorted(dictItems.keys(), reverse=True):
            #utils.log("RECENTS: "+str(key)+" "+repr(dictItems[key][1].getLabel()))
            listItems.append(dictItems[key])

        return listItems

    def getListennow(self, items):
        listItems = []

        for item in items:
            suggestion = item.get('suggestion_text')
            image = item.get('images', [{'url': ''}])[0]['url']

            # defualt to radio station
            item_type = item.get('type', '3')

            if item['type'] == '1':
                album = item['album']
                listItems.extend(self.createAlbumFolder([{
                    'name': album['title'] + ' (' + suggestion + ')',
                    'artist': album['artist_name'],
                    'albumArtRef': image,
                    'albumId': album['id']['metajamCompactKey']}]))

            elif item['type'] == '3':
                radio = item['radio_station']
                params = {'path': 'create_station',
                          'name': utils.tryEncode('Radio %s (%s)' % (radio['title'], suggestion))}
                params.update(self.getStationSeed(radio['id']['seeds'][0]))
                listItems.append(self.createFolder(params['name'], params, arturl=image))

            else:
                utils.log("ERROR item type unknown " + repr(item['type']))

        return listItems

    def get_situations(self):
        listItems = []
        items = self.api.get_situations()
        for item in items:
            params = {'path': 'situation_items', 'situation_id': item['id']}
            listItems.append(self.createFolder(item['title'], params, arturl=item.get('imageUrl'), fanarturl=item.get('wideImageUrl')))
        return listItems

    def get_situations_items(self, situation_id):
        listItems = []
        items = self.api.get_situations()
        for item in items:
            if item['id'] == situation_id:
                ##return self.getListennow(item['stations'])
                return self.getCategoryStations(item['stations'])
        utils.log("ERROR Situation not found: "+situation_id)
        return None

    def browseStations(self, index=None):
        listItems = []
        items = self.api.getStationsCategories()

        utils.log("INDEX:"+repr(index)+"\n"+repr(items))
        if index:
            # list subcategories from category index
            items = items[int(index)].get('subcategories')
        for item in items:
            # populate with categories or subcategories
            if 'subcategories' in item:
                params = {'path': 'browse_stations'}
            else:
                params = {'path': 'get_stations'}

            params['category'] = items.index(item)
            params['subcategory'] = item['id']
            listItems.append(self.createFolder(item['display_name'], params))
        return listItems

    def getCategoryStations(self, items):
        listItems = []

        utils.log("STATIONS: "+repr(items))
        for item in items:
            #utils.log("STATION: "+repr(item))
            params = {'path': 'create_station', 'name': utils.tryEncode(item['name'])}
            params.update(self.getStationSeed(item['seed']))
            url1 = item['compositeArtRefs'][0]['url'] if 'compositeArtRefs' in item else ''
            url2 = item['imageUrls'][0]['url']
            folder = self.createFolder(item['name'], params, arturl=url1, name2=item.get('description'), fanarturl=url2)
            folder[1].setInfo(type='Music', infoLabels={'comment': item.get('description', 'No description'),
                              'date': time.strftime('%d.%m.%Y', time.gmtime(item.get('recentTimestamp', 0) / 1000000))})
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
        else:
            utils.log("ERROR seedtype unknown " + repr(seed['seedType']))
        return seed_id

    def createAlbumFolder(self, items):
        listItems = []
        for item in items:
            params = {'path': 'store_album', 'album_id': item['albumId']}
            cm = [self.create_menu(30301, "play_all", params),
                  self.create_menu(30309, "add_album_library", params),
                  self.create_menu(30315, "add_to_queue", params)]
            folder = self.createFolder("[%s] %s" % (item['artist'], item['name']), params, cm, item.get('albumArtRef', ''),
                                       item.get('description'), fanarturl=item.get('artistArtRef', ''))
            folder[1].setInfo(type='Music', infoLabels={'comment': item.get('description', 'No description'),
                              'artist': item['artist'], 'album': item['name'], 'mediatype': 'album'})
            listItems.append(folder)
        # print repr(items)
        return listItems

    def createFolder(self, name, params, contextMenu=[], arturl='', name2='*', fanarturl=fanart):
        li = ListItem(label=name, label2=name2, offscreen=True)
        li.setArt({'thumb': arturl, 'fanart': fanarturl})
        li.addContextMenuItems(contextMenu)
        return "?".join([utils.addon_url, urlencode(params, doseq=True)]), li, "true"

    def getSongContextMenu(self, song_id, display_name, song_type):
        params = {'song_id': song_id, 'display_name': display_name}
        cm = []
        if song_id.startswith('T'):
            cm.append(self.create_menu(30309, "add_library", params))
            cm.append(self.create_menu(30319, "artist_topsongs", params))
            cm.append(self.create_menu(30320, "related_artists", params))
        if song_type == 'library':
            cm.append(self.create_menu(30307, "add_playlist", params))
        elif song_type.startswith('playlist'):
            playlist = {'song_id': song_id, 'display_name': display_name, 'playlist_id': song_type[8:]}
            cm.append(self.create_menu(30322, "play_all", playlist))
            cm.append(self.create_menu(30308, "del_from_playlist", playlist))
        cm.append(self.create_menu(30409, "set_thumbs", params))
        cm.append(self.create_menu(30313, "play_yt", params))
        cm.append(self.create_menu(30311, "search_yt", params))
        cm.append(self.create_menu(30310, "start_radio", params))
        return cm

    def getRadioContextMenu(self, name, radio_id):
        params = {'radio_id': radio_id, 'title': name}
        shuffle = params.copy()
        shuffle.update({'shuffle': 'true'})
        return [
            self.create_menu(30301, "play_all", params),
            self.create_menu(30302, "play_all", shuffle),
            self.create_menu(30312, "play_all_yt", params),
            self.create_menu(30321, "play_all_yt", shuffle),
            self.create_menu(30306, "add_favourite", {'radio_id': radio_id, 'title': name, 'path': 'playlist'}),
            self.create_menu(30315, "add_to_queue", params),
            self.create_menu(30318, "delete_station", params)
            ]

    def getPlayAllContextMenu(self, name, playlist, token=None):
        params = {'playlist_id': playlist, 'title': name}
        shuffle = params.copy()
        shuffle.update({'shuffle': 'true'})
        cm = [
            self.create_menu(30301, "play_all", params),
            self.create_menu(30302, "play_all", shuffle),
            self.create_menu(30312, "play_all_yt",params),
            self.create_menu(30321, "play_all_yt", shuffle),
            self.create_menu(30306, "add_favourite", {'playlist_id': playlist, 'title': name, 'path': 'playlist'}),
            self.create_menu(30315, "add_to_queue", params),
            self.create_menu(30317, "delete_playlist", params)
            ]
        if token:
            cm.append(self.create_menu(30310, "start_radio", {'playlist_id': playlist, 'title': name, 'token': token}))
        return cm

    def getFilterContextMenu(self, filter_type, filter_criteria, artist=''):
        params = {'filter_type': filter_type, 'filter_criteria': filter_criteria, 'artist': artist}
        shuffle = params.copy()
        shuffle.update({'shuffle': 'true'})
        return [
            self.create_menu(30301, "play_all", params),
            self.create_menu(30302, "play_all", shuffle),
            self.create_menu(30312, "play_all_yt", params),
            self.create_menu(30321, "play_all_yt", shuffle),
            self.create_menu(30306, "add_favourite", {'path': filter_type, 'name': filter_criteria, 'title': filter_criteria}),
            self.create_menu(30315, "add_to_queue", params),
            self.create_menu(30208, "search", params),
            ]

    def create_menu(self, text_code, action, params={'1':1}):
        return self.lang(text_code), self.contextmenu_action % (action, urlencode(params, doseq=True))

    def getSearch(self, query):
        listItems = []

        def listAlbumsResults():
            for album in result['albums']:
                if 'albumId' in album:
                    listItems.extend(self.createAlbumFolder([album]))
                else:
                    params = {'path': 'album', 'album': utils.tryEncode(album['name']), 'artist': utils.tryEncode(album['artist'])}
                    cm = self.getFilterContextMenu('album', album['name'])
                    folder_name = "[%s] %s" % (album['artist'], album['name'])
                    listItems.append(self.createFolder(folder_name, params, cm, album['albumart'], album['artistart']))

        def listArtistsResults():
            cm = []
            for artist in result['artists']:
                params = {'path': 'artist', 'name': utils.tryEncode(artist['name'])}
                if 'artistId' in artist:
                    params = {'path': 'search_result', 'artistid': artist['artistId'], 'query': utils.tryEncode(artist['name'])}
                    cm = [self.create_menu(30301, "play_all", {'artist_id': artist['artistId']})]
                art = artist['artistArtRef']
                listItems.append(self.createFolder(artist['name'], params, cm, arturl=art, fanarturl=art))

        if isinstance(query, str):
            result = self.api.getSearch(query)
            if result['artists']:
                listItems.append(self.createFolder('[COLOR orange]*** ' + self.lang(30205) + ' ***[/COLOR] +>',
                                                   {'path': 'search_result', 'type': 'artist', 'query': query}))
                listArtistsResults()
            if result['albums']:
                listItems.append(self.createFolder('[COLOR orange]*** ' + self.lang(30206) + ' ***[/COLOR] +>',
                                                   {'path': 'search_result', 'type': 'album', 'query': query}))
                listAlbumsResults()
            if result['tracks']:
                listItems.append(self.createFolder('[COLOR orange]*** ' + self.lang(30213) + ' ***[/COLOR] +>',
                                                   {'path': 'search_result', 'type': 'track', 'query': query}))
                listItems.extend(self.addSongsFromLibrary(result['tracks'], 'library'))
            if result['stations']:
                listItems.append(
                    self.createFolder('[COLOR orange]*** ' + self.lang(30203) + ' ***[/COLOR]', {'path': 'none'}))
                listItems.extend(self.getCategoryStations(result['stations']))
            if result['videos']:
                listItems.append(self.createFolder('[COLOR orange]*** Youtube ***[/COLOR]', {'path': 'none'}))
                for video in result['videos']:
                    listItems.append(
                        self.createFolder(video['title'], {'action': 'play_yt', 'display_name': video['title']}))

        elif 'artistid' in query:
            result = self.api.getArtistInfo(query['artistid'], True, 20, 0)
            if result['albums']:
                listItems.append(
                    self.createFolder('[COLOR orange]*** ' + self.lang(30206) + ' ***[/COLOR]', {'path': 'none'}))
                listAlbumsResults()
            listItems.append(
                self.createFolder('[COLOR orange]*** ' + self.lang(30213) + ' ***[/COLOR]', {'path': 'none'}))
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
            listItems.extend(self.getSearch(query['query']))

        return listItems
