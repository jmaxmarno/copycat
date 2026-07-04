import argparse

ap = argparse.ArgumentParser()
ap.add_argument('--poe_host', default='10.20.2.188', help='Host of the POE server')
ap.add_argument('--poe_port', default=8095, type=int, help='Port to access POE')
ap.add_argument('--watch_directory', default=".", help='directory to watch for changes')
ap.add_argument('--file_patterns', default=["*.dat"], help='file patterns to match and watch', nargs="+")
ap.add_argument('--prod_mode', action='store_true', default=False,
                help='run in prod mode and send to poe address, else just log to console')
ap.add_argument('--output_dir', default=None,
                help='directory to write output files to - be careful, will dump all matching files in this directory')
ap.add_argument('--send_workers', default=4, type=int, help='sender threads doing the TCP forwarding')
ap.add_argument('--queue_max', default=1000, type=int, help='max queued payloads (backstop item cap)')
ap.add_argument('--queue_max_bytes', default=67108864, type=int,
                help='in-memory budget for queued payload bytes; over budget files are shed with a logged warning')
ap.add_argument('--send_timeout', default=15, type=int, help='seconds allowed per connect+send')
ap.add_argument('--send_retries', default=2, type=int, help='re-attempts per payload before it is dropped')
ap.add_argument('--debug', action='store_true', default=False,
                help='per-file debug logging (closed/sent/copied lines); default is the 10s stats line plus warnings/errors')

args = ap.parse_args()
