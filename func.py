import logging
import os
import queue
import socket
import threading

from watchdog.events import PatternMatchingEventHandler

copylogger = logging.getLogger("copycat")


class Stats:
    """Lock-protected counters shared by the dispatch thread and sender workers."""

    def __init__(self, keys):
        self._lock = threading.Lock()
        self._counts = {k: 0 for k in keys}

    def inc(self, key, n=1):
        with self._lock:
            self._counts[key] += n

    def snapshot_and_reset(self):
        """Return a copy of the counters and zero them."""
        with self._lock:
            snap = dict(self._counts)
            for k in self._counts:
                self._counts[k] = 0
        return snap


class ByteBudgetQueue:
    """Bounded payload queue: item cap as a backstop, byte budget as the real limit.

    Bytes are reserved on first enqueue and released only when a payload leaves
    for good (sent, copied, or dropped) — a retry requeue keeps its reservation.
    """

    def __init__(self, max_items, max_bytes):
        self._q = queue.Queue(maxsize=max_items)
        self._lock = threading.Lock()
        self._max_bytes = max_bytes
        self._bytes = 0

    def try_put(self, item, nbytes):
        """Reserve nbytes and enqueue; False (nothing enqueued) if either bound is hit."""
        with self._lock:
            if self._bytes + nbytes > self._max_bytes:
                return False
            self._bytes += nbytes
        try:
            self._q.put_nowait(item)
        except queue.Full:
            with self._lock:
                self._bytes -= nbytes
            return False
        return True

    def requeue(self, item):
        """Re-enqueue a retry without touching the budget; False if the queue is full."""
        try:
            self._q.put_nowait(item)
        except queue.Full:
            return False
        return True

    def get(self):
        return self._q.get()

    def release(self, nbytes):
        with self._lock:
            self._bytes -= nbytes

    def depth(self):
        return self._q.qsize()

    def queued_bytes(self):
        with self._lock:
            return self._bytes

    def empty(self):
        return self._q.empty()


def poe_send(data, host, port, timeout):
    """Send one payload on its own TCP connection.

    The receiver frames by read-until-EOF, so one connection carries exactly one
    payload and close() is the end-of-payload marker. Do not reuse connections.

    Args:
        data: Raw payload bytes, forwarded verbatim.
        host: POE host.
        port: POE port.
        timeout: Seconds allowed for connect and send combined.
    """
    with socket.create_connection((host, port), timeout=timeout) as s:
        s.sendall(data)


def write_copy(src_path, data, output_dir):
    """Write the captured bytes to output_dir under the source file's basename."""
    with open(os.path.join(output_dir, os.path.basename(src_path)), 'wb') as f:
        f.write(data)


def sender_worker(q, args, stats):
    """Drain the queue and do all slow work: TCP send and optional local copy.

    Runs in a daemon thread; several run in parallel. Send failures are
    re-enqueued up to args.send_retries times (requeue keeps the byte
    reservation), then counted as dropped and logged with the filename.
    """
    while True:
        src_path, data, attempts = q.get()
        requeued = False
        try:
            if args.prod_mode and args.poe_host is not None and args.poe_port is not None:
                try:
                    poe_send(data, args.poe_host, args.poe_port, args.send_timeout)
                    stats.inc('sent')
                    stats.inc('bytes_sent', len(data))
                    copylogger.debug(msg=f'sent: {src_path}')
                except OSError as e:
                    if attempts < args.send_retries and q.requeue((src_path, data, attempts + 1)):
                        stats.inc('send_err')
                        requeued = True
                        copylogger.warning(msg=f'send failed (attempt {attempts + 1}), requeued: {src_path}: {e}')
                    else:
                        stats.inc('dropped')
                        copylogger.error(msg=f'send failed after {attempts + 1} attempts, dropped: {src_path}: {e}')
            if not requeued and args.output_dir is not None:
                try:
                    write_copy(src_path, data, args.output_dir)
                    stats.inc('copied')
                    copylogger.debug(msg=f'copied: {src_path}')
                except OSError:
                    stats.inc('errors')
                    copylogger.exception(f'copy failed: {src_path}')
        except Exception:
            stats.inc('errors')
            copylogger.exception(f'worker error: {src_path}')
        finally:
            if not requeued:
                q.release(len(data))


class DerWatchDog(PatternMatchingEventHandler):
    """Captures completed spool files into the send queue.

    Triggers on IN_CLOSE_WRITE (writer finished), not creation: the upstream
    writer creates the file empty and writes in place, so on_created would race
    the write and forward a truncated prefix. The callback stays fast and local
    — read bytes, enqueue — so the read happens before the upstream janitor can
    delete the file; the network lives in sender_worker threads.
    """

    def __init__(self, patterns, args, q, stats):
        """
        Args:
            patterns: filename patterns to trigger on
            args: global args
            q: ByteBudgetQueue shared with the sender workers
            stats: Stats shared with the sender workers and the stats loop
        """
        self.args = args
        self.q = q
        self.stats = stats
        PatternMatchingEventHandler.__init__(self, patterns=patterns, ignore_directories=True)

    def on_closed(self, event):
        self.ingest_path(event.src_path)

    def ingest_path(self, src_path):
        """Read a completed file and enqueue its bytes. Fast + local only."""
        self.stats.inc('seen')
        copylogger.debug(msg=f'closed: {src_path}')
        try:
            with open(src_path, 'rb') as f:
                data = f.read()
        except FileNotFoundError:
            self.stats.inc('vanished')
            copylogger.warning(msg=f'vanished before read: {src_path}')
            return
        except OSError:
            self.stats.inc('errors')
            copylogger.exception(f'read failed: {src_path}')
            return
        if not self.q.try_put((src_path, data, 0), len(data)):
            self.stats.inc('shed')
            copylogger.warning(msg=f'queue full, shed: {src_path}')
