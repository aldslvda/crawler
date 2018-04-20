#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import division
import os
import sys
import re
import time
import json
import base64
from functools import partial
import requests
from six.moves.urllib.parse import urljoin
import traceback 
import hashlib
import urllib
import codecs
import random
from DBUtils.PersistentDB import PersistentDB
import MySQLdb
from datetime import datetime, timedelta
from com_logger import logger
from etc import config as cf
import subprocess
requests.packages.urllib3.disable_warnings()
sys.setrecursionlimit(10000)

TYPE_NEWS_LINK = 'news_list'
TYPE_ARITICLE = 'article'
DEFAULT_USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.7 Safari/537.36',
    "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:41.0) Gecko/20100101 Firefox/41.0"
]
user_agent = random.choice(DEFAULT_USER_AGENTS)
headers = {
    "User-Agent": user_agent,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp;q=0.8"
}
g_del_tags = ['script', 'style']


class Quit():
    pass


class AttrsNotExistsException(Exception):
    pass


class InvalidURLException(Exception):
    pass


class PhantomjsException(Exception):
    pass


class ProxyForbiddenException(Exception):
    pass


def go_quit():
    if os.path.exists(cf.quit_file):
        return True


def get_bomb(strategy):
    return strategy.get('bomb') if strategy.get('bomb') else cf.head_a_link_max


class Retry(object):
    default_exceptions = (Exception)

    def __init__(self, tries, exceptions=None, delay=0, logger=None):
        """
        Decorator for retrying function if exception occurs
        tries -- num tries
        exceptions -- exceptions to catch
        delay -- wait between retries
        """
        self.tries = tries
        if exceptions is None:
            exceptions = Retry.default_exceptions
        self.exceptions = exceptions
        self.delay = delay
        self.logger = logger

    def __call__(self, f):
        def fn(*args, **kwargs):
            exception = self.exceptions
            for i in range(self.tries):
                try:
                    return f(*args, **kwargs)
                except self.exceptions, e:
                    if (i + 1) < self.tries:
                        time.sleep(self.delay)
                    if self.logger is None:
                        print >> sys.stderr, str(e)
                    else:
                        self.logger.warn(str(e))
                    exception = e
            # if no success after tries, raise last exception
            raise exception
        return fn


def parse_url(url, default_port=None):
    '''
    Parse url in the following form:
      PROTO://[USER:[:PASSWD]@]HOST[:PORT][/PATH[;ATTR][?QUERY]]
    A tuple containing (proto, user, passwd, host, port,
        path, tag, attrs, query) is returned,
    where `attrs' is a tuple containing ('attr1=value1', 'attr2=value2', ...)
    '''
    proto, user, passwd, host, port, path, tag, attrs, query = (None, ) * 9

    try:
        proto, tmp_host = urllib.splittype(url)
        tmp_host, tmp_path = urllib.splithost(tmp_host)
        tmp_user, tmp_host = urllib.splituser(tmp_host)
        if tmp_user:
            user, passwd = urllib.splitpasswd(tmp_user)
        host, port = urllib.splitport(tmp_host)
        port = int(port) if port else default_port
        tmp_path, query = urllib.splitquery(tmp_path)
        tmp_path, attrs = urllib.splitattr(tmp_path)
        path, tag = urllib.splittag(tmp_path)
    except Exception, err:
        raise Exception('parse_db_url error - {0}'.format(str(err)))

    return proto, user, passwd, host, port, path, tag, attrs, query


def parse_db_url(db_url, default_port=None):
    '''
    Parse an url representation of one database settings.
    The `db_url' is in the following form:
      PROTO://[USER[:PASSWD]@]HOST[:PORT][/DB/TABLE]
    Tuple (proto, user, passwd, host, port, db, table) is returned
    '''
    proto, user, passwd, host, port, db, table = (None, ) * 7

    try:
        proto, user, passwd, host, port, path = parse_url(db_url,
                                                          default_port)[0:6]
        if not passwd:
            passwd = ''
        tmp_list = path.split('/')[1:]
        db, table = '', ''
        if len(tmp_list) >= 2:
            db, table = tmp_list[0:2]
        elif len(tmp_list) == 1:
            db = tmp_list[0]
    except Exception, err:
        raise Exception('parse_db_url error - {0}'.format(str(err)))

    return proto, str(user), str(passwd), str(host), port, str(db), str(table)


def make_conn(db_url, *args, **kwargs):
    _, user, passwd, host, port, db, _ = parse_db_url(db_url)
    conn = MySQLdb.connect(host=host,
                           port=port,
                           user=user,
                           passwd=passwd,
                           db=db,
                           charset='utf8',
                           use_unicode=False)
    # cur = conn.cursor()
    # cur.execute('set time_zone="+0:00"')
    # cur.close()
    # conn.commit()
    return conn


