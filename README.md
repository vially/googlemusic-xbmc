#Google Music addon for XBMC

##Usage and notes

**This plugin is a very early release and uses an [Unofficial-Google-Music-Api](https://github.com/simon-weber/Unofficial-Google-Music-API) so use at your own risk.**

This plugin has been tested with XBMC 11.0 Eden on Linux running Python 2.7.3

##Installation

To install this add-on you must download it from the [Downloads](https://github.com/vially/googlemusic-xbmc/downloads) page and install it using the Add-on Manager from within XBMC by going to:

1. Settings
2. Add-ons
3. Install from zip file
4. Enter the path to the downloaded file and select OK
5. Open the add-on settings dialog to set your credentials

That's it. You should now be able to run the plugin and enjoy your Google Music from XBMC.

##Features

At the moment it only supports playback of your Google Music songs into XBMC.

##Known issues

###setuptools
This add-on has a transitive dependency on [script.module.protobuf](http://mirrors.xbmc.org/addons/eden/script.module.protobuf/) which requires that [setuptools](http://pypi.python.org/pypi/setuptools) is installed on your system.
However, if you don't have setuptools installed on your system you can still use this plugin by replacing the code in `addons/script.module.protobuf/lib/google/__init__.py` from this:

```py
__import__('pkg_resources').declare_namespace(__name__)
```

into this:

```py
try:
    __import__('pkg_resources').declare_namespace(__name__)
except ImportError:
    __path__ = __import__('pkgutil').extend_path(__path__, __name__)
```

###Expired cookies
In order to avoid logging in to Google Music every time a request to the Google Music Api is being made, this add-on stores the user session in a cookie file: `gmusic_cookies.txt` which is used for all the subsequent requests.
Since no checks are being made to verify that the cookie file is still valid, when the cookies in this file expire the Api calls will start failing and this add-on will stop working.
When this happens you will have to open the add-on settings dialog, go to the Advanced tab and select "Clear cookies".

Hopefully this will be fixed in the next release so this should be just a temporary problem.
