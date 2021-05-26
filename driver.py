#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import psutil
import config
import logging
import logging.config
logger = logging.getLogger('nas')

def get_driver_info():
    print("test driver info")

#/mnt/plots/driver0 mount_prefix is /mnt/plots/driver
nas_driver_mount_preifx = config.get_nas_driver_mount_prefix()
plotter_driver_mount_prefix = config.get_plotter_driver_mount_prefix()
plotter_cache_mount_prefix = config.get_plotter_cache_mount_prefix()


plot_size_k = 108995911228
plot_size_g = 101.3623551


def bytesto(bytes, to, bsize=1024):
    a = {'k': 1, 'm': 2, 'g': 3, 't': 4, 'p': 5, 'e': 6}
    r = float(bytes)
    return bytes / (bsize ** a[to])


def get_drive_by_mountpoint(mountpoint):
    """
    This accepts a mountpoint ('/mnt/enclosure0/rear/column2/drive32') and returns the drive:
    drive32
    """
    return (mountpoint.split("/")[5])


def get_nas_driver_list():
    """
    获得NAS服务器上可以储存plot文件的设备列表
    Return list of tuples of all available plot drives on the system and the device assignment
    [('/mnt/enclosure0/front/column0/drive3', '/dev/sde1')]
    """
    #partitions = psutil.disk_partitions(all=False)
    #mountpoint = []
    #for p in partitions:
    #    if p.device.startswith('/dev/sd') and p.mountpoint.startswith(nas_driver_mount_preifx):
    #        mountpoint.append((p.mountpoint, p.device, p.fstype))
    #return mountpoint

    driver_list = []
    for sub_path in os.listdir(nas_driver_mount_preifx):
        path = '%s/%s' % (nas_driver_mount_preifx, sub_path)
        if os.path.isdir(path):
            info = get_dst_device_info(path)
            if info is not None:
                driver_list.append(info)

    return driver_list


def get_device_by_mountpoint(mountpoint):
    """
    通过挂载点获得对应磁盘设备
    This accepts a mountpoint and returns the device assignment: /dev/sda1 and mountpoint
    """
    partitions = psutil.disk_partitions(all=False)
    for p in partitions:
        #if p.device.startswith('/dev/sd') and p.mountpoint.startswith(mountpoint):
        if p.mountpoint.startswith(mountpoint):
            return p.device
    return None

def get_mountpoint_by_device(device):
    """
    通过磁盘设备文件获得对应的挂载点
    This accepts a mountpoint and returns the device assignment: /dev/sda1 and mountpoint
    """
    partitions = psutil.disk_partitions(all=False)
    for p in partitions:
        if p.device.startswith(device):
            return p.mountpoint


def get_device_info(action, device):
    """
    获得某个磁盘设备的信息
    This allows us to query specific information about our drives including
    temperatures, smart assessments, and space available to use for plots.
    It allows us to simply hand it a drive number (drive0, drive22, etc)
    and will present us with the data back. This utilizes pySMART, but
    a word of caution, use the TrueNAS versions linked to above, the PiPy
    version has a bug!
    """
    import shutil
    from pySMART import Device, DeviceList

    mountpoint = get_mountpoint_by_device(device)

    if action == 'temperature':
        return Device(device).temperature
    if action == 'capacity':
        return Device(device).capacity
    if action == 'health':
        return Device(device).assessment
    if action == 'name':
        return Device(device).name
    if action == 'serial':
        return Device(device).serial
    if action == 'space_total':
        return int(bytesto(shutil.disk_usage(mountpoint)[0], 'g'))
    if action == 'space_used':
        return int(bytesto(shutil.disk_usage(mountpoint)[1], 'g'))
    if action == 'space_free':
        return int(bytesto(shutil.disk_usage(mountpoint)[2], 'g'))
    if action == 'space_free_plots':
        return int(bytesto(shutil.disk_usage(mountpoint)[2], 'g') / plot_size_g)
    if action == 'total_current_plots':
        return int(bytesto(shutil.disk_usage(mountpoint)[1], 'g') / plot_size_g)

