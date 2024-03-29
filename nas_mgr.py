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

from common import  NMS_HOST

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
        self._hpool_map = {}

        query = {'id': self._server_id}
        response = requests.get('http://%s/server/harvester/config' % NMS_HOST, params=query)
        self.config = response.json()
        logger.info('harvester config:%s' % self.config)

        self.driver_report = None

    @property
    def harvester_name(self):
        return self._server_name

    def init_moniter_process(self, index=0):
        path = '/opt/hpool/%s' % index
        logger.info('int logmoniter for path:%s' % path)
        from log_monitor import LogMonitor
        log_path = '%s/log/miner.log.log' % path
        moniter = LogMonitor(self, index, log_path)
        moniter.start_moniter()
        self._hpool_map[moniter.service_name] = moniter

    def start_moniter(self):
        driver_list = driver.get_nas_driver_list()
        driver_cnt = len(driver_list)
        group = int(driver_cnt / 15)

        if driver_cnt % 15 > 0:
            group = group + 1

        logger.info('harvester has %s drivers, and will service in %s groups' % (driver_cnt, group))

        idx=0
        while idx < group:
            self.init_moniter_process(idx)
            idx = idx + 1


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

            if driver_to_use is not None:
                plots_left = driver.get_device_info("space_free_plots", driver_to_use[1])

                logger.info('used_driver_list:%s' % used_driver_list)
                logger.info('driver_to_use:%s path:%s plots left:%s' % (driver_to_use[1], driver_to_use[0], plots_left))

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
        self.start_update_disk_report_process()
        #self.start_moniter()



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

        url = 'http://%s/server/harvester/register' % NMS_HOST
        logger.info('register to manager node:%s url:%s' % (payload, url))

        response = requests.post(url, json=payload)
        logger.info('data:%s' % response.content)
        logger.info('register status:%s data:%s' % (response.status_code, response.json()))

    def start_update_local_info_process(self):
        logger.info('start update local info process')
        self._update_local_info_thread = thread.start_new_thread(self.update_local_info_process, (1,))

    def start_update_disk_report_process(self):
        logger.info('start update disk report process')
        self._update_disk_report_thread = thread.start_new_thread(self.generate_disk_report, (1,))

    def generate_disk_report(self, args):
        while True:
            try:
                logger.info('==== generate harvester driver report ====')
                self.driver_report = driver.get_harvester_driver_report()
                # sleep 30 minutes
                time.sleep(30*60)
            except Exception as e:
                logger.error(traceback.format_exc())

    def update_local_info_process(self, args):
        while True:
            try:
                data = {
                    'name': self._server_name,
                    'info': self.get_local_info(),
                    'cpu': get_cpu_info(),
                    'memory': get_memory_info(),
                    'harvester_service': self.get_harvester_service_info(),
                }
                logger.info('send local info to manager node:%s' % data)
                url = 'http://%s/server/harvester/local-info/update' % NMS_HOST
                response = requests.post(url, json= data)
                logger.info('update local info status:%s data:%s' % (response.status_code, response.json()))

                # sleep 10 minutes
                time.sleep(1*60)
            except Exception as e:
                logger.error(traceback.format_exc())


    def _get_network(self):
        data = {}
        from netifaces import interfaces, ifaddresses, AF_INET
        for ifaceName in interfaces():
            addresses = [i['addr'] for i in ifaddresses(ifaceName).setdefault(AF_INET, [{'addr': 'No IP addr'}])]
            if len(addresses) >= 1 and addresses[0] != 'No IP addr':
                #logger.info('interface:%s address:%s' % (ifaceName, addresses))
                if addresses[0].startswith('10.6'):
                    data['biz_interface'] = ifaceName
                    data['biz_ip'] = addresses[0]
                if addresses[0].startswith('10.8'):
                    data['data_interface'] = ifaceName
                    data['data_ip'] = addresses[0]
        return data

        #s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        #s.connect(('8.8.8.8', 80))
        #return s.getsockname()[0]

    def get_file_count(path):
        return len([name for name in os.listdir(path) if os.path.isfile(os.path.join(path, name))])


    def get_harvester_service_info(self):
        data = []
        for service in self._hpool_map.values():
            data.append(service.get_info())
        return data

    def get_local_info(self):
        from driver import get_harvester_driver_list
        network = self._get_network()
        driver_list = get_harvester_driver_list()

        info = {
            'network': self._get_network(),
            'internal_ip': '127.0.0.1',
            'uptime': uptime(),
            'total_current_plots': sum([item['total_current_plots'] for item in driver_list]),
            'driver_cnt': len(driver_list),
            'file_cnt': sum([item['file_cnt'] for item in driver_list]),
            'space_free_plots': sum([item['space_free_plots'] for item in driver_list]),
            'nc_process_cnt': sum(1 for proc in psutil.process_iter() if proc.name() == 'nc'),
        }

        if self.driver_report is None:
            info['driver_unhealthy_cnt'] = 'NaN'
            info['driver_temperature_high'] = 'NaN'
            info['driver_temperature_low'] = 'NaN'
        else:
            temperature_list = [item['temperature'] for item in self.driver_report['driver']]
            info['driver_unhealthy_cnt'] = len([item for item in self.driver_report['driver'] if item['health'] != 'PASS'])
            info['driver_temperature_high'] = self.max_temperature(temperature_list)
            info['driver_temperature_low'] = self.min_temperature(temperature_list)

        return info

    def max_temperature(self, data):
        t = 0
        for item in data:
            if item is None:
                continue
            if item > t:
                t = item
        return t

    def min_temperature(self,data):
        t = 100
        for item in data:
            if item is None:
                continue
            if item < t:
                t = item
        return t


    def clean_harvester_driver(self):
        from driver import get_harvester_driver_list
        cnt=0
        for driver in get_harvester_driver_list():
            files = os.listdir(driver['mount_path'])
            logger.info('driver:%s path:%s files cnt:%s' % (driver['device'], driver['mount_path'], len(files)))
            for file in files:
                full_name = '%s/%s' % (driver['mount_path'], file)
                create_time = get_filecreatetime(full_name)
                # 过滤出24小时之前创建的文件
                if os.path.isfile(full_name) and ((datetime.datetime.now() - create_time).total_seconds()/3600 > 24):
                    file_size = get_filesize(full_name)
                    if file_size < 101: # check k32 file size
                        logger.info('delete file:%s size:%s' % (full_name, file_size))
                        os.remove(full_name)
                        cnt = cnt + 1
        logger.info('delete file cnt:%s' % cnt)

    def check_plots(self, args):
        """
        检查是重名以及文件大小异常的plot
        """
        files_cnt_map = {}
        files_size_error_map = {}
        from driver import get_harvester_driver_list
        for item in get_harvester_driver_list():
            files = os.listdir(item['mount_path'])
            logger.info('driver:%s path:%s files cnt:%s' % (item['device'], item['mount_path'], len(files)))
            for file in files:
                full_name = '%s/%s' % (item['mount_path'], file)
                if file not in files_cnt_map:
                    files_cnt_map[file] = []
                files_cnt_map[file].append(full_name)

                ignore_today = False
                # 过滤出24小时之前创建的文件 有可能有正在写入的文件
                create_time = get_filecreatetime(full_name)
                if os.path.isfile(full_name):
                    if (ignore_today and ((datetime.datetime.now() - create_time).total_seconds()/3600 > 24)) or (not ignore_today):
                        file_size = get_filesize(full_name)
                        if file_size < 101:
                            # check k32 file size
                            logger.info('plot file:%s size:%s' % (full_name, file_size))
                            files_size_error_map[full_name] = file_size

        files_cnt_map_final = {}
        for key in files_cnt_map:
            if len(files_cnt_map[key]) > 1:
                files_cnt_map_final[key] = files_cnt_map[key]
                logger.info('plot file:%s has %s copies' % (key, len(files_cnt_map[key])))

    def restart_service(self, service_name):
        if service_name in self._hpool_map:
            service = self._hpool_map[service_name]
            service.restart_service()


if __name__ == '__main__':
    pass











