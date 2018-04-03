import os
import time
import json
import subprocess
import urllib
import base64
#import cipher
from requests import post
from requests import put
from requests import patch
from requests import get
from requests import delete
from requests.packages import urllib3
from cc_util import CloudDrive
from cc_util import generate_file
import pprint
from bft_variables import *

class HiDriveCloudOperation:
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
		self.access_token = base64.b64encode(token['access_token'])
		self.headers = dict(Authorization='Bearer %s' % self.access_token)
		return token['access_token']
		
	def __init__(self, account_id = None, path = None):
		urllib3.disable_warnings()
		self.content_dict = dict()	# path <-> id pairs
		self.path = path
		self.account_id = account_id
		self.clouddrive = CloudDrive.HiDrive
		self.rooturl = 'https://api.hidrive.strato.com'
		self.refresh_token()		

	def upload(self, fsource = None, ftarget = None, name = None, retry_count = 5):
		with open(fsource, 'rb') as f:
			url = self.rooturl + '/2.1/file?dir=/public%s&name=%s' % (ftarget, name)
			body = f.read()
			headers = self.headers
			headers['Content-Type'] = 'application/octet-stream'
			resp = put(url = url, headers = headers, data = body)			
			if resp.status_code != 200:
				print '%s failed to upload: %s' % (resp.status_code, fsource)
			
	def upload_bulk_sub(self, files = None, target_full_path = None, retry_count = 5):
		pass

	def upload_bulk(self, fsource = None, ftarget = None, number_of_files = 1):
		pass

	def create_folder(self, folder_name = None, parent_path = None):
		url = self.rooturl + '/2.1/dir?path=/public%s' % urllib.quote(os.path.join(parent_path, folder_name), safe='')		
		resp = post(url = url, headers = self.headers, verify = False)		
		if resp.status_code != 201:			
			print '%s failed to create folder: %s' % (resp.status_code, os.path.join(parent_path, folder_name))		

	def create_path(self, path = None):
		path_list = path.strip('/').split('/')		
		parent_path = '/'
		for p in path_list:
			self.create_folder(folder_name = p, parent_path = parent_path)
			parent_path = os.path.join(parent_path, p)		


	def isfile(self, path = None):
		# determine object type: file or folder
		url = self.rooturl + '/2.1/meta?path=/public%s' % urllib.quote(path, safe='')
		resp = get(url = url, headers = self.headers, verify = False)				
		if resp.status_code == 200:
			if resp.json()['type'] == 'file':
				return True
			else:
				return False

		return False


	def trash(self, path = None):
		if self.isfile(path = path):
			url = self.rooturl + '/2.1/file?path=/public%s' % urllib.quote(path, safe='')
		else:
			url = self.rooturl + '/2.1/dir?path=/public%s&recursive=true' % urllib.quote(path, safe='')
		
		resp = delete(url = url, headers = self.headers, verify = False)				
		if resp.status_code != 204:
			print '%s failed to delete: %s' % (resp.status_code, path)

	def rename(self, path = None, new_name = None):
		if self.isfile(path = path):
			url = self.rooturl + '/2.1/file/rename?path=/public%s&name=%s' % (urllib.quote(path, safe=''), new_name)
		else:
			url = self.rooturl + '/2.1/dir/rename?path=/public%s&name=%s' % (urllib.quote(path, safe=''), new_name)				
		resp = post(url = url, headers = self.headers, verify = False)
		if resp.status_code != 200:
			print '%s failed to rename: %s' % (resp.status_code, path)

	def move(self, old_path = None, new_path = None):		
		path_list = old_path.strip('/').split('/')
		name = path_list.pop()
		new_path = os.path.join(new_path, name)
		if self.isfile(path = old_path):			
			url = self.rooturl + '/2.1/file/move?src=/public%s&dst=/public%s' % (urllib.quote(old_path, safe=''), urllib.quote(new_path, safe=''))
		else:
			url = self.rooturl + '/2.1/dir/move?src=/public%s&dst=/public%s' % (urllib.quote(old_path, safe=''), urllib.quote(new_path, safe=''))			
		resp = post(url = url, headers = self.headers, verify = False)
		if resp.status_code != 200:
			print '%s failed to move: %s' % (resp.status_code, old_path)

	def get_content_list(self, path = None):
		content = dict()
		if path == None:
			path = self.path
		url = self.rooturl + '/2.1/dir?path=/public%s' % urllib.quote(path, safe='')
		resp = get(url = url, headers = self.headers, verify = False)				
		if resp.status_code == 200:
			content_json = resp.json()			
			for child in content_json['members']:
				child_path = os.path.join(content_json['path'], child['name'])
				url = self.rooturl + '/2.1/meta?path=%s' % child_path
				resp = get(url = url, headers = self.headers, verify = False)
				child_json = resp.json()
				temp_dict = dict()
				temp_dict['full_path'] = child_path			
				if child_json['type'] == 'dir':
					temp_dict['is_file'] = False
					temp_dict['size'] = 0
					content.update(self.get_content_list(path = temp_dict['full_path'][len('/public'):]))
				else:
					temp_dict['is_file'] = True
					temp_dict['size'] = child_json['size']

				temp_dict['name'] = child['name']								
				temp_dict['relative_path'] = temp_dict['full_path'].replace('/public{}'.format(self.path), '')
				temp_dict['mtime'] = child_json['mtime']
				content[temp_dict['relative_path']] = temp_dict

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
			self.create_folder(folder_name = 'hidrivefolder%s' % i, parent_path = self.path)
			self.upload(fsource = source, ftarget = os.path.join(self.path, 'hidrivefolder%s' % i), 
							name = 'hidrivefile%s.file' % i)

			# upload files on root path
			self.upload(fsource = source, ftarget = self.path, name = 'root_hidrivefile%s.file' % i)

	def cloud_operation2(self):
		#self.refresh_token()
		# move folder from root to folder
		self.move(old_path = os.path.join(self.path, 'hidrivefolder4'),
					new_path = os.path.join(self.path, 'hidrivefolder1'))
		self.move(old_path = os.path.join(self.path, 'hidrivefolder5'),
					new_path = os.path.join(self.path, 'hidrivefolder2'))
		self.move(old_path = os.path.join(self.path, 'hidrivefolder6'),
					new_path = os.path.join(self.path, 'hidrivefolder3'))

		# move files from root to folder
		self.move(old_path = os.path.join(self.path, 'root_hidrivefile4.file'), 
					new_path = os.path.join(self.path, 'hidrivefolder1'))
		self.move(old_path = os.path.join(self.path, 'root_hidrivefile5.file'), 
					new_path = os.path.join(self.path, 'hidrivefolder2'))
		self.move(old_path = os.path.join(self.path, 'root_hidrivefile6.file'), 
					new_path = os.path.join(self.path, 'hidrivefolder3'))

	def cloud_operation3(self):
		#self.refresh_token()
		# rename folders	
		self.rename(path = os.path.join(self.path, 'hidrivefolder1/hidrivefolder4'),
					new_name = 'sub_hidrivefolder1')
		self.rename(path = os.path.join(self.path, 'hidrivefolder2/hidrivefolder5'),
					new_name = 'sub_hidrivefolder2')
		self.rename(path = os.path.join(self.path, 'hidrivefolder3/hidrivefolder6'),
					new_name = 'sub_hidrivefolder3')

		# rename files
		self.rename(path = os.path.join(self.path, 'hidrivefolder1/root_hidrivefile4.file'),
					new_name = 'sub_hidrivefile1.file')
		self.rename(path = os.path.join(self.path, 'hidrivefolder2/root_hidrivefile5.file'),
					new_name = 'sub_hidrivefile2.file')
		self.rename(path = os.path.join(self.path, 'hidrivefolder3/root_hidrivefile6.file'),
					new_name = 'sub_hidrivefile3.file')

	def cloud_operation4(self):
		#self.refresh_token()
		# trash folders and files
		for i in range(1, 4):
			self.trash(os.path.join(self.path, 'hidrivefolder%s/sub_hidrivefolder%s' % (i, i)))
			self.trash(os.path.join(self.path, 'hidrivefolder%s/sub_hidrivefile%s.file' % (i, i)))
			self.trash(os.path.join(self.path, 'hidrivefolder%s' % i))
			self.trash(os.path.join(self.path, 'root_hidrivefile%s.file' % i))

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
	a = HiDriveCloudOperation(path = '/QNAP/Automation/test')
	a.access_token = base64.b64encode('vaY17E3RvvXSm5I0NjRm')
	a.headers = dict(Authorization='Bearer %s' % a.access_token)		
	#a.cloud_init_operation()
	#a.cloud_operation1()
	#a.cloud_operation2()
	#a.cloud_operation3()
	a.cloud_operation4()
	#pprint.pprint(a.get_content_list())
	