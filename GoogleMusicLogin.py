import os
import sys
import time
from datetime import datetime

from gmusicapi import Mobileclient, Webclient

class GoogleMusicLogin():
    def __init__(self):
        self.main      = sys.modules["__main__"]
        self.xbmcgui   = self.main.xbmcgui
        self.settings  = self.main.settings
        self.gmusicapi = Mobileclient(debug_logging=False,validate=False,verify_ssl=True)

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

    def getStreamUrl(self,song_id):
        device_id = self.getDevice()
        self.main.log("getStreamUrl songid: %s device: %s"%(song_id,device_id))

        if device_id:
            #retrieve stream quality from settings
            quality = { '0':'hi','1':'med','2':'low' } [self.settings.getSetting('quality')]
            self.main.log("getStreamUrl quality: %s"%quality)

            stream_url = self.gmusicapi.get_stream_url(song_id, device_id, quality)
        else:
            self.main.log("NO DEVICE, using WEBCLIENT to stream")
            self.gmusicapi = Webclient(debug_logging=False,validate=False,verify_ssl=False)
            self.login(client='web')
            streams = self.gmusicapi.get_stream_urls(song_id)
            if len(streams) > 1:
                import xbmc
                xbmc.executebuiltin("XBMC.Notification("+self.main.plugin+",'All Access track not playable')")
                raise Exception('All Access track not playable, no mobile device found in account!')
            stream_url = streams[0]

        return stream_url

    def getDevice(self):
        return self.settings.getSetting('device_id')

    def initDevice(self):
        device_id = self.settings.getSetting('device_id')

        if not device_id:
            self.main.log('Trying to fetch the device_id')
            webclient = Webclient(debug_logging=False,validate=False,verify_ssl=False)
            self.checkCredentials()
            username = self.settings.getSetting('username')
            password = self.settings.getSetting('password')
            try:
                webclient.login(username, password)
                if webclient.is_authenticated():
                    devices = webclient.get_registered_devices()
                    self.main.log(repr(devices))
                    for device in devices:
                        if device["type"] in ("PHONE","IOS"):
                            device_id = str(device["id"])
                            break
            except:
                dialog = self.xbmcgui.Dialog()
                dialog.ok("Device not Found", "Please provide a valid device_id in the addon settings")
                self.settings.openSettings()
                self.xbmc.executebuiltin("XBMC.RunPlugin(%s)" % sys.argv[0])
            if device_id:
                if device_id.lower().startswith('0x'): device_id = device_id[2:]
                self.settings.setSetting('device_id',device_id)
                self.main.log('Found device_id: '+device_id)
            else:
                self.main.log('No device found!')


    def clearCookie(self):
        self.settings.setSetting('logged_in-mobile', "")
        self.settings.setSetting('logged_in-web', "")
        self.settings.setSetting('authtoken-mobile', "")
        self.settings.setSetting('authtoken-web', "")
        self.settings.setSetting('cookie-xt', "")
        self.settings.setSetting('cookie-sjsaid', "")
        self.settings.setSetting('device_id', "")

    def logout(self):
        self.gmusicapi.logout()

    def login(self,nocache=False,client='mobile'):
        if nocache or not self.settings.getSetting('logged_in-'+client):
            self.main.log('Logging in')
            username = self.settings.getSetting('username')
            password = self.settings.getSetting('password')

            try:
                self.gmusicapi.login(username, password)
            except Exception as e:
                self.main.log(repr(e))
            if not self.gmusicapi.is_authenticated():
                self.main.log("Login failed")
                self.settings.setSetting('logged_in-'+client, "")
                self.language = self.settings.getLocalizedString
                dialog = self.xbmcgui.Dialog()
                dialog.ok(self.language(30101), self.language(30102))
                self.settings.openSettings()
            else:
                self.main.log("Login succeeded")
                if not nocache:
                    self.settings.setSetting('logged_in-'+client, "1")
                    self.settings.setSetting('authtoken-'+client, self.gmusicapi.session._authtoken)
                    #for i in self.gmusicapi.session._rsession.cookies:
                    #    self.main.log("COOKIES FOUND::"+repr(i))
                    if(client == 'web'):
                        self.settings.setSetting('cookie-xt', self.gmusicapi.session._rsession.cookies['xt'])
                        self.settings.setSetting('cookie-sjsaid', self.gmusicapi.session._rsession.cookies['sjsaid'])
                    self.settings.setSetting('cookie-date', str(datetime.now()))
        else:

            self.main.log("Loading auth from cache")
            self.gmusicapi.session._authtoken = self.settings.getSetting('authtoken-'+client)
            if(client == 'web'):
                self.gmusicapi.session._rsession.cookies['xt'] = self.settings.getSetting('cookie-xt')
                self.gmusicapi.session._rsession.cookies['sjsaid'] = self.settings.getSetting('cookie-sjsaid')
            self.gmusicapi.session.is_authenticated = True
