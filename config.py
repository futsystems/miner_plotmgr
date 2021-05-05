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

    if sys.version_info.major == 2:  # Python 2
        with open('./config.conf', 'rb') as cfgfile:
            config.readfp(cfgfile)
    else:  # Python 3
        config.read_file(open('config.conf', 'rb'))


    mount_path=config.get('plotter', 'mount_path')

    return {
        'mount_path': mount_path

    }