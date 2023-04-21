import argparse

ap = argparse.ArgumentParser()
ap.add_argument('--poe_host', default='10.20.2.188', help='Host of the POE server')
ap.add_argument('--poe_port', default=8095, help='Port to access POE')
ap.add_argument('--watch_directory', default=".", help='directory to watch for changes')
ap.add_argument('--file_patterns', default=["*.dat"], help='file patterns to match and watch', nargs="+")
ap.add_argument('--prod_mode', action='store_true', default=False, help='run in prod mode and send to poe address, else just log to console')

args = ap.parse_args()
