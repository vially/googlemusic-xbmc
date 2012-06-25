import os
import sys
import xbmcgui

class GoogleMusicLogin():
    def __init__(self):
        self.xbmcgui = sys.modules["__main__"].xbmcgui
        self.settings = sys.modules["__main__"].settings
        self.language = sys.modules["__main__"].language
        self.common = sys.modules["__main__"].common
        self.dbg = sys.modules["__main__"].dbg
        self.gmusicapi = sys.modules["__main__"].gmusicapi

        self._cookie_file = os.path.join(self.settings.getAddonInfo('path'), self.settings.getSetting('cookie_file'))

    def login(self):
        if not self.settings.getSetting('logged_in'):
            self.common.log('Logging in')

            username = self.settings.getSetting('username')
            password = self.settings.getSetting('password')

            self.gmusicapi.login(username, password)

            if not self.gmusicapi.is_authenticated():
                self.common.log("Login failed")
                self.settings.setSetting('logged_in', "")
                dialog = self.xbmcgui.Dialog()
                dialog.ok(self.language(30101), self.language(30102))
            else:
                self.common.log("Login succeeded")
                self.gmusicapi.session.cookies.save(filename=self._cookie_file, ignore_discard=True)
                self.settings.setSetting('logged_in', "1")
        else:
            from cookielib import LWPCookieJar

            self.common.log("Loading cookie from file")
            self.gmusicapi.session.cookies = LWPCookieJar()
            self.gmusicapi.session.cookies.load(filename=self._cookie_file, ignore_discard=True)
            self.gmusicapi.session.logged_in = True
