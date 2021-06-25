#!/usr/bin/python
# -*- coding: utf-8 -*-

import os, time, sys, datetime, subprocess
import requests

if sys.version_info.major == 2:   # Python 2
    import thread
else:                             # Python 3
    import _thread as thread

import driver
import traceback
import logging.config
logging.config.fileConfig('logging.conf')
logger = logging.getLogger('nas')


class LogMonitor(object):
    def __init__(self, harvester_mgr, index, log_file):
        self.harvester_mgr = harvester_mgr
        self._log_file = log_file
        self._capicity_remote_value = 0
        self._capicity_remote_unit = 'TB'
        self._capicity_remote_update_time = datetime.datetime.now()
        self._capicity_remote_first_update_time = None

        self._log_update_time = None
        self._log_lost_interval = 3 #如果3分钟内没有日志信息 则我们认为程序掉线
        self._log_start_check_interval =1 #程序启动1分钟后执行检查

        self._capicity_local_value = 0
        self._capicity_local_check_time = datetime.datetime.now()
        self._capicity_local_check_interval = 1
        self._index = index

        self._lost_power = False
        self._lost_power_time = None
        self._lost_power_interval = 3 #如果丢失算力后 在这个时间内没有回复 则重启服务
        self._lost_power_reboot_fired = False
        self._lost_power_reboot_time = None #
        self._lost_power_reboot_interval = 3 #丢失书算力重启后 在这个时间之后检查算力 启动过程中算力缓慢增长 提前检查导致误报
        self._lost_power_reboot_fail_interval = 6 #如果超过这个时间 算力还没有回复 则判定为算力重启失败 需要人工干预

        self._target_ratio = 0.95
        self._ratio = 1


        self._scan_time_out = False
        self._start_time = None #monitor 开始时间


        self._status = 'PENDING'

        self.service_name = "srv.hpool%s" % self._index


    def get_info(self):

        return {
            'index': self._index,
            'service': 'srv.hpool%s' % self._index,
            'local_power': self._capicity_local_value,
            'remote_power': round(float(self._capicity_remote_value),2),
            'remote_power_unit': self._capicity_remote_unit,
            'status': self._status
        }

    def start_moniter(self):
        logger.info('start moniter process')
        self._log_thread = thread.start_new_thread(self.log_process, (1,))
        self._check_thread = thread.start_new_thread(self.check_process, (1,))

    def restart_service(self):
        if self._status != 'RESTART':
            try:
                subprocess.check_call(["supervisorctl", "restart", self.service_name])
                self._status = 'RESTART_MANUAL'
                self.log_restart("srv.hpool%s" % self._index, 'manual')
            except subprocess.CalledProcessError as e:
                logger.warning(e.output)
                self._status = 'RESTART_FAIL'

    def log_process(self, args):
        self._start_time = datetime.datetime.now()
        while not os.path.exists(self._log_file):
            logger.info('log file:%s do not exist, wait some time' % self._log_file)
            time.sleep(1)

        f = open(self._log_file, 'r')
        while True:
            line = ''
            while len(line) == 0 or line[-1] != '\n':
                tail = f.readline()
                if tail == '':
                    time.sleep(1)  # avoid busy waiting
                    # f.seek(0, io.SEEK_CUR) # appears to be unneccessary
                    continue
                line += tail
            self._log_process(line)

    def check_process(self,args):
        while True:
            self._check_process()
            time.sleep(2)

    def _check_process(self):
        now = datetime.datetime.now()
        # 没有执行过算力检查 或者 距离上次算力检查超过检查间隔
        if self._capicity_local_check_time is None or (now-self._capicity_local_check_time).total_seconds() > self._capicity_local_check_interval*60:
            # 如果获得矿池算力值
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
                self._capicity_local_value = round(plot_cnt * 101.4 * 0.0009765625, 2)

                self._capicity_local_check_time = now
                raito = round(self._capicity_remote_value / float(self._capicity_local_value),2)
                self._ratio = raito

                logger.info('group:%s local power:%s remote power:%s %s ratio:%s' % (
                self._index, self._capicity_local_value, self._capicity_remote_value, self._capicity_remote_unit, raito))


                if raito < self._target_ratio:
                    if self._lost_power is False:
                        self._lost_power = True
                        self._lost_power_time = now
                        self._status = 'LOST_POWER'
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
                                try:
                                    subprocess.check_call(["supervisorctl", "restart", self.service_name])
                                    self._status = 'RESTART'
                                    self.log_restart( "srv.hpool%s" % self._index, 'lost power')
                                except subprocess.CalledProcessError as e:
                                    logger.warning(e.output)
                                    self._status = 'RESTART_FAIL'

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
                                    self._status = 'RESTART_STILL_LOST'
                        else:
                            # reboot service and wait plot scan
                            pass
                    else:
                        #没有重启服务 且算力恢复 算力摇摆
                        if raito > self._target_ratio:
                            logger.info('power is recovered')
                            self._status = 'OK'
                else:
                    self._status = 'OK'


        if self._scan_time_out:
            logger.info('scan plots time out, restart service directly')
            try:
                subprocess.check_call(["supervisorctl", "restart", self.service_name])
                self._status = 'RESTART'
                self.log_restart("srv.hpool%s" % self._index, 'scan time out')
            except subprocess.CalledProcessError as e:
                logger.warning(e.output)
                self._status = 'RESTART_FAIL'

        # 启动1分钟后 再进行时间检查
        logger.info('now:%s start:%s secends:%s' % (now,self._start_time,(now - self._start_time).total_seconds()))
        if (now - self._start_time).total_seconds() > self._log_start_check_interval*60:
            # 如果没有获得任何远端日志时间 或者 最近的远端日志时间过去一定时间 则认为offline
            if self._log_update_time is None or (now - self._log_update_time).total_seconds() > self._log_lost_interval * 60:
                logger.info('%s has not got message from server in %s minutes' % (self.service_name, self._log_lost_interval))
                self._status = 'OFFLINE'





    def _log_process(self, log_line):
        now = datetime.datetime.now()

        if log_line.startswith('time='):
            time_value = log_line[6:25]
            dt = datetime.datetime.fromisoformat(time_value)
            self._log_update_time = dt
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

                if 'badbit or failbit after reading size 104' in log_line:
                    tmp = log_line.split('file=')
                    error_file = tmp[1].split(' ')[0]
                    if not os.path.isfile(error_file):
                        size = 0
                    else:
                        size = os.path.getsize(error_file)
                    logger.debug('error file:%s size:%s' % (error_file, size))

                if '扫盘超时间' in log_line:
                    self._scan_time_out = True


                #logger.info('check data:%s' % items[3])
                #tmp_data = items[3].split('=')
                #if tmp_data[0] == 'capacity':
                #    logger.info('new capacity data received:%s' % tmp_data[1])


    def log_restart(self,service,reason):
        try:
            data = {
                'harvester': self.harvester_mgr.harvester_name,
                'service': service,
                'reason': reason
            }

            response = requests.post('http://nagios.futsystems.com:9090/server/harvester/service/restart', json=data)
            #logger.info('status:% data:%s' % (response.status_code, response.json()))
        except Exception as e:
            logger.error(traceback.format_exc())