def make_pool(db_url):
    return PersistentDB(creator=partial(make_conn, db_url))


def get_md5(src):
    myMd5 = hashlib.md5()
    try:
        myMd5.update(src)
    except UnicodeEncodeError:
        myMd5.update(src.encode('utf-8'))
    return myMd5.hexdigest()


def format_url(url):
    url = url.replace('\\', '/').replace('//', '/').replace('//', '/')
    return url.replace('http:/', 'http://').replace('HTTP:/', 'HTTP://').\
        replace('https:/', 'https://').replace('HTTPS:/', 'HTTPS://')


def save_run_id(id):
    try:
        with open(os.path.join('var', 'cache', 'run_id'), 'w') as f:
            f.write(str(id))
    except:
        logger.error(traceback.format_exc())


def read_run_id():
    try:
        with open(os.path.join('var', 'cache', 'run_id'), 'r') as f:
            return int(f.read())
    except:
        logger.error(traceback.format_exc())
        return 0


def load_sites_first():
    try:
        if os.path.exists('sites_first.json'):
            return json.load(open('sites_first.json', 'r')).get('ids')
    except:
        logger.error(traceback.format_exc())


def get_ture_url(home_url, url):
    if url:
        url = url.strip()
        if url in ['#', 'javascript:void(0);', 'javascript:;']:
            return None
        if url.startswith('//'):
            return 'http:' + url
        url1 = home_url
        url2 = url
        home_url = format_url(home_url)
        url = format_url(url)
        if not url.lower().startswith('http'):
            url = urljoin(home_url, url)
            logger.debug('urljoin: {}, from[{}, {}]'.format(url, url1, url2))
    return url


def save_tmp_web_html(file_name, content):
    if cf.local_test:
        if not content:
            logger.warn('content is None, save to %s error' % file_name)
            return
        try:
            codecs.open(file_name, 'wb', encoding='utf-8').write(
                content)
        except:
            try:
                codecs.open(file_name, 'wb', encoding='utf-8').write(
                    unicode(content, encoding='gbk'))
            except:
                try:
                    codecs.open(file_name, 'wb',
                                encoding='utf-8').write(
                        unicode(content, encoding='utf-8'))
                except:
                    logger.error(traceback.format_exc())


@Retry(2, delay=3, logger=logger)
def get_html(url, strategy=dict()):
    referer = strategy.get('referer')
    if referer is not None:
        headers['Referer'] = referer
    if strategy.get('proxy'):
        logger.info('get proxy from {}'.format(cf.proxy_url))
        proxy = {"http": "http://" + requests.get(cf.proxy_url).text}
        logger.info('use proxy {}'.format(proxy))
        if proxy['http'].strip() == "http://":
            raise Exception('fetch proxy empty, sleep 3s to retry')
        res = requests.get(url, headers=headers, timeout=(5, 60), verify=False,
                           proxies=proxy)
    else:
        res = requests.get(url, headers=headers, timeout=(5, 20), verify=False)
    res.raise_for_status()
    # content = res.content
    res.encoding = res.apparent_encoding
    content = res.text
    if not content:
        raise Exception(u'fetch {} empty, sleep 3s to retry'.format(url))
    save_tmp_web_html('web.html', content)
    return content


def get_home_url(url):
    home_url = re.compile(r'(.*/)').findall(url)
    if home_url:
        home_url = home_url[0]
    else:
        home_url = url
    return home_url


def get_new_path(url, strategy):
    add_path = []
    add_path.append(url)
    new_path = strategy.get('new_path')
    for add in new_path:
        if isinstance(add, (str, unicode)):
            add_path.append(add)
        elif isinstance(add, dict):
            date_str = add.get('date')
            if date_str:
                date_obj = time.gmtime()
                for one_date_piece in date_str:
                    if '$' in one_date_piece:
                        one_date_piece = one_date_piece.strip('$')
                        d_now = datetime.now() + timedelta(-1)
                        add_path.append(d_now.strftime(one_date_piece))
                    else:
                        add_path.append(
                            time.strftime(one_date_piece, date_obj))
    new_url = '/'.join(add_path)
    return format_url(new_url)


def get_new_path_content(url, strategy):
    new_url = get_new_path(url, strategy)
    config_home_url = strategy.get('home_url')
    home_url = get_home_url(new_url)
    if config_home_url:
        link_type = strategy.get('link_type')
        if link_type == TYPE_NEWS_LINK:
            home_url = get_home_url(config_home_url)
    html_content = get_html(new_url, strategy)
    return home_url, html_content


