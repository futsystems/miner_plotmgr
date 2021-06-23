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
        self._capicity_remote_value = None
        self._capicity_remote_unit = 'TB'
        self._capicity_remote_update_time = datetime.datetime.now()
        self._capicity_remote_first_update_time = None

        self._capicity_local_check_time = datetime.datetime.now()
        self._capicity_local_check_interval = 1
        self._index = index

        self._lost_power = False
        self._lost_power_time = None
        self._lost_power_interval = 3
        self._lost_power_reboot_fired = False
        self._lost_power_reboot_time = None
        self._lost_power_reboot_interval = 3
        self._lost_power_reboot_fail_interval = 6

        self._target_ratio = 1

        self._status = None

    def get_info(self):
        return {
            'service': 'srv.hpool%s' % self._index,
            'local_power': self._lost_power,
            'remote_power': self._capicity_remote_value,
            'remote_power_unit': self._capicity_remote_unit,
            'status': self._status
        }

    def start_moniter(self):
        logger.info('start moniter process')
        self._moniter_process = thread.start_new_thread(self.monitor_process, (1,))

    def monitor_process(self, args):
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
        now = datetime.datetime.now()
        # 没有执行过算力检查 或者 距离上次算力检查超过检查间隔
        if self._capicity_local_check_time is None or (now-self._capicity_local_check_time).total_seconds() > self._capicity_local_check_interval*60:
            # 获得矿池算力值
            if self._capicity_remote_value is not None:
                driver_list = []
                flag = self._index * 15
                while flag < (self._index + 1)*15:
                    mount_path = '/mnt/plots/driver%s' % flag
                    #logger.info('mount path:%s' % mount_path)
                    info = driver.get_dst_device_info('/mnt/plots/driver%s' % flag)
                    if info is not None:
                        driver_list.append(info)
                    flag = flag + 1

                plot_cnt = sum([item['file_cnt'] for item in driver_list])
                power = round(plot_cnt * 101.4 * 0.0009765625, 2)

                self._capicity_local_check_time = now
                raito = self._capicity_remote_value / float(power)

                logger.info('group:%s local power:%s remote power:%s %s ratio:%s' % (
                self._index, power, self._capicity_remote_value, self._capicity_remote_unit, raito))


                if raito < self._target_ratio:
                    if self._lost_power is False:
                        self._lost_power = True
                        self._lost_power_time = now
                        self._status = 'LOSTPOWER'
                        logger.info('[power lost],will reboot in %s minutes if not recovered' % self._lost_power_interval)
                    else:
                        if self._lost_power_reboot_fired:
                            #丢失算力已经重启
                            pass
                        else:
                            if (now - self._lost_power_time).total_seconds() > self._lost_power_interval * 60:
                                logger.warn('lost power for %s minutes, reboot service' % self._lost_power_interval)
                                #丢失算力超过一定时间则执行重启
                                self._lost_power_reboot_fired = True
                                self._lost_power_reboot_time = now
                                self._target_ratio = 0.9
                                self._status = 'RESTART'


                # 如果检测到算力丢失
                if self._lost_power:
                    #并且已经触发重启 并且 超过重启时间间隔 则执行检查
                    if self._lost_power_reboot_fired:
                        if (now - self._lost_power_reboot_time).total_seconds() > self._lost_power_reboot_interval * 60:
                            if raito > self._target_ratio:
                                logger.info('power is recovered')
                                self._lost_power = False
                                self._lost_power_reboot_fired = False
                                self._status = 'OK'
                            else:
                                if (now - self._lost_power_reboot_time).total_seconds() < self._lost_power_reboot_fail_interval * 60:
                                    logger.info('power is not recovered will check later')
                                else:
                                    logger.warn('power do not recover after reboot in %s minutes' % self._lost_power_reboot_fail_interval)
                                    self._status = 'LOSTPOWER(RESTART)'


                        else:
                            # reboot service and wait plot scan
                            pass
                    else:
                        #没有重启服务 且算力恢复
                        if raito > self._target_ratio:
                            logger.info('power is recovered')
                            self._status = 'OK'


    def log_process(self, log_line):
        now = datetime.datetime.now()

        if log_line.startswith('time='):
            time_value = log_line[6:25]
            dt = datetime.datetime.fromisoformat(time_value)
            if (now - dt).total_seconds() < 120:
                #logger.debug('event time:%s passed in 2 minutes' % time_value)
                #logger.debug('====> %s' % log_line)
                if 'capacity' in log_line:
                    tmp = log_line.split('capacity="')
                    capacity_data = tmp[1].split('"')[0]
                    items = capacity_data.split(' ')
                    #logger.debug('capicity data:%s' % capacity_data)
                    if self._capicity_remote_value is None:
                        self._capicity_remote_first_update_time = datetime.datetime.now()
                    self._capicity_remote_value = float(items[0])
                    self._capicity_remote_unit = items[1]
                    self._capicity_remote_update_time = dt

                #logger.info('check data:%s' % items[3])
                #tmp_data = items[3].split('=')
                #if tmp_data[0] == 'capacity':
                #    logger.info('new capacity data received:%s' % tmp_data[1])

