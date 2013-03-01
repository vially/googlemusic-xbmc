import sys, xbmc, xbmcgui, xbmcplugin, xbmcaddon

# plugin constants
version = "0.8.2"
plugin = "GoogleMusic-" + version

# xbmc hooks
settings = xbmcaddon.Addon(id='plugin.audio.googlemusic')
__info__ = settings.getAddonInfo
__icon__ = __info__('icon')

dbg = settings.getSetting( "debug" ) == "true"
dbglevel = 3

# plugin variables
storage = ""

# utility functions
def parameters_string_to_dict(parameters):
    ''' Convert parameters encoded in a URL to a dict. '''
    paramDict = {}
    if parameters:
        paramPairs = parameters[1:].split("&")
        for paramsPair in paramPairs:
            paramSplits = paramsPair.split('=')
            if (len(paramSplits)) == 2:
                paramDict[paramSplits[0]] = paramSplits[1]
    return paramDict

def log(message):
    if dbg:
        print "[%s] %s" % (plugin, message)

if (__name__ == "__main__" ):
    if dbg:
        print plugin + " ARGV: " + repr(sys.argv)
    else:
        print plugin

    import GoogleMusicStorage
    storage = GoogleMusicStorage.GoogleMusicStorage()

    import GoogleMusicApi
    api = GoogleMusicApi.GoogleMusicApi()

    import GoogleMusicPlaySong
    song = GoogleMusicPlaySong.GoogleMusicPlaySong()
        
    params = parameters_string_to_dict(sys.argv[2])
    get = params.get

    if (get("action") == "play_song"):
        song.play(get("song_id"))
    else:
        import GoogleMusicNavigation
        navigation = GoogleMusicNavigation.GoogleMusicNavigation()

        import GoogleMusicLogin

        if (not params):
            # check for initing cookies, db and library only on main menu
            GoogleMusicLogin.GoogleMusicLogin(None).checkCookie()
            storage.checkDbInit()
            
            if not storage.isPlaylistFetched('all_songs'):
                xbmc.executebuiltin("XBMC.Notification("+plugin+",'Loading library',5000,"+__icon__ +")")
                navigation.api.updatePlaylistSongs('all_songs')
            
            navigation.listMenu()
        elif (get("action")):
            navigation.executeAction(params)
        elif (get("path")):
            navigation.listMenu(params)
        else:
            print plugin + " ARGV Nothing done.. verify params " + repr(params)
