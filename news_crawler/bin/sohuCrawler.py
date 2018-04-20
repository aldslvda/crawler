#!/usr/bin/env python
#coding: utf-8

import os
import sys,syslog
import json
import time
import datetime
import traceback
import json
import urllib2
import re
from bs4 import BeautifulSoup
import xmltodict
import types
import sqlite3
import base64
import appSystemVars
from com_logger import appLogger

from requestData import RequestData
from appTaskSender import appCrawlerQueue
###

reload(sys)
sys.setdefaultencoding( "utf-8" )

MODULENAME = 'sohu'
MAINCONFIGBUFFER = open('etc/system.conf','r').read()
TRACESOURCEID = json.loads(MAINCONFIGBUFFER)['appDicts'][MODULENAME]['id']

#TRACESOURCEID = 93

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

def DateFormat(publishtime):
    return time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(publishtime))

def setTask(task):
    sohuCrawlerQueue.setProducer()
    sohuCrawlerQueue.setTask(task)
    print('sent to host mq')

def getNewsidAndSubid(link):
    m = re.findall(r'(\w*[0-9]+)\w*',link)
    return m[0],m[1]

def getVideoMid(link):
    m = re.findall(r'(\w*[0-9]+)\w*',link)
    return m[1]

def id2Url(pageid,pagenum):
    return "http://api.k.sohu.com/api/channel/v5/news.go?channelId="\
    +str(pageid)+"&num=20&imgTag=1&showPic=1&picScale=11&rt=json&net=wifi&cdma_lat=30.291624&cdma_lng=120.112367&from=channel&times=1&page="\
    +str(pagenum)+"&action=1&mode=0&cursor=0&mainFocalId=0&focusPosition=1&viceFocalId=0&lastUpdateTime=0&gbcode=330100&p1=NjAxOTc3ODM2MzMyODQ3NTIwNw%3D%3D&gid=02ffff11061111aa097fa653215ce95aa7913aabc9819f&pid=-1"

def AlbumUrl(pageid,pagenum):
    return "http://api.k.sohu.com/api/photos/listInChannel.go?rt=json&channelId="+str(pageid)+\
        "&pageSize=20&pageNo="+str(pagenum)+\
        "&offset=-1&p1=NjAxOTc3ODM2MzMyODQ3NTIwNw%3D%3D&gid=02ffff11061111aa097fa653215ce95aa7913aabc9819f&pid=-1"

def Albumdetail(gid):
    return "http://api.k.sohu.com/api/photos/gallery.go?&gid="+str(gid)+"&openType=0&channelId=54&zgid=02ffff11061111aa097fa653215ce95aa7913aabc9819f&from=news&fromId=null&showSdkAd=1&supportTV=1&refer=3&p1=NjAxOTc3ODM2MzMyODQ3NTIwNw%3D%3D&pid=-1"

def detailUrl(newsid,subid,time):
    return "http://zcache.k.sohu.com/api/news/cdn/v1/article.go/"\
    +newsid+"/1/"+subid+"/0/3/1/24/29/3/1/1/"+time+".xml"

def Videodetail(mid):
    return "http://api.k.sohu.com/api/video/message.go?id="\
    +mid+"&p1=NjAxOTc3ODM2MzMyODQ3NTIwNw%3D%3D&gid=02ffff11061111aa097fa653215ce95aa7913aabc9819f&pid=-1"

def getList(url):
    req = urllib2.Request(url)
    try:
        res = urllib2.urlopen(req,data=None,timeout=5)
        return res.read()
    except:  
        return None 

def sendToMQ(rd):
    rd_json = rd.hostparseToJson()
    rd_base64 = base64.encodestring(json.dumps(rd_json))
    setTask(rd_base64)

