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
from hashlib import md5
import StringIO, gzip
reload(sys)
sys.setdefaultencoding( "utf-8" )

MODULENAME = 'jinritt'
MAINCONFIGBUFFER = open('etc/system.conf','r').read()
#TRACESOURCEID = json.loads(MAINCONFIGBUFFER)['appDicts'][MODULENAME]['id']
TRACESOURCEID = json.loads(MAINCONFIGBUFFER)['appDicts'][MODULENAME]['id']
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
    jinrittCrawlerQueue.setProducer()
    jinrittCrawlerQueue.setTask(task)
    print('sent to host mq')

def DateFormat(publishtime):
    return time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(publishtime))

def getChannels():
    url = 'http://a1.go2yd.com/Website/user/login-as-guest?appid=yidian&cv=2.6.1.3&distribution'+\
    '=com.apple.appstore&net=wifi&password=936ab0ac0775ef325f24d84def9ab7eb33837024&platform=0&'+\
    'secret=e3c7ff428f84e282cd4983aa220d3f328db3ef5f&username=HG_5A0905CFE252&version=010904'
    loginfo = requests.get(url).json()
    print json.dumps(loginfo)
    global Cookie
    Cookie = loginfo['cookie']
    clist = []
    cnlurl = 'http://a1.go2yd.com/Website/user/get-info?platform=1&appid=yidian&cv=3.2.0(42227)&version=010913&net=wifi'
    headers = {'Cookie':Cookie}
    for i in requests.get(cnlurl, headers = headers).json()['user_channels']:
        clist.append({'name':i['name'], 'id':i['channel_id']})
    return clist
def id2Url(channel, pagenum):
    url = 'http://a1.go2yd.com/Website/channel/news-list-for-channel?platform=1&infinite=true&'+\
    'cstart=0&cend=50&appid=yidian&cv=3.2.0(42227)&refresh=1&channel_id='+str(channel['id'])+'&fields=docid&'+\
    'fields=date&fields=image&fields=image_urls&fields=like&fields=source&fields=title&fields=url'+\
    '&fields=comment_count&fields=up&fields=down&version=010913&net=wifi'
    print url
    return json.loads(getList(url))['result']

def detailUrl(item):
    return item['url']

def getList(url):
    req = urllib2.Request(url)
    req.add_header("Cookie", Cookie)
    res = urllib2.urlopen(req)
    return res.read()

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
        pubtime = newsitem['date']
        rd.setPublishTime(pubtime)
        imagesrc = []
        rd.setCategory('image')
        soup = BeautifulSoup(getList(detailurl))
        text = soup.find_all("p")
        imglist = soup.find_all("img")
        for img in imglist:
            if img.has_attr('src') and img['src'] != '':
                imagesrc.append(img['src'].replace('\\"', ''))
        rd.setSourceUrl(imagesrc)
        content = ''
        for t in text:
            if t.string:
                content += t.string
        content = content.replace('\r', '').replace('\n', '').replace('\t', '').replace('"', '“')
        rd.setContent(content)
        print '====*'+rd._clip_title+'*===='
        print json.dumps(rd.hostparseToJson())
        return rd, True
    except KeyError:
        appLogger.warning(traceback.format_exc())
        return rd, False
    except:
        appLogger.error(traceback.format_exc())
        return rd, False

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
        break

def main():

    global  jinrittConf,jinrittCrawlerQueue,Channels,CurrentTime,TenDaysAgoTime
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
    #2. load jinritt config
    jinrittConf = loadConfig(configFile)
    Channels = getChannels()
    #jinrittCrawlerQueue = appCrawlerQueue (jinrittConf["amqpurl"],jinrittConf["request_queue"], jinrittConf["request_queue"], jinrittConf["request_queue"])
    jinrittCrawlerQueue = appCrawlerQueue(
            ampqer.getURL(), ampqer.getExchange(), ampqer.getRoutingKey(), ampqer.getHostQueue()
            )
   
    CurrentTime = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime())
    TenDaysAgo = (datetime.datetime.now() - datetime.timedelta(int(timeperiod)))
    TenDaysAgoTime = TenDaysAgo.strftime("%Y-%m-%d %H:%M:%S")
    #start crawler
    print("Start jinrittCrawler ...")
    for channel in Channels:
        getNewsList(channel)

if __name__ == '__main__':
    try:
        main()
    except:
        appLogger.error(traceback.format_exc())

