import sys, xbmc, xbmcgui, xbmcplugin, xbmcaddon, xbmcvfs

# plugin constants
version = "0.2.1"
plugin = "GoogleMusic-" + version

# xbmc hooks
settings = xbmcaddon.Addon(id='plugin.audio.googlemusic')
language = settings.getLocalizedString
dbg = settings.getSetting( "debug" ) == "true"
dbglevel = 3

# plugin variables
storage = ""
common = ""

if (__name__ == "__main__" ):
    if dbg:
        print plugin + " ARGV: " + repr(sys.argv)
    else:
        print plugin

    import CommonFunctions
    common = CommonFunctions
    common.plugin = plugin

    import GoogleMusicStorage
    storage = GoogleMusicStorage.GoogleMusicStorage()

    if (not settings.getSetting("firstrun")):
        storage.initializeDatabase()
        settings.setSetting("firstrun", "1")

    import GoogleMusicNavigation
    navigation = GoogleMusicNavigation.GoogleMusicNavigation()

    if (not sys.argv[2]):
        navigation.listMenu()
    else:
        params = common.getParameters(sys.argv[2])
        get = params.get
        if (get("action")):
            navigation.executeAction(params)
        elif (get("path")):
            navigation.listMenu(params)
        else:
            print plugin + " ARGV Nothing done.. verify params " + repr(params)
