# -*- coding: utf-8 -*-
#!/usr/bin/python

# BFT automation test
import sys
import signal
import datetime
import time
import logging
import shutil

#import httplib
import urllib
import urllib2
import json
import os

import subprocess
import ConfigParser

from cc_util import create_job
from cc_util import start_job
from cc_util import check_job
from cc_util import comp_file
from cc_util import get_ip_address
from cc_util import CloudDrive
from cc_util import generate_dir
from cc_util import clean_up
from cc_util import run_operation
from cc_util import Logger
from cc_util import get_account_id
from cc_util import get_free_job_id
from cc_util import BFT
from cc_util import connector_class_name_dict
from cc_util import change_debug_log_size
from cc_util import enable_detail_log
from cc_util import get_testing_env_info
from cc_util import get_email_recipients
from nas_operation import NasOperation
from dropbox_cloud_operation import DropboxCloudOperation
from googledrive_cloud_operation import *
from amazon_cloud_operation import AmazonCloudOperation
from onedrive_cloud_operation import OneDriveCloudOperation
from box_cloud_operation import BoxCloudOperation
from yandex_cloud_operation import YandexCloudOperation
from hubic_cloud_operation import HubicCloudOperation
from conflict_operation import ConflictOperation
from bft_variables import *
from send_report import send_report

usage_msg = 'Usage: python %s <dropbox/googledrive/amazon/onedrive/box/yandex/hubic> ' + \
			'-t <simple/long/advance/conflict> ' + \
			'<-c rename_src/rename_dst/replace_src_with_dst/replace_dst_with_src/newer_win> ' + \
			'<-l>\n\n\t\t-l : loop the operations' + \
			'\n\t\t-m : manually start each operations' + \
			'\n\t\t-s : send report via email'

if len(sys.argv) == 1:
	print(usage_msg % sys.argv[0])
	exit(1)

if '-t' in sys.argv:
	t = sys.argv[sys.argv.index('-t') + 1]
	if t in ('simple', 'long', 'advance', 'filter', 'conflict'):
		bft_type = t
		if t == 'conflict':
			bft_type = BFT.conflict
			if '-c' in sys.argv:
				conflict_policy = sys.argv[sys.argv.index('-c') + 1]
			else:
				print(usage_msg % sys.argv[0])
				exit(1)		
	else:
		print(usage_msg % sys.argv[0])
		exit(1)	
else:
	print(usage_msg % sys.argv[0])
	exit(1)	

connector_name = sys.argv[1]

# check if bft needs to be run in loop
is_loop = True if '-l' in sys.argv else False

# check if user wants to continue each operation manually
auto_continue_operation = False if '-m' in sys.argv else True

# check if report needs to be sent via email
is_send_report = True if '-s' in sys.argv else False
report_dict = dict()
report_dict.update(get_testing_env_info(qpkg_name))
report_dict['cloud_service'] = connector_name
ip_address = report_dict['ip_address']
print 'ip address: %s' % ip_address

