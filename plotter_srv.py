#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import requests, socket
from flask import Flask
from flask import request
from flask import render_template
from plotter_mgr import PlotterManager
from message import Response
import driver
import logging.config,traceback
import subprocess


logging.config.fileConfig('logging.conf')
logger = logging.getLogger('nas')

template_dir = os.path.dirname(os.path.realpath(__file__))
template_dir = os.path.join(template_dir, 'templates')

logger.info('template dir:%s' % template_dir)

app = Flask(__name__, template_folder=template_dir)

plotter = PlotterManager()

@app.route('/')
def hello_world():
    return 'plotter server v1.0'


@app.route('/config/nagios')
def config_nagios():
    """
    get nagios node config file
    :return:
    """
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
    driver_list = driver.get_plotter_driver_list()
    cache_list = driver.get_plotter_cache_list()
    data={'name': socket.gethostname(),
          'driver_list': driver_list,
          'cache_list': cache_list,
          }
    return render_template('plotter.hpool.yaml', data=data)


@app.route('/config/plotman')
def config_plotman():
    """
    get plotman config file
    1.get cache/dst device base on lcoal system
    2.get plotting/scheduling config from management system
    :return:
    """
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

    import requests
    query = {'id': server_id}
    # get plot config from config center, if not setted, will return default value
    response = requests.get('http://114.215.171.108:9090/server/plotter/plot-config', params=query)
    logger.info('response:%s' % response)

    config = response.json()
    logger.info('plot config data:%s' % config)

    #data = data.update(data2)
    logger.info('data:%s' % data)
    #{'k': '32', 'e': True, 'n_threads': 3, 'n_buckets': 128, 'job_buffer': 4200, 'global_max_jobs': 10,
    # 'global_stagger_m': 48, 'tmpdir_max_jobs': 10, 'tmpdir_stagger_phase_major': 2, 'tmpdir_stagger_phase_minor': 1,
    # 'tmpdir_stagger_phase_limit': 5}
    return render_template('plotter.plotman.yaml', data=data, config=config)

@app.route('/config/plotman/is_plotting_run')
def config_plotman_ISPLOTTINGRUN():
    """
    get plot config is_plotting_run
    如果设置为False则srv.plot重启后就不会执行plot程序，直到该参数设置为True
    :return:
    """
    try:
        hostname = socket.gethostname()
        server_id = hostname.split('-')[1]
        query = {'id': server_id}
        # get plot config from config center, if not setted, will return default value
        response = requests.get('http://114.215.171.108:9090/server/plotter/info', params=query)
        config = response.json()
        if config['code'] == 0:
            logger.info('response:%s plot info data:%s' % (response, config))

            return config['data']['is_plotting_run']
    except Exception as e:
        logger.error(traceback.format_exc())
    finally:
        return False






@app.route('/service/restart')
def restart_service():
    """
    restart service base on service name
    :return:
    """
    service_name = request.args.get('service_name')
    result = subprocess.check_call(["supervisorctl", "restart", service_name])
    return Response(result,'restart service %s' % ('success' if result == 0 else 'failed')).to_json()


@app.route('/config/plotman/apply')
def apply_plotman_config():
    """
    generate plotman config and apply
    :return:
    """
    result = subprocess.check_call(["/opt/src/scripts/apply_plotman_config.sh"])
    return Response(result,'apply plotman  %s' % ('success' if result == 0 else 'failed')).to_json()


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
    nas_ip = request.args.get('nas_ip')
    if nas_ip is None or nas_ip == '':
        return Response(100, 'nas ip is empty').to_json()
    res = plotter.start_sending_process(nas_ip)
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


