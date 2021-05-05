#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import time
import subprocess
import logging
import logging.config
import driver
from message import Response

if sys.version_info.major == 2:   # Python 2
    import thread
else:                             # Python 3
    import _thread as thread
import requests
import config

import json

logger = logging.getLogger('nas')


class PlotManager(object):
    def __init__(self):
        self.config = config.get_plotter_setting()
        self.nas_server = None
        self._send_to_nas = False
        self._sending_thread = None

    def get_plot_dst_decive_to_send(self):
        """
        检查plot储存目录，将生成的plot发送到远端NAS
        :return:
        """
        mount_path = self.config['mount_path']
        if (not os.path.exists(mount_path)) or (not os.path.isdir(mount_path)):
            return None

        dst_device_list = driver.get_plot_dst_device_list(self.config['mount_path'])
        #logger.info('dst_device_list:%s' % dst_device_list)
        current_device = None
        current_ratio = 1
        #找出剩余空间最小的
        for device in dst_device_list:
            logger.info('device:%s' % device)
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


    def start_sending_process(self):
        if self.nas_server is None:
            logger.info('Please set nas server first')
            return (False, 'Please set nas server first')

        if self._send_to_nas:
            logger.info('Sending process already started')
            return (False, 'Sending process already started')

        logger.info('Start sending process')
        self._send_to_nas = True
        self._sending_thread = thread.start_new_thread(self.sending_process, (1,))
        return (True, '')


    def stop_sending_process(self):
        if self._send_to_nas:
            logger.info('Stop sending process')
            self._send_to_nas = False
            return (True, '')
        return (False, 'Sending process is not started')


    def sending_process(self, obj):
        while True:
            if not self._send_to_nas:
                logger.info("Sending Process Thread Exit")
                thread.exit_thread()
            device = self.get_plot_dst_decive_to_send()
            if device is not None:
                for plot_file in os.listdir(device['mount_path']):
                    if os.path.isfile(plot_file) and plot_file.endswith(".plot"):
                        logger.info('Will send plot:%s to nas:%s' % (plot_file, self.nas_server))
                        #self.send_plot(file, self.nas_server)

            time.sleep(10)




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
        url_stop = 'http://%s:8080/nc/stop' % (nas_server)

        response = requests.get(url_start)
        if response.status_code != 200:
            logger.warn('NAS Server:%s response error' % nas_server)
            return (False, 'NAS Server response error')
        else:
            result = response.json()
            if result['code'] != 0:
                logger.warn('Start NC eror:%s' % result['msg'])
                return [False, result['msg']]
            else:
                logger.info('Try send [%s] to NAS Server %s@%s ' %(plot_file, result['data']['path'], nas_server))
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

                    #2. check file and remove local
                    logger.info('Check remote file:%s@%s' % (remoe_path, nas_server))
                    url_check = 'http://%s:8080/plot/info?path=%s' % (nas_server, remoe_path)
                    response = requests.get(url_check)
                    if response.status_code != 200:
                        logger.warn('NAS Server response error')
                    else:
                        result = response.json()
                        if result['code'] != 0:
                            logger.warn('NAS Server get plot info error:%s' % result['msg'])
                        else:
                            remote_size = result['data']['size']
                            local_size = os.path.getsize(plot_file)
                            if remote_size == local_size:
                                logger.warn('Plot Size math,delete local file')


if __name__ == '__main__':
    logging.config.fileConfig('logging.conf')
    #pm = PlotManager()
    #logger.info(pm.config)
    import driver
    #driver.get_plot_dst_list('/user')
    list = driver.get_plot_dst_device_list('/mnt/dst')

    logger.info('list:%s' % list)
    #pm.send_plot('/Users/qianbo/worktable/pyproject/plotmgr/plot_mgr.py','192.168.1.11')











