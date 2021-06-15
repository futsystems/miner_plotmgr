#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import time
import subprocess
import logging, traceback
import logging.config
import psutil
import driver
from message import Response
import plot_log

if sys.version_info.major == 2:   # Python 2
    import thread
else:                             # Python 3
    import _thread as thread
import requests
import config
import socket
import requests
import datetime

from common import get_cpu_info, get_memory_info, uptime, get_nvme_info


import json

logger = logging.getLogger('nas')


class PlotterManager(object):
    def __init__(self):
        self.config = config.get_plotter_setting()
        self.nas_ip = None
        self.nas_name = 'nas'

        self._send_to_nas = False
        self._sending_thread = None
        self._server_name = socket.gethostname()
        self._server_ip = self.__get_internal_ip()

        logger.info('will start statistic process')
        self._start_update_statistic_process()

        logger.info('will start local info process')
        self._start_update_local_info_process()


    def get_plot_dst_decive_to_send(self):
        """
        检查plot储存目录，将生成的plot发送到远端NAS
        :return:
        """
        #mount_path = self.config['mount_path']
        #if (not os.path.exists(mount_path)) or (not os.path.isdir(mount_path)):
        #    return None

        dst_device_list = driver.get_plotter_driver_list()
        #logger.info('dst_device_list:%s' % dst_device_list)
        current_device = None
        current_ratio = 1
        #找出剩余空间最小的
        for device in dst_device_list:
            ratio = device['space_free']/float(device['space_total'])
            if ratio < current_ratio:
                current_ratio = ratio
                current_device = device
        return current_device

    @property
    def is_sending_live(self):
        return self._send_to_nas

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
                   'nvme': get_nvme_info(),
                   }
        logger.info('register to manager node:%s' % payload)

        response = requests.post('http://nagios.futsystems.com:9090/server/plotter/register', json=payload)
        logger.info('status:%s data:%s' % (response.status_code, response.json()))


    def start_sending_process(self, nas_name, nas_ip):
        #if self.nas_server is None:
        #    logger.info('Please set nas server first')
        #    return (False, 'Please set nas server first')
        if self._send_to_nas:
            logger.info('Sending process already started')
            return (False, 'Sending process already started')

        logger.info('Start sending process')
        self.nas_ip = nas_ip
        self.nas_name = nas_name
        self._send_to_nas = True
        self._sending_thread = thread.start_new_thread(self.sending_process, (1,))
        return (True, '')


    def _start_update_statistic_process(self):
        logger.info('start update statistic process')
        self._update_statistic_thread = thread.start_new_thread(self.update_statistic_process, (1,))

    def _start_update_local_info_process(self):
        logger.info('start update local info process')
        self._update_local_info_thread = thread.start_new_thread(self.update_local_info_process, (1,))


    def stop_sending_process(self):
        if self._send_to_nas:
            logger.info('Stop sending process')
            self._send_to_nas = False
            return (True, '')
        return (False, 'Sending process is not started')


    def sending_process(self, args):
        while True:
            if not self._send_to_nas:
                logger.info("Sending Process Thread Exit")
                thread.exit_thread()
            device = self.get_plot_dst_decive_to_send()
            path = '/mnt/cache/00/dst'
            # if plotter do not have driver to store plot, plot just in cache
            if device is not None:
                path = device['mount_path']
            logger.info('device:%s which need to send plot, using path:%s' % (device, path))
            files = os.listdir(path)
            cnt = 0
            for plot_file in files:
                #logger.info('plot_file:%s is file:%s isplot:%s' % (plot_file, os.path.isfile(plot_file), plot_file.endswith(".plot")))
                if plot_file.endswith('.plot'):
                    logger.info('====> Will send %s/%s to harvester:%s(%s)' % (path,plot_file, self.nas_name, self.nas_ip))
                    plot_full_name = '%s/%s' % (path, plot_file)
                    res = self.send_plot(path, plot_file)
                    if res[0]:
                        logger.info('Send plot success <===')
                        cnt = cnt+1
                    else:
                        logger.info('Send plot fail,%s <===' % res[1])
                    time.sleep(10)
                #if cnt > 5:
                #    break
            time.sleep(10)

    def update_statistic_process(self, args):
        while True:
            try:
                statistic = plot_log.get_plot_statistic()
                data = {
                    'name': self._server_name,
                    'statistic': statistic
                }

                response = requests.post('http://nagios.futsystems.com:9090/server/plotter/statistic/update', json=data)

                logger.info('status:%s data:%s' % (response.status_code, response.json()))

                # sleep 10 minutes
                time.sleep(10*60)
            except Exception as e:
                logger.error(traceback.format_exc())

    def update_local_info_process(self,args):
        while True:
            try:
                info = self.get_local_info()
                data = {
                    'name': self._server_name,
                    'info': info,
                    'cpu': get_cpu_info(),
                    'memory': get_memory_info(),
                }

                response = requests.post('http://nagios.futsystems.com:9090/server/plotter/local-info/update', json=data)
                logger.info('status:%s data:%s' % (response.status_code, response.json()))

                # sleep 1 minutes
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
        plot_cnt = 1
        driver_cnt = 1

        info = {
            'internal_ip': internal_ip,
            'plot_cnt': plot_cnt,
            'driver_cnt': driver_cnt,
            'is_sending_run': self._send_to_nas,
            'uptime': uptime()
        }

        return info

    def stop_plot_transfer(self,plot_file_name,result,reason):
        try:
            data = {
                'plot_file_name': plot_file_name,
                'plot_check': result,
                'plot_check_fail_reason': reason,
            }

            response = requests.post('http://nagios.futsystems.com:9090/server/transfer/stop', json=data)
            #logger.debug('start plot transfer ')
        except Exception as e:
            logger.error(traceback.format_exc())

    def start_plot_transfer(self,plot_file_name,plotter_path,harvester_path,nc_pid,nc_port):
        try:
            data = {
                'plot_file_name': plot_file_name,
                'plotter_server': self._server_name,
                'plotter_ip': self._server_ip,
                'plotter_path': plotter_path,
                'harvester_server': self.nas_name,
                'harvester_ip': self.nas_ip,
                'harvester_path': harvester_path,
                'nc_pid': nc_pid,
                'nc_port': nc_port,
            }

            response = requests.post('http://nagios.futsystems.com:9090/server/transfer/start', json=data)
            #logger.info('status:% data:%s' % (response.status_code, response.json()))
        except Exception as e:
            logger.error(traceback.format_exc())

    def send_plot(self, path, filename):
        """
        send plot file to remote nas server
        :param nas_server:
        :param plot_file:
        :return:
        """
        plot_file = '%s/%s' % (path, filename)
        if not os.path.isfile(plot_file):
            return (False, 'File:%s do not exist' % plot_file)
        local_size = os.path.getsize(plot_file)
        if local_size == 0:
            os.remove(plot_file)
            return (False, 'File:%s size is 0' % plot_file )

        url_start = 'http://%s:8080/nc/start?file=%s' % (self.nas_ip, filename)
        url_stop = 'http://%s:8080/nc/stop' % self.nas_ip
        #logger.debug('Request Url Start:%s Stop:%s' % (url_start, url_stop))
        response = requests.get(url_start)
        #logger.debug('response:%s' % response)
        if response.status_code != 200:
            logger.warn('NAS Server:%s response error' % self.nas_ip)
            return (False, 'NAS Server response error')
        else:
            result = response.json()
            if result['code'] != 0:
                logger.warn('Start NC error:%s' % result['msg'])
                return [False, result['msg']]
            else:
                self.start_plot_transfer(filename, path, result['data']['path'], result['data']['pid'], result['data']['port'])
                logger.info('Start remote nc service success,sending plot to %s:%s' % (self.nas_ip,result['data']['path']))
                try:
                    cmd_path = os.path.split(os.path.abspath(__file__))[0]
                    cmd_send_plot = '%s/send_plot.sh' % cmd_path
                    remote_path = '%s/%s' % (result['data']['path'], filename)
                    logger.info('Execute cmd:%s arg1:%s arg2:%s arg3:%s' % (cmd_send_plot, plot_file, self.nas_ip, result['data']['port']))
                    subprocess.call([cmd_send_plot, plot_file, self.nas_ip, str(result['data']['port'])])

                    #os.system(nc_cmd)
                except subprocess.CalledProcessError as e:
                    logger.warning(e.output)
                finally:
                    #1. stop nc server
                    response = requests.get(url_stop)
                    if response.status_code != 200:
                        logger.warn('NAS Server response error')
                        #return (False, 'NAS Server response error')
                    else:
                        result = response.json()
                        if result['code'] != 0:
                            logger.warn('NAS Server stop nc error:%s' % result['msg'])
                            #return [False, result['msg']]
                        else:
                            logger.info('Stop remote nc service success')

                    #2. check file and remove local
                    logger.info('Check remote file:%s from NAS %s' % (remote_path, self.nas_ip))
                    url_check = 'http://%s:8080/plot/info?path=%s' % (self.nas_ip, remote_path)
                    response = requests.get(url_check)
                    if response.status_code != 200:
                        logger.warn('NAS Server response error')
                        self.stop_plot_transfer(filename, False, 'Check File Response Error(Http)')
                        return [False, result['msg']]
                    else:
                        result = response.json()
                        if result['code'] != 0:
                            logger.warn('NAS Server get plot info error:%s' % result['msg'])
                            self.stop_plot_transfer(filename, False, result['msg'])
                            return [False, result['msg']]
                        else:
                            remote_size = result['data']['size']

                            if remote_size == local_size:
                                logger.info('Remote Size:%s Local Size:%s Plot size match,delete local file' % (remote_size, local_size))
                                os.remove(plot_file)
                                delte_file_cmd = '/opt/src/scripts/remove_file.sh %s' % plot_file
                                process = subprocess.Popen(delte_file_cmd, shell=True, stdout=subprocess.PIPE,
                                                           stderr=subprocess.PIPE)
                                process.wait()

                                self.stop_plot_transfer(filename, True, '')
                                return [True, result['msg']]
                            else:
                                logger.warn('Plot size dismatch, will send file later')
                                self.stop_plot_transfer(filename, False, 'Plot File Size Dismatch')
                                return [False, 'File size dismatch']



if __name__ == '__main__':
    logging.config.fileConfig('logging.conf')
    #pm = PlotManager()
    #logger.info(pm.config)
    import driver
    #driver.get_plot_dst_list('/user')
    list = driver.get_plot_dst_device_list('/mnt/dst')

    logger.info('list:%s' % list)
    #pm.send_plot('/Users/qianbo/worktable/pyproject/plotmgr/plot_mgr.py','192.168.1.11')