def get_new_refresh_html(html):
    html = html.replace('http-equiv="refresh"', 'HTTP-EQUIV="REFRESH"')
    html = html.replace(';url', ';URL')
    html = html.replace('; url', ';URL')
    return html


def parse_refresh(new_url, url, strategy):
    try_times = 0
    while True:
        new_url = get_ture_url(url, new_url[0])
        url = new_url
        home_url = get_home_url(new_url)
        html = get_html(new_url, strategy)
        html = get_new_refresh_html(html)
        new_url = re.compile(
            r'HTTP-EQUIV="REFRESH".*URL=(.*?)"').findall(html)
        if not new_url or try_times > 10:
            if strategy.get('new_path'):
                return get_new_path_content(home_url, strategy)
            else:
                return home_url, html
        else:
            try_times += 1


def parse_location(re_href, url, strategy):
    try_times = 0
    while True:
        new_url = get_ture_url(url, re_href[0])
        url = new_url
        home_url = get_home_url(new_url)
        html = get_html(new_url, strategy)
        re_href = re.compile(
            r'window.location="(.*)"').findall(html)
        if not re_href or try_times > 10:
            if strategy.get('new_path'):
                return get_new_path_content(home_url, strategy)
            else:
                return home_url, html
        else:
            try_times += 1


def com_invalid_url(url, strategy=None):
    if not url or len(url) <= 4 or not url.lower().startswith('http'):
        return True
    if 'javacript:' in url.lower() or 'mailto:' in url.lower():
        return True


def domain_invalid_url(url, strategy):
    url = url.lower()
    domain = strategy.get('domain')
    if domain:
        if isinstance(domain, (str, unicode)):
            if domain.lower() not in url:
                return True
        elif isinstance(domain, list):
            for one_domain in domain:
                if one_domain.lower() in url:
                    return False
            return True


def invalid_url(url, strategy):
    if com_invalid_url(url, strategy):
        logger.error('com_invalid_url [{}]'.format(url))
        return True

    if domain_invalid_url(url, strategy):
        logger.error('domain_invalid_url [{}]'.format(url))
        return True

    domain = strategy.get('domain')
    link_type = strategy.get('link_type')
    add_index_pages = strategy.get('add_index_pages')
    if add_index_pages:
        if url in add_index_pages:
            if link_type and (link_type == TYPE_ARITICLE):
                return True
            else:
                return False
    if link_type and (link_type == TYPE_ARITICLE):
        if domain:
            if isinstance(domain, (str, unicode)):
                if url.lower().rstrip('/').endswith(domain.lower()):
                    return True
            elif isinstance(domain, list):
                for one_domain in domain:
                    if url.lower().rstrip('/').endswith(one_domain.lower()):
                        return True
        for ends in cf.invalid_ends + cf.media_ends:
            if url.lower().endswith(ends):
                return True
    full_remove_urls = strategy.get('invalid_full')
    if full_remove_urls:
        for r_url in full_remove_urls:
            if url.rstrip('/') == r_url.lower().rstrip('/'):
                return True
    remove_urls = strategy.get('invalid')
    if remove_urls:
        for r_url in remove_urls:
            m = re.compile(r_url).findall(url)
            if m:
                return True


