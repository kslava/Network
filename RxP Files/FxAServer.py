#from FxA import *
from RxP import *
import threading
import sys
import time
"""
Server class
"""
class FxAServer():
	def __init__(self, srcPortN, dstIP, dstPortN):
		self.srcPortN = srcPortN
		self.dstIP = dstIP
		self.dstPortN = dstPortN
		self.socket = Socket()
		self.dstAddress = (self.dstIP, self.dstPortN)
		self.socket.bind(self.srcPortN)
		self.terminate = False
		self.connected = False
		self.free = True
		self.fileOpenError = "fileOpenError"
		self.disconnect = "disconnect"
		self.endMsg = "endMsg"
		self.sendSize = 1024
		#self.fxa =FxA(self.srcPortN, self.dstIP, self.dstPortN) 
		"""
		self.lisTh = threading.Thread(target = self.listen)
		self.lisTh.daemon = True
		self.lisTh.start()
		"""
		self.useTh = threading.Thread(target = self.getUserInput, name = "userT")
		self.useTh.daemon = True
		self.useTh.start()
		while not self.terminate:
			self.listen()
		self.socket.close()
		sys.exit()
		
	"""
	Waits for the command from the client
	"""
	def waitCommand(self):
		print "waiting for command"
		command = ""
		while command == "" and not self.terminate:
			command = self.socket.receive()
		
		if command == None:
			self.connected = False
		elif command[:3] == "get":
			fileName = command[4:]
			print "sending ", fileName
			self.sendFile(fileName)
		elif command[:4] == "post":
			fileName = command[5:]
			print "receiving ", fileName
			self.getFile(fileName)
		elif command == self.disconnect:
			self.connected = False
		#print "command",command, self.connected
	"""
	Receives input from the user.
	"""
	def getUserInput(self):
		while not self.terminate:
			uInput = raw_input('type the command: ')
			if type(uInput) == str:
				if uInput == "terminate":
					self.terminate = True
					self.connected = False
					print "shutting down"
					self.socket.close()
					print "closed socket"
					t0 = time.time()
					while time.time() - t0 >= 1.1:
						pass
					#sys.exit()
				elif uInput[:6] == "window":
					try:
						winSize = int(uInput[7:])
					except:
						print "Wrong input value"						
					else:	
						self.socket.setWindowSize(winSize)
						print "Window size set to ", winSize
				else:
					print "Invalid command"
		self.socket.close()
		sys.exit()	
	"""
	Listens for clients
	"""
	def listen(self):
		while not self.terminate:
			#print "I am listening"
			self.connected = self.socket.listen(self.dstAddress)
			if self.connected:
				print "connected"
				while self.connected:
					self.waitCommand()
					#msg = self.socket.receive()
					#print "msg server got:", msg
		#self.socket.close()
		#sys.exit()
	"""
	This method sends the file with fileName
	"""
	def sendFile(self, fileName):
		self.free = False
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
		self.free = True
		print "file sent"
	"""
	This files recieves file from the client and names it new + oldName 
	"""
	def getFile(self, fileName):
		self.free = False
		#msg = "get " + fileName
		#self.socket.send(msg)
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
		self.free = True
		print "got the file:", fileName
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
	client = FxAServer(srcPortN, dstIP, dstPortN)
if __name__ == "__main__":
    main(sys.argv[1:])