#!/usr/bin/python

import os
import sys
import time
import subprocess
from cc_util import get_install_path
from bft_variables import *

print 'running simple BFT'
usage_msg = 'python %s <dropbox/googledrive/amazon/onedrive/box/yandex/hubic> <-c>' % sys.argv[0]
qpkg_path = get_install_path(qpkg_name)
init_env_cmd = '. %s/bin/env.sh' % qpkg_path

# restart CloudDriveSync engine
subprocess.call('%s/%s.sh restart' % (qpkg_path, qpkg_name), shell=True)

cwd = os.getcwd()
# starting sync jobs
subprocess.Popen('%s;cd %s;python bft.py %s -t simple -s' % (init_env_cmd, cwd, sys.argv[1]), shell = True)