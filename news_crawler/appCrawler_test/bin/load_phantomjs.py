#!/usr/bin/env python
#coding: utf-8
import time
import sys
import signal
import re
import traceback
import json
import copy
import urllib2
import subprocess
from PIL import Image
from dbc_api_python import deathbycaptcha
from bs4 import BeautifulSoup
from selenium import webdriver
import appSystemVars
from requestData import RequestData
def get_weibo_phantomjs_driver():
    cap = webdriver.DesiredCapabilities.PHANTOMJS
    cap['phantomjs.page.settings.resourceTimeout'] = '30000'
    cap['phantomjs.page.settings.loadImages'] = True
    cap['phantomjs.page.settings.userAgent'] = "Mozilla/5.0 (Macintosh; Intel Mac OS X "\
        +"10_12_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3004.3 Safari/537.36"
    cap["phantomjs.page.customHeaders.Cookie"] = 'UOR=localhost:8080,weibo.com,www.cnblogs.com'\
        +'; SUB=_2AkMi9F5zdcNhrAZXnf0Uzm7kaYRUiFeq7p-gb07ZFyFzLS9Mwl0IxSRqthF8XNyg'\
        +'iETP51EFZ11B26f_WhhMNbUON7HW4dMXSw0.;'
    #set proxy
    driver = webdriver.PhantomJS(executable_path='./bin/phantomjs')
    #driver.start_session(cap)
    driver.implicitly_wait(30)
    driver.set_page_load_timeout(30)
    #print driver.get_cookies()
    return driver

def get_wechat_phantomjs_driver():
    cap = webdriver.DesiredCapabilities.PHANTOMJS
    cap['phantomjs.page.settings.resourceTimeout'] = '60000'
    cap['phantomjs.page.settings.loadImages'] = True
    cap['phantomjs.page.settings.userAgent'] = \
        "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/538.1 (KHTML, like Gecko) Safari/538.1"

    driver = webdriver.PhantomJS(executable_path='./bin/phantomjs')
    #driver.start_session(cap)
    driver.implicitly_wait(30)
    driver.set_page_load_timeout(30)
    return driver


def cut_image():
    image =Image.open('vcode1.jpg')
    box = (290, 20, 400, 65)  #设置要裁剪的区域
    region = image.crop(box)     #此时，region是一个新的图像对象。
    #region.show()#显示的话就会被占用，所以要注释掉
    region.save("vcode_cut.jpg")

def get_vcode():
    client = deathbycaptcha.SocketClient('bm0546', 'vobile123')
    try:
        captcha = client.decode('vcode_cut.jpg', 10)
        if captcha:
            print("CAPTCHA %s solved: %s" % (captcha["captcha"], captcha["text"]))
            return captcha["text"]
    except deathbycaptcha.AccessDeniedException:
        traceback.print_exc()

def transform_short_url(url):
    if 'http' not in url:
        url = 'http:'+url
    res_type = "Fail" #Fail/Weibo/OutLink
    video_url = None
    req = urllib2.urlopen(url)
    current_url = req.geturl()
    if 'weibo.com' in current_url or 'miaopai.com' in current_url:
        res_type = "Weibo"
        try:
            video_url = 'http'+BeautifulSoup(req.read()).find('video')['src']
        except:
            pass
    else:
        res_type = "OutLink"
        video_url = current_url
    if not video_url:
        res_type = "Fail"
    return res_type, video_url

def load_weibo_page(url):
    success, news = False, None
    try:
        driver = get_weibo_phantomjs_driver()
        driver.get(url)
        page_source = driver.page_source
        #print page_source[:30]
        #open('test.html', 'w+').write(page_source)
        driver.get_screenshot_as_file('./weibopage.jpg')
        soup = BeautifulSoup(page_source, "lxml")
        news = soup.find_all('div', {'action-type':'feed_list_item'})
        success = True
        news_list = []
        for i in news:
            rd, success = gen_weibo_news(i)
            if success:
                news_list.append(rd)
        print "==========",len(news_list),"==========="
        with open('weibo.out', 'w+') as f:
            json.dump({"status":0,"data":{"news":news_list}}, f)
    except:
        time.sleep(20)
        with open('weibo.out', 'w+') as f:
            json.dump({"status":-1,"data":{"error":traceback.format_exc()}}, f)
    finally:
        try:
            driver.service.process.send_signal(signal.SIGTERM)
            driver.quit()
        except:
            pass
    exit(0)

