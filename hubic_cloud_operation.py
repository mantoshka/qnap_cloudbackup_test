# -*- coding: utf-8 -*-
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
from requests import head
from requests.packages import urllib3
from cc_util import CloudDrive
from cc_util import generate_file
import pprint
from bft_variables import *

class HubicCloudOperation:	
	def refresh_token(self, retry_count = 5):					
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
		
		self.get_rooturl()			
	
		return token['access_token']
		
	def get_rooturl(self):		
		url = 'https://api.hubic.com/1.0/account/credentials'		
		resp = get(url = url, headers = self.headers, verify = False)	
		if resp.status_code == 200:
			resp_json = resp.json()				
			self.rooturl = resp_json['endpoint'] + '/default'
			self.access_token = resp_json['token']		
			self.headers = { "X-Auth-Token" : self.access_token }	
		else:
			print '{} exception happens during credentials check'.format(resp.status_code)
			exit(1)

	def __init__(self, account_id = None, path = None):			
		urllib3.disable_warnings()
		if path.startswith('/'):	
			self.path = path.replace('/', '', 1)
		else:
			self.path = path
		self.account_id = account_id
		self.clouddrive = CloudDrive.Hubic		
		self.refresh_token()											

	def upload(self, fsource = None, ftarget = None, name = None, retry_count = 5):
		with open(fsource, 'rb') as f:
			url = self.rooturl + '/%s/%s' % (ftarget, name)
			headers = dict(self.headers)
			headers['X-Detect-Content-Type'] = True
			resp = put(url = url, headers = headers, data = f.read(), verify = False)
			if resp.status_code != 201:
				print 'failed to upload: %s' % fsource
		
	def upload_bulk_sub(self, files = None, target_full_path = None, retry_count = 5):
		pass

	def upload_bulk(self, fsource = None, ftarget = None, number_of_files = 1):
		pass

	def create_folder(self, folder_name = None, parent_path = None):
		url = self.rooturl + '/%s/%s' % (parent_path, folder_name)
		headers = dict(self.headers)
		headers['Content-Type'] = 'application/directory'				
		resp = put(url = url, headers = headers, verify = False, params = dict(format='json'))		
		if resp.status_code != 201:
			print 'failed to create folder: %s' % folder_name
					
	def create_path(self, path = None):
		url = self.rooturl + '/%s' % path
		headers = dict(self.headers)
		headers['Content-Type'] = 'application/directory'					
		resp = put(url = url, headers = headers, verify = False, params = dict(format='json'))
		if resp.status_code != 201:
			print 'failed to create path: %s' % path

	def trash_object(self, path = None):	
		url = self.rooturl + '/%s' % path
		resp = delete(url = url, headers = self.headers, verify = False, params = dict(format='json'))
		if resp.status_code != 204:
			print 'failed to delete: %s' % path

	def trash(self, path = None):
		resp = get(url = self.rooturl, headers = self.headers, verify = False, params = dict(format='json'))		
		obj_json = resp.json()
		for obj in obj_json:
			if obj['name'].startswith(path + '/') or obj['name'] == path:
				self.trash_object(obj['name'])	

	def rename(self, path = None, new_name = None):
		path_list = path.strip('/').split('/')
		path_list.pop()
		new_path = os.path.join('/'.join(path_list), new_name)
		# get all objects
		resp = get(url = self.rooturl, headers = self.headers, verify = False, params = dict(format='json'))
		obj_json = resp.json()
		headers = dict(self.headers)
		for obj in obj_json:
			if obj['name'].startswith(path + '/') or obj['name'] == path:					
				'''	alternative COPY method
				url = self.rooturl + '/%s' % obj['name']
				headers = '-H "X-Auth-Token: %s" -H "Destination: default/%s"' % (self.access_token, obj['name'].replace(path, new_path, 1))
				cmd = 'curl -i %s -X COPY %s' % (url, headers)								
				subprocess.call(cmd, shell = True)													
				'''
				headers['X-Copy-From'] = '/default/%s' % obj['name']
				headers['Content-Length'] = '0'				
				url = self.rooturl + '/%s' % obj['name'].replace(path, new_path, 1)				
				resp = put(url = url, headers = headers, verify = False)				
				if resp.status_code == 201:
					self.trash_object(obj['name'])
	
	def move(self, old_path = None, new_path = None):		
		resp = get(url = self.rooturl, headers = self.headers, verify = False, params = dict(format='json'))
		obj_json = resp.json()
		headers = dict(self.headers)
		path_list = old_path.strip('/').split('/')
		new_path = os.path.join(new_path, path_list.pop())		
		for obj in obj_json:
			if obj['name'].startswith(old_path + '/') or obj['name'] == old_path:
				headers['X-Copy-From'] = '/default/%s' % obj['name']
				headers['Content-Length'] = '0'				
				url = self.rooturl + '/%s' % obj['name'].replace(old_path, new_path, 1)				
				resp = put(url = url, headers = headers, verify = False)				
				if resp.status_code == 201:
					self.trash_object(obj['name'])			

	def get_content_list(self):					
		url = '{}?prefix={}'.format(self.rooturl, self.path)		
		resp = get(url = url, headers = self.headers, verify = False, params = dict(format='json'))		
		obj_json = resp.json()		
		content_dict = dict()					
		for obj in obj_json:			
			if obj['name'].startswith(self.path + '/'):				
				url = self.rooturl + '/%s' % obj['name']
				resp = head(url = url, headers = self.headers, verify = False)
				if resp.status_code == 200:
					temp_dict = dict()
					resp_dict = dict(resp.headers)					
					temp_dict['name'] = obj['name']					
					temp_dict['full_path'] = '/%s' % obj['name']
					temp_dict['relative_path'] = obj['name'].replace(self.path, '')
					if resp_dict['content-type'] == 'application/directory':
						temp_dict['is_file'] = False
						temp_dict['size'] = 0
						temp_dict['mtime'] = 0
					else:
						temp_dict['is_file'] = True
						temp_dict['size'] = int(resp_dict['content-length'])
						temp_dict['mtime'] = resp_dict['last-modified']

					content_dict[temp_dict['relative_path']] = temp_dict

				else:
					print 'status_code: %s' % resp.status_code

		return content_dict				

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
			self.create_folder(folder_name = 'hubicfolder%s' % i, parent_path = self.path)			
			self.upload(fsource = source, ftarget = os.path.join(self.path, 'hubicfolder%s' % i), 
							name = 'hubicfile%s.file' % i)

			# upload files on root path
			self.upload(fsource = source, ftarget = self.path, name = 'root_hubicfile%s.file' % i)

		# return operation identifier for report
		return 'cloud_create_result'

	def cloud_operation2(self):
		self.refresh_token()
		# move folder from root to folder
		self.move(old_path = os.path.join(self.path, 'hubicfolder4'),
					new_path = os.path.join(self.path, 'hubicfolder1'))
		self.move(old_path = os.path.join(self.path, 'hubicfolder5'),
					new_path = os.path.join(self.path, 'hubicfolder2'))
		self.move(old_path = os.path.join(self.path, 'hubicfolder6'),
					new_path = os.path.join(self.path, 'hubicfolder3'))

		# move files from root to folder
		self.move(old_path = os.path.join(self.path, 'root_hubicfile4.file'), 
					new_path = os.path.join(self.path, 'hubicfolder1'))
		self.move(old_path = os.path.join(self.path, 'root_hubicfile5.file'), 
					new_path = os.path.join(self.path, 'hubicfolder2'))
		self.move(old_path = os.path.join(self.path, 'root_hubicfile6.file'), 
					new_path = os.path.join(self.path, 'hubicfolder3'))

		# return operation identifier for report
		return 'cloud_move_result'

	def cloud_operation3(self):
		self.refresh_token()
		# rename folders	
		self.rename(path = os.path.join(self.path, 'hubicfolder1/hubicfolder4'),
					new_name = 'sub_hubicfolder1')
		self.rename(path = os.path.join(self.path, 'hubicfolder2/hubicfolder5'),
					new_name = 'sub_hubicfolder2')
		self.rename(path = os.path.join(self.path, 'hubicfolder3/hubicfolder6'),
					new_name = 'sub_hubicfolder3')

		# rename files
		self.rename(path = os.path.join(self.path, 'hubicfolder1/root_hubicfile4.file'),
					new_name = 'sub_hubicfile1.file')
		self.rename(path = os.path.join(self.path, 'hubicfolder2/root_hubicfile5.file'),
					new_name = 'sub_hubicfile2.file')
		self.rename(path = os.path.join(self.path, 'hubicfolder3/root_hubicfile6.file'),
					new_name = 'sub_hubicfile3.file')

		# return operation identifier for report
		return 'cloud_rename_result'

	def cloud_operation4(self):		
		self.refresh_token()
		# trash folders and files
		for i in range(1, 4):
			self.trash(os.path.join(self.path, 'hubicfolder%s/sub_hubicfolder%s' % (i, i)))
			self.trash(os.path.join(self.path, 'hubicfolder%s/sub_hubicfile%s.file' % (i, i)))
			self.trash(os.path.join(self.path, 'hubicfolder%s' % i))
			self.trash(os.path.join(self.path, 'root_hubicfile%s.file' % i))

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

	def cloud_operation14(self):
		pass

# for self testing purpose
if __name__ == '__main__':
	a = HubicCloudOperation(path = 'QNAP/中文test')
	a.access_token = '4Tu4dUl3YCxubqujU8QEIEaYZBBMwOuJyVx59cWr6egoZhQJYcSnPasezUCsmU7L'
	a.headers = dict(Authorization='Bearer %s' % a.access_token)		
	url = 'https://api.hubic.com/1.0/account/credentials'
	resp = get(url = url, headers = a.headers, verify = False)
	resp_json = resp.json()	
	a.rooturl = resp_json['endpoint'] + '/default'
	a.access_token = resp_json['token']
	a.headers = { "X-Auth-Token" : a.access_token }					
	a.cloud_init_operation()	
	a.create_folder(folder_name = 'test3', parent_path = a.path)
	a.create_folder(folder_name = 'test4', parent_path = a.path)	
	#a.cloud_operation1()		
	#a.cloud_operation2()
	#a.cloud_operation3()
	#a.cloud_operation4()
	#a.trash('QNAP/test1_renamed')
	pprint.pprint(a.get_content_list())	
	
	