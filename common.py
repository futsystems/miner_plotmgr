#!/usr/bin/python
# -*- coding: utf-8 -*-

import socket
import os, mdstat, subprocess, re
import logging, traceback
import driver
import logging.config
import psutil
import datetime
from cpuinfo import get_cpu_info as _get_cpu_info
logger = logging.getLogger('nas')

def get_cpu_info():
    data = _get_cpu_info()
    return {
        'brand': data['brand_raw'],
        'count': data['count'],
        'hz_advertised': data['hz_advertised_friendly'],
        'hz_actual': data['hz_actual_friendly'],
        'used_percent': psutil.cpu_percent(),
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

def uptime():
    with open('/proc/uptime', 'r') as f:
        uptime_seconds = float(f.readline().split()[0])
        return uptime_seconds

def get_nvme_info():
        nvme_list = driver.get_plotter_nvme_list()
        nvme_size = 0
        if len(nvme_list) > 0:
            nvme_size = get_block_device_size(nvme_list[0])

        return {
            'nvme_cnt': len(nvme_list),
            'nvme_size': round(nvme_size/1000/1000/1000/1000, 1),
            'is_cache_raid': len(mdstat.parse()['devices']) > 0
        }

def get_cache_info():
    nvme_list = driver.get_plotter_nvme_list()

    return {
        'usage': _get_cache_usage(),
        'temperature': ' '.join([get_nvme_temperature(device) for device in nvme_list]),
    }

def _get_cache_usage(path='/mnt/cache/00'):
    if os.path.ismount(path):
        return psutil.disk_usage(path).percent
    return 'Not Set'



def empty_str(arg):
    if arg is None:
        return True
    if arg == '':
        return True
    return False




def get_free_port():
    sock = socket.socket()
    sock.bind(('', 0))
    ip, port = sock.getsockname()
    sock.close()
    return port

def get_block_device_size(filename):
    "Get the file size by seeking at end"
    fd= os.open(filename, os.O_RDONLY)
    try:
        return os.lseek(fd, 0, os.SEEK_END)
    finally:
        os.close(fd)

def get_filesize(filePath):
    """
    :return sizde by GB
    :param filePath:
    :return:
    """
    fsize = os.path.getsize(filePath)
    fsize = fsize/float(1024*1024*1024)
    return round(fsize,2)

def get_filecreatetime(filePath):
    timestamp= os.path.getctime(filePath)
    return datetime.datetime.fromtimestamp(timestamp)


def get_nvme_temperature(dev='/dev/nvme0n1'):
    try:
        command = ['nvme', 'smart-log', dev]
        p = subprocess.Popen(command, stdout=subprocess.PIPE)
        out, err = p.communicate()
        txt = str(out, encoding="utf8")
        #txt.split('\n')[2] -> 'temperature                         : 54 C'
        return txt.split('\n')[2].split(':')[1].strip()
    except Exception as e:
        return 'NaN'

NMS_HOST = 'miner-nms.futsystems.com'

if __name__ == '__main__':
    logging.config.fileConfig('logging.conf')
    cpu = get_memory_info()
    logger.info('cpu:%s' % cpu)

