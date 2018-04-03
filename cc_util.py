# -*- coding: utf-8 -*-
import sys
reload(sys)  
sys.setdefaultencoding('utf8')

import os
import time
import datetime
import urllib
import urllib2
import random

import socket
import fcntl
import struct

import shutil
import json

import subprocess
import ConfigParser

import hashlib

import pprint

doc_type = ['.doc', '.xls', '.pdf', '.docx', '.xlsx', '.txt', '.ppt', '.pptx', '.html', '.htm']
pic_type = ['.jpg', '.bmp', '.tif', '.pbm', '.png', '.tga', '.xar', '.xbm']
vid_type = ['.avi', '.mpg', '.mp4', '.mkv', '.fli', '.flv', '.rm', '.ram']	
app_type = ['.exe', '.com', '.bat', '.bin', '.o', '.sh']
music_type = ['.mp3', '.wav', '.wma', '.aac', '.dss', '.msv', '.dvf', '.m4p', '.3gp', '.amr', '.awb']
temp_type = ['.tmp', '.cache', '.ci', '.crc', '.tmt', '.~', '.xx']
type_dict = {'document' : doc_type, 'picture' : pic_type, 'video' : vid_type, 'application' : app_type,
				 'music' : music_type, 'temp' : temp_type}

connector_class_name_dict = {'dropbox' : 'DropboxConnector',
							 'googledrive' : 'GoogleDriveConnector',
							 'amazon' : 'AmazonCloudDriveConnector',
							 'onedrive' : 'OneDriveConnector',
							 'box' : 'BoxConnector',
							 'yandex' : 'YandexDiskConnector',
							 'hubic' : 'HubicConnector',
							 'hidrive' : 'HiDriveConnector'
							}

class Logger(object):
    def __init__(self, working_dir):
        self.terminal = sys.stdout
        print 'log: %s' % os.path.join(working_dir, 'cc.log')
        self.log = open(os.path.join(working_dir, 'cc.log'), 'w')

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message) 


def enum(**enums):
    return type('Enum', (), enums)

CloudDrive = enum(Dropbox = 'Dropbox', GoogleDrive = 'GoogleDrive', AmazonCloudDrive = 'AmazonCloudDrive',
				  OneDrive = 'OneDrive', Box = 'Box', Yandex = 'Yandex', HiDrive = 'HiDrive',
				  Hubic = 'Hubic')

BFT = enum(simple = 'simple', long = 'long', advance = 'advance', filter = 'filter', conflict = 'conflict')

def load_qpkg_conf():
    """
    @return: list of installed QPKG()
    """
    fp = open('/etc/config/qpkg.conf')
    parser = ConfigParser.ConfigParser()
    parser.readfp(fp)
    
    fp.close()
	
    qpkg_dict = dict()
    for qpkg_name in parser.sections():
		try:
			qpkg_dict[qpkg_name] = { 'name' : parser.get(qpkg_name, 'Name'),
									 'version' : parser.get(qpkg_name, 'Version'),
									 'install_path' : parser.get(qpkg_name, 'Install_Path') }							 
		except:
			pass
			        
    return qpkg_dict

def get_install_path(qpkg_name):
	# check if qpkg is installed
	qpkg_dict = load_qpkg_conf()
	if not qpkg_dict.has_key(qpkg_name):
		print '%s is not installed!' % qpkg_name
		exit(1)
			
	# get install path of qpkg
	return qpkg_dict[qpkg_name]['install_path']

def enable_detail_log(qpkg_name = None):
	f = '{}/conf/cloudconnector.conf'.format(get_install_path(qpkg_name))
	old = '"detail_log": false,'
	new = '"detail_log": true,'

	lines = []
	with open(f) as infile:
	    for line in infile:
	        line = line.replace(old, new)
	        lines.append(line)
	with open(f, 'w') as outfile:
	    for line in lines:
	        outfile.write(line)


