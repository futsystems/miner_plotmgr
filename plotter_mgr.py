#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import time
import subprocess
import logging, traceback
import logging.config
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
import json

logger = logging.getLogger('nas')


class PlotterManager(object):
    def __init__(self):
        self.config = config.get_plotter_setting()
        self.nas_server = None
        self._send_to_nas = False
        self._sending_thread = None
        self._server_name = socket.gethostname()

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

    def set_nas_server(self,nas_server):
        self.nas_server = nas_server

    @property
    def is_sending_live(self):
        return self._send_to_nas


    def start_sending_process(self, nas_ip):
        #if self.nas_server is None:
        #    logger.info('Please set nas server first')
        #    return (False, 'Please set nas server first')
        #
        if self._send_to_nas:
            logger.info('Sending process already started')
            return (False, 'Sending process already started')

        logger.info('Start sending process')
        self.nas_server = nas_ip
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
            logger.info('device:%s which need to send plot' % device)
            if device is not None:
                for plot_file in os.listdir(device['mount_path']):
                    #logger.info('plot_file:%s is file:%s isplot:%s' % (plot_file, os.path.isfile(plot_file), plot_file.endswith(".plot")))
                    if plot_file.endswith(".test"):

                        logger.info('====> Will send plot:%s from dst:%s to nas:%s' % (plot_file, device['mount_path'], self.nas_server))
                        plot_full_name = '%s/%s' % (device['mount_path'], plot_file)
                        res = self.send_plot(plot_full_name, self.nas_server)
                        if res[0]:
                            logger.info('Send plot success <===')
                        else:
                            logger.info('Send plot fail,%s <===' % res[1])
                        break
            else:
                logger.info("There is no plot dst device")

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

                logger.info('status:% data:%s' % (response.status_code, response.json()))

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
                    'info': info
                }

                response = requests.post('http://nagios.futsystems.com:9090/server/plotter/local-info/update', json=data)
                logger.info('status:% data:%s' % (response.status_code, response.json()))

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
            'is_sending_run': self._send_to_nas
        }

        return info



    def send_plot(self, plot_file, nas_server):
        """
        send plot file to remote nas server
        :param nas_server:
        :param plot_file:
        :return:
        """
        if not os.path.isfile(plot_file):
            return (False, 'File:%s do not exist' % plot_file)

        file_name = plot_file.split('/')[-1]
        url_start = 'http://%s:8080/nc/start?file=%s' % (nas_server, file_name)
        url_stop = 'http://%s:8080/nc/stop' % nas_server
        logger.debug('Request Url Start:%s Stop:%s' % (url_start, url_stop))
        response = requests.get(url_start)
        if response.status_code != 200:
            logger.warn('NAS Server:%s response error' % nas_server)
            return (False, 'NAS Server response error')
        else:
            result = response.json()
            if result['code'] != 0:
                logger.warn('Start NC error:%s' % result['msg'])
                return [False, result['msg']]
            else:
                logger.info('Start remote nc service success,sending plot:%s to NAS Server:%s Path:%s' % (plot_file, nas_server, result['data']['path']))
                try:
                    #nc_cmd = '%s | nc -q2 %s 4040' % (plot_file, nas_server)
                    cmd_path = os.path.split(os.path.abspath(__file__))[0]
                    cmd_send_plot = '%s/send_plot.sh' % cmd_path
                    remoe_path = '%s/%s' % (result['data']['path'], file_name)
                    #subprocess.call(['send_plot.sh', plot_file])
                    logger.info('Execute cmd:%s arg1:%s arg2:%s' % (cmd_send_plot, plot_file, nas_server))
                    subprocess.call([cmd_send_plot, plot_file, nas_server])
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
                    logger.info('Check remote file:%s from NAS %s' % (remoe_path, nas_server))
                    url_check = 'http://%s:8080/plot/info?path=%s' % (nas_server, remoe_path)
                    response = requests.get(url_check)
                    if response.status_code != 200:
                        logger.warn('NAS Server response error')
                        return [False, result['msg']]
                    else:
                        result = response.json()
                        if result['code'] != 0:
                            logger.warn('NAS Server get plot info error:%s' % result['msg'])
                        else:
                            remote_size = result['data']['size']
                            local_size = os.path.getsize(plot_file)
                            if remote_size == local_size:
                                logger.info('Plot size match,delete local file')
                                os.remove(plot_file)
                                return [True, result['msg']]
                            else:
                                logger.warn('Plot size dismatch, will send file later')
                        return [False, result['msg']]


if __name__ == '__main__':
    logging.config.fileConfig('logging.conf')
    #pm = PlotManager()
    #logger.info(pm.config)
    import driver
    #driver.get_plot_dst_list('/user')
    list = driver.get_plot_dst_device_list('/mnt/dst')

    logger.info('list:%s' % list)
    #pm.send_plot('/Users/qianbo/worktable/pyproject/plotmgr/plot_mgr.py','192.168.1.11')











