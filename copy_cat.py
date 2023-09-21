import asyncio
import time
import logging
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler
import queue
from threading import Thread
from func import process_queue, DerWatchDog
from synoptic_logging.logging_components import rotating_namer, JsonLogFormatter
from logging.handlers import TimedRotatingFileHandler
import os, sys



def main():
    # run
    # logging.basicConfig(level=logging.INFO,
    #                     format='%(asctime)s - %(message)s',
    #                     datefmt='%Y-%m-%d %H:%M:%S')
    # make logs dir if doesn't exist
    if not os.path.exists('./logs'):
        os.makedirs('./logs')
    rotating_log_handler = TimedRotatingFileHandler(
        filename=os.path.join("./logs", 'copycat.log')
        , when='H'
        , interval=6,
        backupCount=12)
    rotating_log_handler.namer = rotating_namer
    rotating_log_handler.setFormatter(JsonLogFormatter({"level": "levelname",
                                               "message": "message",
                                               "loggerName": "name",
                                               "processName": "processName",
                                               # "processID": "process",
                                               # "threadName": "threadName",
                                               # "threadID": "thread",
                                               "timestamp": "asctime"}))

    copylogger = logging.getLogger(
        "copycat")  # this can be anything unless you want to reference an existing logger
    rotating_log_handler.setLevel(20)
    copylogger.setLevel(10)
    copylogger.addHandler(rotating_log_handler)
    basic_handler = logging.StreamHandler(sys.stdout)
    basic_handler.setLevel(10)
    copylogger.addHandler(basic_handler)
    copylogger.info(args._get_kwargs())
    stats_dict = {'sent': 0, 'copied': 0, 'errors': 0, 'total': 0}
    work_queue = queue.Queue()
    worker = Thread(target=asyncio.run,
                    args=(process_queue(work_queue, poe_host, poe_port, stats_dict, mode, output_directory),),
                    daemon=True).start()
    event_handler = DerWatchDog(queue=work_queue, patterns=file_patterns)

    observer = Observer()
    observer.schedule(event_handler, path)
    observer.start()
    try:
        while True:
            copylogger.info(msg=stats_dict)
            for k, v in stats_dict.items():
                stats_dict[k] = 0
            # stats_dict = {'files_sent': 0, 'files_copied': 0, 'errors': 0, 'total': 0}
            time.sleep(10)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == '__main__':
    from args import args
    print(args._get_kwargs())
    file_patterns = args.file_patterns
    path = args.watch_directory
    mode = 'prod' if args.prod_mode is True else 'dev'
    output_directory = args.output_dir
    poe_host = args.poe_host
    poe_port = args.poe_port
    main()
