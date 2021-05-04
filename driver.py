#!/usr/bin/python
# -*- coding: utf-8 -*-


import psutil

from pySMART import Device, DeviceList
from natsort import natsorted
import shutil

def get_driver_info():
    print("test driver info")

plot_size_k = 108995911228
plot_size_g = 101.3623551


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

def bytesto(bytes, to, bsize=1024):
    a = {'k': 1, 'm': 2, 'g': 3, 't': 4, 'p': 5, 'e': 6}
    r = float(bytes)
    return bytes / (bsize ** a[to])


def get_device_by_mountpoint(mountpoint):
    """
        This accepts a mountpoint and returns the device assignment: /dev/sda1 and mountpoint
        """
    partitions = psutil.disk_partitions(all=False)
    for p in partitions:
        if p.device.startswith('/dev/sd') and p.mountpoint.startswith(mountpoint):
            return p.device

def get_mountpoint_by_device(device):
    """
        This accepts a mountpoint and returns the device assignment: /dev/sda1 and mountpoint
        """
    partitions = psutil.disk_partitions(all=False)
    for p in partitions:
        if p.device.startswith(device):
            return p.mountpoint


def get_device_info(action, device):
    """
    This allows us to query specific information about our drives including
    temperatures, smart assessments, and space available to use for plots.
    It allows us to simply hand it a drive number (drive0, drive22, etc)
    and will present us with the data back. This utilizes pySMART, but
    a word of caution, use the TrueNAS versions linked to above, the PiPy
    version has a bug!
    """
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
        This looks at all available plot drives that start with /dev/sd and include
        /mnt/enclosure in the mount path (this covers all of my plot drives), it then
        looks for any drive that has enough space for at least one plot (k32), sorts
        that list based on the drive# sorting (drive0, drive10, etc) sorting and then
        returns the mountpoint of the device we want to use. Basically the same as above
        but simply returns the 'next' available drive we want to use. This also checks
         to make sure the drive selected has not been marked as "offline".
        #TODO incorporate in get_plot_drive_with_available_space()
        """
    #with open('offlined_drives', 'r') as offlined_drives_list:
    #    offlined_drives = [current_drives.rstrip() for current_drives in offlined_drives_list.readlines()]
    available_drives = []
    for part in psutil.disk_partitions(all=False):
        if part.device.startswith('/dev/sd') \
                and part.mountpoint.startswith('/mnt/dst') \
                and get_device_info('space_free_plots', part.device) >= 1:
            available_drives.append((part.mountpoint, part.device))
    return natsorted(available_drives)[0]

if __name__ == '__main__':
    d = get_list_of_plot_drives()
    print(d)



