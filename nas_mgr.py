#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import subprocess
import logging
import logging.config
import driver

logging.config.fileConfig('logging.conf')
logger = logging.getLogger('nas')



class UploadProcess(object):
    def __init__(self):
        self.__pid = None
        self.__port = None
        self.__start_time = None

class NasManager(object):
    def __init__(self):
        self.__upload_process = {}
        self.__current_driver = None


    def get_next_driver(self):
        """
        get next driver used to store plot
        :return:
        """
        return driver.get_plot_drive_to_use()



    def start_nc(self, plot_name):
        """
        start nc to receive plot file
        client user command nc 127.0.0.1 4040 -q2 < plot_file_name to send file
        :param plot_name:
        :return:
        """

        driver_to_use = driver.get_plot_drive_to_use()
        #plots_left = driver.get_device_info("space_free_plots", driver_to_use[1])
        plot_path = '%s/%s' % (driver_to_use[0], plot_name)
        nc_cmd = 'nc -l -q5 -p 4040 > "%s" < /dev/null' % plot_path
        screen_cmd = "screen -d -m -S nc bash -c '%s'" % nc_cmd
        logger.info('Nas server start nc to receive plot file:%s,CMD:%s' % (plot_name, nc_cmd))
        #process = subprocess.Popen(nc_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        #logger.info('NC started,pid:%s' % process.pid)


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
    #driver_to_use = driver.get_plot_drive_to_use()
    #logger.info('driver to use:%s' % driver_to_use[1])
    #plots_left = driver.get_device_info("space_free_plots", driver_to_use[1])
    #logger.info('plots left:%s' % plots_left)










