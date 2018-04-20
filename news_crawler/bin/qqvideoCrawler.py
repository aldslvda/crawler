#!/usr/bin/env python
#coding: utf-8

import os
import sys
import json
import time
import datetime
import traceback
import json
import urllib2
import random
import ctypes
import md5
import sqlite3
import base64
import appSystemVars
from com_logger import appLogger

from bs4 import BeautifulSoup
from requestData import RequestData
from appTaskSender import appCrawlerQueue

reload(sys)
sys.setdefaultencoding("utf-8")

MODULENAME = 'qqvideo'
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

def setTask(task):
    qqvideoCrawlerQueue.setProducer()
    qqvideoCrawlerQueue.setTask(task)
    print('sent to host mq')

def setlinkTask(task):
    qqvideolinkQueue.setProducer()
    qqvideolinkQueue.setTask(task)
    print('send to link mq [%s]' %str(task))

def DateFormat(s):
    return s[3:7]+"-"+s[7:9]+"-"+s[9:11]+" 00:00:00"

def header_gen(url):
    qnrid,qnsig = qnsig_gen()
    header = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.10; rv:48.0) Gecko/20100101 Firefox/48.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': 1,
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    header["qn-rid"] = qnrid
    header["qn-sig"] = qnsig
    return header

def qnsig_gen():
    a = '2001-1-1 00:00:00'
    t = time.mktime(time.strptime(a,'%Y-%m-%d %H:%M:%S'))
    curtime = int(time.time()-t)
    ra = ctypes.c_uint32(random.randrange(0xffffffff))
    dw = ctypes.c_uint32(((ctypes.c_uint64(ra.value).value * 0x80008001) >> 32) & 0xffffffff)
    ret = ctypes.c_uint32(ra.value - (((dw.value >> 0xf) << 0x10) - (dw.value >> 15)))
    sz3 = "%x%04x"%(curtime,ret.value)
    m = md5.new()
    m.update('appver=17_areading_2.5.0&cgi=getSubNewsInterest&deviceToken=&devid=865174029323182&qn-rid='\
    +sz3+'&secret=qn123456')
    qnsig = m.hexdigest().upper()
    return sz3,qnsig

def id2Url(pageid):
    return "http://r.inews.qq.com/getQQNewsIndexAndItems?appver=8.1.1_qqnews_4.7.0&__qnr=1b535362278d&screen_width=320"+\
    "&idfa=079CEE24-1595-4B6D-9AFD-38E8492E7BEE&screen_height=568&devid=67B9A8F8-0EC8-486C-847B-231D7D709D67&device_model=iPhone&screen_scale=2&store=248&chlid="\
    +pageid+"&ischannel=1&lc_ids=&readmode=1&isoffline=0&kChannelUpdateChannelID="+pageid

def detailUrl(pageid,newsid):
    return "http://cdn.inews.qq.com/getSimpleNews/8.1.1_qqnews_4.7.0/"+pageid+"/"+newsid+"/wifi?appver=8.1.1_qqnews_4.7.0&screen_width=320"+\
    "&idfa=079CEE24-1595-4B6D-9AFD-38E8492E7BEE&screen_height=568&devid=67B9A8F8-0EC8-486C-847B-231D7D709D67&device_model=iPhone&screen_scale=2&store=248"

def sendToMQ(rd):
    rd_json = rd.hostparseToJson()
    rd_base64 = base64.encodestring(json.dumps(rd_json))
    setTask(rd_base64)

def sendTolinkMQ(rd):
    rd_json = rd.linkparseToJson()
    rd_base64 = base64.encodestring(json.dumps(rd_json))
    setlinkTask(rd_base64)

