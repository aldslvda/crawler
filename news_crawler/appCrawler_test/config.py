#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import socket
import struct
try:
    import fcntl
except:
    pass


def get_ip_address(ifname):
    skt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    pktString = fcntl.ioctl(skt.fileno(), 0x8915,
                            struct.pack('256s', ifname[:15]))
    return socket.inet_ntoa(pktString[20:24])


try:
    this_ip = get_ip_address('eth1')
except:
    try:
        this_ip = get_ip_address('eth0')
    except:
        this_ip = '127.0.0.1'
index_ip = '121.41.96.26'
log_level = 'INFO'
log_title = 'website_crawler'
quit_file = 'var/cache/stop'
site_name = 'sites.json'
addr = 'amqp://guest:guest@121.40.73.207:5672'
cache_q = 'crawler_cache_website' 
# 部分网站首页存在链接陷阱，通过最大值避免，比如http://www.whtv.com.cn
head_a_link_max = 999
# 更新缓存的小时数，3表示凌晨3点
up_cache_hour = 3
# 临时执行缓存更新清理开关
cache_update_test = False
# 缓存最大保留天数
cache_save_day = 3
# BigCache的set_update保存到本地的个数
back_updata_max = 100000
if this_ip == index_ip:
    index_module = True
    mq_url = 'http://121.40.73.207:8011/queue/'
    send_queue = 'crawler_news_website'
    sleep = 10
    process_pool_num = 2
    db_ip = 'mysql://xhs:xhs!@#1107@rm-bp1ht37b3a56m15s2.mysql.rds.aliyuncs.com:3306/crawler'
else:
    index_module = False
    get_queue = 'crawler_news_website'
    send_queue = 'host_dispatch'
    if this_ip in ['120.26.52.123']:
        thread_num = 1
    elif this_ip in ['120.26.61.192', '120.26.40.76', '121.199.64.158']:
        thread_num = 8
    else:
        thread_num = 4
exchange = 'xhs_exchange'
max_img_url = 600
# return like 112.124.33.81:63267
proxy_url = 'http://wiseproxy.ops.vobile.org/getProxy?site=weixin&&partition=aliyun'
if os.name == 'nt':
    phantomjs_command = "python exe_phantomjs.py '{}'"
else:
    phantomjs_command = "timeout 300 python2.7 exe_phantomjs.py '{}'"
head = '$json$'
cache_path = 'var/cache/cache.json'
mq_ok_cache_path = 'var/cache/mq_ok_cache.json'
min_mq_count = 1000
up_idx_cache_path = 'var/cache/up_idx_cache.json'
db_cache_path = 'var/cache/db_cache.json'
db_max_id_path = 'var/cache/db_cache_max_id'
# 是否加载子页面解析，数量巨大，容易堆积
add_index_pages = False
# 在add_index_pages是False情况下，根据下面关键字筛选进行解析的链接
add_index_pages_keys = [u'国际', u'国内', u'新闻', u'政情', u'财经', u'政经', u'要闻',
                        u'教育', u'社会', u'外媒', u'文娱', u'时政', u'省内', u'综治',
                        u'资讯', u'政治', u'科教', u'经济', u'热闻', u'体育', u'娱乐',
                        u'艺术', u'头条']
# TYPE_ARITICLE invalid ends
invalid_ends = ['.com', '.cn', '.net', '.org',
                '/index.html', '/index.htm', '/index.shtml', '/contactus.jsp']
# TYPE_NEWS_LINK & TYPE_ARITICLE invalid ends
media_ends = ['.jpg', '.png', '.gif', '.jpeg', '.pdf', '.flv', '.mp4', '.mp3',
              '.apk', '.exe', '.doc', '.wmv', ]
must_js = [u'图片', u'影像']
# 根据标题删除常见无新闻链接
rm_titles = [u'分类广告', u'广告', u'人民法院公告', u'更多', u'>>更多', u'更多>>', '>>more',
             'more', 'more>>', u'查看更多', u'电脑版', u'客户端', u'下载电脑客户端', u'修改密码']
local_test = False
local_test_max = 20
local_test_article_url = 'http://focus.scol.com.cn/zgsz/201701/55801154.html'
local_test_url = 'http://www.scol.com.cn/'
