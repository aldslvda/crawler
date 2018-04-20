#!/usr/bin/env python
#coding: utf-8

from __future__ import division
import os
import sys,syslog
import json
import time
import datetime
import traceback
import json
import urllib2,urllib
import sqlite3
import base64
import requests
import re
from bs4 import BeautifulSoup
import appSystemVars
from com_logger import appLogger

from appTaskSender import appCrawlerQueue
from com_logger import appLogger
from hashlib import md5
import thread
from selenium import webdriver
import ConfigParser
import copy
import signal
import subprocess
reload(sys)
sys.setdefaultencoding("utf-8")

MODULENAME = 'weibo'
MAINCONFIGBUFFER = open('etc/system.conf', 'r').read()
HEADERS = {}
def loadSystemConf(config):
    conf = appSystemVars.appSystemConf
    conf.loadConfig(config)
    return conf

def usage():
    appLogger.info( '%s -c config_dir' % sys.argv[0])
    exit(-1)

def loadConfig(config):
    return json.loads(open(config).read())

def getMd5(string):
    m = md5()
    m.update(string)
    return m.hexdigest()
def setTask(task):
    weiboCrawlerQueue.setProducer()
    weiboCrawlerQueue.setTask(task)
    appLogger.info('send to host mq')

def setlinkTask(task):
    weibolinkQueue.setProducer()
    weibolinkQueue.setTask(task)
    print('send to link mq')
def DateFormat(publishtime):
    return time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(publishtime))

def getweiboChannels(tracksourceHost,tracksourcePort):
    url = 'http://'+str(tracksourceHost)+':'+str(tracksourcePort)+'/api/tracksource?sourceType=weibo&limit=10000'
    print url
    res = requests.get(url)
    jsonstr = res.text.encode('utf-8')
    return  json.loads(jsonstr)['rows']


def weiboNewsList(channel):
    url = 'http://www.weibo.com/'+channel['sign']+'?profile_ftype=1&is_all=1#_0'
    success, news = False, None
    phantomjs_cmd = 'python bin/load_phantomjs.py weibo load_page "%s"'%(url,)
    p = subprocess.Popen(phantomjs_cmd, shell=True)
    p.communicate()
    #time.sleep(300)
    res = json.load(open('weibo.out', 'r+'))
    #print res
    if not res['status']:
        success = True
        news = res['data']['news']
    else:
        appLogger.error(res['data']['error'])
    return success, news
def sendToMQ(rd):
    rd_base64 = base64.encodestring(json.dumps(rd))
    #appLogger.info(rd['content'])
    setTask(rd_base64)

def sendTolinkMQ(rd):
    rd_base64 = base64.encodestring(json.dumps(rd))
    setlinkTask(rd_base64)

def parse_repost(repost):
    try:
        return int(repost)
    except:
        return 0

def getNewsList(channel):
    appLogger.info("Crawling Channels ... channelid is " + channel['name'])

    time.sleep(10)
    print channel['sign'], channel['name'].encode('utf-8')
    try:
        isSuccess, newsList = weiboNewsList(channel)
        if not isSuccess or (newsList is None or len(newsList) < 1):
            return
    except:
        appLogger.error(traceback.format_exc())
        appLogger.warn("fail to crawl "+channel['name']+" main page")
        return
    for rd in newsList:
        rd['trackSourceId'] = int(channel['id'])
        appLogger.info(rd['clipTitle'] + "is successfully crawled , sending to MQ...")
        if len(rd['sourceUrl']) != 0 or len(rd['content']) != 0:
            sendToMQ(rd)

def main():
    global config, weiboCrawlerQueue, Channels, CurrentTime, TenDaysAgoTime, weibolinkQueue
    if len(sys.argv) != 3:
        usage()

    config_dir = sys.argv[2]
    configFile = os.path.join(config_dir, MODULENAME+".conf")

    #1.load system config
    appConf = appSystemVars.appSystemConf
    appConf.loadConfigBuffer(MAINCONFIGBUFFER)
    crawlerDB = appConf.getCrawlerDB()
    resultManager = appConf.getResultManager()
    DBPC = appConf.getDBPC()

    logConfigger = appConf.getLogger()
    ampqer = appConf.getMQ()
    timeperiod = appConf.getTimePeriod()

    tracksource = appConf.getTrackSource()
    tracksourceHost = tracksource.getHost()
    tracksourcePort = tracksource.getPort()
    #2. load weibo config
    Channels = getweiboChannels(tracksourceHost, tracksourcePort)
    config = ConfigParser.ConfigParser()
    config.read(configFile)
    weiboCrawlerQueue = appCrawlerQueue(\
        ampqer.getURL(), ampqer.getExchange(), ampqer.getRoutingKey(), ampqer.getHostQueue())

    weibolinkQueue = appCrawlerQueue(\
        ampqer.getURL(), ampqer.getExchange(), ampqer.getRoutingKey(), ampqer.getLinkQueue())
    CurrentTime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    TenDaysAgo = (datetime.datetime.now() - datetime.timedelta(int(timeperiod)))
    TenDaysAgoTime = TenDaysAgo.strftime("%Y-%m-%d %H:%M:%S")
    #start crawler
    appLogger.info("Start weiboCrawler ...")

    start = time.time()
    for channel in Channels:
        if channel['name'] in '新华网 央视新闻  北京日报  新浪视频 中安在线 人民日报 重庆晚报  泰州晚报 北京晨报 南通网':
            print channel['name']
            getNewsList(channel)
    end = time.time()
    #crawl timeline
    print end-start
if __name__ == '__main__':
    while True:
        try:
            main()
        except:
            appLogger.error(traceback.format_exc())
        time.sleep(1200)