def setRdInfo(newsitem,rd):
    #print newsitem["link"]
    newsid,subid = getNewsidAndSubid(newsitem["link"])
    clipurl = detailUrl(newsid,subid,newsitem["time"])
    print clipurl
    rd.setClipUrl(clipurl)
    rd.setClipTitle(newsitem["title"])
    rd.setPublishTime(DateFormat(int(newsitem["updateTime"])/1000))
    rd.setViewCount(int(newsitem["commentNum"]))
    if newsitem.has_key("media"):
        rd.setClipSource(newsitem["media"])
    rd.setCategory('image')
    detail = getList(clipurl)
    if not detail == None and not detail == "":
        newsdetail = xmltodict.parse(detail)
    else :
        return rd,False
    #print json.dumps(newsdetail)
    srcurl = []
    if newsdetail["root"].has_key("photos"):
        if type(newsdetail["root"]["photos"]["photo"]) is types.ListType:
            for img in newsdetail["root"]["photos"]["photo"]:
                #print img
                srcurl.append(img["pic"])
        else:
            srcurl.append(newsdetail["root"]["photos"]["photo"]["pic"])
    if newsdetail['root'].has_key('content'):
        soup = BeautifulSoup(newsdetail['root']['content'])
        text = ''
        for i in soup.find_all('p'):
            text+=i.text
        text = text.replace('\r','').replace('\n','').replace('\t','').replace('"','“')
        rd.setContent(text)
    rd.setSourceUrl(srcurl)
    print '=================REQUEST DATA================'
    print json.dumps(rd.hostparseToJson())
    print '=================REQUEST DATA================'
    return rd,True

def getNewsList(channelid):
    pagenum = 1
    lasttime = CurrentTime

    print("Crawling Channels ... channelid is " + channelid)
    
    rd = RequestData()
    rd.setTrackSourceID(TRACESOURCEID)
    rd.setSouceType('app')
    rd.setMetaID('')
    #get requestdata
    while (cmp(lasttime,TenDaysAgoTime) == 1):
        
        #print pagenum
        listurl = id2Url(ChannelIds[channelid],pagenum)
        print(listurl)
        time.sleep(1)

        newsLists = getList(listurl)

        if newsLists == None:
            continue
        newsLists = json.loads(newsLists)

        if not newsLists.has_key("articles") or len(newsLists["articles"]) == 0:
            break
        for newsitem in newsLists["articles"]:
            if not newsitem.has_key("link") or not newsitem.has_key("time") or newsitem["link"] == "" or newsitem["link"][0:4]=="chan":
                continue
            try:
                rd,isSuccess = setRdInfo(newsitem,rd)
            except:
                isSuccess = False
            if not isSuccess:
                continue
            if len(rd._source_url)==0:
                continue
            
            print(rd._clip_title + "is successfully crawled , sending to MQ...")
            sendToMQ(rd)
            print("successfully sent to MQ !")            

            lasttime = rd._publish_time

        pagenum += 1

def getAlbumList(channelid):
    pagenum = 1
    lasttime = CurrentTime

    print("Crawling Channels ... channelid is " + channelid)
    
    rd = RequestData()
    rd.setTrackSourceID(TRACESOURCEID)
    rd.setSouceType('app')
    rd.setMetaID('')

    domaindb = sqlite3.connect("news.db")
    cursor = domaindb.cursor()
    cursor.execute("create table if not exists sohunews (id integer primary key,pid text)")
    #get requestdata
    while (cmp(lasttime,TenDaysAgoTime) == 1):
        
        #print pagenum
        listurl = AlbumUrl(ChannelIds[channelid],pagenum)

        time.sleep(1)
        newsLists = json.loads(getList(listurl))

        if not newsLists.has_key("news") or len(newsLists["news"]) == 0:
            break
        for newsitem in newsLists["news"]:
            if not newsitem.has_key("gid"):
                continue
            cursor.execute("select * from sohunews where pid='"+str(newsitem["gid"])+"'")
            if len(cursor.fetchall())>0:
                #print("Newsitem has been crawled before, pass...")
                continue
            clipurl = Albumdetail(str(newsitem["gid"]) )
            newsdetail = getList(clipurl)
            if newsdetail == None:
                continue
            rd.setClipUrl(clipurl)
            rd.setClipTitle(newsitem["title"])
            rd.setPublishTime(DateFormat(int(newsitem["time"])/1000))
            rd.setViewCount(int(newsitem["commentNum"]))
            rd.setCategory('image')

            newsdetail = xmltodict.parse(newsdetail)
    
            srcurl = []
            new_srcurl = []
            if newsdetail["root"].has_key("gallery"):
                if type(newsdetail["root"]["gallery"]["photo"]) is types.ListType:
                    for img in newsdetail["root"]["gallery"]["photo"]:

                        srcurl.append(img["pic"])
                else:
                    srcurl.append(newsdetail["root"]["gallery"]["photo"]["pic"])

            if len(srcurl)==0:
                continue

            #FIX https://seals.vobile.cn/trac/ProjectManagement/ticket/743
            for url in srcurl:
                if url.find(',http') > 0:
                    new_srcurl.append(url[:url.find(',http')])
                else:
                    new_srcurl.append(url)

            rd.setSourceUrl(new_srcurl)
            print(rd._clip_title + "is successfully crawled , sending to MQ...")
            sendToMQ(rd)
            print("successfully sent to MQ !")
            domaindb.execute("insert into sohunews(pid) values('"+ str(newsitem["gid"]) +"')")
            domaindb.commit()
            lasttime = rd._publish_time

        pagenum += 1
    domaindb.close()

