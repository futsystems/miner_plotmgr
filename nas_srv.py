#!/usr/bin/python
# -*- coding: utf-8 -*-


from flask import Flask
from flask import request
from nas_mgr import NasManager
from message import Response

import logging
import logging.config

logging.config.fileConfig('logging.conf')
logger = logging.getLogger('nas')

app = Flask(__name__)
nas = NasManager()


@app.route('/')
def hello_world():
    return 'hello world'

@app.route('/debug')
def debug():
    return 'debug'


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
def stop_nc():
    """
    stop nc
    :return:
    """
    nc = nas.get_current_nc()
    return Response(0, '', nc).to_json()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)


