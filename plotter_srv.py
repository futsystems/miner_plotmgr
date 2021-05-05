#!/usr/bin/python
# -*- coding: utf-8 -*-


from flask import Flask
from flask import request
from plotter_mgr import PlotterManager
from message import Response
import logging.config

logging.config.fileConfig('logging.conf')
logger = logging.getLogger('plotter')

app = Flask(__name__)

plotter = PlotterManager()

@app.route('/')
def hello_world():
    return 'hello world'



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


