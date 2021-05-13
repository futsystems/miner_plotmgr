#!/usr/bin/python
# -*- coding: utf-8 -*-

import os

from flask import Flask
from flask import request
from flask import render_template
from plotter_mgr import PlotterManager
from message import Response
import driver
import logging.config

logging.config.fileConfig('logging.conf')
logger = logging.getLogger('nas')

template_dir = os.path.dirname(os.path.realpath(__file__))
template_dir = os.path.join(template_dir, 'templates')

logger.info('template dir:%s' % template_dir)

app = Flask(__name__, template_folder=template_dir)

plotter = PlotterManager()

@app.route('/')
def hello_world():
    return 'plotter server'


@app.route('/config/nagios')
def config_nagios():
    import socket
    driver_list = driver.get_plotter_driver_list()
    cache_list = driver.get_plotter_cache_list()
    vcpu_count = os.cpu_count()
    data={'name': socket.gethostname(),
          'driver_list': driver_list,
          'driver_cnt': len(driver_list),
          'cache_list': cache_list,
          'cache_cnt': len(cache_list),
          'vcpu_cnt': vcpu_count,

          }
    return render_template('plotter.nagios.html', data=data)


@app.route('/config/frpc')
def config_frpc():
    import socket
    hostname = socket.gethostname()
    server_id = hostname.split('-')[1]
    data={'name': socket.gethostname(),
          'server_id': server_id

          }
    return render_template('plotter.frpc.html', data=data)

@app.route('/config/plotman')
def config_client():
    import socket
    hostname = socket.gethostname()
    server_id = hostname.split('-')[1]
    driver_list = driver.get_plotter_driver_list()
    cache_list = driver.get_plotter_cache_list()
    data={'name': socket.gethostname(),
          'server_id': server_id,
          'driver_list': driver_list,
          'driver_cnt': len(driver_list),
          'cache_list': cache_list,
          'cache_cnt': len(cache_list),

          }
    return render_template('plotter.frpc.html', data=data)



@app.route('/plot/sending/nas/set')
def plot_sending_set_nas():
    """
    set nas ip address, plotter will send plot to
    :return:
    """
    nas_ip = request.args.get('nas_ip')
    if nas_ip is None or nas_ip == '':
        return Response(100, 'nas ip is empty').to_json()
    plotter.set_nas_server(nas_ip)
    return Response(0, '').to_json()

@app.route('/plot/sending/start')
def start_plot_sending():
    """
    start sending plot to nas server
    :return:
    """
    res = plotter.start_sending_process()
    return Response(0 if res[0] else 1,res[1]).to_json()


@app.route('/plot/sending/stop')
def stop_plot_sending():
    """
    stop sending plot to nas server
    :return:
    """
    res = plotter.stop_sending_process()
    return Response(0 if res[0] else 1, res[1]).to_json()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)


