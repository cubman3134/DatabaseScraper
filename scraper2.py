import time
from threading import Thread, Lock
import random
import socket
import time
import urllib2
from bs4 import BeautifulSoup
import errno
import sys
import re
import datetime
from socket import error as socket_error
from httplib import BadStatusLine
import signal
import threading
import mysql.connector
import os

request_headers = {
	"Accept-Language": "en-US,en;q=0.5",
	"User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:40.0) Gecko/20100101 Firefox/40.0",
	"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
	"Referer": "http://services.runescape.com",
	"Connection": "keep-alive"
}

quote_page = "http://services.runescape.com/m=itemdb_oldschool/viewitem?obj="
proxies_page = "http://us-proxy.org"
proxies_file = "proxies.txt"
output_file = "output.txt"

class Proxy:
	proxyDictionary = dict()
	currentNumberProxies = 0
	proxyIP = ""
	numOffenses = 0

class ThreadHandler:
	maxNumThreads = 80
	proxyDictionaryLock = threading.Lock()
	proxyFileLock = threading.Lock()
	urgentLock = threading.Lock()
	printLock = threading.Lock()	

def sigHandler(signum, frame):
	mydb.commit()
	mydb.close()
	cleanup_stop_thread()
	print(str(threading.activeCount()))
	sys.exit()
signal.signal(signal.SIGINT, sigHandler)
signal.signal(signal.SIGTERM, sigHandler)

mydb = mysql.connector.connect(
	host="dbs.eecs.utk.edu",
	user="pholt4",
	passwd=str(sys.argv[1]),
	database="cs465_pholt4"
	)

mycursor = mydb.cursor()

def setupProxies():
	ThreadHandler.proxyFileLock.acquire()
	f = open(proxies_file, 'r')
	for line in f.readlines():
		currentProxy = Proxy()
		Proxy.currentNumberProxies += 1
		currentProxy.proxyIP = line.rstrip()
		Proxy.proxyDictionary[currentProxy.proxyIP] = currentProxy
	f.close()
	ThreadHandler.proxyFileLock.release()

def get_proxies():
	ThreadHandler.proxyFileLock.acquire()
	open(proxies_file, 'w').close()
	f = open(proxies_file, 'a')
	try:
		req = urllib2.Request(proxies_page, headers = request_headers)
		page = urllib2.urlopen(req, timeout = 4)
		soup = BeautifulSoup(page, 'html.parser')
	except(urllib2.URLError, socket.timeout, socket_error) as e:
		ThreadHandler.proxyFileLock.release()
		return False
	proxies = soup.tbody
	if proxies is not None:
		for child in proxies.children:
			currentProxy = ""
			for i, c in enumerate(str(child)):
				if(i > 7):
					if(c == '<'):
						break
					currentProxy += c
			f.write(currentProxy + '\n')
	else:
		ThreadHandler.proxyFileLock.release()
		return False
	f.close()
	ThreadHandler.proxyFileLock.release()
	return True

def acquireProxyDictLock():
	ThreadHandler.proxyDictionaryLock.acquire()
	if len(Proxy.proxyDictionary) < 5:
		get_proxies()
		setupProxies()

def delete_proxy(ip, deletion_reason):
	acquireProxyDictLock()
	ThreadHandler.proxyFileLock.acquire()
	if Proxy.proxyDictionary.get(ip) is None:
		ThreadHandler.proxyFileLock.release()
		ThreadHandler.proxyDictionaryLock.release()
		return
	f = open(proxies_file, "r+")
	d = f.readlines()
	f.seek(0)
	for i in d:
		if i.rstrip() != ip:
			f.write(i)
	f.truncate()
	f.close()	
	ThreadHandler.proxyFileLock.release()
	del Proxy.proxyDictionary[ip]
	ThreadHandler.proxyDictionaryLock.release()
	Proxy.currentNumberProxies -= 1

def checkApplicableEntries(f1):
	f = open(f1, 'r')
	total = 0
	for line in f.readlines():
		if line.find("None") == -1:
			total += 1
	print total

def combineFiles(files = []):
	itemsSet = set()
	for currentFile in range(len(files) - 1):
		checkApplicableEntries(files[currentFile])
		f = open(files[currentFile], 'r')
		for line in f.readlines():
			if line.find("None") == -1:
				itemsSet.add(line)
	for curItem in itemsSet:
		print(curItem.rstrip())
	print("Total: " + str(len(itemsSet)))

