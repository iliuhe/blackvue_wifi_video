import pdb
import pycurl
from StringIO import StringIO
import time
import os
import urllib2
import sys
import smtplib
from email.mime.text import MIMEText
import datetime
import subprocess
import logging

'''
IF want to delete the duplicated BV1 xxx, do
sudo rm -rf /etc/NetworkManager/system-connections/BV*
'''

def csv2list(csv_file):
    res = []
    with open(csv_file, 'rb') as fp:
        for line in fp.readlines():
            res.append(line[:-1].split(','))
    return res

def get_url_raw_info(url):
    buffer = StringIO()
    c = pycurl.Curl()
    try:
        c.setopt(c.URL, url)
        c.setopt(c.WRITEDATA, buffer)
        c.perform()
        c.close()
        body = buffer.getvalue()
        return body
    except:
    	logger.exception('Cannot load video list page from black vue ... ')
    	return -1

def video_download(url, destination, blocksize=8192):
    print "Downloading to {0}".format(destination)
    start = time.time() 
    resume = os.path.exists(destination)
    with open(destination, "ab") as fh:
        if resume:
            # print "Resuming download"
            fh.seek(0, 2)
            curpos = fh.tell()
            header =  {'Range':'bytes={0}-'.format(curpos)}
            request = urllib2.Request(url, headers=header)
            try:
                wh = urllib2.urlopen(request)
            except urllib2.HTTPError, inst:
                if inst.code == 416:
                    return
            try:
                size = int(wh.info().getheaders("Content-Length")[0]) + curpos
            except IndexError:
                size = 999999999
            cur = curpos
            if size == cur:
                return
        else:
            wh = urllib2.urlopen(url)
            try:
                size = int(wh.info().getheaders("Content-Length")[0]) 
            except IndexError:
                size = 999999999
            cur = 0
            
        content = wh.read(blocksize)
        while content:
            cur += len(content)
            fh.write(content)
            content = wh.read(blocksize)
            sys.stdout.write("Progress: {0:8}% \t {1}k of {2}k \r".format(round((float(cur)/size)*100.0,2), cur/1024.0, size/1024.0))
            sys.stdout.flush()
    print size / 1024.0 / float(time.time() - start) 

def raw_web_info_analysis_IVUE(raw_data, save_folder_root, storage_dict):
	video_download_info_list = []

	items = raw_data.split('href="')
	for i in range(1, len(items), 2):
		item = items[i]
		video_dir = item.split('"><b>')[0]
		file_name = video_dir.split('/DCIM/MOVIE/')[-1]
		temp_video_address = IVUE_ip_root + video_dir
		date = file_name.split('_')[0]+file_name.split('_')[1]
		save_file_name = save_folder_root + date + '/' + file_name
		if date in storage_dict:
			if save_file_name in storage_dict[date]:
				continue
		video_download_info_list.append([temp_video_address, save_file_name, date])
	return video_download_info_list


def raw_web_info_analysis(raw_data, save_folder_root, storage_dict):
    lines = raw_data.split('\r\n')
    video_download_info_list = []
    for i, line in enumerate(lines):
        if len(line) < 7:
            continue
        temp_video_address = ip_address + line[2:].split(',')[0]
        file_name = temp_video_address.split('/')[-1]
        date = file_name.split('_')[0]

        # target saved video path
        save_file_name = save_folder_root + date + '/' + file_name
        if date in storage_dict:
        	if save_file_name in storage_dict[date]:
        		continue
        video_download_info_list.append([temp_video_address, save_file_name, date])
        # print 'Video ' + file_name + ' already exists in ' + save_file_name
    return video_download_info_list

def download_video_from_list(video_download_info_list):
    job_number = len(video_download_info_list)
    success_list, fail_list = [], []
    video_list_csv = target_folder_root + 'video_list.csv'
    fp = open(video_list_csv, 'a')

    for i, video_info in enumerate(video_download_info_list):
        [temp_video_address, file_name, date] = video_info
        logger.info(datetime.datetime.now(), 'Downloading ' + file_name + ' ' + str(i+1) + '/' + str(job_number))
        if not os.path.exists(os.path.dirname(file_name)):
            logger.info('Folder ' + os.path.dirname(file_name) + ' does not exist, creating this folder')
            os.mkdir(os.path.dirname(file_name))
        try:
            video_download(temp_video_address, file_name)
            success_list.append(temp_video_address)
            fp.write(','.join([date, file_name]) + '\n')
            # pdb.set_trace()
        except Exception as e:
            logger.exception(e)
            fail_list.append(temp_video_address)
            pdb.set_trace()
    return success_list, fail_list

