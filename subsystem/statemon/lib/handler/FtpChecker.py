"""
$Id: FtpChecker.py,v 1.1 2003/06/19 12:53:07 magnun Exp $
$Source: /usr/local/cvs/navbak/navme/subsystem/statemon/lib/handler/FtpChecker.py,v $
"""
from abstractChecker import AbstractChecker, Event
import ftplib, Socket
class FTP(ftplib.FTP):
	def __init__(self,timeout,host='',user='',passwd='',acct=''):
		ftplib.FTP.__init__(self)
		if host:
			self.connect(host)
		if user:
			self.login(user,passwd,acct)
		self.timeout = timeout
	def connect(self, host = '', port = 0):
		'''Connect to host.  Arguments are:
		- host: hostname to connect to (string, default previous host)
		- port: port to connect to (integer, default previous port)'''
		if host: self.host = host
		if port: self.port = port
		msg = "getaddrinfo returns an empty list"
		self.sock = Socket.Socket(self.timeout)
		self.sock.connect((self.host,self.port))
		self.file = self.sock.makefile('rb')
		self.welcome = self.getresp()
		return self.welcome

class FtpChecker(AbstractChecker):
	"""
	takes the args:
	username
	password
	path (ACCT)
	"""
	def __init__(self,serviceid,boksid,ip,args,version):
		port = args.get('port',21)
		AbstractChecker.__init__(self,'ftp',serviceid,boksid,(ip,port),args,version)
	def execute(self):
		s = FTP(self.getTimeout())
		ip,port = self.getAddress()
		output = s.connect(ip,port)
		args = self.getArgs()
		username = args.get('username','')
		password = args.get('password','')
		path = args.get('path','')
		output = s.login(username,password,path)
		if output[:3] == '230':
			return Event.UP,'code 230'
		else:
			return Event.DOWN,output.split('\n')[0]

def getRequiredArgs():
	"""
	Returns a list of required arguments
	"""
	requiredArgs = []
	return requiredArgs
			
