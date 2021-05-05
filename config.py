# -*- coding: utf-8 -*-

import sys,os


def get_plotter_setting():
    """

    """
    import ConfigParser
    config=ConfigParser.ConfigParser()
    with open('./config.conf', 'rb') as cfgfile:
        config.readfp(cfgfile)
        mount_path=config.get('plotter', 'mount_path')

    return {
        'mount_path': mount_path

    }