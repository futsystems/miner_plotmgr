#!/usr/bin/python
# -*- coding: utf-8 -*-

import os, sys, time, psutil, datetime, socket
import subprocess
import requests
from common import get_memory_info, get_cpu_info, uptime, get_free_port, get_filecreatetime, get_filesize
import logging, traceback

if sys.version_info.major == 2:   # Python 2
    import thread
else:                             # Python 3
    import _thread as thread

import logging.config
import driver
import threading

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
        self._server_name = socket.gethostname()
        self._server_id = self._server_name.split('-')[1]

        self._nc_map = {}
        self._nc_map_lock = threading.Lock()

        query = {'id': self._server_id}
        response = requests.get('http://114.215.171.108:9090/server/harvester/config', params=query)
        self.config = response.json()
        logger.info('harvester config:%s' % self.config)

    def get_next_driver(self):
        """
        get next driver used to store plot
        :return:
        """
        return driver.get_plot_drive_to_use()

    def start_nc(self, ip_addr, plot_name):
        """
        start nc to receive plot file
        client user command nc 127.0.0.1 4040 -q2 < plot_file_name to send file
        :param plot_name:
        :return:
        """
        self._nc_map_lock.acquire()
        try:
            logger.info('ip:%s start nc to send file:%s' % (ip_addr, plot_name))
            if ip_addr in self._nc_map:
                return Response(101, 'nc is already started', self._nc_map[ip_addr])

            port = get_free_port()

            used_driver_list = [item['driver'] for item in self._nc_map.values()]
            driver_to_use = driver.get_plot_drive_to_use(used_driver_list)
            logger.info('used_driver_list:%s' % used_driver_list)
            logger.info('driver_to_use:%s path:%s' % (driver_to_use[1], driver_to_use[0]))

            #logger.info('driver_to_use:%s' % [item['driver'] for item in driver_to_use])

            if len(driver_to_use) > 0:

                plots_left = driver.get_device_info("space_free_plots", driver_to_use[1])

                plot_path = '%s/%s' % (driver_to_use[0], plot_name)
                nc_cmd = 'nc -l -q 10 -p %s > "%s" < /dev/null' % (port, plot_path)
                #screen_cmd = "screen -d -m -S nc bash -c '%s'" % nc_cmd
                logger.info('Nas server start nc to receive plot file:%s,CMD:%s driver:%s' % (plot_name, nc_cmd, driver_to_use[1]))
                process = subprocess.Popen(nc_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                #process.wait() 不能等待否则会导致http request一直没有返回
                time.sleep(1)
                self._nc_map[ip_addr] = {
                    'pid': process.pid,
                    'plot_file': plot_name,
                    'path': driver_to_use[0],
                    'port': port,
                    'driver': driver_to_use[1]
                }

                logger.info('NC started,pid:%s port:%s' % (process.pid, port))
                return Response(0, 'nc start success', self._nc_map[ip_addr])
            else:
                logger.info('there is no driver to store plot,please add or replace')
                return Response(1, 'nc start fail', None)
        except Exception as e:
            logger.error(traceback.format_exc())
        finally:
            self._nc_map_lock.release()


    def get_plot_info(self, plot_file):
        size = 0
        if not os.path.isfile(plot_file):
            size = 0
        else:
            size = os.path.getsize(plot_file)

        return {'size': size}


    def stop_nc(self, ip_addr):
        """
        stop nc
        :return:
        """
        #self._nc_map_lock.acquire()

        if ip_addr in self._nc_map:
            data = self._nc_map[ip_addr]
            logger.info('Nas server stop nc ip:%s data:%s' % (ip_addr, data))
            pid = data['pid']
            logger.info('stop nc pid:%s for file:%s' % (data['pid'], data['plot_file']))
            nc_cmd = '/usr/bin/kill %s nc >/dev/null 2>&1' % pid
            # Popen创建进程后直接返回 需要执行wait确保执行完毕
            process = subprocess.Popen(nc_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            process.wait()
            time.sleep(2)
            self._nc_map.pop(ip_addr, None)
        else:
            pass
        #self._nc_map_lock.release()

        return Response(0, 'nc stop success')

    def on_start(self):
        register_thread = thread.start_new_thread(self._on_start, (1,))

    def _on_start(self, args):
        # wait 5 secends to let flask run
        time.sleep(5)

        self.register()

        self.start_update_local_info_process()


    def register(self):
        # returns the time in seconds since the epoch
        last_reboot_ts = psutil.boot_time()
        # coverting the date and time in readable format
        last_reboot = datetime.datetime.fromtimestamp(last_reboot_ts).strftime('%Y-%m-%d %H:%M:%S')

        hostname = socket.gethostname()
        payload = {'name': hostname,
                   'boot_time': last_reboot,
                   'cpu': get_cpu_info(),
                   'memory': get_memory_info(),
                   }
        logger.info('register to manager node:%s' % payload)

        response = requests.post('http://nagios.futsystems.com:9090/server/harvester/register', json=payload)
        logger.info('register status:%s data:%s' % (response.status_code, response.json()))


    def start_update_local_info_process(self):
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
                logger.info('update local info status:%s data:%s' % (response.status_code, response.json()))

                # sleep 10 minutes
                time.sleep(1*60)
            except Exception as e:
                logger.error(traceback.format_exc())


    def __get_internal_ip(self):
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        return s.getsockname()[0]

    def get_file_count(path):
        return len([name for name in os.listdir(path) if os.path.isfile(os.path.join(path, name))])

    def get_local_info(self):
        from driver import get_harvester_driver_list
        internal_ip = self.__get_internal_ip()
        driver_list = get_harvester_driver_list()
        plot_cnt = 0
        file_cnt = 0
        for item in driver_list:
            plot_cnt = plot_cnt + item['total_current_plots']
            file_cnt = file_cnt + item['file_cnt']

        driver_cnt = len(driver_list)

        info = {
            'internal_ip':internal_ip,
            'uptime': uptime(),
            'plot_cnt': plot_cnt,
            'driver_cnt': driver_cnt,
            'file_cnt': file_cnt

        }
        return info

    def clean_harvester_driver(self):
        from driver import get_harvester_driver_list
        cnt=0
        for driver in get_harvester_driver_list():
            files = os.listdir(driver['mount_path'])
            logger.info('driver:%s path:%s files cnt:%s' % (driver['device'], driver['mount_path'], len(files)))
            for file in files:
                full_name = '%s/%s' % (driver['mount_path'], file)
                create_time = get_filecreatetime(full_name)
                #logger.info('file:%s time:%s' % (file, create_time))
                # 过滤出24小时之前创建的文件
                if os.path.isfile(full_name)  and ((datetime.datetime.now() - create_time).total_seconds()/3600 > 24):
                    file_size = get_filesize(full_name)
                    if file_size < 102: # check k32 file size
                        logger.info('delete file:%s' % full_name)
                        os.remove(full_name)
                        cnt = cnt + 1
        logger.info('delete file cnt:%s' % cnt)

if __name__ == '__main__':
    pass











