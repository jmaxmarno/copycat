CopyCat
===

Uses the [Watchdog](https://github.com/gorakhargosh/watchdog) library to monitor a directory and log or send files to another POE.
Only fires when a file is created that matches the _--file_pattern/s_.

## Configurable Arguments

`--poe_host`, default=`10.20.2.188`, help='Host of the POE server')

`--poe_port`, default=8095, help='Port to access POE')

`--watch_directory`, default=".", help='directory to watch for changes')

`--file_patterns`, default=["*.dat"], help='file patterns to match and watch', nargs="+")

`--prod_mode`, action='store_true', default=False, help='run in prod mode and send to poe address, else just log to console')


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

