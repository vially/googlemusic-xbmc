import os
import sys
import time
from datetime import datetime

from gmusicapi import Mobileclient, Webclient


class GoogleMusicLogin():
    def __init__(self):
        self.main      = sys.modules["__main__"]
        self.xbmcgui   = self.main.xbmcgui
        self.xbmc      = self.main.xbmc
        self.settings  = self.main.settings

        if self.getDevice():
            self.gmusicapi = Mobileclient(debug_logging=False,validate=False)
        else:
            self.gmusicapi = Webclient(debug_logging=False,validate=False)


    def checkCookie(self):
        # Remove cookie data if it is older then 7 days
        if self.settings.getSetting('cookie-date') != None and len(self.settings.getSetting('cookie-date')) > 0:
            if (datetime.now() - datetime(*time.strptime(self.settings.getSetting('cookie-date'), '%Y-%m-%d %H:%M:%S.%f')[0:6])).days >= 7:
                self.clearCookie()

    def checkCredentials(self):
        if not self.settings.getSetting('username'):
            self.settings.openSettings()

    def getApi(self):
        return self.gmusicapi

    def getDevice(self):
        return self.settings.getSetting('device_id')

    def initDevice(self):
        device_id = self.settings.getSetting('device_id')

        if not device_id:
            self.main.log('Trying to fetch the device_id')
            webclient = Webclient(debug_logging=False,validate=False)
            self.checkCredentials()
            username = self.settings.getSetting('username')
            password = self.settings.getSetting('password')
            webclient.login(username, password)
            if webclient.is_authenticated():
                devices = webclient.get_registered_devices()
                self.main.log(repr(devices))
                for device in devices:
                    if device["type"] in ("PHONE","IOS"):
                        device_id = str(device["id"])
                        break
            if device_id:
                if device_id.lower().startswith('0x'): device_id = device_id[2:]
                self.settings.setSetting('device_id',device_id)
                self.main.log('Found device_id: '+device_id)


    def clearCookie(self):
        self.settings.setSetting('logged_in', "")
        self.settings.setSetting('authtoken', "")
        self.settings.setSetting('cookie-xt', "")
        self.settings.setSetting('cookie-sjsaid', "")
        self.settings.setSetting('device_id', "")

    def logout(self):
        self.gmusicapi.logout()

    def login(self,nocache=False):
        if nocache or not self.settings.getSetting('logged_in'):
            self.main.log('Logging in')
            username = self.settings.getSetting('username')
            password = self.settings.getSetting('password')

            try:
                self.gmusicapi.login(username, password)
            except Exception as e:
                self.main.log(repr(e))
            if not self.gmusicapi.is_authenticated():
                self.main.log("Login failed")
                self.settings.setSetting('logged_in', "")
                self.language = self.settings.getLocalizedString
                dialog = self.xbmcgui.Dialog()
                dialog.ok(self.language(30101), self.language(30102))
                self.settings.openSettings()
            else:
                self.main.log("Login succeeded")
                if not nocache:
                    self.settings.setSetting('logged_in', "1")
                    self.settings.setSetting('authtoken', self.gmusicapi.session._authtoken)
                    self.settings.setSetting('cookie-xt', self.gmusicapi.session._rsession.cookies['xt'])
                    self.settings.setSetting('cookie-sjsaid', self.gmusicapi.session._rsession.cookies['sjsaid'])
                    self.settings.setSetting('cookie-date', str(datetime.now()))
        else:

            self.main.log("Loading auth from cache")
            self.gmusicapi.session._authtoken = self.settings.getSetting('authtoken')
            self.gmusicapi.session._rsession.cookies['xt'] = self.settings.getSetting('cookie-xt')
            self.gmusicapi.session._rsession.cookies['sjsaid'] = self.settings.getSetting('cookie-sjsaid')
            self.gmusicapi.session.is_authenticated = True
