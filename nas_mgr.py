#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import subprocess
import logging
import logging.config

logging.config.fileConfig('logging.conf')
logger = logging.getLogger('nas')


class UploadProcess(object):
    def __init__(self):
        self.__pid = None
        self.__port = None
        self.__start_time = None

class NasManager(object):
    def __init__(self):
        self.__upload_process = { }


    def start_nc(self, plot_name):
        """
        start nc to receive plot file
        client user command nc 127.0.0.1 4040 -q2 < plot_file_name to send file
        :param plot_name:
        :return:
        """
        plot_path= '/mnt/dst/00/%s' % plot_name
        nc_cmd = 'nc -l -q5 -p 4040 > "%s" < /dev/null' % plot_path
        screen_cmd = "screen -d -m -S nc bash -c '%s'" % nc_cmd
        logger.info('Nas server start nc to receive plotfile:%s,CMD:%s' % (plot_name, nc_cmd))
        process = subprocess.Popen(nc_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info('NC started,pid:%s' % process.pid)

    def stop_nc(self):
        """
        stop nc
        :return:
        """
        logger.info('Nas server stop nc')
        nc_cmd='/usr/bin/killall -9 nc >/dev/null 2>&1'
        process = subprocess.Popen(nc_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

if __name__ == '__main__':
    #df_cmd = "screen -d -m -S nc bash -c 'nc -l -q5 -p 4040 >/mnt/dst/00/test.file'"
    #process = subprocess.Popen(df_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    #err = process.stderr.read()
    nas = NasManager()
    nas.start_nc('file1')


