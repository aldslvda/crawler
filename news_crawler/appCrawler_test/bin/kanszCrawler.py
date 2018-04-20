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
import base64
import base64
from bs4 import BeautifulSoup
import appSystemVars
from com_logger import appLogger

from requestData import RequestData
from appTaskSender import appCrawlerQueue
###
from hashlib import md5
reload(sys)
sys.setdefaultencoding("utf-8")

MODULENAME = 'kansz'
MAINCONFIGBUFFER = open('etc/system.conf','r').read()

TRACESOURCEID = json.loads(MAINCONFIGBUFFER)['appDicts'][MODULENAME]['id']
#TRACESOURCEID = 0
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
    kanszCrawlerQueue.setProducer()
    kanszCrawlerQueue.setTask(task)
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
    url = 'http://mobile.kan0512.com/szh/news.php?appkey=mmv6bfo799vcDHqfZBlqtDp4NHCCb4xn&appid=36&device_token=a208b0006a33c29fd5a9e65cb1c59a30&version=4.0.3&app_version=4.0.3&avos_device_token=a208b0006a33c29fd5a9e65cb1c59a30&client_id_ios=d4f0d314bff53801c4fdb1f7a10451bc&offset='+str(pagenum*20)+'&column_id='+str(channel['id'])
    return url

def getChannels():
    url = 'https://mobile.kan0512.com/szh/news_recomend_column_copy.php?appkey=mmv6bfo799vcDHqfZBlqtDp4NHCCb4xn&appid=36&device_token=a208b0006a33c29fd5a9e65cb1c59a30&version=4.0.3&app_version=4.0.3&avos_device_token=a208b0006a33c29fd5a9e65cb1c59a30'
    return url

def detail_url(newsid):
    return "https://mobile.kan0512.com/szh/item.php?appkey=mmv6bfo799vcDHqfZBlqtDp4NHCCb4xn&appid=36&device_token=a208b0006a33c29fd5a9e65cb1c59a30&version=4.0.3&app_version=4.0.3&avos_device_token=a208b0006a33c29fd5a9e65cb1c59a30&client_id_ios=d4f0d314bff53801c4fdb1f7a10451bc&id=%s"%str(newsid)

def getList(url):
    req = urllib2.Request(url)
    res = urllib2.urlopen(req)
    return res.read()

def setRdInfo(newsitem,rd):
    try:
        #print json.dumps(newsitem)
        print("Setting up Requestdata ... NewsTitle is " + newsitem["title"])
        clip_url = detail_url(newsitem['id'])
        detail = json.loads(getList(clip_url))
        rd.setClipTitle(newsitem["title"])
        pubtime = newsitem['publish_time']
        rd.setPublishTime(pubtime)
        imagesrc = []
        rd.setCategory('image')
        if newsitem.has_key("childs_data"):
            imglist = newsitem["childs_data"]  
            for img in imglist:
                imagesrc.append(img['host']+img['dir']+img['filepath']+img['filename'])
        rd.setSourceUrl(imagesrc)
        rd.setClipUrl(newsitem['content_url'])
        soup = BeautifulSoup(detail['content'])
        text = soup.find_all("p")
        content = ''
        for t in text:
            if t.string:
                content+=t.string
        content = content.replace('\r','').replace('\n','').replace('\t','').replace('"','“')
        rd.setContent(content)
        rdv = rd.copyrd()
        rdv.setCategory('video')
        vsrc = []
        if detail.has_key('content_video_url'):
            vsrc.append(detail['content_video_url'])
        rdv.setSourceUrl(vsrc)
        rd.hostparseToJson()
        rdv.hostparseToJson()
        return rd,rdv,True
    except:
        appLogger.error(traceback.format_exc())
        print('crawl page failed')
        return rd,rd,False

def getNewsList(channel):
    #print channel
    pagenum = 0
    lasttime = CurrentTime

    print("Crawling Channels ... channelid is %s" %channel['name'])
    
    rd = RequestData()

    rd.setTrackSourceID(TRACESOURCEID)
    rd.setSouceType('app')
    rd.setMetaID('')
    while (cmp(lasttime,TenDaysAgoTime) == 1):
        time.sleep(1)
        print channel['name'],pagenum
        clipurl = id2Url(channel,pagenum)
        print clipurl
        try :
            newsLists =  json.loads(getList(clipurl))
            newsList = newsLists['list']
            if not newsList:
                break
        except:
            print("fail to crawl page")
            pagenum += 1
            continue

        for newsitem in newsList:
            if not newsitem.has_key("id") or newsitem['id'] =='':
                continue 

            print(newsitem["title"])

            rd,rdv,isSuccess= setRdInfo(newsitem,rd)        
            if not isSuccess:
                continue

            print(rd._clip_title + "is successfully crawled , sending to MQ...")
            if rd._source_url or rd._content:
                sendToMQ(rd)
            if rdv._source_url or rdv._content:
                sendToMQ(rdv)

            lasttime = rd._publish_time
        pagenum += 1

def main():

    global  kanszConf,kanszCrawlerQueue,Channels,CurrentTime,TenDaysAgoTime
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

    #2. load kansz config
    kanszConf = loadConfig(configFile)
    Channels = json.loads(getList(getChannels()))['list']
    #kanszCrawlerQueue = appCrawlerQueue (kanszConf["amqpurl"],kanszConf["request_queue"], kanszConf["request_queue"], kanszConf["request_queue"])
    kanszCrawlerQueue = appCrawlerQueue(
            ampqer.getURL(), ampqer.getExchange(), ampqer.getRoutingKey(), ampqer.getHostQueue()
            )
   
    CurrentTime = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime())
    TenDaysAgo = (datetime.datetime.now() - datetime.timedelta(int(timeperiod)))
    TenDaysAgoTime = TenDaysAgo.strftime("%Y-%m-%d %H:%M:%S")
    #start crawler
    print("Start kanszCrawler ...")
    for channel in Channels:
        getNewsList(channel)
    #crawl timeline

if __name__ == '__main__':
    try:
        main()
    except:
        appLogger.error(traceback.format_exc())

