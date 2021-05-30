#!/usr/bin/python
# -*- coding: utf-8 -*-

import os, sys, time, psutil, datetime, socket
import subprocess
import requests
from common import get_memory_info, get_cpu_info, uptime
import logging, traceback
from driver import get_harvester_driver_list
if sys.version_info.major == 2:   # Python 2
    import thread
else:                             # Python 3
    import _thread as thread

import logging.config
import driver
from message import Response

logging.config.fileConfig('logging.conf')
logger = logging.getLogger('nas')



class UploadProcess(object):
    def __init__(self):
        self.__pid = None
        self.__port = None
        self.__start_time = None

class NasManager(object):
    def __init__(self):
        self.__current_nc = None
        self.__current_driver = None
        self._server_name = socket.gethostname()
        self._start_update_local_info_process()


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
        if self.__current_nc is not None:
            return Response(101, 'nc is already started', self.__current_nc)

        driver_to_use = driver.get_plot_drive_to_use()
        plots_left = driver.get_device_info("space_free_plots", driver_to_use[1])

        plot_path = '%s/%s' % (driver_to_use[0], plot_name)
        nc_cmd = 'nc -l -q3 -p 4040 > "%s" < /dev/null' % plot_path
        #screen_cmd = "screen -d -m -S nc bash -c '%s'" % nc_cmd
        logger.info('Nas server start nc to receive plot file:%s,CMD:%s' % (plot_name, nc_cmd))
        process = subprocess.Popen(nc_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        #process.wait() 不能等待否则会导致http request一直没有返回
        time.sleep(1)
        self.__current_nc = {
            'pid': process.pid,
            'plot_file': plot_name,
            'path': driver_to_use[0],
            'port': 4040,
        }
        logger.info('NC started,pid:%s' % process.pid)
        return Response(0, 'nc start success', self.__current_nc)

    def get_plot_info(self,plot_file):
        size = 0
        if not os.path.isfile(plot_file):
            size = 0
        else:
            size = os.path.getsize(plot_file)

        return {'size': size}


    def stop_nc(self):
        """
        stop nc
        :return:
        """
        logger.info('Nas server stop nc')
        nc_cmd='/usr/bin/killall -9 nc >/dev/null 2>&1'
        #Popen创建进程后直接返回 需要执行wait确保执行完毕
        process = subprocess.Popen(nc_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process.wait()
        #os.system(nc_cmd)
        # wait some time to wait nc stop complete try check_out
        time.sleep(2)
        self.__current_nc = None
        return Response(0, 'nc stop success')

    def get_current_nc(self):
        return self.__current_nc


    def register(self):
        register_thread = thread.start_new_thread(self._register, (1,))

    def _register(self, args):
        # wait 5 secends to let flask run
        time.sleep(5)
        # returns the time in seconds since the epoch
        last_reboot_ts = psutil.boot_time()
        # coverting the date and time in readable format
        last_reboot = datetime.datetime.fromtimestamp(last_reboot_ts).strftime('%Y-%m-%d %H:%M:%S')

        hostname = socket.gethostname()
        payload = {'name': hostname,
                   'boot_time':last_reboot,
                   'cpu': get_cpu_info(),
                   'memory': get_memory_info(),
                   }
        logger.info('register to manager node:%s' % payload)

        response = requests.post('http://nagios.futsystems.com:9090/server/harvester/register', json=payload)
        logger.info('status:%s data:%s' % (response.status_code, response.json()))

    def _start_update_local_info_process(self):
        logger.info('start update local info process')
        self._update_local_info_thread = thread.start_new_thread(self.update_local_info_process, (1,))

    def update_local_info_process(self, args):
        while True:
            try:
                data = {
                    'name': self._server_name,
                    'info': self.get_local_info(),
                    'cpu': get_cpu_info(),
                    'memory': get_memory_info(),

                }
                logger.info('send local info to manager node:%s' % data)
                response = requests.post('http://nagios.futsystems.com:9090/server/harvester/local-info/update', json= data)
                logger.info('status:%s data:%s' % (response.status_code, response.json()))

                # sleep 10 minutes
                time.sleep(1*60)
            except Exception as e:
                logger.error(traceback.format_exc())


    def __get_internal_ip(self):
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        return s.getsockname()[0]

    def get_local_info(self):
        internal_ip = self.__get_internal_ip()

        driver_list = get_harvester_driver_list()
        plot_cnt = 0
        for item in driver_list:
            plot_cnt = plot_cnt + item['total_current_plots']
        driver_cnt = len(driver_list)
        info = {
            'internal_ip':internal_ip,
            'uptime': uptime(),
            'plot_cnt': plot_cnt,
            'driver_cnt': driver_cnt,

        }
        return  info

if __name__ == '__main__':
    #df_cmd = "screen -d -m -S nc bash -c 'nc -l -q5 -p 4040 >/mnt/dst/00/test.file'"
    #process = subprocess.Popen(df_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    #err = process.stderr.read()
    driver_list = get_harvester_driver_list()
    logging.info(driver_list)
    #driver_to_use = driver.get_plot_drive_to_use()
    #logger.info('driver to use:%s' % driver_to_use[1])
    #plots_left = driver.get_device_info("space_free_plots", driver_to_use[1])
    #logger.info('plots left:%s' % plots_left)










