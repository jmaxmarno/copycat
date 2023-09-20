import logging
import socket
from watchdog.events import PatternMatchingEventHandler
import asyncio
import shutil
import os

copylogger = logging.getLogger("copycat")

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
        copylogger.error(f'poe_send error:{dat_file} -- \n {e}')
        copylogger.error(f'poe_send error: {e}')


# try to copy a file to the output directory, if it fails, log it
def try_copy(src_path, output_dir):
    try:
        shutil.copyfile(src_path, os.path.join(output_dir, src_path.split('/')[-1]))
        copylogger.info(msg=f'copied: {src_path}')

    except Exception as e:
        copylogger.error(f'copy error: {src_path} -- \n {e}')


async def process_queue(change_queue, host, port, stats_dict, mode='dev', output_dir=None):
    while True:
        if not change_queue.empty():
            slug = change_queue.get()
            copylogger.debug(msg=slug.src_path)
            stats_dict['total'] += 1
            # logging.info(msg=slug)
            if mode == 'prod' and host is not None and port is not None:
                poe_send(slug.src_path, host, port)
                stats_dict['sent'] += 1
                copylogger.info(msg=f'sent: {slug.src_path}')
            if output_dir is not None:
                try_copy(slug.src_path, output_dir)
                stats_dict['copied'] += 1
        else:
            await asyncio.sleep(.05)


class DerWatchDog(PatternMatchingEventHandler):
    def __init__(self, queue, patterns):
        PatternMatchingEventHandler.__init__(self, patterns=patterns)
        self.Q = queue

    def on_created(self, event):
        self.Q.put(event)
