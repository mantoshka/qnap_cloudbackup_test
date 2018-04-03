import os
import sys
import time
import urllib2
import urllib
import shutil
import subprocess
import json
import cipher
from urllib2 import HTTPError
from cc_util import generate_dir
from cc_util import generate_file
from cc_util import append_file
from cc_util import CloudDrive
from requests import post
from requests import put
from requests import patch
from requests import get
from requests import delete
from requests.packages import urllib3
import pprint
from bft_variables import *

class DropboxCloudOperation:
	"""docstring for CloudOperation"""			
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
		return token['access_token']

	def __init__(self, account_id = None, root_path = None):
		self.account_id = account_id
		self.root_path = root_path
		self.clouddrive = CloudDrive.Dropbox
		urllib3.disable_warnings()
		self.refresh_token()

	def create_folder(self, folder_path = None, retry_count=5):
		try:
			dropbox_url = 'https://api.dropboxapi.com/1/fileops/create_folder?access_token=' + self.access_token + \
	 				'&root=auto&path=' + urllib.quote(folder_path, safe='')
			urllib2.urlopen(dropbox_url)
		except HTTPError:
			if retry_count != 0:
				sleep = (6 - retry_count) * 5
				print 'HTTPError: %s \nbacking-off and retrying in %s seconds' % (sys.exc_info()[0], sleep)
				time.sleep(sleep)
				self.create_folder(folder_path=folder_path, retry_count = retry_count - 1)

	def upload(self, fsource = None, ftarget = None, retry_count=5):	
		try:
			cmd = 'curl -k -H "Authorization: Bearer ' + self.access_token + '" https://content.dropboxapi.com/1/files_put/auto/' + \
						urllib.quote(ftarget, safe='') + '? -T ' + fsource
			subprocess.call(cmd, shell=True)
		except HTTPError:
			if retry_count != 0:
				sleep = (6 - retry_count) * 5
				print 'HTTPError: %s \nbacking-off and retrying in %s seconds' % (sys.exc_info()[0], sleep)
				time.sleep(sleep)
				self.upload(fsource=fsource, ftarget=ftarget, retry_count = retry_count - 1)

	def delete(self, fpath, retry_count = 5):
		try:
			dropbox_url = 'https://api.dropboxapi.com/1/fileops/delete?access_token=' + self.access_token + \
								'&root=auto&path=' + urllib.quote(fpath, safe='')
			urllib2.urlopen(dropbox_url)
		except HTTPError:
			if retry_count != 0:
				sleep = (6 - retry_count) * 5
				print 'HTTPError: %s \nbacking-off and retrying in %s seconds' % (sys.exc_info()[0], sleep)
				time.sleep(sleep)
				self.delete(fpath=fpath, retry_count = retry_count - 1)

	def copy(self, from_path = None, to_path = None):
		url = 'https://api.dropboxapi.com/1/fileops/copy?access_token={}' + \
				'&root=auto&from_path={}&to_path={}'.format(self.access_token,
															urllib.quote(from_path, safe=''),
															urllib.quote(to_path, safe=''))
		resp = post(url = url, verify = False)
		print resp.status_code

	def move(self, from_path = None, to_path = None, retry_count = 5):
		try:
			dropbox_url = 'https://api.dropboxapi.com/1/fileops/move?access_token=' + self.access_token + '&root=auto' + \
								'&from_path=' + urllib.quote(from_path, safe='') + \
								'&to_path=' + urllib.quote(to_path, safe='') 
			urllib2.urlopen(dropbox_url)
		except HTTPError:
			if retry_count != 0:
				sleep = (6 - retry_count) * 5
				print 'HTTPError: %s \nbacking-off and retrying in %s seconds' % (sys.exc_info()[0], sleep)
				time.sleep(sleep)
				self.move(from_path=from_path, to_path=to_path, retry_count = retry_count - 1)

	def get_dropbox_folder_content(self, path = None):
		dropbox_url = 'https://api.dropboxapi.com/1/metadata/auto/' + path + '?access_token=' + self.access_token + \
						'&file_limit=25000'
		return json.loads(urllib2.urlopen(dropbox_url).read())

	def get_content_list(self, path = None):
		content = dict()
		if path == None:
			path = self.root_path
		dropbox_json = self.get_dropbox_folder_content(path)		
		for f in dropbox_json['contents']:
			temp_dict = dict()
			if f['is_dir']:
				temp_dict['is_file'] = False
				temp_dict['size'] = 0
				temp_dict['mtime'] = 0

				# iterate folder contents
				content.update(self.get_content_list(f['path']))
			else:
				temp_dict['is_file'] = True
				temp_dict['size'] = f['bytes']
				temp_dict['mtime'] = f['modified']								
		
			temp_dict['name'] = os.path.basename(f['path'])
			temp_dict['full_path'] = os.path.join(self.root_path, f['path'])
			temp_dict['relative_path'] = f['path'].replace(self.root_path, '')
			content[temp_dict['relative_path']] = temp_dict

		return content

	def cloud_init_operation(self):
		# delete cloud folder if it already exists
		try:
			print 'cleaning up previous cloud folder'
			dropbox_url = 'https://api.dropboxapi.com/1/fileops/delete?root=auto&path=' + urllib.quote(self.root_path, safe='') + \
						'&access_token=' + self.access_token
			urllib2.urlopen(dropbox_url)
		except:	
			pass

		# create cloud destination folder
		print 'creating new cloud folder'
		dropbox_url = 'https://api.dropboxapi.com/1/fileops/create_folder?access_token=' + self.access_token + \
		 				'&root=auto&path=' + urllib.quote(self.root_path, safe='')
		dropbox_json = json.loads(urllib2.urlopen(dropbox_url).read())
		if dropbox_json['is_dir']:
			print 'successfully created dropbox cloud storage destination: %s' % self.root_path

	def cloud_operation1(self):
		# generate temp files to upload
		flist = generate_file(os.path.join(os.getcwd(), 'automation_tmp'), 1024, num=6, file_name='root_cloud_file_', file_type='.txt')

		# create some folder on root path and some files inside the folder
		cloud_dir = ['cloudA', 'cloudB', 'cloudC', 'cloudD', 'cloudE', 'cloudF']
		for d in cloud_dir:
			self.create_folder(os.path.join(self.root_path, d))
			self.upload(fsource = flist[0], ftarget = os.path.join(self.root_path, '%s/%s_file.txt' % (d, d)))
		
		# upload some files on root path
		count = 1;
		for f in flist:
			self.upload(fsource = f, ftarget = os.path.join(self.root_path, 'root_cloud_file_%s.txt' % count))
			count = count + 1

		# delete the temp files
		shutil.rmtree(os.path.join(os.getcwd(), 'automation_tmp'))

		# return operation identifier for report
		return 'cloud_create_result'

	def cloud_operation2(self):
		# simulating rename by copying to new file/folder and delete old file/folder
		cloud_dir = { 'cloudD' : 'cloudD_renamed', 'cloudE' : 'cloudE_renamed', 'cloudF' : 'cloudF_renamed' }
		cloud_files = { 'root_cloud_file_4.txt' : 'root_cloud_file_4_renamed.txt',
						'root_cloud_file_5.txt' : 'root_cloud_file_5_renamed.txt',
						'root_cloud_file_6.txt' : 'root_cloud_file_6_renamed.txt' }
		for d in cloud_dir:
			self.copy(from_path = os.path.join(self.root_path, d), to_path = os.path.join(self.root_path, cloud_dir[d]))			
			self.delete(os.path.join(self.root_path, d))

		for f in cloud_files:
			self.copy(from_path = os.path.join(self.root_path, f), to_path = os.path.join(self.root_path, cloud_files[f]))
			self.delete(os.path.join(self.root_path, f))

		# return operation identifier for report
		return 'cloud_rename_result'		

	def cloud_operation3(self):
		# move some folder from root to sub-folder
		cloud_dir = { 'cloudD_renamed' : 'cloudA/sub_cloudA',
					  'cloudE_renamed' : 'cloudB/sub_cloudB', 
					  'cloudF_renamed' : 'cloudC/sub_cloudC'}
		for d in cloud_dir:
			self.move(from_path = os.path.join(self.root_path, d), to_path = os.path.join(self.root_path, cloud_dir[d]))

		# move some files from root to sub-folder
		cloud_files = { 'root_cloud_file_4_renamed.txt' : 'cloudA/root_cloud_file_4_renamed.txt',
						'root_cloud_file_5_renamed.txt' : 'cloudB/root_cloud_file_5_renamed.txt',
						'root_cloud_file_6_renamed.txt' : 'cloudC/root_cloud_file_6_renamed.txt' }
		for f in cloud_files:
			self.move(from_path = os.path.join(self.root_path, f), to_path = os.path.join(self.root_path, cloud_files[f]))

		# return operation identifier for report
		return 'cloud_move_result'

	def cloud_operation4(self):
		# upload edited files (simulate editing files)
		flist = generate_file(os.path.join(os.getcwd(), 'automation_tmp'), 1024, num=3, file_name='root_cloud_file_', file_type='.txt')
		append_file(os.path.join(os.path.join(os.getcwd(), 'automation_tmp'), 'root_local_file_1.txt'))
		append_file(os.path.join(os.path.join(os.getcwd(), 'automation_tmp'), 'root_local_file_2.txt'))
		append_file(os.path.join(os.path.join(os.getcwd(), 'automation_tmp'), 'root_local_file_3.txt'))

		count = 1;
		for f in flist:
			self.upload(fsource = f, ftarget = os.path.join(self.root_path, 'root_cloud_file_%s.txt' % count))
			count = count + 1

		# delete the temp files
		shutil.rmtree(os.path.join(os.getcwd(), 'automation_tmp'))

		# return operation identifier for report
		return 'cloud_edit_result'

	def cloud_operation5(self):
		# delete some folders
		cloud_dir = ['cloudA/sub_cloudA', 'cloudB/sub_cloudB', 'cloudC/sub_cloudC']
		for d in cloud_dir:
			self.delete(os.path.join(self.root_path, d))

		# delete some files
		cloud_files = ['cloudA/root_cloud_file_4.txt', 'cloudB/root_cloud_file_5.txt', 'cloudC/root_cloud_file_6.txt' ]
		for f in cloud_files:
			self.delete(os.path.join(self.root_path, f))

		# return operation identifier for report
		return 'cloud_delete_result'

	def cloud_operation6(self):
		pass

	def cloud_operation7(self):
		pass

	def cloud_operation8(self):
		pass

	def cloud_operation9(self):
		pass

	def cloud_operation10(self):
		# generate 10,000 x 10 Bytes temporary files
		temp_dir = os.path.join(os.getcwd(), 'temp_files')
		flist = generate_file(temp_dir, file_size = 10, num = 10000, file_name='file_', file_type='.txt')

		# create the destination folder
		self.create_folder(os.path.join(self.root_path, 'cloud_10Kfiles'))

		# upload files to cloud folder
		count = 1;
		for f in flist:
			self.upload(fsource = f, ftarget = os.path.join(self.root_path, 'cloud_10Kfiles/cloud_file_%s.txt' % count))
			count = count + 1

		# delete temp files
		shutil.rmtree(temp_dir)

	def cloud_operation11(self):
		# create the destination folder
		self.create_folder(os.path.join(self.root_path, 'cloud_10Kfiles_2'))

		# move 10,000 x 10 Bytes files to other folder
		for i in range(1, 10001):
			self.move(from_path = os.path.join(self.root_path, 'cloud_10Kfiles/cloud_file_%s.txt' % i),
						 to_path = os.path.join(self.root_path, 'cloud_10Kfiles_2/cloud_file_%s.txt' % i))

	def cloud_operation12(self):
		# delete 10,000 x 10 Bytes files from cloud folder
		for i in range(1, 10001):
			self.delete(os.path.join(self.root_path, 'cloud_10Kfiles_2/cloud_file_%s.txt' % i))

	def cloud_operation13(self):
		pass

	def cloud_operation14(self):
		# conflict case
		# create temp files to upload
		flist = generate_file(os.path.join(os.getcwd(), 'automation_tmp'),
								 5 * 1024, num=1, file_name='root_', file_type='.txt')

		# upload files to cloud
		for i in range(1, 6):
			self.upload(fsource = flist[0], ftarget = os.path.join(self.root_path, 'root%s.txt' % i))
			self.create_folder(folder_path = os.path.join(self.root_path, 'rootfolder%s' % i))
			self.upload(fsource = flist[0], ftarget = os.path.join(self.root_path, 'rootfolder%s/file%s1.txt' % (i, i)))

	def cloud_cleanup_operation(self):
		dropbox_json = self.get_dropbox_folder_content(path = self.root_path)
		print dropbox_json
		for f in dropbox_json['contents']:
			print 'deleting %s' % os.path.join(f['root'], f['path'])
			self.delete(fpath = os.path.join(f['root'], f['path']))

		
if __name__ == '__main__':
	a = DropboxCloudOperation(root_path = '/QNAP/test')
	#a.cloud_init_operation()
	#a.cloud_operation1()
	pprint.pprint(a.get_content_list())



		
	

