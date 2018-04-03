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
import pprint
from bft_variables import *

class YandexCloudOperation:	
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
		self.headers = dict(Authorization='OAuth %s' % self.access_token)
		return token['access_token']
		
	def __init__(self, account_id = None, path = None):
		self.content_dict = dict()	# path <-> id pairs
		self.path = path
		self.account_id = account_id
		self.clouddrive = CloudDrive.Yandex
		self.rooturl = 'https://cloud-api.yandex.net'
		self.content_dict = dict()
		self.refresh_token()		
		urllib3.disable_warnings()

	def upload(self, fsource = None, ftarget = None, name = None, retry_count = 5):
		url = self.rooturl + '/v1/disk/resources/upload?path=%s&overwrite=true' % urllib.quote(os.path.join(ftarget, name), safe = '')
		resp = get(url = url, headers = self.headers, verify = False)
		if resp.status_code == 200:
			with open(fsource, 'rb') as f:
				upload_url = resp.json()['href']
				files = [('file', (fsource, f.read(), ''))]
				resp = put(url = upload_url, files = files, verify = False)
				if resp.status_code != 201:
					print 'failed to upload: %s' % fsource

		
	def upload_bulk_sub(self, files = None, target_full_path = None, retry_count = 5):
		pass

	def upload_bulk(self, fsource = None, ftarget = None, number_of_files = 1):
		pass

	def create_folder(self, folder_name = None, parent_path = None):
		fname = os.path.join(parent_path, folder_name)		
		url = self.rooturl + '/v1/disk/resources/?path=%s' % urllib.quote(fname, safe='')
		resp = put(url = url, headers = self.headers, verify=False)		
		if resp.status_code != 201:			
			if resp.status_code == 409:
				print '%s folder exists: %s' % (resp.status_code, fname)			
			else:	
				print '%s failed to create folder: %s' % (resp.status_code, fname)
			
		
	def create_path(self, path = None):
		path_list = path.strip('/').split('/')
		parent_path = '/'
		for p in path_list:
			self.create_folder(folder_name = p, parent_path = parent_path)
			parent_path = os.path.join(parent_path, p)
		
	def trash(self, path = None):	
		url = self.rooturl + '/v1/disk/resources?path=%s&permanently=true' % urllib.quote(path, safe='')
		resp = delete(url = url, headers = self.headers, verify = False)
		if resp.status_code not in (202, 204):			
			print '%s failed to delete: %s' % (resp.status_code, path)	
			
	def rename(self, path = None, new_name = None):
		path_list = path.strip('/').split('/')
		path_list.pop()
		new_path = '/%s' % os.path.join('/'.join(path_list), new_name) 
		url = self.rooturl + '/v1/disk/resources/move?from=%s&path=%s&overwrite=true' % (urllib.quote(path, safe=''),
																						 urllib.quote(new_path, safe=''))
		resp = post(url = url, headers = self.headers, verify = False)
		if resp.status_code not in (201, 202):
			print '%s failed to rename: %s' % (resp.status_code, path)
	
	def move(self, old_path = None, new_path = None):		
		path_list = old_path.strip('/').split('/')
		name = path_list.pop()
		url = self.rooturl + '/v1/disk/resources/move?from=%s&path=%s&overwrite=true' % (urllib.quote(old_path, safe=''),
																						 urllib.quote(os.path.join(new_path, name), safe=''))
		resp = post(url = url, headers = self.headers, verify = False)
		if resp.status_code not in (201, 202):
			print '%s failed to move: %s' % (resp.status_code, old_path)

	def get_content_list(self, path = None):		
		content = dict()
		if path == None:
			path = self.path
		url = self.rooturl + '/v1/disk/resources?path=%s&limit=10000' % urllib.quote(path)
		resp = get(url = url, headers = self.headers, verify = False)
		print resp
		if resp.status_code == 200:
			content_json = resp.json()
			#pprint.pprint(content_json)
			for item in content_json['_embedded']['items']:
				temp_dict = dict()
				if item['type'] == 'dir':				
					temp_dict['is_file'] = False
					temp_dict['size'] = 0
					content.update(self.get_content_list(path = item['path'][len('disk:'):]))
				else:
					temp_dict['is_file'] = True
					temp_dict['size'] = item['size']

				temp_dict['name'] = item['name']
				temp_dict['full_path'] = item['path'][len('disk:'):]
				temp_dict['relative_path'] = temp_dict['full_path'].replace(self.path, '')
				temp_dict['mtime'] = item['modified']
				content[temp_dict['relative_path']] = temp_dict

			return content
		else:
			print 'error while trying to get content'


	def cloud_init_operation(self):
		self.refresh_token()
		# trash path folder if exists
		self.trash(path = self.path)		

		# create path folder
		self.create_path(path = self.path)		

	def cloud_operation1(self):
		self.refresh_token()				
		flist = generate_file(os.path.join(os.getcwd(), 'automation_tmp'),
								 10 * 1024, num=1, file_name='temp_file', file_type='.txt')
		source = flist[0]

		num = 6
		for i in range(1, num + 1):
			# create folders on root on upload files within it			
			fid = self.create_folder(folder_name = 'yandexfolder%s' % i, parent_path = self.path)			
			self.upload(fsource = source, ftarget = os.path.join(self.path, 'yandexfolder%s' % i), 
							name = 'yandexfile%s.file' % i)

			# upload files on root path
			self.upload(fsource = source, ftarget = self.path, name = 'root_yandexfile%s.file' % i)

	def cloud_operation2(self):
		self.refresh_token()
		# move folder from root to folder
		self.move(old_path = os.path.join(self.path, 'yandexfolder4'),
					new_path = os.path.join(self.path, 'yandexfolder1'))
		self.move(old_path = os.path.join(self.path, 'yandexfolder5'),
					new_path = os.path.join(self.path, 'yandexfolder2'))
		self.move(old_path = os.path.join(self.path, 'yandexfolder6'),
					new_path = os.path.join(self.path, 'yandexfolder3'))

		# move files from root to folder
		self.move(old_path = os.path.join(self.path, 'root_yandexfile4.file'), 
					new_path = os.path.join(self.path, 'yandexfolder1'))
		self.move(old_path = os.path.join(self.path, 'root_yandexfile5.file'), 
					new_path = os.path.join(self.path, 'yandexfolder2'))
		self.move(old_path = os.path.join(self.path, 'root_yandexfile6.file'), 
					new_path = os.path.join(self.path, 'yandexfolder3'))

	def cloud_operation3(self):
		self.refresh_token()
		# rename folders	
		self.rename(path = os.path.join(self.path, 'yandexfolder1/yandexfolder4'),
					new_name = 'sub_yandexfolder1')
		self.rename(path = os.path.join(self.path, 'yandexfolder2/yandexfolder5'),
					new_name = 'sub_yandexfolder2')
		self.rename(path = os.path.join(self.path, 'yandexfolder3/yandexfolder6'),
					new_name = 'sub_yandexfolder3')

		# rename files
		self.rename(path = os.path.join(self.path, 'yandexfolder1/root_yandexfile4.file'),
					new_name = 'sub_yandexfile1.file')
		self.rename(path = os.path.join(self.path, 'yandexfolder2/root_yandexfile5.file'),
					new_name = 'sub_yandexfile2.file')
		self.rename(path = os.path.join(self.path, 'yandexfolder3/root_yandexfile6.file'),
					new_name = 'sub_yandexfile3.file')

	def cloud_operation4(self):
		pass
		'''
		self.refresh_token()
		# trash folders and files
		for i in range(1, 4):
			self.trash(os.path.join(self.path, 'yandexfolder%s/sub_yandexfolder%s' % (i, i)))
			self.trash(os.path.join(self.path, 'yandexfolder%s/sub_yandexfile%s.file' % (i, i)))
			self.trash(os.path.join(self.path, 'yandexfolder%s' % i))
			self.trash(os.path.join(self.path, 'root_yandexfile%s.file' % i))
		'''
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

	def cloud_operation14(self):
		pass

# for self testing purpose
if __name__ == '__main__':
	a = YandexCloudOperation(path = '/QNAP/test')
	a.access_token = '7deea21800b24717b94be488a317acc3'
	a.headers = dict(Authorization='OAuth %s' % a.access_token)	
	#a.cloud_init_operation()	
	#a.cloud_operation1()	
	#a.cloud_operation2()
	#a.cloud_operation3()
	#a.cloud_operation4()
	con_dict = a.get_content_list()
	pprint.pprint(con_dict)
	
	