## the generated dictionary has keys as folder name and each list consist of video names
def video_storage_check(folder):

    if not os.path.exists(folder + 'video_list.csv'):
    	logger.info('No video_list.csv found, create one')
        open(folder + 'video_list.csv', 'w')
        return {}
    
    save_list = csv2list(folder + 'video_list.csv')
    video_dict = {}
    for item in save_list:
        # item: date_folder, file_name
        if item[0] not in video_dict:
            video_dict[item[0]] = [item[1]]
        else:
            video_dict[item[0]].append(item[1])

    return video_dict

# not used right now
def camera_video_check(test_url):
    raw_info = get_url_raw_info(test_url)
    video_info_list = raw_web_info_analysis(raw_info)
    stat = {}
    for x in video_info_list:
        if x[2] not in stat:
            stat[x[2]] = 0
        else:
            stat[x[2]] += 1
    #print video_info_list
    print stat
    print len(video_info_list)
    return str(stat), str(len(video_info_list))


####################################################################################
####################################################################################
####################################################################################

def stdout_2_list(stdout):
	lines = stdout.split('\n')
	output_list = []
	for line in lines:
		if len(line) != 0:
			output_list.append(line.split())
	return output_list

def check_current_wifi():
	process = subprocess.Popen(['nmcli', 'dev'], stdout = subprocess.PIPE)
	out, err = process.communicate()
	out_list = stdout_2_list(out)
	wifi_status = [line for line in out_list if line[1] == 'wifi'][0]
	
	if len(wifi_status) > 4:
		wifi_ssid = wifi_status[3] + ' ' + wifi_status[4]
	elif len(wifi_status) == 4:
		wifi_ssid = wifi_status[3]
	else:
		wifi_ssid = 'UNKNOW?'

	# print wifi_status
	if wifi_status[2] == 'connected':
        logger.info('Currently conneted to WIFI: ' + wifi_ssid)
		return True, wifi_ssid
	else:
        logger.info('Currently not connected to WIFI')
		return False, ''

def check_available_wifi():
	process = subprocess.Popen(['nmcli', 'dev', 'wifi'], stdout = subprocess.PIPE)
	out, err = process.communicate()
	outlist = stdout_2_list(out)
	available_wifi = list(set([x[0] for x in outlist[1:]]))
	return available_wifi

def disconnect_wifi(ssid):
	process = subprocess.Popen(['nmcli', 'con', 'down', 'id', ssid], stdout = subprocess.PIPE)
    logger.info('Disconnected to WIFI: ' + ssid)
	return

def connect_to_wifi(idx):
	new_ssid, pw = WIFI_LIST[idx]
	connected, old_ssid = check_current_wifi()
	if connected:
		if new_ssid == old_ssid[:3]:
			return True, 'Already connected to ' + new_ssid
		disconnect_wifi(old_ssid)
		time.sleep(3)
	available_wifi = check_available_wifi()
	if new_ssid not in available_wifi:
		logger.error('Cannot detect ' + new_ssid)
        logg.info('Current available wifi are: ' + available_wifi)
		return False, 'Cannot detect ', new_ssid
	process = subprocess.Popen(['nmcli', 'dev', 'wifi', 'connect', new_ssid, 'password', pw])
	out, err = process.communicate()
	logger.info('Connect to WIFI output: ' + str(out) + ', ' + err)
	return True, 'Connected to ' + new_ssid + ' successfully'

####################################################################################
####################################################################################
####################################################################################

