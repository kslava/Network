#from FxA import *
from RxP import *
import sys
import string
import threading

import py_compile
#py_compile.compile('FxA.py')
py_compile.compile('RxP.py')

"""
Client class
"""
class FxAClient():
	def __init__(self, srcPortN, dstIP, dstPortN):
		self.connected = False
		self.srcPortN = srcPortN
		self.dstIP = dstIP
		self.dstPortN = dstPortN
		self.socket = Socket()
		self.dstAddress = (self.dstIP, self.dstPortN)
		self.socket.bind(self.srcPortN)
		self.fileOpenError = "fileOpenError"
		self.disconnect = "disconnect"
		self.endMsg = "endMsg"
		self.sendSize = 1024
		#self.fxa =FxA(self.srcPortN, self.dstIP, self.dstPortN)
		
		
		self.userCommand()
		
	"""
	Parses and identifies user commands. Then it executes them.
	"""
	def userCommand(self):
		while True:
			uInput = raw_input('type the command: ')
			if type(uInput) == str: 
				if uInput == "connect":
					if self.connected: print "Already connected"
					else: 
						state = self.socket.connect(self.dstAddress)
						self.connected = state
						if state:
							print "Connected"
							
							#self.useTh = threading.Thread(target = self.getServerC, name = "serverT")
							#self.useTh.daemon = True
							#self.useTh.start()
						else: "Failed to connect"

				elif uInput == "disconnect":
					self.socket.send(self.disconnect)
					self.socket.close()
					print "Disconnected"
					#self.socket.close()
					sys.exit()
				elif uInput[:6] == "window":
					try:
						winSize = int(uInput[7:])
					except:
						print "Wrong input value"						
					else:	
						self.socket.setWindowSize(winSize)
						print "Window size set to ", winsSize
				elif uInput[:3] == "get":
					self.get(uInput[4:])
				elif uInput[:4] == "post":
					self.post(uInput[5:])
				else: print "Invalid command"
	"""
	Gets the file from the server and names it new+Old Name
	"""
	def get(self, fileName):
		msg = "get " + fileName
		self.socket.send(msg)
		receiving = True
		#file = ""
		newFileName = "new"+fileName
		f = open(newFileName, 'w+')
		#f.write("")
		#f.close()
		while receiving:
			m = self.socket.receive()
			if m == self.fileOpenError:
				print "Invalid File Name"
				receiving = False
			elif m == self.endMsg:
				receiving = False
			else:
				f.write(m)
				#file += m
		f.close()
		print "got the file:", fileName
	"""
	Posts a file on the server
	"""
	def post(self, fileName):
		msg = "post " + fileName
		self.socket.send(msg)
		try:
			f = open(fileName)
		except:
			self.socket.send(self.fileOpenError)
		else:
			doneReading = False
			while not doneReading:
				data = f.read(self.sendSize)
				if data == "":
					doneReading = True
					self.socket.send(self.endMsg)
				else:	
					self.socket.send(data)
		print "file sent"
			
"""
Parses through the user input and makes sure that the input is valid.
@param argv the arguments from the user.
@return srcPortN, dstIP, dstPortN, False otherwise.
"""		
def inputParse(argv):
	if len(argv) < 3 or len(argv) > 4:
		print "Incorrect number of arguments. Please try again"
		sys.exit()
	try:
		srcPortN = int(argv[0])
		dstIP = argv[1]
		dstPortN = int(argv[2])
		
	except:
		print "Incorrect arguments. Please try again" 
		sys.exit()
	else:
		if dstPortN < 0 or dstPortN > 65535 or srcPortN < 0 or srcPortN > 65535:
			print "Invalid Port Number"
			sys.exit()
	return srcPortN, dstIP, dstPortN
		
"""
Initiates the FxA and RxP class.
@param argv the arguments from the user
"""		
def main(argv):
	srcPortN, dstIP, dstPortN = inputParse(argv)
	client = FxAClient(srcPortN, dstIP, dstPortN)
if __name__ == "__main__":
    main(sys.argv[1:])
