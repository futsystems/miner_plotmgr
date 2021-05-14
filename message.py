#!/usr/bin/python
# -*- coding: utf-8 -*-


import json
from flask import jsonify

class Response(object):
    def __init__(self, code, msg, data=None):
        self._code = code
        self._msg = msg
        self._data = data


    def to_json(self):
        return jsonify(
            {
                'code' : self._code,
                'msg' : self._msg,
                'data' : self._data

            }
        )