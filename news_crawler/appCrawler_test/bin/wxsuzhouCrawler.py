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
import StringIO, gzip
reload(sys)
sys.setdefaultencoding( "utf-8" )

MODULENAME = 'wxsuzhou'
MAINCONFIGBUFFER = open('etc/system.conf','r').read()

TRACESOURCEID = json.loads(MAINCONFIGBUFFER)['appDicts'][MODULENAME]['id']
#TRACESOURCEID = json.loads(MAINCONFIGBUFFER)['appDicts'][MODULENAME]['id']
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
    wxsuzhouCrawlerQueue.setProducer()
    wxsuzhouCrawlerQueue.setTask(task)
    print('sent to host mq')

def DateFormat(publishtime):
    return time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(publishtime))

def id2Url(channel):
    url = channel['id']
    print url
    soup =BeautifulSoup(getList(url))
    newsList = []
    for i in soup.find_all('a'):
        if i.has_attr('href') and '/doc/' in i['href'] and DateFormat(int(time.time()))[:4] in i['href']:
            newsList.append('http://news.2500sz.com/'+i['href'])
    return newsList

def getList(url):
    req = urllib2.Request(url)    
    res = urllib2.urlopen(req)
    return res.read()

def sendToMQ(rd):
    rd_json = rd.hostparseToJson()
    rd_base64 = base64.encodestring(json.dumps(rd_json))
    print(json.dumps(rd_json))
    setTask(rd_base64)
def setRdInfo(newsitem,rd):
    try:
        detailurl = newsitem
        print detailurl
        soup = BeautifulSoup(getList(detailurl))
        info = soup.find('section',attrs={'class':'dbt'})
        contentsoup = soup.find('div',attrs={'class':'wen'})
        title = info.h1.text
        pubtime = info.h2.span.i.text
        print("Setting up Requestdata ... NewsTitle is " + title)
        rd.setClipUrl(detailurl)
        rd.setClipTitle(title)
        rd.setPublishTime(pubtime)
        imagesrc = []
        rd.setCategory('image')
        text = contentsoup.find_all("p")
        imglist = contentsoup.find_all("img")
        for img in imglist:
            if img['src']!='':
                imagesrc.append('http://news.2500sz.com/'+img['src'].replace('\\"',''))
        rd.setSourceUrl(imagesrc)
        content = ''
        for t in text:
            if t.text!=None:
                content+=t.text
        content = content.replace('\r','').replace('\n','').replace('\t','').replace('"','“')
        rd.setContent(content)
        if len(content)>0:
            f = file('./newstext/'+getMd5(rd._clip_title)+'.txt','w+')
            f.write(content)
            f.close()
        print json.dumps(rd.hostparseToJson())
        return rd,True
    except:
        appLogger.error(traceback.format_exc())
        print('crawl page failed')
        return rd,False

def getNewsList(channel):
    lasttime = CurrentTime
    print("Crawling Channels ... channelid is " +channel['name'])
    rd = RequestData()
    rd.setTrackSourceID(TRACESOURCEID)
    rd.setSouceType('app')
    rd.setMetaID('')
    while (cmp(lasttime,TenDaysAgoTime) == 1):
        time.sleep(1)
        print channel['name']
        try :
            newsList = id2Url(channel)
            if newsList==None or len(newsList)<1:
                break
        except:
            appLogger.error(traceback.format_exc())
            print("fail to crawl page")
            break

        for newsitem in newsList:
            time.sleep(0.5)
            #print(newsitem["title"])
            rd,isSuccess= setRdInfo(newsitem,rd)        
            if not isSuccess:
                continue

            print(rd._clip_title + "is successfully crawled , sending to MQ...")
            if len(rd._source_url)!=0 or len(rd._content)!=0:
                sendToMQ(rd)

            lasttime = rd._publish_time
        break

def main():

    global  wxsuzhouConf,wxsuzhouCrawlerQueue,Channels,CurrentTime,TenDaysAgoTime
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


    #2. load wxsuzhou config
    wxsuzhouConf = loadConfig(configFile)
    Channels = wxsuzhouConf["channels"]
    #wxsuzhouCrawlerQueue = appCrawlerQueue (wxsuzhouConf["amqpurl"],wxsuzhouConf["request_queue"], wxsuzhouConf["request_queue"], wxsuzhouConf["request_queue"])
    wxsuzhouCrawlerQueue = appCrawlerQueue(
            ampqer.getURL(), ampqer.getExchange(), ampqer.getRoutingKey(), ampqer.getHostQueue()
            )
   
    CurrentTime = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime())
    TenDaysAgo = (datetime.datetime.now() - datetime.timedelta(int(timeperiod)))
    TenDaysAgoTime = TenDaysAgo.strftime("%Y-%m-%d %H:%M:%S")
    #start crawler
    print("Start wxsuzhouCrawler ...")
    for channel in Channels:
        getNewsList(channel)

if __name__ == '__main__':
    try:
        main()
    except:
        appLogger.error(traceback.format_exc())

