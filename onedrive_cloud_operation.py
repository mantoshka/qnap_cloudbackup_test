import os
import time
import json
import subprocess
import urllib
import cipher
from requests import post
from requests import put
from requests import patch
from requests import get
from requests import delete
from requests.packages import urllib3
from cc_util import CloudDrive
from cc_util import generate_file
from cc_util import save_json
import pprint
from bft_variables import *

class OneDriveCloudOperation:
	def refresh_token(self):				
		# read the token from conf file
		conf_name = '/etc/config/cloudconnector/%s/cloudconnector.0.conf' % qpkg_name
		with open(conf_name) as fp:		
			conf_json = json.load(fp)
		
		encrypted_token = urllib.unquote(conf_json['account_dict'][self.account_id]['auth']).decode('utf8')
		if qpkg_name == 'CloudDriveSync':
			key = 'P7U2RZrMwTGsS0fq5jKAR9KUuldpLD7k' 
		else:
			key = 'g8nCsbKAT5jbSopITKhKlKlUJdTxD49w'		
		token = json.loads(cipher.decode(encrypted_token, key))
		self.access_token = token['access_token']
		self.headers = dict(Authorization='Bearer %s' % self.access_token)		
		return token['access_token']
		
	def __init__(self, account_id = None, path = None):
		self.content_dict = dict()	# path <-> id pairs
		self.path = path
		self.account_id = account_id
		self.clouddrive = CloudDrive.OneDrive
		self.rooturl = 'https://api.onedrive.com/v1.0'
		self.refresh_token()
		urllib3.disable_warnings()

	def upload(self, fsource = None, ftarget = None, name = None, retry_count = 5):
		with open(fsource, 'rb') as f:
			url = self.rooturl + '/drive/root:%s/%s:/content' % (ftarget, name)
			body = f.read()
			resp = put(url = url, headers = self.headers, data = body)
			if resp.status_code != 201:
				print 'failed to upload: %s' % fsource
			
	def upload_bulk_sub(self, files = None, target_full_path = None, retry_count = 5):
		pass

	def upload_bulk(self, fsource = None, ftarget = None, number_of_files = 1):
		pass

	def create_folder(self, folder_name = None, parent_path = None):
		url = self.rooturl + 'drive/root:/%s:/children' % parent_path		
		headers = self.headers
		headers['Content-Type'] = 'application/json'
		body = { 
				'name' : folder_name,
				'folder' : { },
				'@name.conflictBehavior' : 'rename'
				}
		resp = post(url = url, headers = headers, data = json.dumps(body))		

	def create_path(self, path = None):
		path_list = path.strip('/').split('/')
		name = path_list.pop()
		parent_path = '/'.join(path_list)
		url = self.rooturl + 'drive/root:/%s:/children' % parent_path
		headers = self.headers
		headers['Content-Type'] = 'application/json'
		body = { 
				'name' : name,
				'folder' : { },
				'@name.conflictBehavior' : 'rename'
				}
		resp = post(url = url, headers = headers, data = json.dumps(body))
		if resp.status_code != 201:
			print '%s: cannot create path' % resp.status_code

	def trash(self, path = None):
		url = self.rooturl + '/drive/root:%s' % path				
		resp = delete(url = url, headers = self.headers, verify = False)		
		if resp.status_code != 204:
			print 'failed to delete: %s' % path		

	def rename(self, path = None, new_name = None):
		url = self.rooturl + '/drive/root:%s' % path
		headers = self.headers
		headers['Content-Type'] = 'application/json'
		body = { 
				'name' : new_name
				}
		resp = patch(url = url, headers = headers, data = json.dumps(body))
		if resp.status_code != 200:
			print 'failed to rename: %s' % path

	def move(self, old_path = None, new_path = None):		
		url = self.rooturl + '/drive/root:%s' % old_path
		headers = self.headers
		headers['Content-Type'] = 'application/json'
		body = { 
				'parentReference' : { 'path' : '/drive/root:%s' % new_path }
				}
		resp = patch(url = url, headers = headers, data = json.dumps(body))
		if resp.status_code != 200:
			print 'failed to move: %s' % old_path

	def get_content_list(self, path = None, retry_count = 5):				
		content = dict()
		if path == None:
			path = self.path
		
		# OneDrive changes its API call sometimes, need to update below URL when it happens		
		url = '{}/drive/root:{}:/children'.format(self.rooturl, path)		
		resp = get(url = url, headers = self.headers, verify = False)
		if resp.status_code == 200:
			content_json = resp.json()					
			for child in content_json['value']:								
				temp_dict = dict()
				temp_dict['full_path'] = os.path.join(child['parentReference']['path'][len('/drive/root:'):], child['name'])				
				if child.has_key('folder'):
					temp_dict['is_file'] = False
					temp_dict['size'] = 0
					content.update(self.get_content_list(path = temp_dict['full_path']))
				else:
					temp_dict['is_file'] = True
					temp_dict['size'] = child['size']

				temp_dict['name'] = child['name']								
				temp_dict['relative_path'] = temp_dict['full_path'].replace(self.path, '')
				temp_dict['mtime'] = child['lastModifiedDateTime']			
				content[temp_dict['relative_path']] = temp_dict
		elif resp.status_code == 401:
			self.refresh_token()
		else:
			print '{} failed to get content list...'.format(resp.status_code)
			if retry_count != 0:
				retry_period = (6 - retry_count) * 5
				print 'retrying in {} seconds'.format(retry_period)
				time.sleep(retry_period)
				content.update(self.get_content_list(path = path, retry_count = retry_count - 1))
		
		return content				
		

	def cloud_init_operation(self):
		# trash path folder if exists
		self.trash(self.path)

		# create path folder
		self.create_path(self.path)

	def cloud_operation1(self):
		#self.refresh_token()		
		flist = generate_file(os.path.join(os.getcwd(), 'automation_tmp'),
								 10 * 1024, num=1, file_name='temp_file', file_type='.txt')
		source = flist[0]

		num = 6
		for i in range(1, num + 1):
			# create folders on root on upload files within it
			self.create_folder(folder_name = 'onedrivefolder%s' % i, parent_path = self.path)
			self.upload(fsource = source, ftarget = os.path.join(self.path, 'onedrivefolder%s' % i), 
							name = 'onedrivefile%s' % i)

			# upload files on root path
			self.upload(fsource = source, ftarget = self.path, name = 'root_onedrivefile%s' % i)

		# return operation identifier for report
		return 'cloud_create_result'

	def cloud_operation2(self):
		#self.refresh_token()
		# move folder from root to folder
		self.move(old_path = os.path.join(self.path, 'onedrivefolder4'),
					new_path = os.path.join(self.path, 'onedrivefolder1'))
		self.move(old_path = os.path.join(self.path, 'onedrivefolder5'),
					new_path = os.path.join(self.path, 'onedrivefolder2'))
		self.move(old_path = os.path.join(self.path, 'onedrivefolder6'),
					new_path = os.path.join(self.path, 'onedrivefolder3'))

		# move files from root to folder
		self.move(old_path = os.path.join(self.path, 'root_onedrivefile4'), 
					new_path = os.path.join(self.path, 'onedrivefolder1'))
		self.move(old_path = os.path.join(self.path, 'root_onedrivefile5'), 
					new_path = os.path.join(self.path, 'onedrivefolder2'))
		self.move(old_path = os.path.join(self.path, 'root_onedrivefile6'), 
					new_path = os.path.join(self.path, 'onedrivefolder3'))

		# return operation identifier for report
		return 'cloud_move_result'

	def cloud_operation3(self):
		#self.refresh_token()
		# rename folders	
		self.rename(path = os.path.join(self.path, 'onedrivefolder1/onedrivefolder4'),
					new_name = 'sub_onedrivefolder1')
		self.rename(path = os.path.join(self.path, 'onedrivefolder2/onedrivefolder5'),
					new_name = 'sub_onedrivefolder2')
		self.rename(path = os.path.join(self.path, 'onedrivefolder3/onedrivefolder6'),
					new_name = 'sub_onedrivefolder3')

		# rename files
		self.rename(path = os.path.join(self.path, 'onedrivefolder1/root_onedrivefile4'),
					new_name = 'sub_onedrivefile1')
		self.rename(path = os.path.join(self.path, 'onedrivefolder2/root_onedrivefile5'),
					new_name = 'sub_onedrivefile2')
		self.rename(path = os.path.join(self.path, 'onedrivefolder3/root_onedrivefile6'),
					new_name = 'sub_onedrivefile3')

		# return operation identifier for report
		return 'cloud_rename_result'

	def cloud_operation4(self):
		#self.refresh_token()
		# trash folders and files
		for i in range(1, 3):
			self.trash(os.path.join(self.path, 'onedrivefolder%s/sub_onedrivefolder%s' % (i, i)))
			self.trash(os.path.join(self.path, 'onedrivefolder%s/sub_onedrivefile%s' % (i, i)))
			self.trash(os.path.join(self.path, 'onedrivefolder%s' % i))
			self.trash(os.path.join(self.path, 'root_onedrivefile%s' % i))

		# return operation identifier for report
		return 'cloud_delete_result'

	def cloud_operation5(self):
		pass

	def cloud_operation6(self):
		pass

	def cloud_operation7(self):
		pass

	def cloud_operation8(self):
		pass

	def cloud_operation9(self):
		pass

	def cloud_operation10(self):
		pass

	def cloud_operation11(self):
		pass

	def cloud_operation12(self):
		pass

	def cloud_operation13(self):
		pass

	def  cloud_operation14(self):
		pass

