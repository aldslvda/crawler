#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import copy
import time
import signal
import traceback
import requests
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import config as cf
# from com_logger import logger
from utils import save_tmp_web_html, json_encode, json_decode
sys.setrecursionlimit(10000)
b_debug = False


def get_phantomjs_driver(strategy):
    cap = webdriver.DesiredCapabilities.PHANTOMJS
    cap['phantomjs.page.settings.resourceTimeout'] = '60000'
    cap['phantomjs.page.settings.loadImages'] = True
    cap['phantomjs.page.settings.userAgent'] = \
        "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/538.1 "\
        "(KHTML, like Gecko) Safari/538.1"
    if strategy.get('user-agent'):
        cap['phantomjs.page.settings.userAgent'] = strategy.get('user-agent')
    if strategy.get('referer'):
        # logger.debug('add referer: %s' % strategy.get('referer'))
        cap["phantomjs.page.customHeaders.Referer"] = strategy.get('referer')
    if strategy.get('cookie'):
        # logger.debug('use cookie {}'.format(strategy.get('cookie')))
        cap["phantomjs.page.customHeaders.Cookie"] = strategy.get('cookie')
    proxy = webdriver.Proxy()
    if strategy.get('proxy'):
        # logger.info('get proxy from {}'.format(cf.proxy_url))
        proxy_url = requests.get(cf.proxy_url).text
        # logger.debug('use proxy {}'.format(proxy_url))
        if not proxy_url:
            raise Exception('fetch proxy empty, sleep 3s to retry')
        proxy.proxy_type = webdriver.common.proxy.ProxyType.MANUAL
        proxy.http_proxy = proxy_url
    else:
        proxy.proxy_type = webdriver.common.proxy.ProxyType.SYSTEM
    proxy.add_to_capabilities(cap)
    driver = webdriver.PhantomJS(executable_path='./phantomjs')
    driver.implicitly_wait(60)
    driver.set_page_load_timeout(60)
    #driver.set_window_size(4096, 2160)
    return driver


def run_phantomjs(url, strategy=dict(), phantomjs_config=dict()):
    driver = None
    try:
        driver = get_phantomjs_driver(strategy)
        driver.get(url)
    except Exception, e:
        if b_debug:
            print traceback.format_exc()
        if driver:
            driver.service.process.send_signal(signal.SIGTERM)
            driver.quit()
        print(cf.head + json_encode(
            {'error': 'PhantomjsException', 'message': str(e)}))
        return
    current_url = copy.copy(driver.current_url)
    page_source = copy.copy(driver.page_source)
    # logger.info('phantomjs go {}'.format(current_url))
    driver.service.process.send_signal(signal.SIGTERM)
    driver.quit()
    save_tmp_web_html('web.html', page_source)
    if (u'403 - 禁止访问: 访问被拒绝' in page_source or
            'ERROR: The requested URL could not be retrieved' in
            page_source) and strategy.get('proxy'):
        print(cf.head + json_encode(
            {'error': 'ProxyForbiddenException', 'current_url': current_url,
             'page_source': page_source}))
        return
    print(cf.head + json_encode(
        {'current_url': current_url, 'page_source': page_source}))


def main():
    global b_debug
    try:
        if len(sys.argv) >= 3:
            b_debug = True
        if b_debug:
            print json.dumps(
                json_decode(sys.argv[1]), indent=4, ensure_ascii=False)
        params_json = json_decode(sys.argv[1])
        url = params_json['url']
        strategy = params_json['strategy']
        phantomjs_config = params_json['phantomjs_config']
        run_phantomjs(url, strategy, phantomjs_config)
    except:
        if b_debug:
            print traceback.format_exc()
        print(cf.head + json_encode(
            {'error': 'ParmasParse', 'message': traceback.format_exc()}))


if __name__ == '__main__':
    main()
