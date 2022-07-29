#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import subprocess
from flask import Flask
from flask import request
from flask import render_template
from flask_cors import *

from nas_mgr import NasManager
from message import Response
import datetime
import logging.config

import driver

logging.config.fileConfig('logging.conf')
logger = logging.getLogger('nas')

template_dir = os.path.dirname(os.path.realpath(__file__))
template_dir = os.path.join(template_dir, 'templates')

logger.info('template dir:%s' % template_dir)

harvester = NasManager()

driver_list_cache ={
    'time': datetime.datetime.now(),
    'list': None,
}

from common import NMS_HOST

class HarvesterFlaskApp(Flask):
  def run(self, host=None, port=None, debug=None, load_dotenv=True, **options):
    harvester.on_start()

    #if not self.debug or os.getenv('WERKZEUG_RUN_MAIN') == 'true':
    super(HarvesterFlaskApp, self).run(host=host, port=port, debug=debug, load_dotenv=load_dotenv, **options)

app = HarvesterFlaskApp(__name__, template_folder=template_dir)
CORS(app, resources=r'/*')

@app.route('/')
def hello_world():
    return 'nas server'


@app.route('/config/nagios')
def config_nagios():
    """
    get nagios node config file
    :return:
    """
    import socket
    driver_list = driver.get_nas_driver_list()
    vcpu_count = os.cpu_count()
    data={'name': socket.gethostname(),
          'driver_list': driver_list,
          'driver_cnt': len(driver_list),
          'vcpu_cnt': vcpu_count,
          }
    return render_template('harvester.nagios.html', data=data)

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
    return render_template('harvester.frpc.html', data=data)


def _get_driver_list_cache():
    if driver_list_cache['list'] is None:
        driver_list = driver.get_nas_driver_list()
        driver_list_cache['list'] = driver_list
        driver_list_cache['time'] = datetime.datetime.now()
        return driver_list
    else:
        cache_time = driver_list_cache['time']
        if (datetime.datetime.now() - cache_time).total_seconds() > 60*5:
            driver_list = driver.get_nas_driver_list()
            driver_list_cache['list'] = driver_list
            driver_list_cache['time'] = datetime.datetime.now()
            return driver_list
        else:
            return driver_list_cache['list']



@app.route('/config/hpool')
def config_hpool():
    """
    get hpool config file, depend on plot driver
    :return:
    """
    import socket

    driver_list = _get_driver_list_cache()
    #logger.info('driver list:%s' % driver_list)
    size = request.args.get('size')
    index = request.args.get('index')
    config = harvester.config
    if size is None or index is None:
        data = {'name': socket.gethostname(),
          'driver_list': driver_list,
          'auto_scan_plot': config['auto_scan_plot'],
          'id': 0
          }
        return render_template('harvester.hpool.yaml', data=data)
    else:
        page_list = driver_list[int(index)*int(size):(int(index)+1)*int(size)]
        data = {'name': socket.gethostname(),
          'driver_list': page_list,
          'auto_scan_plot': config['auto_scan_plot'],
          'id': index,
          }
        return render_template('harvester.hpool.yaml', data=data)

@app.route('/config/harvester/flax')
def config_falx():
    """
    get hpool config file, depend on plot driver
    :return:
    """
    import socket
    driver_list = driver.get_nas_driver_list()
    data={'name': socket.gethostname(),
          'driver_list': driver_list,
          }
    return render_template('harvester.flax.html', data=data)

@app.route('/config/harvester/chia')
def config_chia():
    """
    get chia harvester config file
    :return:
    """
    import socket
    import requests

    hostname = socket.gethostname()
    server_id = hostname.split('-')[1]
    driver_list = driver.get_nas_driver_list()

    query = {'id': server_id}

    response = requests.get('http://%s:9090/server/harvester/config' % NMS_HOST, params=query)
    config = response.json()

    logger.info('harvester config data:%s' % config)

    data={'name': hostname,
          'driver_list': driver_list,
          'farmer_address': config['farmer_address']
          }
    return render_template('harvester.chia.html', data=data)


@app.route('/config/hpool/supervisor')
def config_hpool_supervisor():
    """
    get hpool config file, depend on plot driver
    :return:
    """
    index = request.args.get('index')
    data = {'index': index,
      }
    return render_template('harvester.hpool.supervisor.html', data=data)

@app.route('/nc/start')
def start_nc():
    """
    start nc server to receive plot file
    :return:
    """

    plot_file = request.args.get('file')
    if plot_file is None or plot_file == '':
        return Response(100, 'file args is empty').to_json()

    ip_addr = request.remote_addr

    #logger.info('upload plot file:%s' % plot_file)

    res = harvester.start_nc(ip_addr, plot_file)
    return res.to_json()


@app.route('/nc/stop')
def stop_nc():
    """
    stop nc
    :return:
    """
    ip_addr = request.remote_addr

    res = harvester.stop_nc(ip_addr)
    return res.to_json()

@app.route('/nc/current')
def current_nc():
    """
    stop nc
    :return:
    """
    nc = harvester.get_current_nc()
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
    info = harvester.get_plot_info(path)
    return Response(0, '', info).to_json()


@app.route('/driver/list')
def driver_list():
    """
    stop nc
    :return:
    """
    import driver
    list = driver.get_nas_driver_list()
    return Response(0, '', list).to_json()

@app.route('/driver/clean')
def driver_clean():
    """
    stop nc
    :return:
    """
    harvester.clean_harvester_driver()
    return Response(0,'','').to_json()

@app.route('/system/shutdown')
def system_poweroff():
    """
    power machine
    :return:
    """
    os.system("shutdown now -h")
    return Response(0, 'shutdown success').to_json()

@app.route('/config/change')
def config_change():
    """
    restart service base on service name
    :return:
    """
    logger.info('----- config change, restart api.harvester -----')
    command = ['supervisorctl', 'restart', 'api.harvester']
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return Response('', 'will sync config latter').to_json()

@app.route('/service/restart')
def restart_service():
    """
    restart service base on service name
    :return:
    """
    service_name = request.args.get('service_name')
    result = subprocess.check_call(["supervisorctl", "restart", service_name])
    return Response(result,'restart service %s' % ('success' if result == 0 else 'failed')).to_json()


@app.route('/harvester/restart')
def restart_harvester():
    """
    restart service base on service name
    :return:
    """
    service_name = request.args.get('service_name')
    harvester.restart_service(service_name)
    return Response('', 'restart service success').to_json()

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


@app.route('/api/report')
def api_report():
    """
    stop sending plot to nas server
    :return:
    """
    driver_report = driver.get_harvester_driver_report()

    data = {

        'driver':driver_report
    }
    return Response(0,'', data).to_json()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)


