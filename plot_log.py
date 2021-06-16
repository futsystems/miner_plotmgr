#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import subprocess
import psutil


import logging.config

logging.config.fileConfig('logging.conf')
logger = logging.getLogger('nas')


def get_file_list(file_path):
    if not os.path.exists('/opt/chia/logs'):
        return []

    dir_list = os.listdir(file_path)
    if len(dir_list) > 0:
        # 注意，这里使用lambda表达式，将文件按照最后修改时间顺序升序排列
        # os.path.getmtime() 函数是获取文件最后修改时间
        # os.path.getctime() 函数是获取文件最后创建时间
        dir_list = sorted(dir_list,  key=lambda x: x.split('.')[0], reverse=True)
        # print(dir_list)
    return dir_list

def get_plot_statistic():
    import re
    from datetime import datetime, timedelta
    plot_logs = get_file_list('/opt/chia/logs')
    #logger.info('plot logs:%s' % plot_logs)
    plotting_cnt = 0
    plotted_cnt = 0
    coppied_cnt = 0
    plot_time_sum = 0
    copy_time_sum = 0
    now = datetime.now()
    last_24_hours_dt = now - timedelta(days=1)
    last_day_plotted_cnt = 0
    last_day_plotted_time_sum =0
    out_day = False
    for log in plot_logs:
        file = '/opt/chia/logs/%s' % log
        #logger.info('file:%s' % file)
        result = subprocess.check_output(['/opt/src/scripts/log_cat.sh', file])
        #logger.info(result)

        if result == b'':
            plotting_cnt = plotting_cnt + 1
        else:

            result_str = result.decode("utf-8")
            rows = result_str.split('\n')
            plot_time=0
            copy_time=0
            if len(rows) >= 2:
                plot_time = re.findall(r"Total time = (.+?) seconds", rows[0])[0]
                date_time_str = rows[0].split(') ')[1]
                dt = datetime.strptime(date_time_str, '%a %b %d  %H:%M:%S %Y')
                #logger.info('plotted time:%s dt:%s' % (date_time_str, dt.strftime('%Y-%m-%d %H:%M:%S')))

                if dt >= last_24_hours_dt:
                    last_day_plotted_cnt = last_day_plotted_cnt+1
                    last_day_plotted_time_sum = last_day_plotted_time_sum + float(plot_time)
                else:
                    out_day = True

                #采样最近5个平均值
                if plotted_cnt < 5:
                    plotted_cnt = plotted_cnt + 1
                    plot_time_sum = plot_time_sum + float(plot_time)

            if len(rows) >= 3:
                coppied_cnt = coppied_cnt + 1
                copy_time = re.findall(r"Copy time = (.+?) seconds", rows[1])[0]
                copy_time_sum = copy_time_sum + float(copy_time)


            #logger.info('plot time:%s copy time:%s' % (plot_time, copy_time))
        if out_day and plotted_cnt >= 5:
            break
    #logger.info('plotting:%s plot time sum:%s plotted:%s avg time:%s' % (plotting_cnt, plot_time_sum, plotted_cnt, plot_time_sum/plotted_cnt))
    return {
        'plot_process_cnt': get_plot_process_count(),
        'plotting_cnt': plotting_cnt,
        'avg_plot_time': round(plot_time_sum/plotted_cnt, 2) if plotted_cnt > 0 else 0,
        'avg_copy_time': round(copy_time_sum/coppied_cnt, 2) if coppied_cnt > 0 else 0,
        'plot_output': last_day_plotted_cnt,
    }


def get_plot_process_count():
    pids = psutil.pids()
    plotting_cnt = 0
    for pid in pids:
        try:
            p = psutil.Process(pid)
            # get process name according to pid
            process_name = p.name()
            if process_name.startswith('chia'):
                plotting_cnt = plotting_cnt +1
        except Exception as e:
            pass
        

    return plotting_cnt


if __name__ == '__main__':
    logger.info('get plot log statistic:%s' % get_plot_statistic())
