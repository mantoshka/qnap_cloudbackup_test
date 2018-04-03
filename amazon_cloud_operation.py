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

class AmazonCloudOperation:
	def refresh_token(self):				
		# read the token from conf file
		conf_name = '/etc/config/cloudconnector/%s/cloudconnector.0.conf' % qpkg_name
		with open(conf_name) as fp:
			conf_json = json.load(fp)
		
		encrypted_token = urllib.unquote(conf_json['account_dict'][self.account_id]['auth']).decode('utf8')
		if qpkg_name == 'HybridCloudSync':
			key = 'g8nCsbKAT5jbSopITKhKlKlUJdTxD49w'
		else:
			key = 'P7U2RZrMwTGsS0fq5jKAR9KUuldpLD7k'		
		token = json.loads(cipher.decode(encrypted_token, key))
		self.access_token = token['access_token']
		self.headers = dict(Authorization='Bearer %s' % self.access_token)
		return token['access_token']

	def __init__(self, account_id = None, path = None):
		self.content_dict = dict()	# path <-> id pairs
		self.path = path
		self.rooturl = 'https://drive.amazonaws.com/drive/v1'
		self.account_id = account_id
		self.clouddrive = CloudDrive.AmazonCloudDrive
		self.refresh_token()
		urllib3.disable_warnings()

	def get_root_id(self):
		url = 'https://drive.amazonaws.com/drive/v1/nodes?filters=kind:FOLDER AND isRoot:true'
		resp = get(url = url, headers = self.headers)
		json_data = json.loads(resp.text)	
		self.content_dict[''] = json_data['data'][0]['id']	# save root id
		return json_data['data'][0]['id']

	def get_id(self, path = None):
		# check first if path is already mapped in path <-> id dictionary
		if not path.startswith('/'):
			path = '/%s' % path
		if self.content_dict.has_key(path):
			#print 'match id found!'
			return self.content_dict[path]

		path_list = path.strip('/').split('/')
		url = 'https://drive.amazonaws.com/drive/v1/nodes/%s/children?filters=name:%s AND kind:FOLDER' % (self.get_root_id(), path_list[0])
		resp = get(url = url, headers = self.headers)
		json_data = json.loads(resp.text)
		fid = None
		if json_data['count'] != 0:
			fid = json_data['data'][0]['id']
			self.content_dict['/%s' % path_list[0]] = fid
		
		if len(path_list) == 1 or fid == None:
			return fid
		
		temp_path = '/%s' % path_list[0]
		for p in path_list[1:]:
			temp_path = os.path.join(temp_path, p)
			if self.content_dict.has_key(temp_path):
				fid = self.content_dict[temp_path]
			else:
				url = 'https://drive.amazonaws.com/drive/v1/nodes/%s/children?filters=name:%s' % (fid, p)
				resp = get(url = url, headers = self.headers)
				print resp.raise_for_status()
				json_data = resp.json()
				if json_data['count'] == 0:
					return None
				else:
					fid = json_data['data'][0]['id']			
					self.content_dict[temp_path] = fid

		return fid	

	def upload(self, fsource = None, ftarget = None, name = None, retry_count = 5):
		with open(fsource, 'rb') as f:	
			if name == None:	# if no given name, then use file source name
				name = ftarget.strip('/').split('/').pop()
			target_id = self.get_id(ftarget)
			if target_id == None:
				target_id = self.create_path(ftarget)
			url = 'https://content-na.drive.amazonaws.com/cdproxy/nodes?suppress=deduplication'
			_metadata = { 'name' : name, 'kind' : 'FILE', 'parents' : [target_id] }
			files = [('metadata', ('', json.dumps(_metadata), 'application/json')),
					 ('content', (fsource, f.read(), 'FILE'))] 
			resp = post(url = url, headers = self.headers, files = files, verify = False)			
			if resp.status_code == 201:
				json_data = json.loads(resp.text)
				self.content_dict['/%s/%s' % (ftarget, name)] = json_data['id']
			else:
				if retry_count == 0:
					print 'failed to upload: %s' % fsource

				print 'Error: backing-off and retrying in 10 seconds'
				time.sleep(10)
				self.refresh_token()				
				self.upload(fsource = fsource, ftarget = ftarget, name = name, retry_count = retry_count - 1)

	def upload_bulk_sub(self, files = None, target_full_path = None, retry_count = 5):
		try:
			url = 'https://content-na.drive.amazonaws.com/cdproxy/nodes?suppress=deduplication'
			resp = post(url = url, headers = self.headers, files = files, verify = False)			
			if resp.status_code != 201:
				if resp.status_code == 409:
					print 'file exists!'
					return None
				else:
					resp.raise_for_status()
			else:
				self.content_dict[target_full_path] = resp.json()['id']
		except:
			if retry_count == 0:
				print 'failed to upload file'
				return None

			print 'Error: backing-off and retrying in 10 seconds'			
			time.sleep(10)
			self.refresh_token()
			self.upload_bulk_sub(url = url, files = files, target_full_path = target_full_path,
									retry_count = retry_count - 1)	

	def upload_bulk(self, fsource = None, ftarget = None, number_of_files = 1):
		f = open(fsource, 'rb')
		name = fsource.strip('/').split('/').pop()
		name_list = name.split('.')
		name = name_list[0]
		ext = name_list[1]
		target_id = self.get_id(ftarget)
		if target_id == None:
			#print 'target_id not found'
			target_id = self.create_path(ftarget)

		#print 'target path: %s' % ftarget
		for i in range(1, number_of_files + 1):			
			target_name = '%s_%s.%s' % (name, i, ext)
			_metadata = { 'name' : target_name, 'kind' : 'FILE', 'parents' : [target_id] }
			files = [('metadata', ('', json.dumps(_metadata), 'application/json')),
					 ('content', (fsource, f.read(), 'FILE'))]
			#print 'target_id: %s' % target_id
			print 'uploading...%s' % target_name
			target_full_path = os.path.join(ftarget, target_name)
			#print 'target_full_path: %s' % target_full_path
			self.upload_bulk_sub(files = files, target_full_path = target_full_path)
			f.seek(0)

		f.close()


	def create_folder(self, folder_name = None, parent_id = None):
		_metadata = { 'name' : folder_name, 'kind' : 'FOLDER' }
		if parent_id != None:
			_metadata['parents'] = [parent_id]
		#print 'metadata: %s' % _metadata
		url = 'https://drive.amazonaws.com/drive/v1/nodes?'
		resp = post(url = url, headers = self.headers, data = json.dumps(_metadata))
		if resp.status_code == 201:
			json_data = resp.json()
			return json_data['id']
		else:
			print 'failed to create folder: %s' % folder_name
			return None


	def create_path(self, path = None):
		path_list = path.strip('/').split('/')
		pid = self.get_id(path_list[0])
		print '%s : %s' % (path_list[0], pid)
		if pid == None:
			print 'creating... %s' % path_list[0]
			pid = self.create_folder(folder_name = path_list[0])
			self.content_dict['/%s' % path_list[0]] = pid

		if len(path_list) > 1:
			parent_id = pid
			for i in range(2, len(path_list) + 1):
				temp_path = '/'.join(path_list[:i])
				pid = self.get_id(path = temp_path)
				print '%s : %s' % (temp_path, pid)
				if pid == None:
					print 'creating...%s' % temp_path
					pid = self.create_folder(folder_name = path_list[i-1], parent_id = parent_id)
					self.content_dict['/%s' % temp_path] = pid

				parent_id = pid

		return pid

	def trash(self, path = None):
		print 'trashing: %s' % path
		fid = self.get_id(path = path)
		if fid == None:
			print 'path not found: %s' % path
			return
		url = 'https://drive.amazonaws.com/drive/v1/trash/%s?' % fid
		resp = put(url = url, headers = self.headers)
		#print resp.status_code
		if resp.status_code == 200:
			print 'successfully moved to trash: %s' % path
			self.content_dict.pop(path)

	def rename(self, path = None, new_name = None):
		fid = self.get_id(path)
		path_list = path.strip('/').split('/')
		path_list.pop()
		parent_folder = '/'.join(path_list)
		parent_id = self.get_id(path = '/'.join(path_list))
		path_list.append(new_name)
		new_path = '/' + '/'.join(path_list)
		_metadata = { 'name' : new_name, 'parents' : [parent_id] }
		print 'renaming...%s' % path
		#print '%s : %s' % (parent_folder, parent_id)
		url = 'https://drive.amazonaws.com/drive/v1/nodes/%s' % fid
		resp = patch(url = url, headers = self.headers, data = json.dumps(_metadata))
		#print resp.status_code
		if resp.status_code == 200:
			self.content_dict[new_path] = resp.json()['id']
			self.content_dict.pop(path)

	def move(self, old_path = None, new_path = None):		
		child_id = self.get_id(old_path)
		path_list = old_path.strip('/').split('/')
		name = path_list.pop()
		old_parent_id = self.get_id('/'.join(path_list))
		new_parent_id = self.get_id(new_path)
		_metadata = { 'fromParent' : old_parent_id, 'childId' : child_id }
		url = 'https://drive.amazonaws.com/drive/v1/nodes/%s/children?' % new_parent_id
		resp = post(url = url, headers = self.headers, data = json.dumps(_metadata))
		if resp.status_code == 200:
			self.content_dict[os.path.join(new_path, name)] = resp.json()['id']
			self.content_dict.pop(old_path)

	def get_content_list(self, path = None):
		if path == None:
			path = self.path
		content = dict()
		url = self.rooturl + '/nodes/%s/children' % self.get_id(path)
		resp = get(url = url, headers = self.headers, verify = False)
		if resp.status_code == 200:
			content_json = resp.json()			
			for item in content_json['data']:								
				temp_dict = dict()				
				if item['kind'] == 'FOLDER':
					temp_dict['is_file'] = False
					temp_dict['size'] = 0
					content.update(self.get_content_list(path = os.path.join(path, item['name'])))
				else:
					temp_dict['is_file'] = True
					temp_dict['size'] = item['contentProperties']['size']

				temp_dict['full_path'] = os.path.join(path, item['name'])
				temp_dict['relative_path'] = temp_dict['full_path'].replace(self.path, '')
				temp_dict['name'] = item['name']
				temp_dict['mtime'] = item['modifiedDate']
				content[temp_dict['relative_path']] = temp_dict

			return content



	def cloud_init_operation(self):
		# trash path folder if exists
		self.trash(self.path)

		# create path folder
		self.create_path(self.path)

	def cloud_operation1(self):
		self.refresh_token()
		parent_id = self.get_id(self.path)
		flist = generate_file(os.path.join(os.getcwd(), 'automation_tmp'),
								 10 * 1024, num=1, file_name='temp_file', file_type='.txt')
		source = flist[0]

		num = 6
		for i in range(1, num + 1):
			# create folders on root on upload files within it
			self.create_folder(folder_name = 'amazonfolder%s' % i, parent_id = parent_id)
			self.upload(fsource = source, ftarget = os.path.join(self.path, 'amazonfolder%s' % i), 
							name = 'amazonfile%s.txt' % i)

			# upload files on root path
			self.upload(fsource = source, ftarget = self.path, name = 'root_amazonfile%s.txt' % i)

	def cloud_operation2(self):
		self.refresh_token()
		# move folder from root to folder
		self.move(old_path = os.path.join(self.path, 'amazonfolder4'),
					new_path = os.path.join(self.path, 'amazonfolder1'))
		self.move(old_path = os.path.join(self.path, 'amazonfolder5'),
					new_path = os.path.join(self.path, 'amazonfolder2'))
		self.move(old_path = os.path.join(self.path, 'amazonfolder6'),
					new_path = os.path.join(self.path, 'amazonfolder3'))

		# move files from root to folder
		self.move(old_path = os.path.join(self.path, 'root_amazonfile4.txt'), 
					new_path = os.path.join(self.path, 'amazonfolder1'))
		self.move(old_path = os.path.join(self.path, 'root_amazonfile5.txt'), 
					new_path = os.path.join(self.path, 'amazonfolder2'))
		self.move(old_path = os.path.join(self.path, 'root_amazonfile6.txt'), 
					new_path = os.path.join(self.path, 'amazonfolder3'))

	def cloud_operation3(self):
		self.refresh_token()
		# rename folders	
		self.rename(path = os.path.join(self.path, 'amazonfolder1/amazonfolder4'),
					new_name = 'sub_amazonfolder1')
		self.rename(path = os.path.join(self.path, 'amazonfolder2/amazonfolder5'),
					new_name = 'sub_amazonfolder2')
		self.rename(path = os.path.join(self.path, 'amazonfolder3/amazonfolder6'),
					new_name = 'sub_amazonfolder3')

		# rename files
		self.rename(path = os.path.join(self.path, 'amazonfolder1/root_amazonfile4.txt'),
					new_name = 'sub_amazonfile1.txt')
		self.rename(path = os.path.join(self.path, 'amazonfolder2/root_amazonfile5.txt'),
					new_name = 'sub_amazonfile2.txt')
		self.rename(path = os.path.join(self.path, 'amazonfolder3/root_amazonfile6.txt'),
					new_name = 'sub_amazonfile3.txt')

	def cloud_operation4(self):
		self.refresh_token()
		# trash folders and files
		for i in range(1, 4):
			self.trash(os.path.join(self.path, 'amazonfolder%s/sub_amazonfolder%s' % (i, i)))
			self.trash(os.path.join(self.path, 'amazonfolder%s/sub_amazonfile%s.txt' % (i, i)))
			self.trash(os.path.join(self.path, 'amazonfolder%s' % i))
			self.trash(os.path.join(self.path, 'root_amazonfile%s.txt' % i))

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
	a = AmazonCloudOperation(path = '/QNAP/test')
	a.access_token = 'Atza|IQEBLjAsAhRHqekzQ9JkjX5DqOpPCsynawG_ewIUdEnGSpbhiQgA-IQUYXkOJzDsrTxRbPrFjcW5wMdfJfBRJGUjhj8_8923gYu5T_Xpeai8-kPPGzTpjVjT9tYLlXKp4aYBy5LsB3UrmMalACuG2Mgx0BKVzqNI6IVWILirzFoeA_QiVVxkLAOQEXxiWukILQBb2sRc_YcEZ52AVdijzLxRbQjS0Ewkd2crfj8n-cJu7OvfWnYS3SIXkuFocuDCwHJSpKrGXcQD9ClVnrSje961PLShVAcUrwN28ZYM4PjpEMXYDZi1wqSQ5HVAX3TC9HyuaMhaLfazxV3d82GbWrntSl7RSrC7MPF_PlYZUMRnV41Z8s1aSbFFdjdfIQ7cGBkFg0p9RVswsQfUKcm-7rceyRV_k3sJnImGlang1D6GG2jmbMGb4oVAiPVi6krCCe1a9S3KzuYkVyI9Gmp3Gv61k4skOlcQxEw8KX5ewHddpuQ9QWw63I9mpDlrmdWUgqgQ'
	a.headers = dict(Authorization='Bearer %s' % a.access_token)
	a.cloud_init_operation()
	a.cloud_operation1()
	#a.cloud_operation2()
	#a.cloud_operation3()
	#a.cloud_operation4()
	pprint.pprint(a.get_content_list())
	