def change_debug_log_size(qpkg_name = None, new_size = 30000000, number_of_files = 1):
	f = '%s/conf/cc-log.conf' % get_install_path(qpkg_name)
	old = "args=('$BASE$/log/$USER_ID$/$JOB_ID$/cloudconnector-debug.log', 'a', 1500000, 1, '^(qnap.*)|(cc)$')"
	new = "args=('$BASE$/log/$USER_ID$/$JOB_ID$/cloudconnector-debug.log', 'a', %s, %s, '^(qnap.*)|(cc)$')" % (new_size, number_of_files)

	lines = []
	with open(f) as infile:
	    for line in infile:
	        line = line.replace(old, new)
	        lines.append(line)
	with open(f, 'w') as outfile:
	    for line in lines:
	        outfile.write(line)

def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])

def get_account_id(ip_address = None, qpkg_name = None, nas_sid=None, connector_class_name = None):
	cgi_cmd = 'http://' + ip_address + \
				':8080/cgi-bin/qpkg/' + qpkg_name + \
				'/cloudconnector.cgi?sid=' + nas_sid + \
				'&cmd=list_accounts'

	account_json = json.loads(urllib2.urlopen(cgi_cmd).read())
	for acc in account_json['result']['list']:
		if acc['connector_class_name'] == connector_class_name:
			return acc['id']

	print 'Error: %s account is not found' % connector_class_name
	exit(1)

def get_email_recipients():
	with open(os.getcwd() + '/full_automation.conf', 'rb') as f:
		automation_conf = json.load(f)

	return automation_conf["report_recipient"]

def get_free_job_id(ip_address=None, qpkg_name=None, nas_sid=None):
	cgi_cmd = 'http://' + ip_address + \
				':8080/cgi-bin/qpkg/' + qpkg_name + \
				'/cloudconnector.cgi?sid=' + nas_sid + \
				'&cmd=list_jobs&job_type=sync'

	job_json = json.loads(urllib2.urlopen(cgi_cmd).read())
	if job_json['result']['remaining'] == 0:
		print 'Number of job exceeds limitation of 20 jobs!'
		exit(1)

	# get the biggest job id which is already used
	max_job_id = 0
	for job in job_json['result']['list']:
		if int(job['id']) > max_job_id:
			max_job_id = int(job['id'])

	return str(max_job_id + 1)

def get_testing_env_info(qpkg_name = None):
	env_info_dict = dict()
	
	fp = open('/etc/config/qpkg.conf')
	parser = ConfigParser.ConfigParser()
	parser.readfp(fp)    
	fp.close()

	env_info_dict['qpkg_name'] = qpkg_name
	env_info_dict['qpkg_version'] = parser.get(qpkg_name, 'Version')

	fp = open('/etc/config/uLinux.conf')
	parser = ConfigParser.ConfigParser()
	parser.readfp(fp)    
	fp.close()

	try:
		env_info_dict['ip_address'] = get_ip_address('eth0')
	except IOError:
		env_info_dict['ip_address'] = get_ip_address('eth1')

	env_info_dict['server_name'] = parser.get('System', 'Server Name')
	env_info_dict['server_model'] = parser.get('System', 'Internal Model')
	env_info_dict['qts_version'] = '{} ({})'.format(parser.get('System', 'Version'),
														parser.get('System', 'Build Number'))
	return env_info_dict

# get file MD5 hash
def get_md5(full_path = None):
	if full_path != None:
		with open(full_path, 'rb') as f:
			return hashlib.md5(f.read()).hexdigest()

# compare if two files are the same
def is_same_file(file1 = None, file2 = None):
	if file1 != None and file2 != None:
		file1_md5 = get_md5(file1)
		file2_md5 = get_md5(file2)
		return (file1_md5 == file2_md5)

def generate_dir(*directory_name):
	for directory in directory_name:
		if directory[len(directory)-1] != '/':
			directory += '/'

		if not os.path.exists(directory):
			os.makedirs(directory)	

