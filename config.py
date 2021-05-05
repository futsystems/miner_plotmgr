# -*- coding: utf-8 -*-

import sys,os

if sys.version_info.major == 2:   # Python 2
    import ConfigParser
else:                             # Python 3
    import configparser as ConfigParser



def get_plotter_setting():
    """

    """
    config=ConfigParser.ConfigParser()
    with open('./config.conf', 'rb') as cfgfile:
        config.readfp(cfgfile)
        mount_path=config.get('plotter', 'mount_path')

    return {
        'mount_path': mount_path

    }