#!/usr/bin/env python
#coding: utf-8

import json
import sys


class CrawlerDB(object):
    def __init__(self):
        self._host = ''
        self._port = 0
        self._user = ''
        self._pasw = ''
        self._name = ''

    def loadConfig(self, config_buf):
        conf_data = json.loads (config_buf)
        class_data = conf_data['crawler_db']
        self._host = class_data['host']
        self._port = class_data['port']
        self._user = class_data['username']
        self._pasw = class_data['password']
        self._name = class_data['dbname']

    def getHost(self):
        return self._host

    def getPort(self):
        return self._port
    
    def getUsername(self):
        return self._user

    def getPassword(self):
        return self._pasw

    def getDBName(self):
        return self._name

class ResultManager(object):
    def __init__(self):
        self._host = ''
        self._port = 0
        self._user = ''
        self._pasw = ''

    def loadConfig(self, config_buf):
        conf_data = json.loads (config_buf)
        class_data = conf_data['result_manager']
        self._host = class_data['host']
        self._port = class_data['port']
        self._user = class_data['username']
        self._pasw = class_data['password']

    def getHost(self):
        return self._host

    def getPort(self):
        return self._port
    
    def getUsername(self):
        return self._user

    def getPassword(self):
        return self._pasw

class DBPC(object):
    def __init__(self):
        self._host = ''
        self._port = 0
        self._service = ''
        self._component = ''
        self._interval = 0
        self._try_time_limit = 0

    def loadConfig(self, config_buf):
        conf_data = json.loads (config_buf)
        class_data = conf_data['dbpc']
        self._host = class_data['host']
        self._port = class_data['port']
        self._service = class_data['service']
        self._component = class_data['component']
        self._interval = class_data['interval']
        self._try_time_limit = class_data['try_times_limit']

    def getHost(self):
        return self._host

    def getPort(self):
        return self._port
    
    def getService(self):
        return self._service

    def setComponent(self, component):
        self._component = component

    def getComponent(self):
        return self._component

    def getInterval(self):
        return self._interval

    def getTryTimeLimti(self):
        return self._try_time_limit

class logger(object):
    def __init__(self):
        self._log_level = 'DEBUG'
        self._log_file = 'syslog'

    def loadConfig(self, config_buf):
        conf_data = json.loads (config_buf)
        class_data = conf_data['log']
        self._log_level = class_data['log_level']
        self._log_file = class_data['log_file']

    def getLogLevel(self):
        return self._log_level

    def getLogFile(self):
        return self._log_file

class rabbitmq(object):
    def __init__(self):
        self._url = ''
        self._queue = ''
        self._exchange = ''
        self._routing_key = ''

    def loadConfig(self, config_buf):
        conf_data = json.loads (config_buf)
        class_data = conf_data['appCrawlerMQ']
        self._url = class_data['url']
        self._host_queue = class_data['host_queue']
        self._link_queue = class_data['link_queue']
        self._exchange = class_data['exchange']
        self._routing_key = class_data['routing_key']

    def getURL(self):
        return self._url

    def getHostQueue(self):
        return self._host_queue
    
    def getLinkQueue(self):
        return self._link_queue

    def getExchange(self):
        return self._exchange

    def getRoutingKey(self):
        return self._routing_key

class trackSource(object):
    def __init__(self):
        self._host = ''
        self._port = 8080
        self._url = ''

    def loadConfig(self, config_buf):
        conf_data = json.loads (config_buf)
        class_data = conf_data['trackSource']
        self._host = class_data['host']
        self._port = class_data['port']
        self._url = class_data['url']

    def getHost(self):
        return self._host

    def getPort(self):
        return self._port

    def getURL(self):
        return self._url

class appSystemConf(object):
    def __init__(self):
        self._crawlerDB = CrawlerDB()
        #self._resultManager = ResultManager()
        self._dbpc = DBPC()
        self._logger = logger()
        self._costTime = 28800
        self._process_num = 4
        self._timeperiod = 1
        self._mq = rabbitmq()
        self._trackSource = trackSource()
        self._config_file = None

    def loadConfig(self, config_file):
        self._config_file = config_file
        f = open(config_file)
        config_buf = f.read()
        f.close()
        self.loadConfigBuffer(config_buf)
    
    def loadConfigBuffer(self, buf):
        self._crawlerDB.loadConfig(buf)
        #self._resultManager.loadConfig(buf)
        self._dbpc.loadConfig(buf)
        self._logger.loadConfig(buf)
        self._mq.loadConfig(buf)
        self._costTime = json.loads(buf).get('general').get('cost_time')
        self._timeperiod = json.loads(buf).get('general').get('timeperiod')
        self._process_num = json.loads(buf).get('general').get('process_num')
        self._trackSource.loadConfig(buf)

    def getConfigFilePath(self):
        return self._config_file
        
    def getCrawlerDB(self):
        return self._crawlerDB

    def getResultManager(self):
        #return self._resultManager
        return None

    def getDBPC(self):
        return self._dbpc

    def getLogger(self):
        return self._logger

    def getMQ(self):
        return self._mq

    def getCostTime(self):
        return self._costTime
    
    def getTrackSource(self):
        return self._trackSource

    def getProcessNum(self):
        return self._process_num

    def getTimePeriod(self):
        return self._timeperiod

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('%s config_file' % (sys.argv[0]))
        sys.exit(0)

    appconf = appSystemConf()
    appconf.loadConfig(sys.argv[1])
    print(appconf)
    print(dir(appconf))
