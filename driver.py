#!/usr/bin/python
# -*- coding: utf-8 -*-


import psutil


def get_driver_info():
    print("test driver info")


def get_drive_by_mountpoint(mountpoint):
    """
    This accepts a mountpoint ('/mnt/enclosure0/rear/column2/drive32') and returns the drive:
    drive32
    """
    return (mountpoint.split("/")[5])


def get_list_of_plot_drives():
    """
    Return list of tuples of all available plot drives on the system and the device assignment
    [('/mnt/enclosure0/front/column0/drive3', '/dev/sde1')]
    """
    partitions = psutil.disk_partitions(all=False)
    mountpoint = []
    for p in partitions:
        if p.device.startswith('/dev/sd') and p.mountpoint.startswith('/mnt/dst'):
            mountpoint.append((p.mountpoint, p.device, p.fstype))
    return mountpoint

if __name__ == '__main__':
    p = get_drive_by_mountpoint('/')
    d = get_list_of_plot_drives
    print(d)



