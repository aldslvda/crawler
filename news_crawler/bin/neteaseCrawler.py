#!/usr/bin/env python
#coding: utf-8

import os
import sys
import json
import time
import datetime
import traceback
import urllib2
import sqlite3
import appSystemVars
from com_logger import appLogger

import base64
from bs4 import BeautifulSoup
from requestData import RequestData
from appTaskSender import appCrawlerQueue
###
import requests
reload(sys)
sys.setdefaultencoding("utf-8")

MODULENAME = 'netease'
MAINCONFIGBUFFER = open('etc/system.conf', 'r').read()

TRACESOURCEID = json.loads(MAINCONFIGBUFFER)['appDicts'][MODULENAME]['id']
#TRACESOURCEID = 91

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

def setTask(task):
    neteaseCrawlerQueue.setProducer()
    neteaseCrawlerQueue.setTask(task)
    print('sent to host mq')

def DateFormat(publishtime):
    return time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(publishtime))

def id2Url(pageid,pagenum):
    if pageid =="T1348647853363":
        return "http://c.m.163.com/nc/article/headline/"+pageid+"/"+str((pagenum-1)*20)+"-20.html"
    elif pageid == 'T1457068979049':
        return 'http://c.m.163.com/recommend/getChanListNews?offset='+str((pagenum-1)*20)+\
        '&size=20&channel=T1457068979049&fn=1&passport=&devId=COoUQi7TC401Gv%2FIL0SAxCzBjRa5URXqn70OXHLf%2BRo9KaScezfwpQJEf%2B0EHvF8'+\
        '&version=16.2&spever=false&net=wifi&lat=%2FB6bSQcj6o%2Fb3pxg6be8dg%3D%3D&lon=ydQv2Aj5Vdf%2BpbOBpT%2F5dQ%3D%3D&ts=1476869102'+\
        '&sign=7cviwqvoSDTNcENlv%2Bj0pri9y11WnbsvYXvyN6ri39h48ErR02zJ6%2FKXOnxX046I&encryption=1&canal=ppgg_news'
    else :
        return "http://c.m.163.com/nc/article/list/"+pageid+"/"+str((pagenum-1)*20)+"-20.html"

def detailUrl(newsid):
    return "http://api.netease.cn/neteasego/articlev2.json?id="+ newsid +"&uid=0a0be6b22f09b74c&wm=b207&oldchwm=12030_0001&imei=860311029747961&user_uid=2815529711&from=6048095012&postt=news_news_toutiao_feed_1&chwm=12030_0001"

def getList(url):
    req = urllib2.Request(url)
    req.add_header('User-Agent','Mozilla/5.0 (Linux; Android 4.1.2; Nexus 7 Build/JZ054K) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.166 Safari/535.19')
    res = urllib2.urlopen(req)
    return json.loads(res.read())

def setRdInfo(newsitem,rd):
    print("Setting up Requestdata ... NewsTitle is " + newsitem["title"])
    #print json.dumps(newsitem)
    if not newsitem.has_key("url_3w"):
        return None
    detailurl = newsitem["url_3w"]
    r = requests.get(detailurl)
    soup = BeautifulSoup(r.text)
    content = ''
    for i in soup.find_all('p'):
        content+=i.text
    content = content.replace('\r','').replace('\n','').replace('\t','').replace('"','“')    
    rd.setContent(content)
    rd.setClipUrl(detailurl)
    rd.setClipTitle(newsitem["title"])
    rd.setCategory("image")
    rd.setPublishTime(newsitem["ptime"])
    if newsitem.has_key("replyCount"):
        rd.setViewCount(int(newsitem["replyCount"]))
    rd.setSourceTitle(newsitem["title"])
    if newsitem.has_key("source"):
        rd.setClipSource(newsitem["source"])
    srcurl = []
    if newsitem.has_key("imgsrc"):
        srcurl.append(newsitem["imgsrc"])

    if newsitem.has_key("imgextra"):
        for img in newsitem["imgextra"]:
            srcurl.append(img["imgsrc"])

    rd.setSourceUrl(srcurl)
    #print json.dumps(rd.hostparseToJson())
    return rd