def generate_file(directory_name, file_size = 1024, num = 1, file_name = 'file', file_type = '.file', file_mtime=None, sleep_period = 0):
	if directory_name[len(directory_name)-1] != '/':
		directory_name += '/'
		
	generate_dir(directory_name)
		 
	file_list = list()	 
	for i in range(1, num + 1):
		fname = directory_name + file_name + str(i) + file_type
		f = open(fname, "wb")
		block = 1024				# 1 KB
		char = '0123456789abcdefghijklmnopqrstuvwxyz'
		for i in range(file_size//block):
			f.write(random.choice(char) * block)
		
		remainder = file_size % block
		f.write(random.choice(char) * remainder)
		f.close()
		file_list.append(fname)
		time.sleep(sleep_period)

	if file_mtime != None:
		t0 = datetime.datetime(1970,1,1)
		tdelta = (file_mtime - t0).total_seconds()
		for i in range(1, num + 1):
			os.utime(fname, (0, tdelta))

	return file_list

def generate_folder(directory_name, num = 1, file_num = 1, file_size = 1024):
	generate_dir(directory_name)
	
	for i in range(1, num + 1):
		generate_file(directory_name + "/folder_" + str(i), file_size, file_num) 

def generate_folder_depth(directory_name, depth_num = 1, folder_num = 0, folder_name = 'folder',file_num = 1, file_size = 1024, sleep_period = 0):
	generate_dir(directory_name)
	
	dir_name = directory_name
	generate_folder(dir_name, folder_num, file_num, file_size)
	generate_file(dir_name, file_size, sleep_period = 7)
	for i in range(1, depth_num):
		dir_name = dir_name + '/' + folder_name + str(i+1)
		generate_dir(dir_name)
		generate_file(dir_name, file_size, sleep_period = 7)
		generate_folder(dir_name, folder_num, file_num, file_size)

def delete_folder_content(directory_name):
	for (root, folders, files) in os.walk(directory_name):
		for f in folders:
			delete_folder_content(os.path.join(root, f))
			shutil.rmtree(os.path.join(root, f))

		for f in files:
			os.remove(os.path.join(root, f))	


def append_file(file_name, content='this file has been edited'):
	with open(file_name, 'a') as f:
		f.write(content)

def create_job(nas_sid, qpkg_name, src, dst, account_id='1', job_name='', ip_address='',
				start_immediately = False, conflict_policy = 'rename_src', filesizemin = '', filesizemax = '',
				filedatefrom = '', filedateto = '', schedule_type = 'continuous'):
	cgi_cmd = 'http://' + ip_address + ':8080/cgi-bin/qpkg/' + qpkg_name + '/cloudconnector.cgi?' + \
				'sid=' + nas_sid + '&src_account_id=&direction=2way&' + \
				'dst_account_id=' + account_id + \
				'&sync_src_paths=' + urllib.quote(src, safe='') + \
				'&sync_dst_paths=' + urllib.quote(dst, safe='') + \
				'&schedule_type=' + schedule_type + \
				'&schedule_immediate=' + ('true' if start_immediately else 'false') + '&is_encrypt=false' + \
				'&is_compress=false&conflict_policy=' + conflict_policy + \
				'&limit_file_size_min=' + urllib.quote(filesizemin, safe='') + \
				'&limit_file_size_max=' + urllib.quote(filesizemax, safe='') + \
				'&limit_file_date_from=' + urllib.quote(filedatefrom, safe='') + \
				'&limit_file_date_to=' + urllib.quote(filedateto, safe='') + \
				'&limit_file_type_action=&limit_file_type_filter=&limit_file_type_filter_others=&' + \
				'is_ignore_symbolic_links=true&is_include_hidden_files_folders=false&display_name=' + job_name + \
				'&timeout_in_second=60&maximum_retries=5&retry_interval_in_second=180&maximum_skipped_files=10&' + \
				'maximum_rate=&concurrent_connections=5&cmd=add_job&job_type=sync'
	urllib2.urlopen(cgi_cmd)

def start_job(ip_address = None, qpkg_name = None, nas_sid = None, job_id = None):
	cgi_cmd = 'http://' + ip_address + ':8080/cgi-bin/qpkg/' + qpkg_name + '/cloudconnector.cgi?' + \
				'sid=' + nas_sid + '&cmd=start_job&job_type=sync&id=' + job_id
	urllib2.urlopen(cgi_cmd)

def stop_job(ip_address = None, qpkg_name = None, nas_sid = None, job_id = None):
	# stop the job
	cgi_cmd = 'http://' + ip_address + ':8080/cgi-bin/qpkg/' + qpkg_name + '/cloudconnector.cgi?sid=' + nas_sid + \
					'&cmd=stop_job&job_type=sync&id=' + job_id
	urllib2.urlopen(cgi_cmd)

def modify_job_conflictpolicy(ip_address = None, qpkg_name = None, nas_sid = None, job_id = None, 
								src = None, dst = None, conflict_policy = None):
	cgi_cmd = 'http://%s:8080/cgi-bin/qpkg/%s/cloudconnector.cgi?sid=%s&id=%s&display_name=dropboxbft_conflict_3&' + \
				'is_enabled=true&schedule_type=continuous&schedule_immediate=false&src_account_id=&direction=2way&' + \
				'sync_src_paths=%s&sync_dst_paths=%s&is_encrypt=false&is_compress=false&conflict_policy=%s&' + \
				'limit_file_size_min=&limit_file_size_max=&limit_file_date_from=&limit_file_date_to=&' + \
				'limit_file_type_action=&limit_file_type_filter=&limit_file_type_filter_others=&' + \
				'is_ignore_symbolic_links=true&is_include_hidden_files_folders=false&timeout_in_second=60&' + \
				'maximum_retries=5&retry_interval_in_second=180&maximum_skipped_files=10&maximum_rate=&' + \
				'concurrent_connections=5&cmd=modify_job&' + \
				'job_type=sync' % (ip_address, qpkg_name, nas_sid, job_id, src, dst, conflict_policy)
	urllib2.urlopen(cgi_cmd)	

def get_file_ext(fname = None):
	f = fname.split('.')
	return '.' + f[len(f) - 1]


def comp_file(local_dict = None, cloud_dict = None, filter_size = None, filter_date = None, 
				include_hidden = False, filter_type = None):
	result = 'NA'
	result_msg = ''
	fail_count = 0

	temp_local_dict = dict(local_dict)
	temp_cloud_dict = dict(cloud_dict)
	
	pprint.pprint(temp_cloud_dict)
	from dateutil import parser

	if filter_size != None:		
		for f in temp_local_dict:
			if not(filter_size['min'] < temp_local_dict[f]['size'] < filter_size['max']) and f in temp_cloud_dict:				
				result_msg += '  FAIL (does not meet filter size): %s\n' % temp_local_dict[f]['full_path']
				fail_count += 1
				local_dict.pop(f)
				cloud_dict.pop(f)

		for f in cloud_dict:
			if not(filter_size['min'] < cloud_dict[f]['size'] < filter_size['max']) and f in temp_local_dict:
				result_msg += '  FAIL (does not meet filter size): %s\n' % cloud_dict[f]['full_path']
				fail_count += 1
				local_dict.pop(f)
				cloud_dict.pop(f)

	if filter_date != None:
		from_time = parser.parse(filter_date['from'])
		to_time = parser.parse(filter_date['to'])
		for f in temp_local_dict:
			local_time = parser.parse(temp_local_dict[f]['mtime'])
			if not(from_time < local_time < to_time) and f in temp_cloud_dict:
				result_msg += '  FAIL (does not meet filter date): %s\n' % temp_local_dict[f]['full_path']
				fail_count += 1
				local_dict.pop(f)
				cloud_dict.pop(f)

		for f in temp_cloud_dict:
			cloud_time = parser.parse(temp_cloud_dict[f]['mtime'])
			if not(from_time < cloud_time < to_time) and f in temp_local_dict:
				result_msg += '  FAIL (does not meet filter date): %s\n' % temp_cloud_dict[f]['full_path']
				fail_count += 1
				local_dict.pop(f)
				cloud_dict.pop(f)			

	for f in temp_local_dict:	# iterate through local folder/file list		
		if f in temp_cloud_dict:			
			if temp_local_dict[f]['is_file']:				
				if filter_type != None and get_file_ext(temp_local_dict[f]['name']) in type_dict[filter_type]:
					result_msg += '  FAIL: %s (file is not filtered out)\n' % temp_cloud_dict[f]['name']					
					temp_cloud_dict.pop(f)
					continue 

				if (temp_local_dict[f]['size'] - temp_cloud_dict[f]['size'] != 0): # compare size
					result_msg += '  FAIL: %s (cloud file size is different)\n' % temp_local_dict[f]['full_path']	
					fail_count += 1
					temp_cloud_dict.pop(f)
					continue			
		else:
			if filter_type != None:
				if get_file_ext(temp_local_dict[f]['name']) not in type_dict[filter_type]:		
					result_msg += '  FAIL: %s does not exist in cloud\n' % local_dict[f]['full_path']	
					fail_count = fail_count + 1
			else:
				result_msg += '  FAIL: %s does not exist in cloud\n' % local_dict[f]['full_path']	
				fail_count = fail_count + 1
	for f in temp_cloud_dict:	# iterate through cloud folder/file list (only need to check folder/file existence in local storage)
		if f in temp_local_dict:			
			if temp_local_dict[f]['is_file']:
				if filter_type != None and get_file_ext(temp_cloud_dict[f]['name']) in type_dict[filter_type]:
					result_msg += '  FAIL: %s (file is not filtered out)\n' % temp_local_dict[f]['name']
					continue

				if (temp_local_dict[f]['size'] - temp_cloud_dict[f]['size'] != 0): # compare size
					result_msg += '  FAIL: %s (cloud file size is different)\n' % temp_local_dict[f]['full_path']	
					fail_count += 1
					continue
		else:
			if filter_type != None:
				if get_file_ext(temp_cloud_dict[f]['name']) not in type_dict[filter_type]:
					result_msg += '  FAIL: %s does not exist in local\n' % cloud_dict[f]['full_path']	
					fail_count = fail_count + 1
			else:
				result_msg += '  FAIL: %s does not exist in local\n' % cloud_dict[f]['full_path']	
				fail_count = fail_count + 1

	print '  Error count: %s' % fail_count
	if fail_count == 0:
		result_msg += '  Test result: PASS'
		result = 'PASS'
	else:
		result_msg += '  Test result: FAIL'
		result = 'FAIL'

	return (result, result_msg)

def save_json(filename = None, json_data = None):
	with open(filename, "w") as out_file:
		json.dump(json_data, out_file, indent=4)

def format_value(value):
	if value < 1024:
		return '%s Bps' % value
	elif 1024 < value < (1024 * 1024):
		return '%.2f KBps' % (float(value) / 1024)
	else:
		return '%.2f MBps' % (float(value) / (1024 * 1024))

def check_job(nas_sid, qpkg_name, job_id=None, operation_name=None, sync_src='', 
				ip_address='', working_dir=None, check_result = False, local_object = None,
				cloud_object = None, report_dict = None):
	"""
	check job 
	"""
	# use CGI command to get job status
	# ex: http://192.168.68.8:8080/cgi-bin/qpkg/S3Plus/cloudconnector.cgi?sid=mdvqad0v&cmd=get_job_statistics&job_type=backup&id=1
	cgi_cmd = 'http://' + ip_address + ':8080/cgi-bin/qpkg/' + qpkg_name + '/cloudconnector.cgi?sid=' + nas_sid + \
				'&cmd=get_job_statistics&job_type=sync&id=' + job_id

	job_stat_json = json.loads(urllib2.urlopen(cgi_cmd).read())	

	# check if job is running and synchronized
	if job_stat_json['result']['state'] == 'Running': 
		while job_stat_json['result']['sub_state'] == 'Synchronizing' or job_stat_json['result']['sub_state'] == 'Scanning': 
			print 'job status: %s (%s) (sleeping for 10 seconds)' % (job_stat_json['result']['state'], job_stat_json['result']['sub_state'])
			time.sleep(10)
			job_stat_json = json.loads(urllib2.urlopen(cgi_cmd).read())			
		

		# sleep first for 120 seconds to let local/cloud finishing file sync (copying from temp folder)
		print 'job status: %s (%s) (sleeping for 120 seconds)' % (job_stat_json['result']['state'], job_stat_json['result']['sub_state'])
		
		try:
			print 'recent upload rate: %s' % format_value(job_stat_json['result']['transfer_upload_rate'])
			print 'recent download rate: %s' % format_value(job_stat_json['result']['transfer_download_rate'])
		except KeyError:
			pass

		time.sleep(120)

		if check_result:		
			# get job local folder and cloud destination
			cgi_cmd = 'http://' + ip_address + ':8080/cgi-bin/qpkg/' + qpkg_name +'/cloudconnector.cgi?sid=' + nas_sid + \
						'&cmd=get_job&job_type=sync&id=' + job_id

			job_desc_json = json.loads(urllib2.urlopen(cgi_cmd).read())			

			# get all local and cloud folders and files list
			local_dict = local_object.get_content_list()			
			cloud_dict = cloud_object.get_content_list()			

			filter_size = dict()
			if job_desc_json['result']['limit_file_size_min'] != '':
				pass
			
			if job_desc_json['result']['limit_file_size_max'] != '':
				pass	

			filter_date = dict()
			if job_desc_json['result']['limit_file_date_from'] != '':
				filter_date['from'] = job_desc_json['result']['limit_file_date_from']

			if job_desc_json['result']['limit_file_date_to'] != '':
				filter_date['to'] = job_desc_json['result']['limit_file_date_to']

			# compare local and cloud drives content
			(result, result_msg) = comp_file(local_dict = local_dict, cloud_dict = cloud_dict)
			report_dict[operation_name] = result
			print result_msg			
		else:
			print 'local and cloud files checking has been disabled. Please check result manually'
	elif job_stat_json['result']['state'] == 'Synchronized' or job_stat_json['result']['state'] == 'Failed':
		print 'job status: %s' % job_stat_json['result']['state']
	else:
		print 'Job %s is not running' % job_id
		exit(1)	

def run_operation(nas_sid, qpkg_name, job_id, sync_src, ip_address, local_object, cloud_object, working_dir,
					 check_result, auto_continue_operation, report_dict, *func_arg):
	for func in func_arg:
		print '\nrunning %s' % func.__name__
		operation_name = func()

		if cloud_object.clouddrive == CloudDrive.Hubic:
			start_job(ip_address = ip_address, qpkg_name = qpkg_name, nas_sid = nas_sid, job_id = job_id)

		print 'finished %s (sleeping for 15 seconds)' % func.__name__
		time.sleep(15)		 
		try:
			check_job(nas_sid, qpkg_name, job_id, 
						 operation_name = operation_name,
						 sync_src=sync_src,
						 ip_address=ip_address, 						 
						 working_dir=working_dir,
						 check_result=check_result,
						 local_object=local_object,
						 cloud_object=cloud_object,
						 report_dict=report_dict)
		except urllib2.HTTPError:
			time.sleep(60)
			check_job(nas_sid, qpkg_name, job_id, 
						 operation_name = operation_name,
						 sync_src=sync_src,
						 ip_address=ip_address, 				
						 working_dir=working_dir,
						 check_result=check_result,
						 local_object=local_object,
						 cloud_object=cloud_object,
						 report_dict=report_dict)		

		while not auto_continue_operation:
			run_next = raw_input('Continue next operation (y/n)? ')
			if run_next == 'y':
				break
			elif run_next == 'n':
				exit(1)
			else:
				continue


def clean_up(ip_address=None, nas_sid=None, qpkg_name=None, job_id=None, access_token=None, nas_src=None, cloud_dst=None, cloud_drive = None):
	# ==================================================
	# cleaning up
	# ==================================================
	# stop the job
	cgi_cmd = 'http://' + ip_address + ':8080/cgi-bin/qpkg/' + qpkg_name + '/cloudconnector.cgi?sid=' + nas_sid + \
					'&cmd=stop_job&job_type=sync&id=' + job_id
	urllib2.urlopen(cgi_cmd)
	time.sleep(10)

	# delete the job
	cgi_cmd = 'http://' + ip_address + ':8080/cgi-bin/qpkg/' + qpkg_name + '/cloudconnector.cgi?sid=' + nas_sid + \
					'&cmd=delete_job&job_type=sync&id=' + job_id
	urllib2.urlopen(cgi_cmd)

	# delete local folder
	shutil.rmtree('/share' + nas_src)
	print 'successfully deleted local folder source: %s' % nas_src

	# delete contents from cloud destination
	if cloud_drive == CloudDrive.Dropbox:
		dropbox_url = 'https://api.dropboxapi.com/1/fileops/delete?root=auto&path=' + urllib.quote(cloud_dst, safe='') + \
						'&access_token=' + access_token
		dropbox_json = json.loads(urllib2.urlopen(dropbox_url).read())
		if dropbox_json['is_deleted']:
			print 'successfully deleted dropbox cloud storage destination: %s' % cloud_dst
	else:	# reserve for other cloud drives
		pass


