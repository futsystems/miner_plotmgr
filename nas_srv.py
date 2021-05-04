#!/usr/bin/python
# -*- coding: utf-8 -*-


from flask import Flask
from flask import request
from nas_mgr import NasManager

app = Flask(__name__)
nas = NasManager()


@app.route('/')
def hello_world():
    return 'hello world'

@app.route('/plot/upload', methods=['GET', 'POST'])
def plot_upload():
    plot_file = request.form['file']
    res = nas.start_nc(plot_file)

    return res.to_json()

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)