def setRdInfo(channelid,newsitem,rd):
    rd.setPublishTime(DateFormat(str(newsitem["id"])))
    clipurl = detailUrl(channelid,newsitem["id"])
    print clipurl
    try:
        newsdetail = json.loads(getList(clipurl))
    except:
        return rd,rd,False
    #print getList(clipurl)
    if not newsdetail.has_key("url"):
        return rd,rd,False
    print json.dumps(newsdetail)
    rd.setClipUrl(newsdetail["url"])
    soup = BeautifulSoup(getList(newsdetail["url"]))
    if soup.body.p == None:
        return rd,rd,False
    newstitle = soup.body.p.get_text()
    content = ''
    for i in soup.find_all('p'):
        content+=i.text
    content = content.replace('\r','').replace('\n','').replace('\t','').replace('"','“')
    rd.setContent(content)
    rd.setClipTitle(newstitle)

    rdv = rd.copyrd()
    rdv.setCategory('video')
    rdi = rd.copyrd()
    rdi.setCategory('image')
    videosrc = []
    imagesrc = []
    rdi.setViewCount(int(newsitem["comments"]))
    rdv.setViewCount(int(newsitem["video_hits"]))
    
    print("Setting up Requestdata ... NewsTitle is " + newstitle)
    for source in newsdetail["attribute"]:
        if source[0:3]=='COM':
            continue
        if source[0:3]=='VID':
            videosrc.append(newsdetail["attribute"][source]["playurl"])
        else:
            imagesrc.append(newsdetail["attribute"][source]["url"])
        
    rdi.setSourceUrl(imagesrc)
    if len(videosrc)>0:
        rdv.setOuterClipurl(videosrc[0])
        print json.dumps(rdv.linkparseToJson())
    if len(imagesrc)>0:
        rdi.setSourceUrl(imagesrc)
    
    return rdi,rdv,True

def getChannelNewsList():
    print("Crawling Channels ... channelid is " + channelid)

    lasttime = CurrentTime

    rd = RequestData()
    rd.setTrackSourceID(TRACESOURCEID)
    rd.setSouceType('app')
    rd.setMetaID('')

    news_list = id2Url()
        
    domaindb = sqlite3.connect("news.db")
    cursor = domaindb.cursor()
    cursor.execute("create table if not exists qqvideonews (id integer primary key,pid text)")
    #print channelid
    if len(newsLists["idlist"][0]["ids"]) == 0:
        return
    for newsitem in newsLists["idlist"][0]["ids"]:
        if cmp(lasttime,TenDaysAgoTime) == -1:
            break
        if not int(newsitem["exist"]) == 1:
            continue
        cursor.execute("select * from qqvideonews where pid='"+str(newsitem["id"])+"'")
        if len(cursor.fetchall())>0:
            #print("Newsitem has been crawled before, pass...")
            continue
        try:
            rdi,rdv,isSuccess = setRdInfo(channelid,newsitem,rd)
        except:
            isSuccess = False
        if not isSuccess:
            continue
        print("Newsitem is successfully crawled , sending to MQ...")
        if len(rdi._source_url)!=0:
            #print rdi.hostparseToStr()
            sendToMQ(rdi)
        if rdv._outer_clipurl!="":
            #print rdv.linkparseToStr()
            sendTolinkMQ(rdv)
        domaindb.execute("insert into qqvideonews(pid) values('"+ str(newsitem["id"]) +"')")
        domaindb.commit()
        lasttime = rd._publish_time
        #print rd._publish_time +"::::::"+ rd._clip_title
        time.sleep(0.1)
    domaindb.close()
    
def main():
    global  qqvideoConf,qqvideoCrawlerQueue,ChannelIds,CurrentTime,TenDaysAgoTime,qqvideolinkQueue
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


    #2. load qqvideo config
    qqvideoConf = loadConfig(configFile)
    ChannelIds = qqvideoConf["ChannelIds"]
    #qqvideoCrawlerQueue = appCrawlerQueue (qqvideoConf["amqpurl"],qqvideoConf["request_queue"], qqvideoConf["request_queue"], qqvideoConf["request_queue"])
    #qqvideolinkQueue = appCrawlerQueue (qqvideoConf["amqpurl"],qqvideoConf["outerlink_queue"], qqvideoConf["outerlink_queue"], qqvideoConf["outerlink_queue"])
    qqvideoCrawlerQueue = appCrawlerQueue(
            ampqer.getURL(), ampqer.getExchange(), ampqer.getRoutingKey(), ampqer.getHostQueue()
            )
    qqvideolinkQueue = appCrawlerQueue(
            ampqer.getURL(), ampqer.getExchange(), ampqer.getRoutingKey(), ampqer.getLinkQueue()
            )
    CurrentTime = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime())
    TenDaysAgo = (datetime.datetime.now() - datetime.timedelta(int(timeperiod)))
    TenDaysAgoTime = TenDaysAgo.strftime("%Y-%m-%d %H:%M:%S")

    #3. start to crawler
    getChannelNewsList()

if __name__ == '__main__':
    try:
        main()
    except:
        appLogger.error(traceback.format_exc())

