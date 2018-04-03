#!/usr/bin/python
from dropbox_cloud_operation import DropboxCloudOperation
from googledrive_cloud_operation import *
from amazon_cloud_operation import AmazonCloudOperation
from onedrive_cloud_operation import OneDriveCloudOperation
from box_cloud_operation import BoxCloudOperation
from yandex_cloud_operation import YandexCloudOperation
from hubic_cloud_operation import HubicCloudOperation


class CloudOperation:
	def __init__:
		pass

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
		pass				

	def cloud_operation3(self):
		# move some folder from root to sub-folder
		cloud_dir = { 'cloudD' : 'cloudA/sub_cloudA', 'cloudE' : 'cloudB/sub_cloudB', 'cloudF' : 'cloudC/sub_cloudC'}
		for d in cloud_dir:
			self.move(from_path = os.path.join(self.root_path, d), to_path = os.path.join(self.root_path, cloud_dir[d]))

		# move some files from root to sub-folder
		cloud_files = { 'root_cloud_file_4.txt' : 'cloudA/root_cloud_file_4.txt',
						'root_cloud_file_5.txt' : 'cloudB/root_cloud_file_5.txt',
						'root_cloud_file_6.txt' : 'cloudC/root_cloud_file_6.txt' }
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