try:
	# get SID to use for CGI command
	import sid
	nas_sid = sid.login(nas_user, nas_password)
	print 'successfully get nas sid: %s' % nas_sid

	# enable detail log
	enable_detail_log(qpkg_name)

	# increase debug log size
	change_debug_log_size(qpkg_name = qpkg_name, new_size = 30000000, number_of_files = 10)

	# get account id
	account_id = get_account_id(ip_address = ip_address, qpkg_name = qpkg_name, nas_sid=nas_sid, 
								connector_class_name = connector_class_name_dict[connector_name])

	# get free job id (job id which is not assigned yet)
	job_id = get_free_job_id(ip_address=ip_address, qpkg_name=qpkg_name, nas_sid=nas_sid)
	job_name = '%s_%s_%s' % (connector_name, bft_type, job_id)

	# generate folder to store test result
	work_dir = os.path.join(os.getcwd(), job_name)
	generate_dir(work_dir)
	# write all print to both terminal and log file
	sys.stdout = Logger(work_dir)	
	
	cloud_dst = '/QNAP/Automation/{}/中文{}'.format(ip_address, job_name)
	# create (and run) sync job
	if bft_type != BFT.conflict:
		# set cloud folders
		if connector_name == 'dropbox':
			CloudOp = DropboxCloudOperation(account_id, cloud_dst)
		elif connector_name == 'googledrive':
			CloudOp = GoogleDriveCloudOperation(account_id, cloud_dst)
		elif connector_name == 'amazon':
			CloudOp = AmazonCloudOperation(account_id, cloud_dst)
		elif connector_name == 'onedrive':
			CloudOp = OneDriveCloudOperation(account_id, cloud_dst)
		elif connector_name == 'box':
			CloudOp = BoxCloudOperation(account_id, cloud_dst)
		elif connector_name == 'yandex':
			CloudOp = YandexCloudOperation(account_id, cloud_dst)
		elif connector_name == 'hubic':
			CloudOp = HubicCloudOperation(account_id, cloud_dst)
		CloudOp.cloud_init_operation()

		nas_src = '/Public/{}/中文{}'.format(CloudOp.clouddrive, job_name)
		sync_src = '/share' + nas_src
		NasOp = NasOperation(sync_src)
		NasOp.local_init_test()

		if bft_type == BFT.filter:
			sizemin = '2kb'
			sizemax = '7kb'
			datefrom = '2000/01/01'
			dateto = '2004/01/01'
			create_job(nas_sid, qpkg_name, nas_src, cloud_dst, account_id=account_id, job_name=job_name, 
					ip_address=ip_address, start_immediately = True, 
					filesizemin = sizemin,
					filesizemax = sizemax,
					filedatefrom = datefrom,
					filedateto = dateto)		
		else:
			if connector_name == 'hubic':
				create_job(nas_sid, qpkg_name, nas_src, cloud_dst, account_id=account_id, job_name=job_name, 
						ip_address=ip_address, start_immediately = False, schedule_type = 'start_manually')
			else:
				create_job(nas_sid, qpkg_name, nas_src, cloud_dst, account_id=account_id, job_name=job_name, 
						ip_address=ip_address, start_immediately = True)		
				time.sleep(30)
				print 'checking job status'
				check_job(nas_sid, qpkg_name, job_id = job_id, ip_address=ip_address)
		

	while True:
		if bft_type == BFT.simple:
			print '%s\n%s\n%s' % ('=' * 20, 'LOCAL file/folder operations', '=' * 20)
			run_operation(nas_sid, qpkg_name, job_id, sync_src, ip_address, NasOp,
							CloudOp, work_dir, True, auto_continue_operation, report_dict,
						 	NasOp.local_operation1,
							NasOp.local_operation2,
							NasOp.local_operation3,
							NasOp.local_operation4,
							NasOp.local_operation5,
							NasOp.local_cleanup_operation
							)
			
			print '%s\n%s\n%s' % ('=' * 20, '%s file/folder operations' % connector_name.upper(), '=' * 20)
			run_operation(nas_sid, qpkg_name, job_id, sync_src, ip_address, NasOp,
							CloudOp, work_dir, True, auto_continue_operation, report_dict,
						 	CloudOp.cloud_operation1,
							CloudOp.cloud_operation2,
							CloudOp.cloud_operation3,
							CloudOp.cloud_operation4,
							CloudOp.cloud_operation5
							)
			
			if is_send_report:
				send_report(report_dict, get_email_recipients())
		elif bft_type == BFT.long:
			print '%s\n%s\n%s' % ('=' * 20, 'LOCAL file/folder operations', '=' * 20)
			run_operation(nas_sid, qpkg_name, job_id, sync_src, ip_address, NasOp,
							CloudOp, work_dir, False, auto_continue_operation, report_dict,
						 	NasOp.local_operation11,
							NasOp.local_operation12
							)

			print '%s\n%s\n%s' % ('=' * 20, '%s file/folder operations' % connector_name.upper(), '=' * 20)
			run_operation(nas_sid, qpkg_name, job_id, sync_src, ip_address, NasOp,
							CloudOp, work_dir, False, auto_continue_operation, report_dict,
						 	CloudOp.cloud_operation10,
							CloudOp.cloud_operation11,
							CloudOp.cloud_operation12
							)
		elif bft_type == BFT.advance:
			print '%s\n%s\n%s' % ('=' * 20, 'LOCAL file/folder operations', '=' * 20)
			run_operation(nas_sid, qpkg_name, job_id, sync_src, ip_address, NasOp,
							CloudOp, work_dir, False, auto_continue_operation, report_dict,
						 	NasOp.local_operation6,	
							NasOp.local_operation7,
							NasOp.local_operation8,
							NasOp.local_operation9,
							NasOp.local_operation10,
							NasOp.local_operation13,
							NasOp.local_cleanup_operation
							)
			# add cloud operation
		elif bft_type == BFT.filter:
			run_operation(nas_sid, qpkg_name, job_id, sync_src, ip_address, NasOp,
							CloudOp, work_dir, True, auto_continue_operation, report_dict,
						 	CloudOp.cloud_operation10,
							CloudOp.cloud_operation11,
							CloudOp.cloud_operation12
							)
		elif bft_type == BFT.conflict:
			# conflict operation
			nas_src = '/Public/Dropbox/%s' % job_name
			ConflictOp = ConflictOperation(local_path = nas_src, cloud_path = cloud_dst, account_id = account_id,
				 sid = nas_sid, ip_address = ip_address, qpkg_name = qpkg_name, clouddrive = CloudDrive.Dropbox)

			ConflictOp.conflict_operation(conflict_policy = conflict_policy, is_loop = is_loop)
			break # the loop is inside conflict operation, so no need of loop here

		# if it's not loop, then break the while loop	
		if not(is_loop):
			break	
			
		# sleep for 10 minutes before the next loop	
		time.sleep(600)
		print 'sleeping for 600 seconds before the next loop'
except ZeroDivisionError:
	print "Unexpected error:", sys.exc_info()
finally:
	pass
	#clean_up(ip_address=ip_address, nas_sid=nas_sid, qpkg_name=qpkg_name, job_id=job_id,
	#		access_token=access_token, nas_src=nas_src, cloud_dst=cloud_dst, cloud_drive = CloudDrive.Dropbox)




