#!/usr/bin/env python
#coding: utf-8

import sys 
import os
import httplib
import json
import requests

class httpClient(object):
    def __init__(self, host, port, user, pasw):
        self._host = host
        self._port = port
        self._user = user
        self._pasw = pasw
        self._conn = None #conn

    def httpsConn(self):
        self._conn = httplib.HTTPSConnection(self._host, self._port)

    def httpConn(self):
        self._conn = httplib.HTTPConnection(self._host, self._port)

    def request(self, method, url, request):
        self._conn.request(method, '', request)
        res = self._conn.getresponse()

        return res.status, res.read()

def getAppList(host, port, url='', username='', password=''):
    if not url:
        url = 'api/tracksource?sourceType=app&subclass=video'
    ret = requests.get('http://%s:%d/%s' %(host, port, url))
    return ret.ok, ret.json()

def sendTaskToRM(host, port=443, username='', password=''):
    pass

if __name__ == '__main__':
    print getAppList('192.168.1.11', 8080)
