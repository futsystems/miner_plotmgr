#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import subprocess
import logging
import logging.config
import driver
from message import Response
import requests
import json

logger = logging.getLogger('nas')


class PlotManager(object):
    def __init__(self):
        pass


    def send_plot(self, plot_file, nas_server):
        """
        send plot file to remote nas server
        :param nas_server:
        :param plot_file:
        :return:
        """
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
                logger.info('Send %s to NAS Server :%s' %(plot_file, result['data']['path']))
                try:
                    nc_cmd = '%s | nc -q2 %s 4040' % (plot_file, nas_server)
                    #subprocess.call(['send_plot.sh', plot_file])
                    #subprocess.call(['/home/chia/plot_manager/send_plot.sh', plot_path, plot_to_process])
                    os.system(nc_cmd)
                except subprocess.CalledProcessError as e:
                    logger.warning(e.output)
                finally:
                    response = requests.get(url_start)
                    if response.status_code != 200:
                        return (False, 'NAS Server response error')
                    else:
                        if result['code'] != 0:
                            return [False, result['msg']]

if __name__ == '__main__':
    logging.config.fileConfig('logging.conf')
    pm = PlotManager()
    pm.send_plot('/Users/qianbo/worktable/pyproject/plotmgr/plot_mgr.py','192.168.1.11')











