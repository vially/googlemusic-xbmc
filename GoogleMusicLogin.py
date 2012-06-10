import os
import sys
import xbmcgui

class GoogleMusicLogin():
    def __init__(self):
        self.settings = sys.modules["__main__"].settings
        self.language = sys.modules["__main__"].language
        self.common = sys.modules["__main__"].common
        self.dbg = sys.modules["__main__"].dbg
        self.api = sys.modules["__main__"].api

        self._cookie_file = os.path.join(self.settings.getAddonInfo('path'), 'gmusic_cookies.txt')

    def login(self):
        if not self.settings.getSetting('logged_in'):
            self.common.log('Logging in')

            username = self.settings.getSetting('username')
            password = self.settings.getSetting('password')

            self.api.login(username, password)

            if not self.api.is_authenticated():
                self.common.log("Login failed")
                self.settings.setSetting('logged_in', "")
                dialog = xbmcgui.Dialog()
                dialog.ok(self.language(30101), self.language(30102))
            else:
                self.common.log("Login succeeded")
                self.api.session.cookies.save(filename=self._cookie_file, ignore_discard=True)
                self.settings.setSetting('logged_in', "1")
        else:
            from cookielib import LWPCookieJar

            self.common.log("Loading cookie from file")
            self.api.session.cookies = LWPCookieJar()
            self.api.session.cookies.load(filename=self._cookie_file, ignore_discard=True)
            self.api.session.logged_in = True
