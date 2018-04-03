# conflict operation
import os
import time
import json
import urllib
import cipher
from nas_operation import NasOperation
from dropbox_cloud_operation import DropboxCloudOperation
from googledrive_cloud_operation import GoogleDriveCloudOperation
from amazon_cloud_operation import AmazonCloudOperation
from onedrive_cloud_operation import OneDriveCloudOperation
from requests.packages import urllib3
from cc_util import create_job
from cc_util import start_job
from cc_util import stop_job
from cc_util import check_job
from cc_util import get_free_job_id
from cc_util import CloudDrive

class ConflictOperation:
	def __init__(self, local_path = None, cloud_path = None, account_id = None,
				 sid = None, ip_address = None, qpkg_name = 'CloudDriveSync', clouddrive = None):
		self.localpath = local_path
		self.cloudpath = cloud_path
		self.account_id = account_id	
		self.nas_sid = sid
		self.ip_address = ip_address
		self.qpkg_name = qpkg_name
		self.clouddrive = clouddrive
		urllib3.disable_warnings()

	def conflict_init_test(self):
		NasOp = NasOperation(os.path.join('/share', self.localpath))
		NasOp.local_init_test()

		if self.clouddrive == CloudDrive.Dropbox:
			CloudOp = DropboxCloudOperation(self.account_id, self.cloudpath)			
		elif self.clouddrive == CloudDrive.GoogleDrive:
			CloudOp = GoogleDriveCloudOperation(self.account_id, self.cloudpath)
		elif self.clouddrive == CloudDrive.AmazonCloudDrive:
			CloudOp = AmazonCloudOperation(self.account_id, self.cloudpath)
		elif self.clouddrive == CloudDrive.OneDrive:
			CloudOp = OneDriveCloudOperation(self.account_id, self.cloudpath)

		CloudOp.cloud_init_operation()

	def conflict_operation(self, conflict_policy = 'rename_src', is_loop = False):
		job_id = get_free_job_id(ip_address=self.ip_address, qpkg_name=self.qpkg_name, nas_sid=self.nas_sid)
		job_name = '%s_%s' % (conflict_policy, job_id)
		nas_src = os.path.join(self.localpath, job_name)
		cloud_dst = os.path.join(self.cloudpath, job_name)
		sync_src = '/share' + nas_src
		NasOp = NasOperation(sync_src) 
		NasOp.local_init_test()
		
		if self.clouddrive == CloudDrive.Dropbox:
			CloudOp = DropboxCloudOperation(self.account_id, cloud_dst)		
		elif self.clouddrive == CloudDrive.GoogleDrive:
			CloudOp = GoogleDriveCloudOperation(self.account_id, cloud_dst)
	
		CloudOp.cloud_init_operation()
		create_job(self.nas_sid, self.qpkg_name, nas_src, cloud_dst, account_id = self.account_id, job_name=job_name, 
				ip_address = self.ip_address, start_immediately = False, conflict_policy = conflict_policy)

		while True:
			print '\nconflict_policy: %s' % conflict_policy
			NasOp.local_operation14()
			if conflict_policy == 'newer_win':
				print 'sleeping for 2 minutes before creating cloud files'
				time.sleep(120)	# sleep 2 minutes to make sure cloud files is newer
			CloudOp.cloud_operation14()

			# start the job
			start_job(ip_address = self.ip_address, qpkg_name = self.qpkg_name, nas_sid = self.nas_sid, job_id = job_id)
			time.sleep(10)
			check_job(self.nas_sid, self.qpkg_name, job_id = job_id, ip_address = self.ip_address)

			if not is_loop:
				break
			else:
				# stop the job
				stop_job(ip_address = self.ip_address, qpkg_name = self.qpkg_name, nas_sid = self.nas_sid, job_id = job_id)				
				
				# clean up local and cloud files
				NasOp.local_cleanup_operation()
				CloudOp.cloud_cleanup_operation()








	