import logging
import socket
from watchdog.events import PatternMatchingEventHandler
import asyncio


def poe_send(dat_file, host, port):
    try:
        f = open(dat_file)
        io = f.read()
        f.close()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        s.sendall(bytes(io, 'utf-8'))
        s.close()
    except Exception as e:
        logging.error(f'poe_send error: {e}')
    logging.info(msg=f'sent - {dat_file}')


async def process_queue(change_queue, host, port, mode='dev'):
    while True:
        if not change_queue.empty():
            slug = change_queue.get()
            # logging.info(msg=slug)
            if mode == 'prod':
                poe_send(slug.src_path, host, port)
                logging.info(msg=f'sent: {slug.src_path}')

            else:
                logging.info(msg=str(slug.src_path))
        else:
            await asyncio.sleep(.1)


class DerWatchDog(PatternMatchingEventHandler):
    def __init__(self, queue, patterns):
        PatternMatchingEventHandler.__init__(self, patterns=patterns)
        self.Q = queue

    def on_created(self, event):
        self.Q.put(event)
