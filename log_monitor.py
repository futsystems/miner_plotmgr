#!/usr/bin/python
# -*- coding: utf-8 -*-

import os, time, sys, datetime

if sys.version_info.major == 2:   # Python 2
    import thread
else:                             # Python 3
    import _thread as thread


import logging.config
logging.config.fileConfig('logging.conf')
logger = logging.getLogger('nas')


class LogMonitor(object):
    def __init__(self, log_file):
        self._log_file = log_file

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

    def log_process(self, log_line):
        now = datetime.datetime.now()
        items = log_line.split(' ')
        for item in items:
            data = item.split('=')
            if len(data) == 2:
                if data[0] == 'time':
                    dt = datetime.datetime.strptime(data[1], '%Y-%m-%dT%H:%M:%SZ')
                    if (now - dt).total_seconds() > 120:
                        logger.info('in 2 minuts')
                        logger.info(log_line)

                #logger.info('key:%s value:%s' % (data[0], data[1]))

