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

class BoxCloudOperation:
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
		self.clouddrive = CloudDrive.Box
		self.rooturl = 'https://api.box.com/2.0'
		self.content_dict = dict()
		self.refresh_token()		
		urllib3.disable_warnings()

	def get_id(self, path = None):	
		if not path.startswith('/'):
			path = '/%s' % path
		
		if path in self.content_dict:			
			return (self.content_dict[path]['id'], self.content_dict[path]['type'])
	
		path_list = path.strip('/').split('/')		
		parent_id = 0		
		ftype = None
		for p in path_list:
			fid = None
			url = self.rooturl + '/folders/%s/items?' % parent_id			
			resp = get(url = url, headers = self.headers, verify=False)
			resp_json = resp.json()			
			if len(resp_json['entries']) != 0:
				for entry in resp_json['entries']:
					if entry['name'] == p:
						parent_id = entry['id']
						fid = entry['id']
						ftype = entry['type']
						break

			if fid == None:
				return (fid, ftype)

		self.content_dict[path] = { 'id' : fid, 'type' : ftype }
		return (fid, ftype)

	def upload(self, fsource = None, ftarget = None, name = None, retry_count = 5):
		with open(fsource, 'rb') as f:
			url = 'https://upload.box.com/api/2.0/files/content'		
			(parent_id, ttype) = self.get_id(ftarget)
			_attributes = { 'name' : name, 'parent' : { 'id' : parent_id } }
			files = [('attributes', ('', json.dumps(_attributes), 'application/json')),
					 ('file', (fsource, f.read(), ''))] 
			resp = post(url = url, headers = self.headers, files = files, verify=False)			
			if resp.status_code == 201:				
				self.content_dict[os.path.join(ftarget, name)] = {
																	'id' : resp.json()['entries'][0]['id'],
																	'type' : 'file'
																}
			else:
				print 'failed to upload: %s' % fsource							
		
	def upload_bulk_sub(self, files = None, target_full_path = None, retry_count = 5):
		pass

	def upload_bulk(self, fsource = None, ftarget = None, number_of_files = 1):
		pass

	def create_folder(self, folder_name = None, parent_id = None):
		print 'creating: %s' % folder_name
		url = self.rooturl + '/folders'
		body = {
				'name' : folder_name,
				'parent' : { 'id' : parent_id }
				}		
		resp = post(url = url, headers = self.headers, data = json.dumps(body), verify=False)				
		if resp.status_code == 201:				
			return resp.json()['id']

	def create_path(self, path = None):
		path_list = path.strip('/').split('/')
		parent_id = '0'
		temp_path = ''
		for p in path_list:
			temp_path += '/%s' % p						
			(fid, ftype) = self.get_id(temp_path)				
			if fid == None:
				fid = self.create_folder(folder_name = p, parent_id = parent_id)

			parent_id = fid
		
	def trash(self, path = None):	
		if not path.startswith('/'):
			path = '/%s' % path

		print 'trashing...%s' % path
		(fid, ftype) = self.get_id(path)
		if fid == None:
			print 'path does not exist: %s' % path
			return

		if ftype == 'folder':
			url = self.rooturl + '/folders/%s?recursive=true' % fid		
		else:
			url = self.rooturl + '/files/%s' % fid
		resp = delete(url = url, headers = self.headers, verify = False)		
		if resp.status_code == 204:			
			self.content_dict.pop(path, None)
		else:
			print 'failed to delete: %s' % path					

	def rename(self, path = None, new_name = None):
		(fid, ftype)  = self.get_id(path)
		if fid == None:
			print 'path does not exist: %s' % path
			return

		url = self.rooturl + '/%ss/%s' % (ftype, fid)
		body = { 'name' : new_name }
		resp = put(url = url, headers = self.headers, data = json.dumps(body), verify=False)
		if resp.status_code != 200:
			print 'failed to rename: %s' % path
		else:
			self.content_dict.pop(path)			
	
	def move(self, old_path = None, new_path = None):		
		(fid, ftype) = self.get_id(old_path)
		if fid == None:
			print 'path does not exist: %s' % old_path
			return

		(new_parent_id, temp) = self.get_id(new_path)		
		if new_parent_id == None:
			print 'path does not exist: %s' % new_path
			return

		path_list = old_path.strip('/').split('/')
		fname = path_list[len(path_list) - 1]	
		url = self.rooturl + '/%ss/%s' % (ftype, fid)	
		body = { 'parent' : { 'id' : new_parent_id } }
		resp = put(url = url, headers = self.headers, data = json.dumps(body), verify=False)
		print 'move response: %s' % resp.status_code
		if resp.status_code != 200:
			print 'failed to move: %s' % old_path
		else:
			self.content_dict.pop(old_path)
			self.content_dict[os.path.join(new_path, fname)] = { 'id' : resp.json()['id'], 'type' : ftype }
		
	def get_content_list(self, path = None, fid = None):		
		content = dict()		
		if fid == None:
			if path == None:
				path = self.path
			(fid, ftype) = self.get_id(path)

		url = self.rooturl + '/folders/%s/items?fields=name,modified_at,size' % fid
		resp = get(url = url, headers = self.headers, verify = False)
		if resp.status_code == 200:
			content_json = resp.json()			
			for item in content_json['entries']:
				temp_dict = dict()				
				if item['type'] == 'folder':
					temp_dict['is_file'] = False
					temp_dict['size'] = 0
					content.update(self.get_content_list(path = os.path.join(path, item['name']),fid = item['id']))
				else:
					temp_dict['is_file'] = True
					temp_dict['size'] = item['size']

				temp_dict['full_path'] = os.path.join(path, item['name'])
				temp_dict['relative_path'] = temp_dict['full_path'].replace(self.path, '')
				temp_dict['name'] = item['name']
				temp_dict['mtime'] = item['modified_at']
				content[temp_dict['relative_path']] = temp_dict

			return content

	def cloud_init_operation(self):
		self.refresh_token()
		# trash path folder if exists
		self.trash(path = self.path)
		print 'trashing finished' + '=' * 20

		# create path folder
		self.create_path(path = self.path)
		print 'creating finished' + '=' * 20

	def cloud_operation1(self):
		self.refresh_token()		
		(parent_id, ptype) = self.get_id(self.path)
		flist = generate_file(os.path.join(os.getcwd(), 'automation_tmp'),
								 10 * 1024, num=1, file_name='temp_file', file_type='.txt')
		source = flist[0]

		num = 6
		for i in range(1, num + 1):
			# create folders on root on upload files within it			
			fid = self.create_folder(folder_name = 'boxfolder%s' % i, parent_id = parent_id)
			self.content_dict[os.path.join(self.path, 'boxfolder%s' % i)] = { 'id' : fid, 'type' : 'folder' }
			self.upload(fsource = source, ftarget = os.path.join(self.path, 'boxfolder%s' % i), 
							name = 'boxfile%s.file' % i)

			# upload files on root path
			self.upload(fsource = source, ftarget = self.path, name = 'root_boxfile%s.file' % i)

	def cloud_operation2(self):
		self.refresh_token()
		# move folder from root to folder
		self.move(old_path = os.path.join(self.path, 'boxfolder4'),
					new_path = os.path.join(self.path, 'boxfolder1'))
		self.move(old_path = os.path.join(self.path, 'boxfolder5'),
					new_path = os.path.join(self.path, 'boxfolder2'))
		self.move(old_path = os.path.join(self.path, 'boxfolder6'),
					new_path = os.path.join(self.path, 'boxfolder3'))

		# move files from root to folder
		self.move(old_path = os.path.join(self.path, 'root_boxfile4.file'), 
					new_path = os.path.join(self.path, 'boxfolder1'))
		self.move(old_path = os.path.join(self.path, 'root_boxfile5.file'), 
					new_path = os.path.join(self.path, 'boxfolder2'))
		self.move(old_path = os.path.join(self.path, 'root_boxfile6.file'), 
					new_path = os.path.join(self.path, 'boxfolder3'))

	def cloud_operation3(self):
		self.refresh_token()
		# rename folders	
		self.rename(path = os.path.join(self.path, 'boxfolder1/boxfolder4'),
					new_name = 'sub_boxfolder1')
		self.rename(path = os.path.join(self.path, 'boxfolder2/boxfolder5'),
					new_name = 'sub_boxfolder2')
		self.rename(path = os.path.join(self.path, 'boxfolder3/boxfolder6'),
					new_name = 'sub_boxfolder3')

		# rename files
		self.rename(path = os.path.join(self.path, 'boxfolder1/root_boxfile4.file'),
					new_name = 'sub_boxfile1.file')
		self.rename(path = os.path.join(self.path, 'boxfolder2/root_boxfile5.file'),
					new_name = 'sub_boxfile2.file')
		self.rename(path = os.path.join(self.path, 'boxfolder3/root_boxfile6.file'),
					new_name = 'sub_boxfile3.file')

	def cloud_operation4(self):
		pass
		'''self.refresh_token()
		# trash folders and files
		for i in range(1, 4):
			self.trash(os.path.join(self.path, 'boxfolder%s/sub_boxfolder%s' % (i, i)))
			self.trash(os.path.join(self.path, 'boxfolder%s/sub_boxfile%s.file' % (i, i)))
			self.trash(os.path.join(self.path, 'boxfolder%s' % i))
			self.trash(os.path.join(self.path, 'root_boxfile%s.file' % i))
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

	def  cloud_operation14(self):
		pass

# for self testing purpose
if __name__ == '__main__':
	a = BoxCloudOperation(path = '/QNAP/test')
	a.access_token = 'lkBjLXvdBiRL5In21vbRLeW4mD592FuN'
	a.headers = dict(Authorization='Bearer %s' % a.access_token)
	#a.cloud_init_operation()
	#a.cloud_operation1()	
	#a.cloud_operation2()
	#a.cloud_operation3()
	#a.cloud_operation4()
	pprint.pprint(a.get_content_list())
	