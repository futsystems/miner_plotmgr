#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import subprocess

import logging.config

logging.config.fileConfig('logging.conf')
logger = logging.getLogger('nas')


def get_file_list(file_path):
    dir_list = os.listdir(file_path)
    if not dir_list:
        return
    else:
        # 注意，这里使用lambda表达式，将文件按照最后修改时间顺序升序排列
        # os.path.getmtime() 函数是获取文件最后修改时间
        # os.path.getctime() 函数是获取文件最后创建时间
        dir_list = sorted(dir_list,  key=lambda x: x.split('.')[0])
        # print(dir_list)
        return dir_list

def get_plot_logs():
    plot_logs =  get_file_list('/opt/chia/logs')
    for log in plot_logs:
        file = '/opt/chia/logs/%s' % log
        logger.info('file:%s' % file)
        result = subprocess.check_output(['/opt/src/scripts/log_cat.sh', file])
        logger.info(result)





if __name__ == '__main__':
    logger.info('get plot log list')
    logger.info(get_plot_logs())
