import logging
import socket
from watchdog.events import PatternMatchingEventHandler
import asyncio
import shutil
import os

copylogger = logging.getLogger("copycat")


def poe_send(src_path, host, port):
    f = open(src_path)
    io = f.read()
    f.close()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    s.sendall(bytes(io, 'utf-8'))
    s.close()
    copylogger.debug(msg=f'sent: {src_path}')


# try to copy a file to the output directory, if it fails, log it
def try_copy(src_path, output_dir):
    shutil.copyfile(src_path, os.path.join(output_dir, src_path.split('/')[-1]))
    copylogger.debug(msg=f'copied: {src_path}')


async def process_queue(change_queue, host, port, stats_dict, mode='dev', output_dir=None):
    while True:
        if not change_queue.empty():
            try:
                slug = change_queue.get()
                if not os.path.exists(slug.src_path):
                    raise Exception(f'\nfile not found: {slug.src_path}\n')
                copylogger.debug(msg=slug.src_path)
                stats_dict['total'] += 1
                if mode == 'prod' and host is not None and port is not None:
                    poe_send(slug.src_path, host, port)
                    stats_dict['sent'] += 1
                    copylogger.info(msg=f'sent: {slug.src_path}')
                if output_dir is not None:
                    try_copy(slug.src_path, output_dir)
                    stats_dict['copied'] += 1
            except Exception as e:
                stats_dict['errors'] += 1
                copylogger.exception(f'process_queue error: {e}')
        else:
            await asyncio.sleep(.05)


class DerWatchDog(PatternMatchingEventHandler):
    def __init__(self, queue, patterns):
        PatternMatchingEventHandler.__init__(self, patterns=patterns)
        self.Q = queue

    def on_created(self, event):
        self.Q.put(event)