def get_phantomjs(url, strategy=dict(), wait_phantomjs=False,
                  phantomjs_config=dict()):
    if wait_phantomjs:
        if invalid_url(url, strategy):
            raise InvalidURLException(u'found invalid url {}'.format(url))
        # phantomjs_cmd = cf.phantomjs_command.format(quote(
        #     json.dumps({'url': url, 'strategy': strategy,
        #     'phantomjs_config': phantomjs_config})))
        send_params = {'url': url, 'strategy': strategy,
                       'phantomjs_config': phantomjs_config}
        phantomjs_cmd = cf.phantomjs_command.format(json_encode(send_params))
        logger.info(u"{}exe_phantomjs.py 'url: {} ...' ".format(
            phantomjs_cmd.split('exe_phantomjs.py')[0], url))
        logger.debug(phantomjs_cmd)
        phantomjs_retry = 0
        while True:
            p = subprocess.Popen(phantomjs_cmd, shell=True,
                                 universal_newlines=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            output, stderrdata = p.communicate()
            if stderrdata:
                raise Exception(stderrdata)
            else:
                for line_output in output.strip().split('\n'):
                    if line_output.startswith(cf.head):
                        output = line_output.lstrip(cf.head)
                        break
                page_res = json_decode(output)
                if 'error' in page_res:
                    if 'ProxyForbiddenException' == page_res['error']:
                        if phantomjs_retry <= 10:
                            phantomjs_retry += 1
                            page_res['retry'] = '%d/10' % phantomjs_retry
                            logger.warn(page_res)
                            time.sleep(1)
                        else:
                            raise Exception(page_res)
                    elif 'PhantomjsException' == page_res['error']:
                        for one_js in cf.must_js:
                            if one_js in strategy['name']:
                                page_res['to-do'] = 'must use js load'
                                raise Exception(page_res)
                        if strategy.get('not_request_get'):
                            raise Exception(page_res)
                        else:
                            page_res['to-do'] = 'change use request.get'
                            logger.warn(page_res)
                            return get_html_content(url, strategy)
                    else:
                        raise Exception(page_res)
                else:
                    if cf.local_test:
                        save_tmp_web_html('web.html', page_res['current_url'] +
                                          '\n\n\n' + page_res['page_source'])
                    return page_res['current_url'], page_res['page_source']
    else:
        return get_html_content(url, strategy)


def get_html_content(url, strategy=dict()):
    if invalid_url(url, strategy):
        raise InvalidURLException(u'found invalid url {}'.format(url))
    jump_home = strategy.get('jump_home')
    link_type = strategy.get('link_type')
    if jump_home and link_type is TYPE_NEWS_LINK:
        if strategy.get('new_path'):
            return get_new_path_content(url, strategy)
    html = get_html(url, strategy)
    if html and link_type is not TYPE_ARITICLE and \
            'jump_forbid' not in strategy:
        logger.debug(u'access {}'.format(url))
        html = get_new_refresh_html(html)
        new_url = re.compile(
            r'HTTP-EQUIV="REFRESH".*URL=(.*?)"').findall(html)
        if new_url:
            logger.debug(u'get {} in HTTP-EQUIV="REFRESH"'.format(new_url))
            return parse_refresh(new_url, url, strategy)
        re_href = re.compile(
            r'window.location="(.*)"').findall(html)
        if re_href:
            logger.debug(u'get {} in window.location'.format(re_href))
            return parse_location(re_href, url, strategy)
        if strategy.get('new_path'):
            return get_new_path_content(url, strategy)
    return url, html


def remove_junk_text(soup):
    for del_text in g_del_tags:
        tags = soup.find_all(del_text)
        for tag in tags:
            tag.decompose()


def get_phantomjs_config(strategy, url, config_name):
    wait_phantomjs = False
    phantomjs_config = {}
    attrs_valid = '{}_valid'.format(config_name)
    attrs_valid_config = strategy.get(attrs_valid)
    if attrs_valid_config:
        for url_config in attrs_valid_config:
            m = re.compile(url_config.keys()[0]).findall(url)
            if m:
                wait_phantomjs = True
                phantomjs_config = url_config.values()[0]
    if not wait_phantomjs:
        if config_name in strategy:
            wait_phantomjs = True
        config = strategy.get(config_name)
        if config:
            phantomjs_config = config
    return wait_phantomjs, phantomjs_config


def get_valid(url, check_name, default_name, strategy, html_detail=None):
    def get_smart(valid_key, smart_key):
        if valid_key == check_name and html_detail:
            ret_valid = strategy.get(smart_key)
            if ret_valid:
                assert(isinstance(ret_valid, list))
                for one_rule in ret_valid:
                    for a_content, a_rule in one_rule.items():
                        if a_content in html_detail:
                            return a_rule

    ret_valid = strategy.get(check_name)
    if ret_valid:
        assert(isinstance(ret_valid, list))
        for one_rule in ret_valid:
            for a_url, a_rule in one_rule.items():
                m = re.compile(a_url).findall(url)
                if m:
                    return a_rule

    save_tmp_web_html('html_detail_for_smart.html', html_detail)
    if 'article_valid' == check_name:
        a_rule = get_smart('article_valid', 'article_smart')
        if a_rule:
            return a_rule
    elif 'img_attrs_valid' == check_name:
        a_rule = get_smart('img_attrs_valid', 'img_attrs_smart')
        logger.debug('a_rule: {}'.format(str(a_rule)))
        if a_rule:
            return a_rule
    return strategy.get(default_name)


def json_encode(obj):
    return base64.b64encode(json.dumps(obj))


def json_decode(string):
    return json.loads(base64.b64decode(string))


def always_send(send_mq, send):
    if cf.local_test:
        return
    while True:
        if go_quit():
            break
        try:
            send_mq.send(base64.b64encode(json.dumps(send)))
        except:
            logger.error(traceback.format_exc())
            time.sleep(3)
        else:
            break


def file_size(file_path):
    if os.access(file_path, os.R_OK):
        return os.stat(file_path).st_size
    return 0


def human_size(file_path):
    pre_size = file_size(file_path)
    if pre_size > 1024 * 1024:
        return '{} M'.format(pre_size >> 20)
    elif pre_size > 1024:
        return '{} K'.format(pre_size >> 10)
    else:
        return '{} byte'.format(pre_size)
