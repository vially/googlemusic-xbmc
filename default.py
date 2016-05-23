import sys, utils, xbmc


if (__name__ == "__main__" ):
    utils.log(" ARGV: " + repr(sys.argv))

    params = utils.paramsToDict(sys.argv[2])
    action = params.pop('action','')

    if action == 'play_song':

        import GoogleMusicPlaySong
        GoogleMusicPlaySong.GoogleMusicPlaySong().play(params)

    else:

        reload(sys)
        sys.setdefaultencoding("utf-8")

        import GoogleMusicStorage
        storage = GoogleMusicStorage.storage
        import GoogleMusicLogin
        login = GoogleMusicLogin.GoogleMusicLogin()

        addon = utils.addon

        # if version changed clear cache
        if not addon.getSetting('version') or addon.getSetting('version') != addon.getAddonInfo('version'):
           storage.clearCache()
           login.clearCookie()
           addon.setSetting('version', addon.getAddonInfo('version'))

        # check for initing cookies, db and library
        storage.checkDbInit()
        login.checkCredentials()
        login.checkCookie()
        login.initDevice()

        # check if library needs to be loaded
        if addon.getSetting('fetched_all_songs') == '0':

            xbmc.executebuiltin("XBMC.Notification(%s,%s,5000,%s)" % (utils.plugin, utils.tryEncode(addon.getLocalizedString(30105)) ,addon.getAddonInfo('icon')))
            utils.log('Loading library')
            import GoogleMusicApi
            GoogleMusicApi.GoogleMusicApi().loadLibrary()

            if addon.getSetting('auto_export')=='true' and addon.getSetting('export_path'):
                import GoogleMusicActions
                GoogleMusicActions.GoogleMusicActions().exportLibrary(addon.getSetting('export_path'))

        if action:

            import GoogleMusicActions
            GoogleMusicActions.GoogleMusicActions().executeAction(action, params)

        else:

            import GoogleMusicNavigation
            GoogleMusicNavigation.GoogleMusicNavigation().listMenu(params)

