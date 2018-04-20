import sys
import logging
from collections import OrderedDict
from logging.handlers import SysLogHandler, DatagramHandler
import json
from contextlib import contextmanager
import time
import uuid
sys.setdefaultencoding('utf-8')


class MwFormatter(logging.Formatter):
    """
    rewrite formatter as json msg format
    """

    def __init__(self, fmt, datefmt, **kwargs):
        super(self.__class__, self).__init__(fmt, datefmt)
        self._msg = OrderedDict(**kwargs)

    def format(self, record):
        b_normal_fm = False
        if isinstance(record.msg, (str, unicode)):
            record.msg = record.msg.lstrip()
            if record.msg.startswith('<') or \
                    record.msg.startswith('Traceback'):
                b_normal_fm = True
        if b_normal_fm:
            msg_json = {"msg": ""}
        else:
            msg_json = {"msg": record.msg}
        self._msg.update(msg_json)
        tmp_msg = json.dumps(self._msg, ensure_ascii=False, indent=4)
        if b_normal_fm:
            tmp_msg = u'{}\n{}}}'.format(
                tmp_msg.rstrip('}').strip().rstrip('""'), record.msg)

        u_normal = u'\033[38;5;255m'
        u_error = u'\033[38;5;9m'
        u_warn = u'\033[38;5;11m'
        u_debug = u'\033[38;5;81m'
        if record.levelname in ['ERROR', 'CRITICAL']:
            record.msg = u'{} {} {}'.format(u_error, tmp_msg, u_normal)
        elif record.levelname in ['WARNING']:
            record.msg = u'{} {} {}'.format(u_warn, tmp_msg, u_normal)
        elif record.levelname in ['DEBUG']:
            record.msg = u'{} {} {}'.format(u_debug, tmp_msg, u_normal)
        else:
            record.msg = u'{} {}'.format(u_normal, tmp_msg)
        if record.levelname == 'WARNING':
            record.levelname = 'WARN'
        elif record.levelname == 'CRITICAL':
            record.levelname = 'FATAL'
        return super(self.__class__, self).format(record)


class UDPHandler(DatagramHandler):
    def emit(self, record):
        """
        Emit a record.
        If there is an error with the socket, silently drop the packet.
        If there was a problem with the socket, re-establishes the
        socket.
        """
        try:
            s = self.format(record)
            self.send(s)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


