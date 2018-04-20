import os
import sys
import time
import json
import signal
import traceback
import threading
import select
import multiprocessing
import subprocess32 as subprocess
import requests
import concurrent.futures
from com_logger import appLogger as logger
import appSystemVars
from com_logger import appLogger

import appTaskSender

if len(sys.argv) != 5:
    print '%s -f system.conf -c moduleConfDir' %(sys.argv[0])
    print 'appCrawler version 1.0.0.0'
    sys.exit(0)

class WorkerThread(threading.Thread):
    def __init__(self, app):
        threading.Thread.__init__(self, name=app)
        self.app_name = app
    def run(self):
        crawler_name = self.app_name+'Crawler.py'
        log_file = open('var/log/BN_appMainCrawler.log', 'a+')
        cralwer = subprocess.Popen('python bin/%s -c etc'%crawler_name,
                                   shell=True, stdout=log_file, stderr=log_file)
        try:
            cralwer.communicate(timeout=1200)
        except:
            logger.error(traceback.format_exc())
            logger.info("kill crawler ... crawler name is %s"%crawler_name)
            cralwer.kill()

def load_sysconfig(config):
    conf = appSystemVars.appSystemConf
    conf.loadConfig(config)
    return conf

def get_track_source(host, port, url):
    res = requests.get('http://%s:%d/%s' %(host, port, url))
    if res.status_code != 200:
        logger.error('Cannot Get Tracksource, Exit!')
        sys.exit(-1)
    rows = res.json()['rows']
    app_dicts = {}
    signs_transfer = json.loads(open('etc/signs_transfer.conf').read())
    for row in rows:
        if os.path.exists('./bin/'+row['sign']+'Crawler.py'):
            app_dicts[row['sign']] = row
        elif row['sign'] in signs_transfer:
            if os.path.exists('./bin/'+signs_transfer[row['sign']]+'Crawler.py'):
                app_dicts[signs_transfer[row['sign']]] = row
        else:
            continue
    return app_dicts

def update_sysconfig(configger, app_dict):
    confjson = json.loads(open(configger.getConfigFilePath()).read())
    confjson['appDicts'] = app_dict
    confstr = json.dumps(confjson)
    cfgfile = file(configger.getConfigFilePath(), 'w+')
    cfgfile.truncate()
    cfgfile.write(confstr)
    cfgfile.close()

def app_main_crawler(configger, config_dir):
    main_crawler_cost_time = configger.getCostTime()
    process_num = configger.getProcessNum()
    logger.info('APP Crawler Start!')
    def add_thread(app_name):
        worker_th = WorkerThread(app_name)
        worker_th.start()
        worker_ths.append(worker_th)
    while True:
        track_sourcer = configger.getTrackSource()
        host, port, url = track_sourcer.getHost(), track_sourcer.getPort(), track_sourcer.getURL()
        app_dict = get_track_source(host, port, url)
        app_list = app_dict.keys()
        logger.info('app list is %s' %str(app_list))
        update_sysconfig(configger, app_dict)

        worker_ths = []
        for _ in range(process_num):
            add_thread(app_list.pop())
        while True:
            dead_ths = []
            for one_th in worker_ths:
                if not one_th.isAlive():
                    logger.info(one_th.name + ' dead')
                    dead_ths.append(one_th)
            for one_th in dead_ths:
                worker_ths.remove(one_th)
                add_thread(app_list.pop())
            time.sleep(2)


def main():
    main_config = sys.argv[2]
    module_config_dir = sys.argv[4]
    configger = load_sysconfig(main_config)
    app_main_crawler(configger, module_config_dir)

if __name__ == '__main__':
    try:
        main()
    except:
        logger.error(traceback.format_exc())
