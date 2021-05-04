#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import subprocess


class UploadProcess(object):
    def __init__(self):
        self.__pid = None
        self.__port = None
        self.__start_time = None

class NasManager(object):
    def __init__(self):
        self.__upload_process = { }


    def start_nc(self, plot_name):
        plot_path= '/mnt/dst/00/%s' % plot_name
        df_cmd = 'nc -l -q5 -p 4040 > "%s" < /dev/null' % plot_path
        os.spawnl(os.P_DETACH, df_cmd)


if __name__ == '__main__':
    df_cmd = 'nc -ld -q5 -p 4040 >/mnt/dst/00/test.file'

    process = subprocess.Popen(df_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    err = process.stderr.read()



