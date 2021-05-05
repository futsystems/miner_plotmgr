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
        config.read('../config/plotmgr.conf')
    else:  # Python 3
        config.read('config.conf', encoding="utf-8")


    mount_path=config.get('plotter', 'mount_path')

    return {
        'mount_path': mount_path
    }