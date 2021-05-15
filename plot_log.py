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
        dir_list = sorted(dir_list,  key=lambda x: x.split('.')[0], reverse=True)
        # print(dir_list)
        return dir_list

def get_plot_logs():
    import re
    plot_logs =  get_file_list('/opt/chia/logs')
    logger.info('plot logs:%s' % plot_logs)
    plotting_cnt = 0
    plotted_cnt = 0
    for log in plot_logs:
        file = '/opt/chia/logs/%s' % log
        logger.info('file:%s' % file)
        result = subprocess.check_output(['/opt/src/scripts/log_cat.sh', file])
        logger.info(result)

        if result == b'':
            plotting_cnt = plotting_cnt + 1
        else:
            plotted_cnt = plotted_cnt + 1
            result_str = result.decode("utf-8")
            rows = result_str.split('\n')
            plot_time=0
            copy_time=0
            if len(rows) >= 2:
                plot_time = re.findall(r"Total time = (.+?) seconds", rows[0])[0]
            if len(rows) >= 3:
                copy_time = re.findall(r"Copy time = (.+?) seconds", rows[1])[0]

            logger.info('plot time:%s copy time:%s' % (plot_time, copy_time))


        if plotted_cnt >= 5:
            break

    logger.info('plotting:%s plotted:%s' % (plotting_cnt, plotted_cnt))





if __name__ == '__main__':
    logger.info('get plot log list')
    get_plot_logs()
