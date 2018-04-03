#!/usr/bin/python
import os
import sys
import time
import subprocess
from cc_util import get_install_path
from bft_variables import *

usage_msg = 'python %s <dropbox/googledrive/amazon/onedrive/box/yandex/hubic> <-c>' % sys.argv[0]
qpkg_path = get_install_path(qpkg_name)
init_env_cmd = '. %s/bin/env.sh' % qpkg_path

# restart CloudDriveSync engine
subprocess.call('%s/%s.sh restart' % (qpkg_path, qpkg_name), shell=True)

cwd = os.getcwd()
# starting sync jobs
subprocess.Popen('%s;cd %s;python bft.py %s -t simple' % (init_env_cmd, cwd, sys.argv[1]), shell = True)
time.sleep(120)

subprocess.Popen('%s;cd %s;python bft.py %s -t long' % (init_env_cmd, cwd, sys.argv[1]), shell = True)
time.sleep(120)

subprocess.Popen('%s;cd %s;python bft.py %s -t advance' % (init_env_cmd, cwd, sys.argv[1]), shell = True)
time.sleep(120)

if '-c' in sys.argv:
	subprocess.Popen('%s;cd %s;python bft.py %s -t conflict -c rename_src' % (init_env_cmd, cwd, sys.argv[1]), shell = True)
	time.sleep(120)

	subprocess.Popen('%s;cd %s;python bft.py %s -t conflict -c rename_dst' % (init_env_cmd, cwd, sys.argv[1]), shell = True)
	time.sleep(120)

	subprocess.Popen('%s;cd %s;python bft.py %s -t conflict -c replace_src_with_dst' % (init_env_cmd, cwd, sys.argv[1]), shell = True)
	time.sleep(120)

	subprocess.Popen('%s;cd %s;python bft.py %s -t conflict -c replace_dst_with_src' % (init_env_cmd, cwd, sys.argv[1]), shell = True)
	time.sleep(120)

	subprocess.Popen('%s;cd %s;python bft.py %s -t conflict -c newer_win' % (init_env_cmd, cwd, sys.argv[1]), shell = True)
	time.sleep(120)