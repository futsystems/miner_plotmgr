#!/usr/bin/python
# -*- coding: utf-8 -*-

import os


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
        os.system(df_cmd)


if __name__ == '__main__':
    nas = NasManager()
    nas.start_nc('test_plot_file')

