#Google Music addon for XBMC

##Usage and notes

**This plugin is a very early release and uses an [Unofficial-Google-Music-Api](https://github.com/simon-weber/Unofficial-Google-Music-API) so use at your own risk.**

This plugin has been tested with XBMC 11.0 Eden on Linux running Python 2.7.3

##Installation

This plugin requires the [Unofficial-Google-Music-Api](https://github.com/simon-weber/Unofficial-Google-Music-API) to be installed on your system. For details read the [installation instructions](https://github.com/simon-weber/Unofficial-Google-Music-API#installation).

This plugin also requires two additional XBMC plugins to be installed: `script.module.parsedom (0.9.2)` and `script.common.plugin.cache (0.9.2)`. You have to either install them manually or install an addon from the official XBMC repository which requires them (eg: YouTube).

Clone this repository into a directory named plugin.audio.googlemusic in your xbmc addons directory:

    $ git clone https://github.com/vially/googlemusic-xbmc.git ~/.xbmc/addons/plugin.audio.googlemusic

Open XBMC and navigate to the Music Add-ons list. An addon called Google Music should now appear in the list. Set your Google Music credentials in the addon settings dialog.

That's it. You should now be able to run the plugin and enjoy your Google Music from XBMC.

##Features

At the moment it only supports playback of your Google Music songs into XBMC.
