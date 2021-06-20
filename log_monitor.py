#!/usr/bin/python
# -*- coding: utf-8 -*-

import os, time, sys, datetime

if sys.version_info.major == 2:   # Python 2
    import thread
else:                             # Python 3
    import _thread as thread

import driver
import logging.config
logging.config.fileConfig('logging.conf')
logger = logging.getLogger('nas')


class LogMonitor(object):
    def __init__(self, index, log_file):
        self._log_file = log_file
        self._capicity_value = 0
        self._capicity_unit = 'TB'
        self._capicity_update_time = datetime.datetime.now()
        self._index = index




    def start_moniter(self):
        logger.info('start moniter process')
        self._moniter_process = thread.start_new_thread(self.moniter_process, (1,))

    def moniter_process(self, args):
        while not os.path.exists(self._log_file):
            logger.info('log file:%s do not exist, wait some time' % self._log_file)
            time.sleep(1)

        f = open(self._log_file, 'r')
        while True:
            line = ''
            while len(line) == 0 or line[-1] != '\n':
                tail = f.readline()
                if tail == '':
                    time.sleep(0.1)  # avoid busy waiting
                    # f.seek(0, io.SEEK_CUR) # appears to be unneccessary
                    continue
                line += tail
            self.log_process(line)

            self.check_process()

    def check_process(self):
        driver_list=[]
        flag = self._index * 15
        while flag < (self._index + 1)*15:
            mount_path = '/mnt/plots/driver%s' % flag
            logger.info('mount path:%s' % mount_path)

            info = driver.get_dst_device_info('/mnt/plots/driver%s' % flag)
            if info is not None:
                driver_list.append(info)
            flag = flag + 1

        plot_cnt = sum([driver['file_cnt'] for deriver in driver_list])
        power = round(plot_cnt * 101.4 * 0.0009765625, 2)
        logger.info('power:%s' % power)


    def log_process(self, log_line):
        now = datetime.datetime.now()

        if log_line.startswith('time='):
            time_value = log_line[6:25]
            dt = datetime.datetime.fromisoformat(time_value)
            if (now - dt).total_seconds() < 120:
                logger.debug('event time:%s passed in 2 minutes' % time_value)
                logger.debug('====> %s' % log_line)
                if 'capacity' in log_line:
                    tmp = log_line.split('capacity="')
                    capacity_data = tmp[1].split('"')[0]
                    items = capacity_data.split(' ')
                    logger.info('capicity data:%s' % capacity_data)
                    self._capicity_value = float(items[0])
                    self._capicity_unit = items[1]
                    self._capicity_update_time = dt







                #logger.info('check data:%s' % items[3])
                #tmp_data = items[3].split('=')
                #if tmp_data[0] == 'capacity':
                #    logger.info('new capacity data received:%s' % tmp_data[1])

