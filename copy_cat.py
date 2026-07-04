import glob
import logging
import os
import sys
import time
from logging.handlers import RotatingFileHandler
from threading import Thread

from watchdog.observers import Observer

from func import ByteBudgetQueue, DerWatchDog, Stats, sender_worker
from synoptic_logging.logging_components import JsonLogFormatter

STAT_KEYS = ('seen', 'sent', 'bytes_sent', 'copied', 'vanished', 'shed', 'send_err', 'dropped', 'errors')

# size-based rotation: hard disk ceiling of maxBytes * (backupCount + 1) = 120 MB,
# regardless of log rate (a sink outage during a burst logs per-file warnings)
LOG_MAX_BYTES = 20_000_000
LOG_BACKUP_COUNT = 5


def configure_logging(debug=False):
    if not os.path.exists('./logs'):
        os.makedirs('./logs')
    level = logging.DEBUG if debug else logging.INFO
    rotating_log_handler = RotatingFileHandler(
        filename=os.path.join("./logs", 'copycat.log'),
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT)
    rotating_log_handler.setFormatter(JsonLogFormatter({"level": "levelname",
                                               "message": "message",
                                               "loggerName": "name",
                                               "processName": "processName",
                                               "timestamp": "asctime"}))

    copylogger = logging.getLogger("copycat")
    rotating_log_handler.setLevel(level)
    copylogger.setLevel(level)
    copylogger.addHandler(rotating_log_handler)
    basic_handler = logging.StreamHandler(sys.stdout)
    basic_handler.setLevel(level)
    copylogger.addHandler(basic_handler)
    return copylogger


def main(args):
    copylogger = configure_logging(debug=args.debug)
    copylogger.info(args._get_kwargs())

    stats = Stats(STAT_KEYS)
    q = ByteBudgetQueue(args.queue_max, args.queue_max_bytes)
    for _ in range(args.send_workers):
        Thread(target=sender_worker, args=(q, args, stats), daemon=True).start()

    event_handler = DerWatchDog(patterns=args.file_patterns, args=args, q=q, stats=stats)
    observer = Observer()
    observer.schedule(event_handler, args.watch_directory)
    observer.start()

    # catch-up scan after the observer starts: a double capture is deduped
    # downstream, a gap between scan and watch would not be
    for pattern in args.file_patterns:
        for path in glob.glob(os.path.join(args.watch_directory, pattern)):
            event_handler.ingest_path(path)

    try:
        while True:
            snap = stats.snapshot_and_reset()
            snap['queue_depth'] = q.depth()
            snap['queue_bytes'] = q.queued_bytes()
            copylogger.info(msg=snap)
            time.sleep(10)
    except KeyboardInterrupt:
        observer.stop()
        observer.join()
        deadline = time.time() + 30
        while not q.empty() and time.time() < deadline:
            time.sleep(0.2)
        if not q.empty():
            copylogger.warning(msg=f'exiting with {q.depth()} payloads unsent')


if __name__ == '__main__':
    from args import args
    main(args)
