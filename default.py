import sys, xbmcaddon, xbmcgui, xbmcplugin

# plugin constants
version = "0.8.x"
plugin = "GoogleMusic-" + version

# xbmc hooks
settings = xbmcaddon.Addon(id='plugin.audio.googlemusic')

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

    import GoogleMusicPlaySong
    song = GoogleMusicPlaySong.GoogleMusicPlaySong()

    params = parameters_string_to_dict(sys.argv[2])
    get = params.get

    if (get("action") == "play_song"):
        song.play(params)
    else:

        import GoogleMusicNavigation
        navigation = GoogleMusicNavigation.GoogleMusicNavigation()

        if (not params):
 
            import GoogleMusicLogin
            login = GoogleMusicLogin.GoogleMusicLogin()

            # if version changed clear cache
            if not settings.getSetting('version') or settings.getSetting('version') != version:
               storage.clearCache()
               login.clearCookie()
               settings.setSetting('version',version)
               
            # check for initing cookies, db and library only on main menu
            storage.checkDbInit()

            login.checkCredentials()
            login.checkCookie()
            login.initDevice()

            # check if library needs to be loaded
            if settings.getSetting('fetched_all_songs') == '0':
                import xbmc
                xbmc.executebuiltin("XBMC.Notification("+plugin+",'Loading library',5000,"+settings.getAddonInfo('icon')+")")
                log('Loading library')
                navigation.api.loadLibrary()

            navigation.listMenu()

        elif (get("action")):
            navigation.executeAction(params)
        elif (get("path")):
            navigation.listMenu(params)
        else:
            print plugin + " ARGV Nothing done.. verify params " + repr(params)
            
