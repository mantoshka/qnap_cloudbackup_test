import os
import time
import sys
import shutil
import string
from cc_util import *

class NasOperation:
	def __init__(self, local_path):
		self.path = local_path

	def is_hidden(self, path):
		for n in path.split('/'):
			if n.startswith('.'):
				return True

		return False

	def get_content_list(self, include_hidden = False):
		content = dict()
		for (root, folders, files) in os.walk(self.path):
			for folder in folders:
				if not(include_hidden) and folder.startswith('.'):
					continue

				temp_dict = dict()
				temp_dict['is_file'] = False
				temp_dict['name'] = folder
				temp_dict['full_path'] = os.path.join(root, folder)
				temp_dict['relative_path'] = temp_dict['full_path'][len(self.path):]
				temp_dict['size'] = 0
				temp_dict['mtime'] = 0
				content[temp_dict['relative_path']] = temp_dict

			for f in files:
				if not(include_hidden) and self.is_hidden(os.path.join(root, f)):
					continue

				temp_dict = dict()
				temp_dict['is_file'] = True
				temp_dict['name'] = f
				temp_dict['full_path'] = os.path.join(root, f)
				temp_dict['relative_path'] = temp_dict['full_path'][len(self.path):]
				temp_dict['size'] = os.lstat(temp_dict['full_path']).st_size
				temp_dict['mtime'] = os.lstat(temp_dict['full_path']).st_mtime
				content[temp_dict['relative_path']] = temp_dict


		#with open(filename,"w") as out_file:
		#	json.dump(content, out_file, indent=4)

		return content


	def local_init_test(self):
		# remove source folder if it already exists 
		if os.path.exists(self.path):
			shutil.rmtree(self.path)
			print 'cleaning up previous local folder'

		# generate new source folder
		generate_dir(self.path)
		print 'successfully created local source: %s' % self.path

	def local_operation1(self):
		# create some files on root path
		generate_file(self.path, 1024, num=6, file_name='root_localfile', file_type='.txt')

		# create some files inside sub-folders
		generate_file(os.path.join(self.path, 'localA'), 1024, file_name='localfileA', file_type='.txt')
		generate_file(os.path.join(self.path, 'localB'), 1024, file_name='localfileB', file_type='.txt')
		generate_file(os.path.join(self.path, 'localC'), 1024, file_name='localfileC', file_type='.txt')
		generate_file(os.path.join(self.path, 'localD'), 1024, file_name='localfileD', file_type='.txt')
		generate_file(os.path.join(self.path, 'localE'), 1024, file_name='localfileE', file_type='.txt')
		generate_file(os.path.join(self.path, 'localF'), 1024, file_name='localfileF', file_type='.txt')

		# generate file size 0 bytes
		generate_file(self.path, 0, num = 6, file_name = '0bytes_file', file_type = '.txt')

		# return operation identifier for report
		return 'local_create_result'

	def local_operation2(self):
		# rename some files
		rename_files = {'localD/localfileD1.txt' : 'localD/localfileD1_renamed.txt',
						'localE/localfileE1.txt' : 'localE/localfileE1_renamed.txt',
						'localF/localfileF1.txt' : 'localF/localfileF1_renamed.txt'}

		for ori_file in rename_files:			
			os.rename(os.path.join(self.path, ori_file), os.path.join(self.path, rename_files[ori_file]))
			time.sleep(7)

		# rename some folders
		rename_folders = {'localD' : 'localD_renamed',
						  'localE' : 'localE_renamed',
						  'localF' : 'localF_renamed'}
		for ori_folder in rename_folders:
			os.rename(os.path.join(self.path, ori_folder), os.path.join(self.path, rename_folders[ori_folder]))
			time.sleep(7)		

		# return operation identifier for report
		return 'local_rename_result'

	def local_operation3(self):
		# move some folder from root to sub-folder
		move_folder = {'localD_renamed' : 'localA',
						'localE_renamed' : 'localB',
						'localF_renamed' : 'localC'}
		for ori_folder in move_folder:
			shutil.move(os.path.join(self.path, ori_folder), os.path.join(self.path, move_folder[ori_folder]))
			time.sleep(7)

		# move some files from root to sub-folder
		move_files = {'root_localfile1.txt' : 'localA',
						'root_localfile2.txt' : 'localB',
						'root_localfile3.txt' : 'localC'}
		for ori_file in move_files:			
			shutil.move(os.path.join(self.path, ori_file), os.path.join(self.path, move_files[ori_file]))

		# move files out to other unmonitored folder
		move_files_out = {'root_localfile4.txt' : '/share/Public/temp_root',
							'root_localfile5.txt' : '/share/Public/temp_root',
							'root_localfile6.txt' : '/share/Public/temp_root'}
		generate_dir('/share/Public/temp_root')
		for ori_file in move_files_out:
			shutil.move(os.path.join(self.path, ori_file), move_files_out[ori_file])		
				
		# move folder in from other unmonitored folder
		generate_file('/share/Public/temp_root/temp_folder1', 1024, file_name='tempfile1', file_type='.txt')
		generate_file('/share/Public/temp_root/temp_folder2', 1024, file_name='tempfile2', file_type='.txt')
		generate_file('/share/Public/temp_root/temp_folder3', 1024, file_name='tempfile3', file_type='.txt')
		move_folders_in = {'/share/Public/temp_root/temp_folder1' : 'localA',
							'/share/Public/temp_root/temp_folder2' : 'localB',
							'/share/Public/temp_root/temp_folder3' : 'localC'}
		for ori_folder in move_folders_in:
			shutil.move(ori_folder, os.path.join(self.path, move_folders_in[ori_folder]))		

		# delete temporary root folder
		shutil.rmtree('/share/Public/temp_root')

		# return operation identifier for report
		return 'local_move_result'

	def local_operation4(self):
		# edit some files content
		append_file(os.path.join(self.path, 'root_localfile4.txt'))
		append_file(os.path.join(self.path, 'root_localfile5.txt'))
		append_file(os.path.join(self.path, 'root_localfile6.txt'))

		# return operation identifier for report
		return 'local_edit_result'

	def local_operation5(self):
		# delete some folders
		shutil.rmtree(os.path.join(self.path, 'localA/localD_renamed'))
		shutil.rmtree(os.path.join(self.path, 'localB/localE_renamed'))
		shutil.rmtree(os.path.join(self.path, 'localC/localF_renamed'))

		# delete some files
		os.remove(os.path.join(self.path, 'localA/root_localfile1.txt'))
		os.remove(os.path.join(self.path, 'localB/root_localfile2.txt'))
		os.remove(os.path.join(self.path, 'localC/root_localfile3.txt'))

		# return operation identifier for report
		return 'local_delete_result'

	def local_operation6(self):
		# generate 10 level of folder depth (folder with folder)
		generate_folder_depth(os.path.join(self.path, 'folder_depth'), 
								depth_num = 10,
								folder_num = 1,
								file_num = 1,
								file_size = 1024)		

	def local_operation7(self):
		# generate all types of files (documents, music, videos, pictures, etc...)
		for type_name in type_dict:
			for ftype in type_dict[type_name]:
				generate_file(os.path.join(self.path, 'file-type/'), num = 1, file_name = ftype[1:], file_type = ftype)

	def local_operation8(self):
		# generate folder and files with long names		
		fname_255 = '255_l%sng' % ('o' * 243)	# file name with 128 chars length (including extension .txt)
		generate_file(os.path.join(self.path, 'long-names/'), num = 1, file_name = fname_255, file_type = '.txt')

		generate_folder_depth(os.path.join(self.path, 'folder_depth'), 
								depth_num = 10,
								folder_num = 1,
								folder_name = fname_255,
								file_num = 1,
								file_size = 1024)		


	def local_operation9(self):
		parent_dir = os.path.join(self.path, 'non-multi-byte/')
		generate_dir(parent_dir)
		printable_char = string.printable.replace('/', '') # don't include '/' on the chars list
		fname = ''
		counter = 0
		for ch in printable_char:
			fname += ch
			counter += 1
			if counter == 10:
				generate_file(os.path.join(parent_dir, fname), file_name = fname + '_', file_type='.txt')
				fname = ''
				counter = 0

	def local_operation10(self):
		# generate folder and files with all multi-byte character names (0x80 ~ 0xffff)
		parent_dir = os.path.join(self.path, 'multi-byte/')
		generate_dir(parent_dir)
		fname = ''
		counter = 0
		# wiki link: https://en.wikipedia.org/wiki/Specials_(Unicode_block)
		# wiki link: https://en.wikipedia.org/wiki/Plane_(Unicode)
		skip_char_list = range(0x0860, 0x089F + 1)
		skip_char_list.extend(range(0x1C80, 0x1CBF + 1))
		skip_char_list.extend(range(0x2FE0, 0x2FEF + 1))
		skip_char_list.extend(range(0xD800, 0xF8FF + 1))
		skip_char_list.extend(range(0xFFF0, 0xFFF8 + 1))
		skip_char_list.extend(range(0xFFFE, 0xFFFF + 1))		
		for ch in range(0x80, sys.maxunicode + 1):	# generate multi-byte characters folder and file with 50 characters
			if ch in skip_char_list:	# skip the characters in the skip list
				continue
			fname += unichr(ch)
			counter += 1
			if counter == 50:
				generate_file(os.path.join(parent_dir, fname), file_name = fname + '_', file_type='.txt')
				fname = ''
				counter = 0

	def local_operation11(self):
		# generate 10,000 x 10 Bytes files
		generate_dir(os.path.join(self.path, 'local_10Kfiles'))
		for i in range(1, 11):
			generate_file(os.path.join(self.path, 'local_10Kfiles/1Kfiles_%s' % i), 
							file_size = 10,
							num = 1000,
							file_name='file%s_' % i,
							file_type='.txt',
							sleep_period=5)

	def local_operation12(self):
		# move 1,000 x 10 Bytes files to other sub-folders
		for i in range(1, 1001):
			shutil.move(os.path.join(self.path, 'local_10Kfiles/1Kfiles_6/file6_%s.txt' % i),
						 os.path.join(self.path, 'local_10Kfiles/1Kfiles_1'))
			shutil.move(os.path.join(self.path, 'local_10Kfiles/1Kfiles_7/file7_%s.txt' % i),
						 os.path.join(self.path, 'local_10Kfiles/1Kfiles_2'))
			shutil.move(os.path.join(self.path, 'local_10Kfiles/1Kfiles_8/file8_%s.txt' % i),
						 os.path.join(self.path, 'local_10Kfiles/1Kfiles_3'))
			shutil.move(os.path.join(self.path, 'local_10Kfiles/1Kfiles_9/file9_%s.txt' % i),
						 os.path.join(self.path, 'local_10Kfiles/1Kfiles_4'))
			shutil.move(os.path.join(self.path, 'local_10Kfiles/1Kfiles_10/file10_%s.txt' % i),
						 os.path.join(self.path, 'local_10Kfiles/1Kfiles_5'))

		# delete the empty folders
		shutil.rmtree(os.path.join(self.path, 'local_10Kfiles/1Kfiles_6'))
		shutil.rmtree(os.path.join(self.path, 'local_10Kfiles/1Kfiles_7'))
		shutil.rmtree(os.path.join(self.path, 'local_10Kfiles/1Kfiles_8'))
		shutil.rmtree(os.path.join(self.path, 'local_10Kfiles/1Kfiles_9'))
		shutil.rmtree(os.path.join(self.path, 'local_10Kfiles/1Kfiles_10'))

		# rename the target folders
		os.rename(os.path.join(self.path, 'local_10Kfiles/1Kfiles_1'), os.path.join(self.path, 'local_10Kfiles/2Kfiles_1'))
		os.rename(os.path.join(self.path, 'local_10Kfiles/1Kfiles_2'), os.path.join(self.path, 'local_10Kfiles/2Kfiles_2'))
		os.rename(os.path.join(self.path, 'local_10Kfiles/1Kfiles_3'), os.path.join(self.path, 'local_10Kfiles/2Kfiles_3'))
		os.rename(os.path.join(self.path, 'local_10Kfiles/1Kfiles_4'), os.path.join(self.path, 'local_10Kfiles/2Kfiles_4'))
		os.rename(os.path.join(self.path, 'local_10Kfiles/1Kfiles_5'), os.path.join(self.path, 'local_10Kfiles/2Kfiles_5'))		

	def local_operation13(self):
		# create large file
		flist = generate_file(os.path.join(self.path, 'big-files/'), file_size = 1 * 1024 * 1024 * 1024, num = 20, file_name = '1GB_file', file_type = '.mov')

		# sleep for 30 seconds to let job start synchronizing
		time.sleep(30)

		# delete the files while it's being uploaded
		for f in flist:
			os.remove(f)
			time.sleep(10)


	def local_operation14(self):
		# conflict case
		# create some files on root path
		generate_file(self.path, 1024, num=5, file_name='root', file_type='.txt')

		# create some files inside sub-folders
		generate_file(os.path.join(self.path, 'rootfolder1'), 1024, file_name='file1', file_type='.txt')
		generate_file(os.path.join(self.path, 'rootfolder2'), 1024, file_name='file2', file_type='.txt')
		generate_file(os.path.join(self.path, 'rootfolder3'), 1024, file_name='file3', file_type='.txt')
		generate_file(os.path.join(self.path, 'rootfolder4'), 1024, file_name='file4', file_type='.txt')
		generate_file(os.path.join(self.path, 'rootfolder5'), 1024, file_name='file5', file_type='.txt')

	def local_operation15(self):
		# generate 10 x 100 MB files
		generate_file(self.path, 100 * 1024 * 1024, num = 10, file_name = '100MB_', file_type = '.file')

	def local_operation16(self):
		# generate 100 x 10 MB files
		generate_file(self.path, 10 * 1024 * 1024, num = 100, file_name = '10MB_', file_type = '.file')

	def local_operation17(self):
		# generate 1,000 x 1 MB files
		generate_file(self.path, 1024 * 1024, num = 1000, file_name = '1MB_', file_type = '.file')


	def local_cleanup_operation(self):
		delete_folder_content(self.path)	