def parse_repost(repost):
    try:
        return int(repost)
    except:
        return 0
def gen_weibo_news(newsitem):
    rd = {}
    rd['metaUuid'] = ''
    rd['sourceType'] = 'weibo'
    rd['clipSource'] = ''
    
    try:
        #image and clipurl
        media = newsitem.find("div", {'class':'media_box'})
        rd['category'] = "image"
        imglist = [img['src'].replace("square", "bmiddle").replace("thumbnail", "bmiddle")\
            for img in media.find_all("img")]
        imgsrc = ["http:"+img for img in imglist if img[:2]=='//']
        rd['sourceUrl'] = imgsrc
        postdate = newsitem.find("a", attrs={"node-type": "feed_list_item_date"})
        rd['publishTime'] = postdate['title']
        clip_url = 'http://weibo.com' + postdate['href']
        rd['clipUrl'] = clip_url
        #content and title
        content = newsitem.find("div",attrs={"node-type":"feed_list_content"}).text
        content = content.replace(' ', '')
        topic_group = re.search("#.*#", content)
        clip_group = re.search(u"【.*】", content[:-40])
        clip_title = ''
        if clip_group is not None:
            clip_title += clip_group.group()
        if topic_group is not None:
            clip_title += topic_group.group()

        if not clip_title:
            clip_title = 'weibo.com'
        rd['clipTitle'] = clip_title
        rd['content'] = content
        #viewcount, like and repost
        try:
            count_info = newsitem.find('div', {'class':'WB_handle'})
            repost = count_info.find('span', {'node-type':"forward_btn_text"}).text[1:]
            comment = count_info.find('span', {'node-type':"comment_btn_text"}).text[1:]
            like = count_info.find('span', {'node-type':"like_status"}).text[1:]
            rd['viewCount'] = parse_repost(comment)
            rd['repost'] = parse_repost(repost)
            rd['like'] = parse_repost(like)
        except:
            print traceback.print_exc()
            rd['viewCount'] = 0
            rd['repost'] = 0
            rd['like'] = 0
        #video
        video_tag = newsitem.find('a', {'action-type':'feed_list_url'})
        rdv = copy.deepcopy(rd)
        rdv['category'] = 'video'
        rdv['sourceUrl'] = []
    
        if video_tag and video_tag.has_attr('suda-uatrack') and video_tag['suda-uatrack']:
            res_type, long_url = transform_short_url(video_tag['href'])
            if res_type == 'Weibo':
                rdv['sourceUrl'].append(long_url)
            elif res_type == 'OutLink':
                rdv.pop('sourceUrl')
                rdv["outerClipUrl"] = long_url
            print json.dumps(rdv)
        print json.dumps(rd)
        return rd, True
    except AttributeError:
        traceback.print_exc()
        return rd, False
    except:
        traceback.print_exc()
        time.sleep(20)
        return rd, False
def detailUrl(item):
    if 'http://' in item['content_url']:
        return item['content_url']
    return "http://mp.weixin.qq.com"+item['content_url']

def gen_wechat_news(newsitem, rd):
    rdv, success = None, False
    try:
        detailurl = detailUrl(newsitem).replace('&amp;', '&')
        print detailurl
        time.sleep(5)
        driver = get_wechat_phantomjs_driver()
        driver.get(detailurl)
        time.sleep(10)
        detail = driver.page_source
        #open('test.html', 'w+').write(detail)
        soup = BeautifulSoup(detail, 'lxml')
        print("Setting up Requestdata ... NewsTitle is " + newsitem["title"])
        rd.setClipUrl(detailurl)
        rd.setClipTitle(newsitem["title"])
        pubtime = soup.find('em', attrs={'id':'post-date'}).string+' 00:00:00'
        rd.setPublishTime(pubtime)
        imagesrc = []
        rd.setCategory('image')
        rd.setSourceUrl(imagesrc)
        text = soup.find_all("p")
        sectext = soup.find_all('section')
        imglist = soup.find_all('img')
        for img in imglist:
            if img.has_key('data-src'):
                imagesrc.append(img['data-src'])
        content = ''
        for t in text:
            if t.text != None and t.text not in content:
                content += t.text
        for t in sectext:
            if t.text != None and t.text not in content:
                content += t.text
        content = content.replace('\r', '').replace('\n', '').replace('\t', '').replace('"', '“')
        rd.setContent(content)
        rd = rd.hostparseToJson()
        try:
            rd['viewCount'] = int(soup.find('span', {'id':'sg_readNum3'}).text.replace('+', ''))
            rd['like'] = int(soup.find('span', {'id':'sg_likeNum3'}).text.replace('+', ''))
        except:
            rd['like'], rd['viewCount'] = 0, 0
        #video_urls = qq_video_urls.get_downloadurls_by_content(detail)
        video_urls = []
        rdv = rd.copy()
        rdv['category'] = 'video'
        rdv["sourceUrl"] = video_urls
        success = True
    except:
        time.sleep(20)
        traceback.print_exc()
    finally:
        try:
            driver.service.process.send_signal(signal.SIGTERM)
            driver.quit()
        except:
            pass
    return rd, rdv, success

