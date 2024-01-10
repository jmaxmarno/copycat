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


class DerWatchDog(PatternMatchingEventHandler):
    def __init__(self, patterns, args):
        self.args = args
        self.mode = 'prod' if args.prod_mode is True else 'dev'
        PatternMatchingEventHandler.__init__(self, patterns=patterns)

    def on_created(self, event):
        try:
            slug = event
            self.args.stats_dict['total'] += 1
            copylogger.debug(msg=f'created: {slug.src_path}')
            if not os.path.exists(slug.src_path):
                raise Exception(f'\nfile not found: {slug.src_path}\n')
            if self.mode == 'prod' and self.args.host is not None and port is not None:
                poe_send(slug.src_path, self.args.host, self.args.port)
                self.args.stats_dict['sent'] += 1
                copylogger.info(msg=f'sent: {slug.src_path}')
            if self.args.output_dir is not None:
                try_copy(slug.src_path, self.args.output_dir)
                self.args.stats_dict['copied'] += 1
        except Exception as e:
            self.args.stats_dict['errors'] += 1
            copylogger.exception(f'process_queue error: {e}')