def set_up_logger():
    logger = logging.getLogger('')
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler('logger.log')
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s-%(levelname)s-%(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger

IVUE_url = 'http://192.168.1.254/DCIM/MOVIE'
IVUE_ip_root = 'http://192.168.1.254'
ip_address = 'http://10.99.77.1'
test_url = 'http://10.99.77.1/blackvue_vod.cgi'
folder_root = '/home/he/wifi_download_videos/'    

WIFI_LIST = [['dummy'],['BV1', 'blackvue1'], ['BV2', 'blackvue2'], ['BV3', 'blackvue3'], ['Rincon', '12345678']]
current_wifi_idx = 4

logger.info('Script starts running ...')
if __name__ == '__main__':
	while True:
		# print datetime.datetime.now()
		if current_wifi_idx < 4:
			logger.info('Trying to connect to Blackvue '+ str(current_wifi_idx) + ' ...')
		else:
			logger.info('Trying to connect to IVUE ...')
		try:
			status = connect_to_wifi(current_wifi_idx)
			if not status[0]: 
				raise ValueError('Network problem')
                logger.error('Status: ' + status[1])
			logger.info('Status: ' + status[1])
			if current_wifi_idx < 4:
				logger.info('Connected to Blackvue ' + str(current_wifi_idx) + ' successfully')
			else:
				logger.info('Connected to Rincon successfully')
        except:
			if current_wifi_idx < 4:
				logger.error('Failed to connect to Blackvue '+ str(current_wifi_idx) + ' , will retry later')
			else:
				logger.error('Failed to connect to Rincon, will try later')
			logger.info('Rest for 10 seconds\n\n\n\n\n')
			time.sleep(10)
			current_wifi_idx += 1
			if current_wifi_idx == 5:
				current_wifi_idx = 1
			continue

		if current_wifi_idx < 4:
			target_folder_root = folder_root + 'bv' +str(current_wifi_idx) + '/'
		else:
			target_folder_root = folder_root + 'IVUE/'		
		if not os.path.exists(target_folder_root):
			os.mkdir(target_folder_root)
		# storage check
		storage_dict = video_storage_check(target_folder_root)

		# downloading
		try_times = 0
		while try_times < 3:
			time.sleep(5)
			# check url and get list of videos from the camera
			logger.info('Trying to connect camera server ...')
			if current_wifi_idx < 4:
				raw_info = get_url_raw_info(test_url)
			else:
				raw_info = get_url_raw_info(IVUE_url)

			if raw_info != -1:
				logger.info('Parsing the videoe list ...')
				if current_wifi_idx < 4:
					video_info_list = raw_web_info_analysis(raw_info, target_folder_root, storage_dict)
				else:
					video_info_list = raw_web_info_analysis_IVUE(raw_info, target_folder_root, storage_dict)

				if len(video_info_list) == 0:
					logger.info('No video update for now')
				else:
					download_video_from_list(video_info_list[:10])
					logger.info('10 videos are successfull downloaded from blackvue ' + str(current_wifi_idx))
				break
			else:
				try_times += 1
				# unable to load the blackvue video page
				logger.error('Unable to connect to camera server: ' + str(try_times + 1) + ' try failed')


		if try_times == 3:
			logger.error('Unable to load video list from blackvue ' + str(current_wifi_idx))
			logger.error('Will switch to next camera')
		current_wifi_idx += 1
		if current_wifi_idx == 5:
			current_wifi_idx = 1
		
		logger.info('Rest for 10 seconds\n\n\n\n\n\n\n\n')
		time.sleep(10)


##----------------------------------------------------------
## Below are functions for automatic email
##----------------------------------------------------------

def send_email(subject, message, targets):
    smtp_ssl_host = 'smtp.mail.yahoo.com'
    smtp_ssl_port = 465
    username = 'vadl_blackvue_cam'
    password = 'vadlblackvuecam'
    sender = 'vadl_blackvue_cam@yahoo.com'

    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = ', '.join(targets)
    
    try:
        server = smtplib.SMTP_SSL(smtp_ssl_host, smtp_ssl_port)
        server.login(username, password)
        server.sendmail(sender, targets, msg.as_string())
        server.quit()
        print 'mail send successfully'
    except:
        print 'Unknown error, mail not send'

def generate_email_report(test_url, storage_folder):
    subject = 'Blackvue_camera_report: ' + str(datetime.month) + ' ' + str(datetime.day)
    cam_stat, cam_video_n = camera_video_check(test_url)
    message1 = 'Camera status\n' + cam_stat + '\n' + 'In total: ' + cam_video_n + ' videos on camera\n'
    message2 = 'Download information\n'
    pc_stat = video_storage_check(storage_folder)
    message3 = 'PC Storage\n' + str(pc_stat)
    return subject, message1 + message2 + message3
    
#send_email()