def interact_runescape_url(number, currentProxy, commandType, xDays):
	try:
		currentUrl = quote_page + str(number)
		proxy = urllib2.ProxyHandler({'http': currentProxy})
		opener = urllib2.build_opener(proxy)
		urllib2.install_opener(opener)
		req = urllib2.Request(currentUrl, headers = request_headers)
		page = urllib2.urlopen(req, timeout = 4)
		if page.geturl() != currentUrl:	
			return False
		soup = BeautifulSoup(page, 'html.parser')
		if str(soup.title).find("RuneScape Oldschool") == -1:	
			return False
	except(urllib2.URLError, socket.timeout, socket_error, BadStatusLine):	
		return False
	item = soup.h2
	if commandType == "check":
		return item
	elif commandType == "download":	
		if str(item).find("None") > -1:	
			return None
		strsoup = str(soup)
		pushLocations = [m.start() for m in re.finditer("average180.push", strsoup)]
		curDate = ""
		curPrice = ""
		returnString = "insert into GrandExchange values('" + number + "', "
		dateString = "itemNo int(4)," 
		for cur in pushLocations:
			x = 0
			curString = ""
			haventReached = False	
			while not(haventReached):
				curString = curString + strsoup[cur + x]
				x = x + 1
				if strsoup[cur + x] == ';':
					haventReached = True
			beginningstringname = ", "
			endstringname = ", "
			curDate = re.search('(?<=\')(.*?)(?=\')', curString).group(0)	
			curDate = curDate.replace("/", "d")
			curPrice = re.search(r', (.*?),', curString).group(0).strip(', ').rstrip(',')
			if commandType == "download":
				dateString += "	" + curDate + " int(4),"
				returnString += "'" + curPrice + "', "
		if commandType == "download":
			returnString = returnString[0:len(returnString) - 2]
			returnString += ");"
		dateString = dateString[0:len(dateString) - 1]
		dateString += ");"
		return [returnString, dateString]

def createTable():
	mycursor.execute("drop table if exists GrandExchange")
	insertCommands = "create table GrandExchange("
	dateRet = new_command("DOWNLOAD 560 0".split())
	insertCommands += str(dateRet)
	mycursor.execute(insertCommands)	
	
def new_command(commands):
	currentCommand = 0
	while currentCommand < len(commands):	
		if commands[currentCommand] == "GETPROXIES":
			get_proxies()
			currentCommand += 1
		elif commands[currentCommand] == "CHECKURL":
			acquireProxyDictLock()
			currentProxy = random.choice(Proxy.proxyDictionary.keys())
			ThreadHandler.proxyDictionaryLock.release()
			checkUrlReturnVal = interact_runescape_url(commands[currentCommand + 1], currentProxy, "check")
			while checkUrlReturnVal is False:	
				delete_proxy(currentProxy, "Something went wrong.")
				acquireProxyDictLock()
				currentProxy = random.choice(Proxy.proxyDictionary.keys())
				ThreadHandler.proxyDictionaryLock.release()
				checkUrlReturnVal = interact_runescape_url(commands[currentCommand + 1], currentProxy, "check")
			ThreadHandler.printLock.acquire()
			print(str(commands[currentCommand + 1]) + " " + str(checkUrlReturnVal))
			sys.stdout.flush()
			ThreadHandler.printLock.release()
			currentCommand += 2
		elif commands[currentCommand] == "SETUP":
			setupProxies()
			currentCommand += 1
		elif commands[currentCommand] == "CHECK":
			checkApplicableEntries(commands[currentCommand + 1])
			currentCommand += 2
		elif commands[currentCommand] == "COMBINE":
			total = 1
			files = []
			while len(commands) > total and commands[currentCommand + total].find(".txt") != -1:
				files.append(commands[currentCommand + total])
				total += 1
			combineFiles(files)
			currentCommand += total
		elif commands[currentCommand] == "DOWNLOAD":
			returnVal = None
			while returnVal is None:
				acquireProxyDictLock()
				currentProxy = random.choice(Proxy.proxyDictionary.keys())
				ThreadHandler.proxyDictionaryLock.release()
				returnVal = interact_runescape_url(commands[currentCommand + 1], currentProxy, "download", commands[currentCommand + 2])
				while returnVal is False:
					delete_proxy(currentProxy, "Something went wrong")
					acquireProxyDictLock()
					currentProxy = random.choice(Proxy.proxyDictionary.keys())
					ThreadHandler.proxyDictionaryLock.release()
					returnVal = interact_runescape_url(commands[currentCommand + 1], currentProxy, "download", commands[currentCommand + 2])	
			if commands[currentCommand + 2] == '0':
				return returnVal[1]
			else:	
				ThreadHandler.printLock.acquire()
				mycursor.execute(returnVal[0])
				ThreadHandler.printLock.release()	
			currentCommand += 3
		else:
			currentCommand += 1

createTable()
while 1:	
	if threading.activeCount() < ThreadHandler.maxNumThreads:
		currentLine = sys.stdin.readline()
		if currentLine:
			t = threading.Thread(target = new_command, args = (currentLine.split(),))
			t.daemon = True
			t.start()
		elif threading.activeCount() == 1:
			mydb.commit()
			mydb.close()
			sys.exit()
