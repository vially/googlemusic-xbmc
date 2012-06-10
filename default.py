import sys, xbmc, xbmcgui, xbmcplugin, xbmcaddon
from gmusicapi.api import Api

# plugin constants
version = "0.1.0"
plugin = "GoogleMusic-" + version

# xbmc hooks
settings = xbmcaddon.Addon(id='plugin.audio.googlemusic')
language = settings.getLocalizedString
dbg = settings.getSetting( "debug" ) == "true"
dbglevel = 3

# plugin variables
api = Api()
cache = ""
common = ""

if (__name__ == "__main__" ):
    if dbg:
        print plugin + " ARGV: " + repr(sys.argv)
    else:
        print plugin

    try:
        import StorageServer
    except:
        import storageserverdummy as StorageServer
    cache = StorageServer.StorageServer("GoogleMusic")

    import CommonFunctions
    common = CommonFunctions
    common.plugin = plugin

    import GoogleMusicLogin
    login = GoogleMusicLogin.GoogleMusicLogin()
    login.login()

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
