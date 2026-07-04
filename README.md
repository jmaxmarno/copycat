CopyCat
===

Uses the [Watchdog](https://github.com/gorakhargosh/watchdog) library to monitor a directory and log or send files to another POE.
Fires when a file matching the _--file_pattern/s_ is closed after writing (inotify `IN_CLOSE_WRITE`, Linux only) — i.e. once the writer is done, not on creation. The event callback reads the file's bytes into a bounded in-memory queue; a small pool of sender threads does the TCP forwarding (one connection per file — the receiver frames by connection close). On startup, existing matching files in the watch directory are scanned and forwarded too (duplicates are deduplicated downstream).

### Setup/Install
* Install Python 3.6+
    * use a venv probably (and activate it)
* Install synoptic-logging
``` shell
pip install git+ssh://git@github.com/synoptic/synoptic-logging.git@v1.0.4#egg=synoptic-logging
```
* Install requirements
``` shell
pip install -r requirements.txt
```

## Configurable Arguments

`--poe_host`, default=`10.20.2.188`, help='Host of the POE server')

`--poe_port`, default=8095, help='Port to access POE')

`--watch_directory`, default=".", help='directory to watch for changes')

`--file_patterns`, default=["*.dat"], help='file patterns to match and watch', nargs="+")

`--prod_mode`, action='store_true', default=False, help='run in prod mode and send to poe address, else just log to console')

`--output_dir`, default=None, help='directory to write output files to - be careful, will dump all matching files in this directory')

`--send_workers`, default=4, help='sender threads doing the TCP forwarding'

`--queue_max`, default=1000, help='max queued payloads (backstop item cap)'

`--queue_max_bytes`, default=67108864 (64 MB), help='in-memory budget for queued payload bytes; over budget files are shed with a logged warning'

`--send_timeout`, default=15, help='seconds allowed per connect+send'

`--send_retries`, default=2, help='re-attempts per payload before it is dropped'

`--debug`, default=False, help='per-file debug logging (closed/sent/copied lines); default output is the 10s stats line plus warnings/errors'

## Logging
A stats line is logged every 10s with the counters `seen, sent, bytes_sent, copied, vanished, shed, send_err, dropped, errors` plus `queue_depth`/`queue_bytes` gauges — on a healthy run everything but `seen`/`sent`/`bytes_sent` stays 0 and `queue_depth` returns to 0. Every shed, vanish, retry, and drop is also logged individually with the filename at WARNING/ERROR.

JSON logs go to `./logs/copycat.log` with size-based rotation — hard disk ceiling of 120 MB (20 MB x 6 files) no matter the log rate. The same output goes to stdout; if you run via nohup/redirect rather than systemd, point stdout at `/dev/null` or logrotate it, since that copy is not capped by the app.


## Run
Starting up the directory watcher:

### Dev Mode (Default)
In dev mode, we just log to console.

```
python3 copy_cat.py
```
### Prod Mode
Prod mode send relays the created files matching the file_patterns to the specified POE host and port.
```
python3 copy_cat.py --prod_mode
```

### Output Directory
default="./copycat_output"
```
python3 copy_cat.py --output_dir="./copycat_output"
```

### File Patterns
default=["*.dat"]
use wildcard characters
```
python3 copy_cat.py --file_patterns "*RAWS*" "*.test"
```

