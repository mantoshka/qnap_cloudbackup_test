import os
import json
import sys
import time
import urllib2
import urllib
import shutil
import subprocess
import cipher
from urllib2 import HTTPError
from cc_util import generate_dir
from cc_util import generate_file
from cc_util import append_file
from cc_util import enum
from cc_util import CloudDrive
from requests import get
from requests import post
from requests import patch
from requests import delete
from requests import exceptions
from requests.packages import urllib3
import pprint
from bft_variables import *

GoogleDriveFileType = enum(Document = 1, Form = 2, Sheet = 3, 
							Drawing = 4, Slides = 5, Folder = 6)

class GoogleDriveCloudOperation:
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
		self.clouddrive = CloudDrive.GoogleDrive
		self.access_token = self.refresh_token()
		self.content_dict = dict()
		urllib3.disable_warnings()

	def get_googledrive_json(self, url=None):
		header = dict(Authorization='Bearer %s' % self.access_token) 
		r = get(url=url, headers=header, verify=False)
		return json.loads(r.text)

	def save_json(self, json_data=None, file_name=None):
		with open(file_name, 'w') as f:
			json.dump(json_data, f, indent=4)

	# create a list of IDs for all contents within a folder
	def list_googledrive_dir_content(self, id=None, page_token=None):
		header = dict(Authorization='Bearer %s' % self.access_token) 
		url = 'https://www.googleapis.com/drive/v2/files/%s/children' % id
		temp_list = list()
		temp_json = dict()
		if page_token != None:
			params = dict(pageToken=page_token)
			temp_json = json.loads(get(url=url, headers=header, params=params, verify=False).text)
		else:
			temp_json = json.loads(get(url=url, headers=header, verify=False).text)

		if temp_json.has_key('items'):
			for item in temp_json['items']:
				temp_list.append(item['id'])

		if temp_json.has_key('nextPageToken'):
			temp_list.append(self.list_googledrive_dir_content(id=id, page_token=temp_json['nextPageToken']))

		return temp_list

	def get_content_list(self, fid = None, current_path = None):
		content_dict = dict()
		if fid == None:
			fid = self.get_id(self.root_path)

		if current_path == None:
			current_path = self.root_path
		child_list = self.list_googledrive_dir_content(id=fid)
		# traverse all the child (folder & files) within the root path
		for child_id in child_list:
			temp_dict = dict()
			url = 'https://www.googleapis.com/drive/v2/files/%s' % child_id
			temp_json = self.get_googledrive_json(url = url)
			if temp_json['mimeType'] == 'application/vnd.google-apps.folder':
				temp_dict['is_file'] = False
				temp_dict['size'] = 0

				# if the child is a folder, then traverse again the folder's content
				content_dict.update(self.get_content_list(fid=child_id, 																								
															current_path = os.path.join(current_path, temp_json['title'])))
			else: 
				temp_dict['is_file'] = True
				if temp_json.has_key('fileSize'):
					temp_dict['size'] = int(temp_json['fileSize'])
				else:
					temp_dict['size'] = 0
			
			temp_dict['name'] = temp_json['title']
			temp_dict['full_path'] = os.path.join(current_path, temp_json['title'])
			temp_dict['relative_path'] = temp_dict['full_path'].replace(self.root_path, '')
			temp_dict['mtime'] = temp_json['modifiedDate']
			content_dict[temp_dict['relative_path']] = temp_dict

		return content_dict

	def get_content(self):
		fid = self.get_id(self.root_path)
		return self.get_googledrive_dir_content(fid = fid, current_path = self.root_path)

	def get_id(self, path = None):
		#print '\ntrying to get_id: %s' % path
		if self.content_dict.has_key(path):
			return self.content_dict[path]

		path_list = path.strip('/').split('/')
		root_id = None
		root_url = 'https://www.googleapis.com/drive/v2/files/root/children'
		root = self.get_googledrive_json(root_url)
		if root.has_key('items'):
			for item in root['items']:
				temp_json = self.get_googledrive_json(url = item['childLink'])
				if temp_json.has_key('labels'):
					if temp_json['labels']['trashed']: # skips the folder/file in the trash
						continue

				if temp_json['title'] == path_list[0]:
					root_id = temp_json['id']
					break							

		if root_id == None:
			return None

		# if path is root, then return the root id
		if len(path_list) == 1:
			#print 'id: %s' % root_id
			return root_id

		current_id = root_id
		for f in path_list[1:]:
			old_id = current_id
			child_url = 'https://www.googleapis.com/drive/v2/files/%s/children' % current_id
			child = self.get_googledrive_json(child_url)
			for item in child['items']:
				temp = self.get_googledrive_json(item['childLink'])
				if temp_json.has_key('labels'):
					if temp['labels']['trashed']: # skips the folder/file in the trash
						continue
				if temp['title'] == f:
					current_id = temp['id']
					break
			if current_id == old_id:
				return None

		#print 'id: %s' % current_id
		self.content_dict[path] = current_id
		return current_id

	def create_file_sub(self, url = None, header = None, data = None, retry_count = 5):
		try:
			response = post(url = url, headers = header, data = data, verify=False)	
			if response.status_code == 200:
				resp_json = json.loads(response.text)
				return resp_json['id']
			else:
				print 'failed to create file'
				response.raise_for_status()
		except:
			if retry_count != 0:
				sleep = (6 - retry_count) * 5
				print 'Error: %s \nbacking-off and retrying in %s seconds' % (sys.exc_info()[0], sleep)
				time.sleep(sleep)
				self.refresh_token()
				return self.create_file_sub(url = url, header = header, data = data, retry_count = retry_count - 1)

	def create_file(self, parent_folder_path = None, number = 1, ftype = GoogleDriveFileType.Document):
		if ftype == GoogleDriveFileType.Document:
			file_name = 'cloud_doc'
			mimeType = 'application/vnd.google-apps.document'
		elif ftype == GoogleDriveFileType.Form:
			file_name = 'cloud_form'
			mimeType = 'application/vnd.google-apps.form'
		elif ftype == GoogleDriveFileType.Sheet:
			file_name = 'cloud_sheet'
			mimeType = 'application/vnd.google-apps.spreadsheet'
		elif ftype == GoogleDriveFileType.Drawing:
			file_name = 'cloud_drawing'
			mimeType = 'application/vnd.google-apps.drawing'
		elif ftype == GoogleDriveFileType.Slides:
			file_name = 'cloud_slides'
			mimeType = 'application/vnd.google-apps.presentation'

		url = 'https://www.googleapis.com/drive/v2/files'
		header = dict(Authorization='Bearer %s' % self.access_token)
		header['Content-Type'] = 'application/json'
		parent_id = self.get_id(parent_folder_path)
		if parent_id == None:
			parent_id = self.create(full_path = parent_folder_path)
			 
		parents = list()
		parents.append(dict(id = parent_id))
		file_id_lst = list()
		for i in range(1, number + 1):
			title = '%s%s' % (file_name, i)
			#print 'creating: %s' % os.path.join(parent_folder_path, title)
			body = { 'title' : title, 'mimeType' : mimeType, 'parents' : parents }
			temp_id = self.create_file_sub(url = url, header = header, data = json.dumps(body))
			if temp_id != None:
				file_id_lst.append(temp_id)
			else:
				print 'failed to create: %s' % os.path.join(parent_folder_path, title)

		return file_id_lst

	def upload(self, fsource = None, ftarget = None):
		with open(fsource, 'r') as f:
			parent_id = self.get_id(ftarget)
			url = 'https://www.googleapis.com/upload/drive/v2/files?uploadType=media'
			header = dict(Authorization='Bearer %s' % self.access_token)
			post(url = url, headers = header, data = f.read(), verify = False)

	def create(self, full_path = None, ftype = GoogleDriveFileType.Folder):
		if ftype == GoogleDriveFileType.Folder:
			mimeType = 'application/vnd.google-apps.folder'
		elif ftype == GoogleDriveFileType.Document:
			mimeType = 'application/vnd.google-apps.document'
		elif ftype == GoogleDriveFileType.Form:
			mimeType = 'application/vnd.google-apps.form'
		elif ftype == GoogleDriveFileType.Sheet:
			mimeType = 'application/vnd.google-apps.spreadsheet'
		elif ftype == GoogleDriveFileType.Drawing:
			mimeType = 'application/vnd.google-apps.drawing'
		elif ftype == GoogleDriveFileType.Slides:
			mimeType = 'application/vnd.google-apps.presentation'
		
		path_list = full_path.strip('/').split('/')
		title = path_list[len(path_list) - 1]
		url = 'https://www.googleapis.com/drive/v2/files'
		header = dict(Authorization='Bearer %s' % self.access_token)
		header['Content-Type'] = 'application/json'
		if len(path_list) == 1: # create on root 
			body = { 'title' : title, 'mimeType' : mimeType }
		else:
			# creating the path if it doesn't exist
			parent_id = None
			for i in range(1, len(path_list)):
				temp_path = '/'.join(path_list[:i])
				fid = self.get_id(temp_path)
				if fid == None:
					self.create(temp_path, GoogleDriveFileType.Folder)
				if i == (len(path_list) - 1):
					parent_id = fid

			parent_id = self.get_id('/'.join(path_list[:len(path_list)-1]))
			parents = list()
			parents.append(dict(id = parent_id))
			body = { 'title' : title, 'mimeType' : mimeType, 'parents' : parents }
				
		response = post(url = url, headers = header, data = json.dumps(body), verify=False)
		if response.status_code == 200:
			resp_json = json.loads(response.text)
			return resp_json['id']
		else:
			print 'failed to create: %s' % full_path
			exit(1)

	def rename(self, full_path = None, new_name = None):
		fid = self.get_id(full_path)		
		if fid == None:
			print "Path does not exist!"
			return

		url = 'https://www.googleapis.com/drive/v2/files/%s' % fid
		header = dict(Authorization='Bearer %s' % self.access_token)
		header['Content-Type'] = 'application/json'
		body = { 'title' : new_name }
		patch(url = url, headers = header, data = json.dumps(body), verify=False)
		self.content_dict.pop(full_path)

	def remove(self, full_path = None, fid = None, trash=False):
		if fid == None:
			fid = self.get_id(full_path)			
			if fid == None:
				print "Path does not exist!"
				return

		header = dict(Authorization='Bearer %s' % self.access_token)
		if not(trash):
			url = 'https://www.googleapis.com/drive/v2/files/%s' % fid
			delete(url = url , headers = header, verify=False)
		else:
			url = 'https://www.googleapis.com/drive/v2/files/%s/trash' % fid
			post(url = url , headers = header, verify=False)

		self.content_dict.pop(full_path)

	def move(self, old_full_path = None, new_path = None):		
		fid = self.get_id(old_full_path)
		parent_fid_new = self.get_id(new_path)
		if fid == None or parent_fid_new == None:
			print "Path does not exist"
			return

		url = 'https://www.googleapis.com/drive/v2/files/%s' % fid
		temp = self.get_googledrive_json(url)
		self.save_json(temp, 'old_id')
		if temp.has_key('parents'):
			parent_fid_old = temp['parents'][0]['id']

		url = 'https://www.googleapis.com/drive/v2/files/%s?removeParents=%s&addParents=%s' % \
					(fid, parent_fid_old, parent_fid_new)
		header = dict(Authorization='Bearer %s' % self.access_token)
		patch(url = url, headers = header, verify = False)
		self.content_dict.pop(old_full_path)

	def cloud_init_operation(self):
		# delete cloud folder if it exists
		try:
			self.remove(self.root_path)
			self.create(self.root_path, GoogleDriveFileType.Folder)
			print 'successfully created new cloud folder: %s' % self.root_path
		except exceptions.SSLError as e:
			print e
		
	def cloud_operation1(self):
		# refresh token
		self.refresh_token()

		# create folders and files within the folder
		for i in range(1, 7):
			self.create(full_path = os.path.join(self.root_path, 'cloud%s' % i),
						ftype = GoogleDriveFileType.Folder)
			self.create(full_path = os.path.join(self.root_path, 'cloud%s/cloud_doc%s' % (i, i)),
						ftype = GoogleDriveFileType.Document)

		# create files
		self.create(full_path = os.path.join(self.root_path, 'cloud_sheet'),
					ftype = GoogleDriveFileType.Sheet)
		self.create(full_path = os.path.join(self.root_path, 'cloud_doc'),
					ftype = GoogleDriveFileType.Document)
		self.create(full_path = os.path.join(self.root_path, 'cloud_slides'),
					ftype = GoogleDriveFileType.Slides)
		self.create(full_path = os.path.join(self.root_path, 'cloud_form'),
					ftype = GoogleDriveFileType.Form)
		self.create(full_path = os.path.join(self.root_path, 'cloud_drawing'),
					ftype = GoogleDriveFileType.Drawing)

		# return operation identifier for report
		return 'cloud_create_result'

	def cloud_operation2(self):
		self.refresh_token()
		# rename folders
		self.rename(full_path = os.path.join(self.root_path, 'cloud4'), new_name = 'cloud4_renamed')
		self.rename(full_path = os.path.join(self.root_path, 'cloud5'), new_name = 'cloud5_renamed')
		self.rename(full_path = os.path.join(self.root_path, 'cloud6'), new_name = 'cloud6_renamed')

		# rename files
		self.rename(full_path = os.path.join(self.root_path, 'cloud_sheet'), new_name = 'cloud_sheet_renamed')
		self.rename(full_path = os.path.join(self.root_path, 'cloud_doc'), new_name = 'cloud_doc_renamed')
		self.rename(full_path = os.path.join(self.root_path, 'cloud_slides'), new_name = 'cloud_slides_renamed')
		self.rename(full_path = os.path.join(self.root_path, 'cloud_form'), new_name = 'cloud_form_renamed')
		self.rename(full_path = os.path.join(self.root_path, 'cloud_drawing'), new_name = 'cloud_drawing_renamed')

		# return operation identifier for report
		return 'cloud_rename_result'

	def cloud_operation3(self):
		self.refresh_token()
		# move some folders
		self.move(old_full_path = os.path.join(self.root_path, 'cloud4_renamed'), 
					new_path = os.path.join(self.root_path, 'cloud1'))
		self.move(old_full_path = os.path.join(self.root_path, 'cloud5_renamed'), 
					new_path = os.path.join(self.root_path, 'cloud2'))
		self.move(old_full_path = os.path.join(self.root_path, 'cloud6_renamed'), 
					new_path = os.path.join(self.root_path, 'cloud3'))

		# move some files
		self.move(old_full_path = os.path.join(self.root_path, 'cloud_sheet_renamed'), 
					new_path = os.path.join(self.root_path, 'cloud1'))
		self.move(old_full_path = os.path.join(self.root_path, 'cloud_doc_renamed'), 
					new_path = os.path.join(self.root_path, 'cloud2'))
		self.move(old_full_path = os.path.join(self.root_path, 'cloud_slides_renamed'), 
					new_path = os.path.join(self.root_path, 'cloud3'))

		# return operation identifier for report
		return 'cloud_move_result'

	def cloud_operation4(self):
		self.refresh_token()
		# delete some folders
		self.remove(full_path = os.path.join(self.root_path, 'cloud1/cloud4_renamed'))
		self.remove(full_path = os.path.join(self.root_path, 'cloud2/cloud5_renamed'))
		self.remove(full_path = os.path.join(self.root_path, 'cloud3/cloud6_renamed'))

		# delete some files
		self.remove(full_path = os.path.join(self.root_path, 'cloud1/cloud_sheet_renamed'))
		self.remove(full_path = os.path.join(self.root_path, 'cloud2/cloud_doc_renamed'))
		self.remove(full_path = os.path.join(self.root_path, 'cloud3/cloud_slides_renamed'))

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
		# generate 10,000 files
		self.refresh_token()
		self.file_id_lst = list()
		self.file_id_lst.append(self.create_file(parent_folder_path = os.path.join(self.root_path, 'cloud_10Kfiles/cloud_document/'),
						 number = 2000, ftype = GoogleDriveFileType.Document))
		self.file_id_lst.append(self.create_file(parent_folder_path = os.path.join(self.root_path, 'cloud_10Kfiles/cloud_sheet/'),
						 number = 2000, ftype = GoogleDriveFileType.Sheet))
		self.file_id_lst.append(self.create_file(parent_folder_path = os.path.join(self.root_path, 'cloud_10Kfiles/cloud_slides/'),
						 number = 2000, ftype = GoogleDriveFileType.Slides))
		self.file_id_lst.append(self.create_file(parent_folder_path = os.path.join(self.root_path, 'cloud_10Kfiles/cloud_form/'),
						 number = 2000, ftype = GoogleDriveFileType.Form))
		self.file_id_lst.append(self.create_file(parent_folder_path = os.path.join(self.root_path, 'cloud_10Kfiles/cloud_drawing/'),
						 number = 2000, ftype = GoogleDriveFileType.Drawing))

	def cloud_operation11(self):
		self.refresh_token()
		# remove 10,000 files created at operation5
		for fid in self.file_id_lst:
			self.remove(fid = fid)

	def cloud_operation12(self):
		pass

	def cloud_operation13(self):
		pass

	def cloud_operation14(self):
		# conflict case
		# create temp files to upload
		flist = generate_file(os.path.join(os.getcwd(), 'automation_tmp'),
								 5 * 1024, num=1, file_name='root_', file_type='.txt')

		'''
		# upload files to cloud
		for i in range(1, 6):
			self.upload(fsource = flist[0], ftarget = os.path.join(self.root_path, 'root%s.txt' % i))
			self.create_folder(folder_path = os.path.join(self.root_path, 'rootfolder%s' % i))
			self.upload(fsource = flist[0], ftarget = os.path.join(self.root_path, 'rootfolder%s/file%s1.txt' % (i, i)))
		'''


	def cloud_cleanup_operation(self):
		pass
		

if __name__ == '__main__':
	a = GoogleDriveCloudOperation(root_path = '/QNAP/test')
	a.access_token = 'ya29.WwKDN3uivAEBLzuxCTBVum47mI8uc3xqf3TKOam8HeJRwWXG5P3AXLJo3n1zexOKO_u4yA'
	#a.cloud_init_operation()
	#a.cloud_operation1()
	#a.cloud_operation2()
	#a.cloud_operation3()
	#a.cloud_operation4()
	pprint.pprint(a.get_content_list())




