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
import requests
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

MODULENAME = 'nanfangjia'
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
    nanfangjiaCrawlerQueue.setProducer()
    nanfangjiaCrawlerQueue.setTask(task)
    print('sent to host mq')

def DateFormat(publishtime):
    return time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(publishtime))

def getChannels():
    url = 'http://api.nfapp.southcn.com/nanfang_if/getColumns?siteId=1&version=0&columnType=-1&t=&v=2.8&parentColumnId='
    clist = []
    for j in ['0','20','21']:
        for i in json.loads(getList(url+j))['columns']:
            if i["columnType"] in ['2','4002']:
                clist.append({'name':i['columnName'],'id':i['columnId']})
    return clist
def id2Url(channel,pagenum):
    url = 'http://api.nfapp.southcn.com/nanfang_if/getArticles?columnId='+str(channel['id'])+'&lastFileId=0&count=20&rowNumber='+str(pagenum*20)+'&version=0&adv=1'
    print url
    return json.loads(getList(url))['list']

def detailUrl(item):
    return item['shareUrl']

def getList(url):
    r = requests.get(url)
    r.encoding = r.apparent_encoding
    return r.text

def sendToMQ(rd):
    rd_json = rd.hostparseToJson()
    rd_base64 = base64.encodestring(json.dumps(rd_json))
    print(json.dumps(rd_json))
    setTask(rd_base64)
def setRdInfo(newsitem,rd):
    try:
        print("Setting up Requestdata ... NewsTitle is " + newsitem["title"])
        detailurl = detailUrl(newsitem)
        print detailurl
        rd.setClipUrl(detailurl)
        rd.setClipTitle(newsitem["title"])
        pubtime = newsitem['publishtime'][:19]
        rd.setPublishTime(pubtime)
        imagesrc = []
        rd.setCategory('image')
        soup = BeautifulSoup(getList(detailurl))
        text = soup.find_all("p")
        imglist = soup.find_all("img")
        for img in imglist:
            if img.has_attr('src') and img['src']!='' :
                imagesrc.append(img['src'].replace('\\"',''))
            if img.has_attr('data-src') and img['data-src']!='' :
                imagesrc.append(img['data-src'].replace('\\"',''))
        rd.setSourceUrl(imagesrc)
        content = ''
        for t in text:
            if t.string!=None:
                content+=t.string
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
    lasttime = CurrentTime
    print("Crawling Channels ... channelid is " +channel['name'])
    pagenum =0
    rd = RequestData()
    rd.setTrackSourceID(TRACESOURCEID)
    rd.setSouceType('app')
    rd.setMetaID('')
    while (cmp(lasttime,TenDaysAgoTime) == 1):
        time.sleep(1)
        print channel['name'] ,pagenum 
        try :
            newsList = id2Url(channel,pagenum)
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
        pagenum+=1

def main():

    global  nanfangjiaConf,nanfangjiaCrawlerQueue,Channels,CurrentTime,TenDaysAgoTime
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
    #2. load nanfangjia config
    nanfangjiaConf = loadConfig(configFile)
    Channels = getChannels()
    #nanfangjiaCrawlerQueue = appCrawlerQueue (nanfangjiaConf["amqpurl"],nanfangjiaConf["request_queue"], nanfangjiaConf["request_queue"], nanfangjiaConf["request_queue"])
    nanfangjiaCrawlerQueue = appCrawlerQueue(
            ampqer.getURL(), ampqer.getExchange(), ampqer.getRoutingKey(), ampqer.getHostQueue()
            )
   
    CurrentTime = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime())
    TenDaysAgo = (datetime.datetime.now() - datetime.timedelta(int(timeperiod)))
    TenDaysAgoTime = TenDaysAgo.strftime("%Y-%m-%d %H:%M:%S")
    #start crawler
    print("Start nanfangjiaCrawler ...")
    for channel in Channels:
        getNewsList(channel)

if __name__ == '__main__':
    try:
        main()
    except:
        appLogger.error(traceback.format_exc())

