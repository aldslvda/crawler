#!/usr/bin/env python
#coding: utf-8

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
import base64
from bs4 import BeautifulSoup
import appSystemVars
from com_logger import appLogger

from requestData import RequestData
from appTaskSender import appCrawlerQueue
from com_logger import appLogger
from hashlib import md5
reload(sys)
sys.setdefaultencoding( "utf-8" )

MODULENAME = 'xinhua'
MAINCONFIGBUFFER = open('etc/system.conf','r').read()
#MAINCONFIGBUFFER = '{"appDicts": {"xinhua": {"category": "app", "sign": "xinhua", "indexPage": null, "id": 144, "name": "\u5fae\u4fe1"}}, "log": {"log_file": "syslog", "log_level": "DEBUG"}, "appCrawlerMQ": {"host_queue": "host_dispatch", "exchange": "appCrawler_task", "url": "amqp://guest:guest@121.40.73.207:5672", "routing_key": "appCrawler_task_high", "queue": "appCrawler_task_high", "link_queue": "link_dispatch"}, "crawler_db": {"username": "", "host": "", "password": "", "port": "", "dbname": ""}, "trackSource": {"url": "api/tracksource?sourceType=app", "host": "121.199.64.158", "port": 8080}, "general": {"process_num": 4, "timeperiod": 1, "cost_time": 28800}, "dbpc": {"service": "xhs.appCrawler", "interval": 120, "component": "appMainCrawler", "host": "192.168.1.146", "try_times_limit": 3, "port": 5800}}'
#TRACESOURCEID = json.loads(MAINCONFIGBUFFER)['appDicts'][MODULENAME]['id']
TRACESOURCEID = 903

def loadSystemConf(config):
    conf = appSystemVars.appSystemConf
    conf.loadConfig(config)
    return conf

def usage():
    print '%s -c config_dir' % sys.argv[0]
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
    xinhuaCrawlerQueue.setProducer()
    xinhuaCrawlerQueue.setTask(task)
    appLogger.info('send to host mq [%s]' %str(task))

def DateFormat(publishtime):
    return time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(publishtime))

def detailUrl(item):
    if 'http://' in item['content_url']:
        return item['content_url']
    return "http://mp.weixin.qq.com"+item['content_url']

def getList(url):
    req = urllib2.Request(url)
    res = urllib2.urlopen(req)
    return res.read()

def sendToMQ(rd):
    rd_json = rd.hostparseToJson()
    rd_base64 = base64.encodestring(json.dumps(rd_json))
    print rd_json['content']
    setTask(rd_base64)

def setRdInfo(newsurl,rd):
    try:
        detailurl = newsurl
        print detailurl
        time.sleep(5)
        detail = getList(detailurl)
        soup = BeautifulSoup(detail,'lxml')
        rd.setClipUrl(detailurl)
        title = soup.find('title')
        appLogger.info("Setting up Requestdata ... NewsTitle is " + title.text)
        rd.setClipTitle(title.text)
        info = soup.find('div',attrs = {'class':'xinhua-info'}).text.split('2017')
        print info
        rd.setPublishTime('2017'+info[1])
        rd.setClipSource(info[0])
        videosrc = []
        rd.setCategory('video')
        vlist = soup.find_all('video')
        for i in vlist:
            videosrc.append(i["src"])
        rd.setSourceUrl(videosrc)
        print json.dumps(rd.hostparseToJson())
        return rd,True
    except:
        appLogger.error(traceback.format_exc())
        appLogger.info('crawl page failed')
        return rd,False
def getXinhuaList(url):
    listdetail = getList(url)
    listsoup = BeautifulSoup(listdetail,'lxml')
    clist = []
    for i in listsoup.find_all('tr'):
        if u'新华视频' in  i.text:
            #print i.text
            for j in i.find_all('td'):
                if 'http://' in j.text:
                    clist.append(j.text)
    return clist
def getNewsList(date):
    lasttime = CurrentTime

    appLogger.info("Crawling Xinhuashe Video")
    
    rd = RequestData()
    rd.setSouceType('app')
    rd.setMetaID('')
    rd.setTrackSourceID(TRACESOURCEID)
    try:
        url = 'http://pub.zhongguowangshi.com/getRecord?date='+date
        print url
        newsList = getXinhuaList(url)
            
    except:
        appLogger.info("fail to crawl page")
        return
    for newsurl in newsList:
        rd,isSuccess= setRdInfo(newsurl,rd)        
        if not isSuccess:
            continue

        appLogger.info(rd._clip_title + "is successfully crawled , sending to MQ...")
        if len(rd._source_url)!=0 or len(rd._content)!=0:
            sendToMQ(rd)
        lasttime = rd._publish_time
def main():

    global  xinhuaConf,xinhuaCrawlerQueue,Channels,CurrentTime,TenDaysAgoTime
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
    #2. load xinhua config
    xinhuaCrawlerQueue = appCrawlerQueue(
            ampqer.getURL(), ampqer.getExchange(), ampqer.getRoutingKey(), ampqer.getHostQueue() 
            )
    CurrentTime = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime())
    TenDaysAgo = (datetime.datetime.now() - datetime.timedelta(int(timeperiod)))
    TenDaysAgoTime = TenDaysAgo.strftime("%Y-%m-%d %H:%M:%S")
    #start crawler
    appLogger.info("Start xinhuaCrawler ...")
    for i in range(3):
        videodate = DateFormat(int(time.time())-3600*24*i)[:10]
        getNewsList(videodate)
    #crawl timeline

if __name__ == '__main__':
    while True:
        try:
            main()
        except:
            appLogger.error(traceback.format_exc())
        time.sleep(3600)

