#!/usr/bin/env python
#coding: utf-8

from __future__ import division
import os
import sys
import json
import time
import datetime
import traceback
import base64
import requests
import re
from bs4 import BeautifulSoup
import appSystemVars
from com_logger import appLogger
from requestData import RequestData
from appTaskSender import appCrawlerQueue
from hashlib import md5
import thread
from selenium import webdriver
import qq_video_urls
from PIL import Image
from dbc_api_python import deathbycaptcha
import signal
import subprocess
reload(sys)
sys.setdefaultencoding("utf-8")
MODULENAME = 'wechat'
MAINCONFIGBUFFER = open('etc/system.conf','r').read()
#TRACESOURCEID = json.loads(MAINCONFIGBUFFER)['appDicts'][MODULENAME]['id']
#TRACESOURCEID = 0
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

def crawler(config):
    '''
    return RequestData obj
    '''
    rd = RequestData()
    return rd

def getMd5(string):
    m = md5()
    m.update(string)
    return m.hexdigest()
def setTask(task):
    wechatCrawlerQueue.setProducer()
    wechatCrawlerQueue.setTask(task)
    appLogger.info('====> sent to host mq <====')

def DateFormat(publishtime):
    return time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(publishtime))
def getWechatChannels(tracksourceHost,tracksourcePort):
    url = 'http://'+str(tracksourceHost)+':'+str(tracksourcePort)+'/api/tracksource?sourceType=wechat&limit=10000'
    print url
    res = requests.get(url)
    jsonstr = res.text.encode('utf-8')
    return  json.loads(jsonstr)['rows']

def get_phantomjs_driver():
    cap = webdriver.DesiredCapabilities.PHANTOMJS
    cap['phantomjs.page.settings.resourceTimeout'] = '60000'
    cap['phantomjs.page.settings.loadImages'] = True
    cap['phantomjs.page.settings.userAgent'] = \
        "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/538.1 (KHTML, like Gecko) Safari/538.1"

    driver = webdriver.PhantomJS(executable_path='./bin/phantomjs')
    #driver.start_session(cap)
    driver.implicitly_wait(30)
    driver.set_page_load_timeout(30)
    return driver

def wechatNewsList(channel):
    url = 'http://weixin.sogou.com/weixin?type=1&query='+channel["sign"]+'&ie=utf8&_sug_=y&_sug_type_='
    phantomjs_cmd = 'python bin/load_phantomjs.py wechat load_page "%s"'%(url,)
    p = subprocess.Popen(phantomjs_cmd, shell=True)
    p.communicate()
    success, news = False, None
    res = json.load(open('wechat.out', 'r+'))
    #print res
    if not res['status']:
        success = True
        img_news = res['data']['img_news']
        video_news = res['data']['video_news']
    else:
        appLogger.error(res['data']['error'])
    return success, img_news, video_news


def getList(url, headers=None):
    r = requests.Session()
    req = r.get(url=url, verify=False)
    return req.text.encode('utf-8')

def sendToMQ(rd):
    rd_base64 = base64.encodestring(json.dumps(rd))
    appLogger.info(rd['clipTitle'])
    setTask(rd_base64)

def getNewsList(channel):
    lasttime = CurrentTime
    appLogger.info("Crawling Channels ... channelid is " +channel['name'])
    
    isSuccess, img_news, video_news = wechatNewsList(channel)
    if not isSuccess:
        return
    for newsitem in img_news:
        newsitem['trackSourceId'] = int(channel["id"])
        if newsitem['sourceUrl'] or newsitem['content']:
            sendToMQ(newsitem)

    for newsitem in video_news:
        newsitem['trackSourceId'] = int(channel["id"])
        if newsitem['sourceUrl'] or newsitem['content']:
            sendToMQ(newsitem)

def main():
    global  wechatConf, wechatCrawlerQueue, Channels, CurrentTime, TenDaysAgoTime
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
    #2. load wechat config
    try:
        Channels = getWechatChannels(tracksourceHost, tracksourcePort)
    except:
        appLogger.error(traceback.format_exc())
        wechatConf = loadConfig(configFile)
        Channels = wechatConf['channels']
    wechatCrawlerQueue = appCrawlerQueue(
        ampqer.getURL(), ampqer.getExchange(), ampqer.getRoutingKey(), ampqer.getHostQueue()
        )
    CurrentTime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    TenDaysAgo = (datetime.datetime.now() - datetime.timedelta(int(timeperiod)))
    TenDaysAgoTime = TenDaysAgo.strftime("%Y-%m-%d %H:%M:%S")
    #start crawler
    appLogger.info("Start wechatCrawler ...")
    print len(Channels)
    start = time.time()
    
    channel_list = '太行日报 新华视点 淮北日报 新华视界 新华国际 微黔江 天津日报 人民日报 上海观察 深圳特区报'
    for channel in Channels:
        if channel['name'] in channel_list:
            #print channel['name']
            getNewsList(channel)
            time.sleep(300)
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
