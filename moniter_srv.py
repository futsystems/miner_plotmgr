#!/usr/bin/python
# -*- coding: utf-8 -*-

import os

from flask import Flask
from flask import request
from flask import render_template
import subprocess

import logging.config

logging.config.fileConfig('logging.conf')
logger = logging.getLogger('nagios')

app = Flask(__name__)

@app.route('/icinga2/pki/ticket')
def pki_ticket():
    type = request.args.get('type')
    server_id = request.args.get('id')
    if type is None or type == '':
        return "please provider type,[plotter|harvester]"
    if server_id is None or server_id == '':
        return "please provider server_id,[001/002]"
    server_name = "%s-%s" % (type, server_id)
    logger.info("generate ticket for %s" % server_name)
    result = subprocess.check_output(["icinga2", "pki", "ticket", "--cn", server_name])
    return result

@app.route('/icinga2/config/plotter')
def config_plotter():
    server_id = request.args.get('id')
    if server_id is None or server_id == '':
        return "please provider server_id,[001/002]"
    subprocess.check_output(["/etc/icinga2/zones.d/master/config_plotter.sh", "%s" % server_id])
    return "update config for plotter-%s success" % server_id

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)