import pdb
import time
import os
import sys
import datetime
import subprocess

blackvue_wifi = [['BV1', 'blackvue1'], ['BV2', 'blackvue2']]


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

	if wifi_status[2] == 'connected':
		return True, wifi_ssid
	else:
		return False, ''

def check_available_wifi():
	process = subprocess.Popen(['nmcli', 'dev', 'wifi'], stdout = subprocess.PIPE)
	out, err = process.communicate()
	outlist = stdout_2_list(out)
	
	available_wifi = list(set([x[0] for x in outlist[1:]]))
	return available_wifi

def disconnect_wifi(ssid):
	process = subprocess.Popen(['nmcli', 'con', 'down', 'id', ssid], stdout = subprocess.PIPE)
	return

def connect_to_wifi(new_ssid, pw):
	connected, old_ssid = check_current_wifi()
	if connected:
		disconnected_wifi(old_ssid)
	available_wifi = check_available_wifi()
	if new_ssid not in available_wifi:
		print 'cannot detect ', new_ssid
		print 'current available wifi are: ', available_wifi
		return
	process = subprocess.Popen(['nmcli', 'dev', 'wifi', 'connect', new_ssid, 'password', pw])
	out, err = process.communicate()

	print out, err