def load_wechat_page(url):
    try:
        driver = get_wechat_phantomjs_driver()
        driver.get(url)
        page_source = driver.page_source

        soup = BeautifulSoup(page_source, "lxml")
        logo_url = soup.find('a', attrs={'uigs':"account_name_0"})
        if not logo_url:
            raise Exception("WeChat User Not Found")
        else:
            i = logo_url['href']
        print i
        driver1 = get_wechat_phantomjs_driver()
        driver1.get(i)
        time.sleep(5)
        page_source = driver1.page_source
        soup1 = BeautifulSoup(page_source, "lxml")
        jsonstr = ''
        for i in soup1.find_all('script', attrs={'type':'text/javascript'}):
            if i.string and 'document.domain' in i.string:
                pattern = re.compile(r"var msgList = ([^']+)]};")
                for j in pattern.findall(i.string):
                    jsonstr = j+']}'
                    break
        news = []
        while jsonstr == '':
            #print( soup1
            print("need input auth code!")
            driver1.get_screenshot_as_file('./vcode1.jpg')
            cut_image()
            elem_code = driver1.find_element_by_id('input')
            elem_code.send_keys(get_vcode())

            driver1.find_element_by_id('bt').click()
            for _ in xrange(40):
                time.sleep(0.5)
            driver1.get_screenshot_as_file('./vcode2.jpg')
            for i in soup1.find_all('script', attrs={'type':'text/javascript'}):
                if i.string and 'document.domain' in i.string:
                    pattern = re.compile(r"var msgList = ([^']+)]};")
                    for j in pattern.findall(i.string):
                        jsonstr = j+']}'
                        break
        #print( driver1.page_source
        open('./wechatjson', 'w+').write(jsonstr)
        for i in json.loads(jsonstr)['list']:
            news.append(i["app_msg_ext_info"])
            for j in i["app_msg_ext_info"]["multi_app_msg_item_list"]:
                news.append(j)
        success = True
        img_news_list = []
        video_news_list = []
        for news_item in news:
            rd1 = RequestData()
            rd1.setSouceType('wechat')
            rd1.setMetaID('')
            rd = rd1.copyrd()
            rd, rdv, isSuccess = gen_wechat_news(news_item, rd)
            if not isSuccess:
                continue
            print json.dumps(rd)
            print json.dumps(rdv)
            img_news_list.append(rd)
            video_news_list.append(rdv)
        with open('wechat.out', 'w+') as f:
            json.dump({"status":0,"data":{"img_news":img_news_list, "video_news":video_news_list}}, f)
    except:
        time.sleep(20)
        with open('wechat.out', 'w+') as f:
            json.dump({"status":-1,"data":{"error":traceback.format_exc()}}, f)
    finally:
        try:
            driver.service.process.send_signal(signal.SIGTERM)
            driver.quit()
            driver1.service.process.send_signal(signal.SIGTERM)
            driver1.quit()
        except:
            pass
    return success, news
    

if __name__ ==  "__main__":
    print sys.argv
    if sys.argv[1] not in ['weibo', 'wechat'] or sys.argv[2] not in ['load_page']:
        print 'args uncorrect'
        exit(-1)
    action = sys.argv[1], sys.argv[2]
    param = sys.argv[3]
    if action == ('weibo', 'load_page'):
        print 'Start Load Weibo Page!'
        load_weibo_page(param)
    if action == ('wechat', 'load_page'):
        print 'Start Load WeChat Page!'
        load_wechat_page(param)

    