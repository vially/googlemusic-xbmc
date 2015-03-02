import utils, xbmc
from gmusicapi import Mobileclient, Webclient
from datetime import datetime

class GoogleMusicLogin():
    def __init__(self):
        self.gmusicapi = Mobileclient(debug_logging=False,validate=False,verify_ssl=True)

    def checkCookie(self):
        # Remove cookie data if it is older then 7 days
        if utils.addon.getSetting('cookie-date') != None and len(utils.addon.getSetting('cookie-date')) > 0:
            import time
            if (datetime.now() - datetime(*time.strptime(utils.addon.getSetting('cookie-date'), '%Y-%m-%d %H:%M:%S.%f')[0:6])).days >= 7:
                self.clearCookie()

    def checkCredentials(self):
        if not utils.addon.getSetting('username'):
            utils.addon.openSettings()
        if utils.addon.getSetting('password'):
            import base64
            utils.addon.setSetting('encpassword',base64.b64encode(utils.addon.getSetting('password')))
            utils.addon.setSetting('password','')

    def getApi(self):
        return self.gmusicapi

    def getStreamUrl(self,song_id):
        device_id = self.getDevice()
        utils.log("getStreamUrl songid: %s device: %s"%(song_id,device_id))

        if device_id:
            #retrieve stream quality from settings
            quality = { '0':'hi','1':'med','2':'low' } [utils.addon.getSetting('quality')]
            utils.log("getStreamUrl quality: %s"%quality)

            stream_url = self.gmusicapi.get_stream_url(song_id, device_id, quality)
        else:
            utils.log("NO DEVICE, using WEBCLIENT to stream")
            self.gmusicapi = Webclient(debug_logging=False,validate=False,verify_ssl=False)
            self.login(client='web')
            streams = self.gmusicapi.get_stream_urls(song_id)
            if len(streams) > 1:
                self.language = utils.addon.getLocalizedString
                xbmc.executebuiltin("XBMC.Notification(%s,%s)" %s (utils.plugin, self.language(30104)))
                raise Exception('All Access track not playable, no mobile device found in account!')
            stream_url = streams[0]

        return stream_url

    def getDevice(self):
        return utils.addon.getSetting('device_id')

    def initDevice(self):
        device_id = utils.addon.getSetting('device_id')

        if not device_id:
            utils.log('Trying to fetch the device_id')
            webclient = Webclient(debug_logging=False,validate=False,verify_ssl=False)

            self.login()
            webclient.session._authtoken = utils.addon.getSetting('authtoken-mobile')
            webclient.session.is_authenticated = True
            try:
                webclient.session.getCookies()
                #xtCookie = webclient.session._rsession.cookies['xt']
                #sjsaidCookie = webclient.session._rsession.cookies['sjsaid']
                #devices = self.gmusicapi.get_devices(xtCookie,sjsaidCookie)

                devices = webclient.get_registered_devices()
                utils.log(repr(devices))
                for device in devices:
                    if device["type"] in ("PHONE","IOS"):
                        device_id = str(device["id"])
                        break
            except:
                utils.log('No device found, using default.')
                device_id = "333c60412226c96f"

            if device_id:
                if device_id.lower().startswith('0x'): device_id = device_id[2:]
                utils.addon.setSetting('device_id',device_id)
                utils.log('Found device_id: '+device_id)
            else:
                utils.log('No device found!')


    def clearCookie(self):
        utils.addon.setSetting('logged_in-mobile', "")
        utils.addon.setSetting('logged_in-web', "")
        utils.addon.setSetting('authtoken-mobile', "")
        utils.addon.setSetting('authtoken-web', "")
        utils.addon.setSetting('cookie-xt', "")
        utils.addon.setSetting('cookie-sjsaid', "")
        utils.addon.setSetting('device_id', "")

    def logout(self):
        self.gmusicapi.logout()

    def login(self,nocache=False,client='mobile'):
        if nocache or not utils.addon.getSetting('logged_in-'+client):
            import base64, xbmcgui

            utils.log('Logging in')
            username = utils.addon.getSetting('username')
            password = base64.b64decode(utils.addon.getSetting('encpassword'))

            try:
                self.gmusicapi.login(username, password)
            except Exception as e:
                utils.log(repr(e))
            if not self.gmusicapi.is_authenticated():
                utils.log("Login failed")
                utils.addon.setSetting('logged_in-'+client, "")
                self.language = utils.addon.getLocalizedString
                dialog = xbmcgui.Dialog()
                dialog.ok(self.language(30101), self.language(30102))
                utils.addon.openSettings()
            else:
                utils.log("Login succeeded")
                #print repr(self.gmusicapi.session._rsession.cookies)
                if not nocache:
                    utils.addon.setSetting('logged_in-'+client, "1")
                    utils.addon.setSetting('authtoken-'+client, self.gmusicapi.session._authtoken)
                    #for i in self.gmusicapi.session._rsession.cookies:
                    #    utils.log("COOKIES FOUND::"+repr(i))
                    if(client == 'web'):
                        utils.addon.setSetting('cookie-xt', self.gmusicapi.session._rsession.cookies['xt'])
                        utils.addon.setSetting('cookie-sjsaid', self.gmusicapi.session._rsession.cookies['sjsaid'])
                    utils.addon.setSetting('cookie-date', str(datetime.now()))
        else:

            utils.log("Loading auth from cache")
            self.gmusicapi.session._authtoken = utils.addon.getSetting('authtoken-'+client)
            if(client == 'web'):
                self.gmusicapi.session._rsession.cookies['xt'] = utils.addon.getSetting('cookie-xt')
                self.gmusicapi.session._rsession.cookies['sjsaid'] = utils.addon.getSetting('cookie-sjsaid')
            self.gmusicapi.session.is_authenticated = True