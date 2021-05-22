#!/usr/bin/python
# -*- coding: utf-8 -*-


import os, platform, subprocess, re
import logging, traceback
import logging.config
import psutil
from cpuinfo import get_cpu_info as _get_cpu_info
logger = logging.getLogger('nas')

def get_cpu_info():
    data = _get_cpu_info()
    return {
        'brand': data['brand_raw'],
        'count': data['count'],
        'hz_advertised': data['hz_advertised_friendly'],
        'hz_actual': data['hz_actual_friendly'],

    }


def get_memory_info():
    data = psutil.virtual_memory()
    return {
        'total': data.total,
        'used': data.used,
    }

def get_human_readable_size(num):
    exp_str = [ (0, 'B'), (10, 'KB'),(20, 'MB'),(30, 'GB'),(40, 'TB'), (50, 'PB'),]
    i = 0
    while i+1 < len(exp_str) and num >= (2 ** exp_str[i+1][0]):
        i += 1
        rounded_val = round(float(num) / 2 ** exp_str[i][0], 2)
    return '%s %s' % (int(rounded_val), exp_str[i][1])


if __name__ == '__main__':
    logging.config.fileConfig('logging.conf')
    cpu = get_memory_info()
    logger.info('cpu:%s' % cpu)

