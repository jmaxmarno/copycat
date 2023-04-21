import asyncio
import time
import logging
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler
import queue
from threading import Thread
from func import process_stream_queue, StreamWatchdog


def main():
    # run
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    print(f'watching: {path}')

    work_queue = queue.Queue()
    worker = Thread(target=asyncio.run, args=(process_stream_queue(work_queue, poe_host, poe_port, mode),), daemon=True).start()
    event_handler = StreamWatchdog(queue=work_queue, patterns=file_patterns)

    observer = Observer()
    observer.schedule(event_handler, path)
    observer.start()
    try:
        while True:
            logging.info(msg=f' queue length: {work_queue.qsize()}')
            time.sleep(3)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == '__main__':
    from args import args
    print(args._get_kwargs())
    file_patterns = args.file_patterns
    path = args.watch_directory
    mode = 'prod' if args.prod_mode is True else 'dev'
    poe_host = args.poe_host
    poe_port = args.poe_port
    main()
