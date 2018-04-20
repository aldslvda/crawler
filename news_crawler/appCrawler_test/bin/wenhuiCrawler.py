#!/usr/bin/env python
#coding: utf-8

import os
import sys
import json
import time
import datetime
import traceback
import json
import urllib2,urllib
import sqlite3
import requests
import base64
from bs4 import BeautifulSoup
import appSystemVars
from com_logger import appLogger

from requestData import RequestData
from appTaskSender import appCrawlerQueue
###
from hashlib import md5
reload(sys)
sys.setdefaultencoding( "utf-8" )
MODULENAME = 'wenhui'
#MAINCONFIGBUFFER = open('etc/system.conf','r').read()
MAINCONFIGBUFFER = '{"appDicts": {}, "log": {"log_module": "appCrawler", "log_file": "syslog", "log_level": "DEBUG"}, "appCrawlerMQ": {"host_queue": "host_dispatch", "exchange": "appCrawler_task", "url": "amqp://guest:guest@121.40.73.207:5672", "routing_key": "appCrawler_task_high", "queue": "appCrawler_task_high", "link_queue": "link_dispatch"}, "crawler_db": {"username": "", "host": "", "password": "", "dbname": "", "port": ""}, "trackSource": {"url": "resultmanage/tracksource?sourceType=app", "host": "192.168.1.120", "port": 8080}, "general": {"process_num": 4, "timeperiod": 1, "cost_time": 28800}, "dbpc": {"service": "xhs.appCrawler", "interval": 120, "component": "appMainCrawler", "host": "192.168.1.146", "try_times_limit": 3, "port": 5800}}'
#TRACESOURCEID = json.loads(MAINCONFIGBUFFER)['appDicts'][MODULENAME]['id']
TRACESOURCEID = 128
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
    wenhuiCrawlerQueue.setProducer()
    wenhuiCrawlerQueue.setTask(task)
    print('||||||send to host mq success!|||||')

def sendToMQ(rd):
    rd_json = rd.hostparseToJson()
    rd_base64 = base64.encodestring(json.dumps(rd_json))
    print('send to host mq [%s]' %json.dumps(rd_json))
    setTask(rd_base64)
    

def DateFormat(publishtime):
    return time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(publishtime))

def id2Url(channel,pagenum):
    #print channel['name'].encode("utf-8")
    url = 'http://203.156.244.190:8081/whbapp_web/content/findContents.action?channelId='+str(channel['id'])+'&page='+str(pagenum)
    print url
    return url

def getChannels():
    url = 'http://203.156.244.190:8081/whbapp_web/content/getConfig.action?type=2'
    channels = json.loads(getList(url))['channels']
    channels.append({'id':0,'name':'main'})
    print json.dumps(channels)
    return channels

def detailUrl(item):
    detail = requests.get(item['contentUrl']).json()
    return detail

def getList(url):
    r = requests.get(url)
    return r.text

def setRdInfo(newsitem,rd):
    try:
        print("Setting up Requestdata ... NewsTitle is " + newsitem["title"])
        detail= detailUrl(newsitem)
        print detail
        rd.setClipUrl(detail['shareUrl'])
        rd.setClipTitle(newsitem["title"])
        pubtime = newsitem['releaseDate']
        rd.setPublishTime(pubtime)
        imagesrc = []
        rd.setCategory('image')
        imglist = detail['images']
        for img in imglist:
            imagesrc.append(img['imageUrl'])
        rd.setSourceUrl(imagesrc)
        content = ''
        text = BeautifulSoup(detail['html']).find_all('p')
        for t in text:
            if t.text!=None:
                content+=t.text
        content = content.replace('\r','').replace('\n','').replace('\t','').replace('"','“')
        rd.setContent(content)
        if len(content)>0:
            f = file('./newstext/'+getMd5(rd._clip_title)+'.txt','w+')
            f.write(content)
            f.close()
        print '====*'+rd._clip_title+'*===='
        print json.dumps(rd.hostparseToJson())
        return rd,True
    except:
        appLogger.error(traceback.format_exc())
        print('crawl page failed')
        return rd,False


def getNewsList(channel):
    print channel
    pagenum = 1
    lasttime = CurrentTime

    print("Crawling Channels ... channelid is " +channel['name'])
    
    rd = RequestData()

    rd.setTrackSourceID(TRACESOURCEID)
    rd.setSouceType('app')
    rd.setMetaID('')
    while (cmp(lasttime,TenDaysAgoTime) == 1):
        time.sleep(1)
        print channel['id'],pagenum
        clipurl = id2Url(channel,pagenum)
        try :
            newsLists = json.loads(getList(clipurl))
            newsList = []
            for i in newsLists['dataList']:
                for j in i['list']:
                    newsList.append(j)
            if newsList==None or len(newsList)<1:
                break
        except:
            appLogger.error(traceback.format_exc())
            break

        for newsitem in newsList:
            rd,isSuccess= setRdInfo(newsitem,rd)        
            if not isSuccess:
                continue

            print(rd._clip_title + "is successfully crawled , sending to MQ...")
            if len(rd._source_url)!=0 or len(rd._content)!=0:

                sendToMQ(rd)

            lasttime = rd._publish_time
        pagenum += 1

def main():

    global  wenhuiConf,wenhuiCrawlerQueue,Channels,CurrentTime,TenDaysAgoTime
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


    #2. load wenhui config
    wenhuiConf = loadConfig(configFile)
    Channels = getChannels()
    #wenhuiCrawlerQueue = appCrawlerQueue (wenhuiConf["amqpurl"],wenhuiConf["request_queue"], wenhuiConf["request_queue"], wenhuiConf["request_queue"])
    wenhuiCrawlerQueue = appCrawlerQueue(
            ampqer.getURL(), ampqer.getExchange(), ampqer.getRoutingKey(), ampqer.getHostQueue()
            )
   
    CurrentTime = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime())
    TenDaysAgo = (datetime.datetime.now() - datetime.timedelta(int(timeperiod)))
    TenDaysAgoTime = TenDaysAgo.strftime("%Y-%m-%d %H:%M:%S")
    #start crawler
    #print("Start wenhuiCrawler ...")
    print Channels
    for channel in Channels:
        getNewsList(channel)
    #crawl timeline

if __name__ == '__main__':
    try:
        main()
    except:
        appLogger.error(traceback.format_exc())

