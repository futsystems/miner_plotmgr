#!/usr/bin/python
# -*- coding: utf-8 -*-


import subprocess
from flask import Flask
from flask import request
from flask import render_template
from nas_mgr import NasManager
from message import Response
import logging.config

import driver

logging.config.fileConfig('logging.conf')
logger = logging.getLogger('nas')

app = Flask(__name__)
nas = NasManager()


@app.route('/')
def hello_world():
    return 'nas server'


@app.route('/config/frpc')
def config_frpc():
    """
    get frpc config file base on server name, server number
    :return:
    """
    import socket
    hostname = socket.gethostname()
    server_id = hostname.split('-')[1]
    data={'name': socket.gethostname(),
          'server_id': server_id

          }
    return render_template('plotter.frpc.html', data=data)


@app.route('/config/hpool')
def config_hpool():
    """
    get hpool config file, depend on plot driver
    :return:
    """
    import socket
    driver_list = driver.get_nas_driver_list()
    data={'name': socket.gethostname(),
          'driver_list': driver_list,
          }
    return render_template('plotter.hpool.yaml', data=data)

@app.route('/nc/start')
def start_nc():
    """
    start nc server to receive plot file
    :return:
    """
    plot_file = request.args.get('file')
    if plot_file is None or plot_file == '':
        return Response(100, 'file args is empty').to_json()

    logger.info('upload plot file:%s' % plot_file)

    res = nas.start_nc(plot_file)
    return res.to_json()


@app.route('/nc/stop')
def stop_nc():
    """
    stop nc
    :return:
    """
    res = nas.stop_nc()
    return res.to_json()

@app.route('/nc/current')
def current_nc():
    """
    stop nc
    :return:
    """
    nc = nas.get_current_nc()
    return Response(0, '', nc).to_json()


@app.route('/plot/info')
def plot_info():
    """
    stop nc
    :return:
    """
    path = request.args.get('path')
    if path is None or path == '':
        return Response(100, 'path args is empty').to_json()
    info = nas.get_plot_info(path)
    return Response(0, '', info).to_json()


@app.route('/driver/list')
def driver_list():
    """
    stop nc
    :return:
    """
    import driver
    list = driver.get_nas_driver_list()
    return Response(0,'',list).to_json()

@app.route('/service/restart')
def restart_service():
    """
    restart service base on service name
    :return:
    """
    service_name = request.args.get('service_name')
    result = subprocess.check_call(["supervisorctl", "restart", service_name])
    return Response(result,'restart service %s' % ('success' if result == 0 else 'failed')).to_json()

@app.route('/update')
def update_system():
    """
    update system
    1. /opt/src
    2. /opt/plotter/bin
    3. /opt/nas/bin
    :return:
    """

    command = ['/opt/src/update.sh']
    subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return Response(0, 'update system in background').to_json()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)