def setVinfo(newsitem,rd):
    print("Setting up Requestdata ... NewsTitle is " + newsitem["title"])
    #print json.dumps(newsitem)
    rd.setClipUrl(newsitem['mp4_url'])
    rd.setClipTitle(newsitem["ltitle"])
    rd.setCategory("video")
    rd.setPublishTime(newsitem["ptime"])
    if newsitem.has_key("playCount"):
        rd.setViewCount(int(newsitem["playCount"]))
    rd.setSourceTitle(newsitem["title"])
    if newsitem.has_key("videosource"):
        rd.setClipSource(newsitem["videosource"])
    srcurl = []
    if newsitem.has_key("mp4_url"):
        srcurl.append(newsitem["mp4_url"])
    #if newsitem.has_key("m3u8_url"):
    #    srcurl.append(newsitem["m3u8_url"])
    rd.setSourceUrl(srcurl)
    print json.dumps(rd.hostparseToJson())
    return rd

def getChannelNewsList(channelid):
    print("Crawling Channels ... channelid is " + channelid)

    pagenum = 1
    lasttime = CurrentTime

    rd = RequestData()
    rd.setTrackSourceID(TRACESOURCEID)
    rd.setSouceType('app')
    rd.setMetaID('')
    #print channelid
    while cmp(lasttime,TenDaysAgoTime) == 1:
        #print pagenum
        listurl = id2Url(ChannelIds[channelid],pagenum)
        print listurl
        if ChannelIds[channelid]=='T1457068979049':
            newsLists = getList(listurl)[u'\u89c6\u9891']
        else:
            newsLists = getList(listurl)[ChannelIds[channelid]]
        if len(newsLists) == 0:
            break
        for newsitem in newsLists:
            #print json.dumps(newsitem)
            try:
                if newsitem.has_key('mp4_url') or newsitem.has_key('m3u8_url'):
                    rd = setVinfo(newsitem, rd)
                else:
                    rd = setRdInfo(newsitem, rd)
                lasttime = rd._publish_time

                if not rd:
                    continue
                #print rd._publish_time +":::::"+ rd._clip_title
                print("Newsitem is successfully crawled , sending to MQ...")
                #print rd.hostparseToStr()
                rd_json = rd.hostparseToJson()
                rd_base64 = base64.encodestring(json.dumps(rd_json))
                setTask(rd_base64)
            except:
                appLogger.error(traceback.format_exc())
                print("Newsitem crawling failed")
                continue
        pagenum += 1
def main():

    if len(sys.argv) != 3:
        usage()

    config_dir = sys.argv[2]
    configFile = os.path.join(config_dir, MODULENAME+".conf")
    global neteaseConf, ChannelIds, neteaseCrawlerQueue, CurrentTime, TenDaysAgoTime
    #1.load system config
    appConf = appSystemVars.appSystemConf
    appConf.loadConfigBuffer(MAINCONFIGBUFFER)
    crawlerDB = appConf.getCrawlerDB()
    resultManager = appConf.getResultManager()
    DBPC = appConf.getDBPC()
    logConfigger = appConf.getLogger()
    ampqer = appConf.getMQ()
    timeperiod = appConf.getTimePeriod()


    #2. load netease config

    neteaseConf = loadConfig(configFile)
    ChannelIds = neteaseConf["ChannelIds"]
    neteaseCrawlerQueue = appCrawlerQueue(ampqer.getURL(), ampqer.getExchange(), \
                                          ampqer.getRoutingKey(), ampqer.getHostQueue())

    CurrentTime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    TenDaysAgo = (datetime.datetime.now() - datetime.timedelta(int(timeperiod)))
    TenDaysAgoTime = TenDaysAgo.strftime("%Y-%m-%d %H:%M:%S")

    #3. start to crawler
    ##ChannelIds = {"video":"T1457068979049"}
    for channelid in ChannelIds:
        getChannelNewsList(channelid)


if __name__ == '__main__':
    try:
        main()
    except:
        appLogger.error(traceback.format_exc())

