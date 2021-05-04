#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import subprocess
import logging
import logging.config

logger = logging.getLogger(__name__)


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
        logger.info('Nas server start nc to receive plotfile:%s,cmd:%s' % (plot_name,screen_cmd))
        os.spawnl(os.P_DETACH, screen_cmd)


if __name__ == '__main__':
    logging.config.fileConfig("logging.conf")
    logger = logging.getLogger(__name__)

    #df_cmd = "screen -d -m -S nc bash -c 'nc -l -q5 -p 4040 >/mnt/dst/00/test.file'"
    #process = subprocess.Popen(df_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    #err = process.stderr.read()
    nas = NasManager()
    nas.start_nc('file1')


