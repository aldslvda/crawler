import time
import socket
import traceback

from kombu import Connection, Exchange, Queue, Producer


class AppCrawlerQueue(object):
    """
    crawler result put into the rabbit mq
    """
    def __init__(self, addr, exchange, routing_key, queue_name, logger = None):
        self._exch = Exchange(exchange)
        self._addr = addr
        self._routing_key = routing_key
        self._queue_name = queue_name
        self._queue = Queue(queue_name, self._exch, self._routing_key)
        self._conn = Connection(addr)
        self._task = None
        self._logger = logger
        self._producer = None
    
    def setConsumer(self):
        self._consumer = self._conn.Consumer(self._queue,
                                             callbacks=[self.processTask])
        self._consumer.qos(prefetch_count=1)
        self._consumer.consume()

    def setProducer(self):
        if not self._producer:
            self._producer = Producer (self._conn)

    def reConn(self):
        self._conn.release()
        self._conn = Connection(self._addr)

    def processTask(self, body, message):
        try:
            if not body:
                message.ack()
                return
            self._task = body
            message.ack()
        except:
            pass

    def getTask(self):
        self._task = None
        try:
            self._conn.drain_events(timeout=1)
        except socket.timeout:
            pass
        except:
            self._logger.error('unknown error[%s]' %traceback.format_exc())
            pass
        finally:
            time.sleep(0.1)

        return self._task
    
    def setTask(self, task):
        result = task
        for i in range(5):
            try:
                self._producer.publish(result,
                        exchang=self._exch,
                        declare=[self._queue],
                        routing_key=self._queue_name
                        )
                break
            except:
                self._logger.error('send info error[%s]' %traceback.format_exc())
                time.sleep(10)
                self.reConn()
                self.setProducer()
            continue

    def __del__(self):
        self._conn.release()


def getTask(conn):
    conn.setConsumer()
    print(conn.getTask())


def setTask(conn, task):
    conn.setProducer()
    conn.setTask(task)


def main():

    url = 'amqp://guest:guest@127.0.0.1:5672//'
    request_queue = 'task_queue_test'
    routing_key = 'routingkey'
    exchange = 'exchange'
    conn = AppCrawlerQueue(url, exchange, routing_key, request_queue)

    for i in range(5):
        setTask(conn, '{"a":1}')


if __name__ == '__main__':
    try:
        main()
    except:
        print(traceback.format_exc())