class ALogger(logging.Logger, object):
    '''
    usage: mwlogger = ALogger('task_manager', 'syslog', log_level='DEBUG',
    facility='local0', task_uuid='981288-kk2kjfd-3kj3k34-38484wc')
    mylogger.info("info log. hello world")
    '''

    def __init__(self, log_name, log_handler=None, use_mwformat=True,
                 log_level='INFO', facility='local1', event_handler=None,
                 **kwargs):
        '''
        log_name: name of the logger

        log_handler: It is a handler object or string object or None.
                    StreamHandler, SysLogHandler or FileHandler will be created
                    when log_handler is not logging.handler object.
                    Rule is as follow:

            None: StreamHandler(sys.stderr)
            string object:
            {
                'syslog': SysLogHandler(address="/dev/log",
                        facility=SysLogHandler.facility_names.get(facility, 1))
                'other':  logging.FileHandler(log_handler)
            }
            logging.Handler: use log_handler

        use_mwformat: formatter is:
        '%(threadName)s %(asctime)s %(name)s/%(levelname)s/
         %(filename)s:%(lineno)d:%(funcName)s:%(process)d/%(thread)d:%(message)s'
                      if it is set to True, otherwise is '%(message)s' only

        log_level: 'DEBUG/INFO/ERROR/WARN', must be capital, default is INFO

        facility: default is user, all is follow:
        {'ftp': 11, 'daemon': 3, 'uucp': 8, 'security': 4, 'local7': 23,
        'local4': 20, 'lpr': 6, 'auth': 4, 'local0': 16, 'cron': 9,
        'syslog': 5, 'user': 1, 'mail': 2, 'local5': 21,
        'kern': 0, 'news': 7, 'local6': 22, 'local1': 17,
        'authpriv': 10, 'local3': 19, 'local2': 18}

        event_handler: a udp handler to monitor module, default is None

        **kwargs: additional message, will be logged by json format

        '''
        super(ALogger, self).__init__(log_name)

        self._args = {}
        self._args['log_name'] = log_name
        self._args['log_handler'] = log_handler
        self._args['log_level'] = log_level
        self._args['facility'] = facility
        self._additional_msg = OrderedDict(**kwargs)
        self._args.update(**kwargs)

        self.setLevel(log_level)
        # Format should be set in configures?
        self._datefmt = '%Y%m%dT%H%M%S%Z'
        if use_mwformat:
            self._format = '[%(asctime)s][%(levelname)s]'\
                           '{%(name)s/%(filename)s/%(process)d/%(thread)d}'\
                           '(%(threadName)s|%(funcName)s:%(lineno)d)'\
                           '-%(message)s'
            self.formatter = MwFormatter(self._format, self._datefmt, **kwargs)
        else:
            self._format = '%(message)s'
            self.formatter = logging.Formatter(self._format, self._datefmt)

        if isinstance(log_handler, logging.Handler):
            self.hdlr = log_handler

        elif isinstance(log_handler, basestring):
            if log_handler == 'syslog':
                self.hdlr = SysLogHandler(
                    address="/dev/log",
                    facility=SysLogHandler.facility_names.get(facility, 1))
            else:
                self.hdlr = logging.FileHandler(log_handler)

        elif log_handler is None:
            self.hdlr = logging.StreamHandler(sys.stderr)

        else:
            raise Exception("Invalid Logging Handler")

        self.hdlr.setFormatter(self.formatter)
        self.addHandler(self.hdlr)

        # create event logger
        if event_handler and isinstance(event_handler, UDPHandler):
            self._elogger = self.__class__(
                log_name, log_handler=event_handler, **kwargs)
        else:
            self._elogger = None

    def add_event_handler(self, event_handler):
        if event_handler and isinstance(event_handler, UDPHandler):
            self._elogger = self.__class__(log_name=self._args['log_name'],
                                           log_handler=event_handler,
                                           log_level=self._args['log_level'],
                                           facility=self._args['facility'],
                                           **self._additional_msg)
        else:
            self._elogger = None

    def create_event_handler(self, host, port):
        '''
        create event handler to monitor
        '''
        event_handler = UDPHandler(host, port)
        self._elogger = self.__class__(log_name=self._args['log_name'],
                                       log_handler=event_handler,
                                       log_level=self._args['log_level'],
                                       facility=self._args['facility'],
                                       **self._additional_msg)

    def message_decorate(self, **kwargs):
        '''
        using kwargs decorate message
        '''
        msg = OrderedDict(self._additional_msg, **kwargs)
        formatter = MwFormatter(self._format, self._datefmt, **msg)
        self.hdlr.setFormatter(formatter)

    def message_undecorate(self):
        self.hdlr.setFormatter(self.formatter)

    def create_task_logger(self, task_uuid):
        return self.__class__(task_uuid=task_uuid, **self._args)

    def event(self, ename, msg, errorcode='', etype='moment',
              eid=None, flag='start'):
        logger = self._elogger if self._elogger else self
        with logger.event_logger(ename, errorcode, etype,
                                 eid, flag) as e_logger:
            if etype == 'moment':
                e_logger.error(msg)
            else:
                e_logger.info(msg)

    @contextmanager
    def event_logger(self, ename, errorcode="", etype='moment',
                     eid=None, flag='start'):
        '''
        event is a dict like:
        {
            "type":"long",
            "name":"task",
            "event_uuid":$task_uuid,
            "start_time": $timestamp/"end_time": $timestamp
        } or
        {
            "type":"moment",
            "name": $error,
            "event_uuid": $uuid,
            "start_ime": $timestamp
        }
       '''
        event = {
            "type": etype,
            "name": ename,
            "event_uuid": eid,
        }
        if etype == 'long' and flag == 'end':
            event['end_time'] = int(time.time())
        else:
            event['start_time'] = int(time.time())

        if event["event_uuid"] is None:
            event["event_uuid"] = str(uuid.uuid1())

        try:
            self.message_decorate(event=event, errorcode=errorcode)
            yield self
        finally:
            self.message_undecorate()


app_logger = ALogger('appCrawler', log_level='INFO')


if __name__ == '__main__':
    taskid = str(uuid.uuid1())
    logger = ALogger('test_log', log_level='DEBUG', company_id="vobile123")
    # logger = SocketLogger()

    logger.debug('debug log......')
    logger.info('info log..........')
    logger.warn('warn log..........')
    logger.error('error log..........')
    logger.critical('critical log..........')

    task_logger = logger.create_task_logger("JADDG-i3i32-33kkdkd-3k33k")

    task_logger.debug('debug log......')
    task_logger.info('info log..........')

    logger.message_decorate(task_uuid="19292-2213kd-232j3j-kdjdjd")
    logger.critical('critical log..........')
    logger.error('error log......')
    logger.message_undecorate()

    logger.info('info log..........')
    logger.critical('critical log......')

    # long event
    logger.event('task', 'task created succ', etype='long', eid=taskid)
    logger.event('task', 'task created end',
                 etype='long', eid=taskid, flag='end')

    # moment event
    logger.event('Exception', 'unhandle exception', errorcode='01019900')

    otherlog = logging.getLogger('others')
    # Other logger should set NullHandler as default logging handler to avoid
    # "No handler found" warnings.
    from logging import NullHandler
    otherlog.addHandler(NullHandler())
    otherlog.error('this message should not be logged')

    # Other logger add ALogger instance's hdlr
    otherlog.addHandler(logger.hdlr)
    otherlog.error('other logger test')

    # threads test:
    import threading

    def thr_test(task_uuid):
        task_logger = logger.create_task_logger(task_uuid)
        task_logger.critical('thread critical log..........')
        task_logger.error('thread error log......')
        time.sleep(1)
        task_logger.critical('thread critical log..........')
        task_logger.error('thread error log......')

    thr1 = threading.Thread(target=thr_test, args=('123-456-789',))
    thr2 = threading.Thread(target=thr_test, args=('987-654-321',))

    thr1.start()
    thr2.start()

    thr1.join()
    thr2.join()
