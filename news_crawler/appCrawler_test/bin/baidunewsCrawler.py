#!/usr/bin/env python
#coding: utf-8

import os
import sys
import json
import time
import datetime
import traceback
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
sys.setdefaultencoding("utf-8")

MODULENAME = 'baidunews'
MAINCONFIGBUFFER = open('etc/system.conf', 'r').read()
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
    baidunewsCrawlerQueue.setProducer()
    baidunewsCrawlerQueue.setTask(task)
    print('sent to host mq')

def DateFormat(publishtime):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(publishtime))

def getChannels(channelid):
    clist = []
    for i in channelid:
        clist.append({'name':i, 'id':channelid[i]})
    return clist
def id2Url(channel,pagenum):
    url = 'http://api.baiyue.baidu.com/sn/api/recommendlist'
    print url
    data = channel['id']
    return requests.post(url, data).json()['data']['news']

def detailUrl(item):
    return item['url']

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
        pubtime = DateFormat(int(newsitem['ts'])/1000)
        rd.setPublishTime(pubtime)
        rd.setClipSource(newsitem['site'])
        imagesrc = []
        rd.setCategory('image')
        soup = BeautifulSoup(getList(detailurl))
        text = soup.find_all("p")
        imglist = soup.find_all("img")
        for img in imglist:
            if img.has_attr('src') and img['src']:
                imagesrc.append(img['src'].replace('\\"', ''))
            if img.has_attr('data-src') and img['data-src']:
                imagesrc.append(img['data-src'].replace('\\"', ''))
        rd.setSourceUrl(imagesrc)
        content = ''
        for t in text:
            if t.string:
                content += t.string
        content = content.replace('\r', '').replace('\n', '').replace('\t', '').replace('"', '“')
        rd.setContent(content)
        if content:
            f = file('./newstext/'+getMd5(rd._clip_title)+'.txt', 'w+')
            f.write(content)
            f.close()
        print '====*'+rd._clip_title+'*===='
        print json.dumps(rd.hostparseToJson())
        return rd, True
    except:
        appLogger.error(traceback.format_exc())
        print('crawl page failed')
        return rd, False

def getNewsList(channel):
    lasttime = CurrentTime
    print("Crawling Channels ... channelid is " +channel['name'])
    pagenum = 0
    rd = RequestData()
    rd.setTrackSourceID(TRACESOURCEID)
    rd.setSouceType('app')
    rd.setMetaID('')
    while cmp(lasttime, TenDaysAgoTime) == 1:
        time.sleep(1)
        print channel['name'], pagenum
        try:
            news_list = id2Url(channel, pagenum)
            if not news_list:
                break
        except:
            appLogger.error(traceback.format_exc())
            print("fail to crawl page")
            break
        cnt = 0
        for newsitem in news_list:
            time.sleep(0.5)
            if len(newsitem) == 1:
                continue
            cnt += 1
            rd, isSuccess = setRdInfo(newsitem, rd)
            if not isSuccess:
                continue

            print(rd._clip_title + "is successfully crawled , sending to MQ...")
            if rd._source_url or rd._content:
                sendToMQ(rd)
            lasttime = rd._publish_time
        if cnt:
            pagenum += 1
        else:
            break

def main():

    global  baidunewsConf, baidunewsCrawlerQueue, Channels, CurrentTime, TenDaysAgoTime
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
    #2. load baidunews config
    baidunewsConf = loadConfig(configFile)
    channelid = baidunewsConf
    Channels = getChannels(channelid)
    baidunewsCrawlerQueue = appCrawlerQueue(ampqer.getURL(), ampqer.getExchange(), ampqer.getRoutingKey(), ampqer.getHostQueue())
    CurrentTime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    TenDaysAgo = (datetime.datetime.now() - datetime.timedelta(int(timeperiod)))
    TenDaysAgoTime = TenDaysAgo.strftime("%Y-%m-%d %H:%M:%S")
    #start crawler
    print("Start baidunewsCrawler ...")
    for channel in Channels:
        getNewsList(channel)

if __name__ == '__main__':
    try:
        main()
    except:
        appLogger.error(traceback.format_exc())