def get_plot_drive_to_use():
    """
    用于获得NAS服务器可用于储存Plot的磁盘，通过排序法获得
        This looks at all available plot drives that start with /dev/sd and include
        /mnt/enclosure in the mount path (this covers all of my plot drives), it then
        looks for any drive that has enough space for at least one plot (k32), sorts
        that list based on the drive# sorting (drive0, drive10, etc) sorting and then
        returns the mountpoint of the device we want to use. Basically the same as above
        but simply returns the 'next' available drive we want to use. This also checks
         to make sure the drive selected has not been marked as "offline".
        #TODO incorporate in get_plot_drive_with_available_space()
        """
    from natsort import natsorted
    #with open('offlined_drives', 'r') as offlined_drives_list:
    #    offlined_drives = [current_drives.rstrip() for current_drives in offlined_drives_list.readlines()]
    available_drives = []
    for part in psutil.disk_partitions(all=False):
        if part.device.startswith('/dev/sd') \
                and part.mountpoint.startswith(nas_driver_mount_preifx) \
                and get_device_info('space_free_plots', part.device) >= 1:
            available_drives.append((part.mountpoint, part.device))
    return natsorted(available_drives)[0]


def get_plotter_driver_list():
    """
    用于获得P盘目标文件储存设备列表
    /mnt/dst/00 /mnt/dst/01 分别挂载到不同磁盘，或者组成raid0后挂载到/mnt/dst/00
    :return:
    """
    #logger.info('path:%s'% dst_path)
    dst_device_list = []
    for sub_path in os.listdir(plotter_driver_mount_prefix):
        path = '%s/%s' % (plotter_driver_mount_prefix, sub_path)
        if os.path.isdir(path):
            #logger.info('mount_path:%s' % path)
            info = get_dst_device_info(path)
            if info is not None:
                dst_device_list.append(info)

    return dst_device_list

def get_plotter_nvme_list():
    """
    获得P盘设备上的nvme设备列表
    :return:
    """
    nvme_list = []
    partitions = psutil.disk_partitions(all=True)
    for p in partitions:
        if p.device.startswith('/dev/nvme'):
            nvme_list.append(p)
    return nvme_list

def linux_block_devices():
    import glob
    for blockdev_stat in glob.glob('/sys/block/*/stat'):
        blockdev_dir = blockdev_stat.rsplit('/', 1)[0]
        found_parts = False
        for part_stat in glob.glob(blockdev_dir + '/*/stat'):
            yield blockdev_stat.rsplit('/', 2)[-2]
            found_parts = True
        if not found_parts:
            yield blockdev_dir.rsplit('/', 1)[-1]

def get_plotter_cache_list():
    """
    用于获得P盘缓存设备列表
    /mnt/dst/00 /mnt/dst/01 分别挂载到不同磁盘，或者组成raid0后挂载到/mnt/dst/00
    :return:
    """
    #logger.info('path:%s'% dst_path)

    dst_device_list = []
    for sub_path in os.listdir(plotter_cache_mount_prefix):
        path = '%s/%s' % (plotter_cache_mount_prefix, sub_path)
        if os.path.isdir(path):
            logger.info('mount_path:%s' % path)
            info = get_dst_device_info(path)
            if info is not None:
                dst_device_list.append(info)

    return dst_device_list



def get_dst_device_info(mount_path):
    """
    用于通过挂载点获得对应磁盘设备信息
    :param mount_path:
    :return:
    """
    device = get_device_by_mountpoint(mount_path)
    if device is None:
        return None
    return {
        'mount_path':mount_path,
        'device': device,
        'space_total': get_device_info('space_total', device),
        'space_used': get_device_info('space_used', device),
        'space_free': get_device_info('space_free', device),
        'space_free_plots': get_device_info('space_free_plots', device),
        'total_current_plots': get_device_info('total_current_plots', device),

    }



if __name__ == '__main__':
    d = linux_block_devices()
    print(d)