def getVideoList():
    pagenum = 1
    lasttime = CurrentTime

    print("Crawling Channels ... channelid is VideoChannel")
    
    rd = RequestData()
    rd.setTrackSourceID(TRACESOURCEID)
    rd.setSouceType('app')
    rd.setMetaID('')

    print("Crawling VideoChannel ....")

    domaindb = sqlite3.connect("news.db")
    cursor = domaindb.cursor()
    cursor.execute("create table if not exists sohunews (id integer primary key,pid text)")
    
    #get requestdata
    while (cmp(lasttime,TenDaysAgoTime) == 1):
        
        #print pagenum
        listurl = id2Url(36,pagenum)

        time.sleep(1)
        newsLists = json.loads(getList(listurl))

        if not newsLists.has_key("articles") or len(newsLists["articles"]) == 0:
            break
        for newsitem in newsLists["articles"]:
            if not newsitem.has_key("link") or not newsitem.has_key("time") or newsitem["link"] == "" :
                continue
            cursor.execute("select * from sohunews where pid='"+newsitem["link"]+"'")
            if len(cursor.fetchall())>0:
                #print("Newsitem has been crawled before, pass...")
                pass
            mid = getVideoMid(newsitem["link"])
            clipurl = Videodetail(mid)
            #print clipurl
            newsdetail = getList(clipurl)
            if newsdetail == None:
                continue
            rd.setClipUrl(clipurl)
            rd.setClipTitle(newsitem["title"])
            rd.setCategory('video')
            rd.setPublishTime(DateFormat(int(newsitem["time"])/1000))
            rd.setViewCount(int(newsitem["commentNum"]))
            if newsitem.has_key("media"):
                rd.setClipSource(newsitem["media"])
            newsdetail = json.loads(newsdetail)
    
            srcurl = []
            for item in newsdetail["message"]["playurl"]:
                if newsdetail["message"]["playurl"][item]!="" and \
                   newsdetail["message"]["playurl"][item]!=0  and \
                   newsdetail["message"]["playurl"][item]!=[]  :
                    srcurl.append(newsdetail["message"]["playurl"][item])
            rd.setSourceUrl(srcurl)
            if len(srcurl)==0:
                continue
            print(rd._clip_title + "is successfully crawled , sending to MQ...")
            sendToMQ(rd)
            print("successfully sent to MQ !")
            domaindb.execute("insert into sohunews(pid) values('"+ newsitem["link"] +"')")
            domaindb.commit()
            lasttime = rd._publish_time
            #print type(rd._view_count)
        pagenum += 1
    domaindb.close()

def main():
    global  sohuConf,sohuCrawlerQueue,ChannelIds,CurrentTime,TenDaysAgoTime
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


    #2. load sohu config
    sohuConf = loadConfig(configFile)
    ChannelIds = sohuConf["ChannelIds"]
    #sohuCrawlerQueue = appCrawlerQueue (sohuConf["amqpurl"],sohuConf["request_queue"], sohuConf["request_queue"], sohuConf["request_queue"])
    sohuCrawlerQueue = appCrawlerQueue(
            ampqer.getURL(), ampqer.getExchange(), ampqer.getRoutingKey(), ampqer.getHostQueue()
            )

    CurrentTime = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime())
    TenDaysAgo = (datetime.datetime.now() - datetime.timedelta(int(timeperiod)))
    TenDaysAgoTime = TenDaysAgo.strftime("%Y-%m-%d %H:%M:%S")

    #3.start crawler
    print("Start sohuCrawler ...")
    for channelid in ChannelIds:
        #videos
        if int(ChannelIds[channelid]) == 36:
            #continue
            getVideoList()
        #Album
        if int(ChannelIds[channelid]) == 47 or int(ChannelIds[channelid]) == 54:
            #continue
            getAlbumList(channelid)
        #news
        getNewsList(channelid)

if __name__ == '__main__':
    try:
        main()
    except:
        appLogger.error(traceback.format_exc())