# for self testing purpose
if __name__ == '__main__':
	a = OneDriveCloudOperation(path = '/QNAP/Automation/test')
	a.access_token = 'EwB4Aq1DBAAUGCCXc8wU/zFu9QnLdZXy+YnElFkAASX4N229I7iSt+nKs/YaHc4qReijmwDu/7W56phAo42/BMi9pVP4Qp8fVrpIQ3+lQaf4qyxiUh64jrJrPxaGVnyqjEXYNbgbw5VOrUWFJZgNHEZcbPvOtVQCAWNVLCT1ZNOBPkwbwBNMRpUY5psiAOQWCFY5kuLfCJZ8do1JCZG5d58FvPB1tIDh2Ajt9QKTw9RieKILCjl9ewEqDJiYJLfYmnVdIWzrc1I2vCrCQ6mHRwMFJrOARz3KJkgcIiktyIZ9wMgwShovaI4L2COLLqJhYyQkyff+p48uk3ts/8oTLPE7SlebvY7v+u560CjA44MsrcSmAlE5iRDKAH3fbRsDZgAACK9f2KYiXFyaSAEGnf0ByQBfCW7qtGxx58c5a/AyaMryuypH2IX6ZRGVXYCyhkk68eySeHBhvsKQVkkH6m81dL2AJ1Q/GDTH4qb2dgs2/qtntU5q5HV7++khAlu6Hd+PPzj1WnonBwtUo3K7rhV8x6a/prM4UdG4Ozd2Mb7vNMGYCtMGMxt6VypwP4+lg+btcL1hFySC9q9Q4SqnrobU7mmucxqF+2Vyfyyt0sbeHrPvrs6qujxsC7gdgK+n4pUskHO9Uf0HbvipGS1kAG5VQ7iBT17E0mig85cuZCeukUxHY3+GrfFKZ4hejFmWfhNl50SCdv28G4463vRgtYIa3CRg0tNm18UKaUmItGlM+QvBduGnwWAJhlm0Slmvoefd+AEcl5X5jACdanT7fwTXw4Wu6pJ+AVmMoqOSlGbOs95BM1DqtRylJuEjowOYHI11R6RUZAE='
	a.headers = dict(Authorization='Bearer %s' % a.access_token)
	#a.cloud_init_operation()
	#a.cloud_operation1()
	#a.cloud_operation2()
	#a.cloud_operation3()
	#a.cloud_operation4()
	pprint.pprint(a.get_content_list())
	