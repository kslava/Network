import socket
import threading
import math 
import random
import ctypes
import struct
import hashlib
import string
import time
import sys
from collections import deque

class Socket():
	def __init__(self):
		self.ACK = 1
		self.NACK = 2
		self.SYN = 3
		self.FIN = 4
		MAX_WINDOW_SIZE = 4096  #65485
		self.packetDataSize = 512
		self.MAX_SEQ_NUM = math.pow(2, 32)
		#data types 16 and 32 bits(unsighed int)
		self.uint16 = ctypes.c_uint16
		self.uint32 = ctypes.c_uint32
		#size of a receive buffer 
		self.buffer = 4096	
		#number of types packet will be resend before exiting
		self.resendLimit = 5
		#address to send to
		self.dstAddress = None
		#own port number
		self.port = None
		#sequence number
		self.seq = 0 #random.randrange(MAX_SEQ_NUM)
		#destination sequence number
		self.dstSeq = 0
		#window size
		self.windowSize = MAX_WINDOW_SIZE
		self.sentQ = deque()
		self.receiveQ = deque()
		self.qLock = threading.Lock()
		self.resend = False
		self.finished = 0
		self.done = False
		self.doneReceiveing = False
		self.msg = ""
		self.terminating = False
		self.timeout = False
		self.receiveTimeout = 1
		self.connected = False
		#socket
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		#set timeout on receive
		self.sock.settimeout(0.5)

	"""
	binds to the port number
	"""
	def bind(self, port):
		self.port = port
		self.sock.bind(("", port))
	"""
	Disconnect from the server. Server will continue to listen to other clients
	"""
	def disconncect(self):
		self.sendFin()
		self.connected = False
	"""
	Connects to the server with dstAddress
	"""
	def connect(self, dstAddress):
		self.dstAddress = dstAddress
		numTimes = self.resendLimit
		while numTimes > 0:
			data = self.sendSyn()
			print "send syn"
			good = self.checkChecksum(data)
			if good:
				self.dstSeq = struct.unpack("<L", data[4:8])[0]
				challenge = str(data[16:])
				hash = hashlib.md5()
				hash.update(challenge)
				cHash = hash.hexdigest()
				pack = self.packet(cHash)
				data, address = self.sendAndWait(pack)
				type =  struct.unpack("<B", data[10])[0]
				#print struct.unpack("<H", data[8:10])[0]
				
				if type == self.ACK:
					self.windowSize = struct.unpack("<H", data[8:10])[0]
					self.connected = True
					return True
				else: return False
			else:
				numTimes -= 1
	"""
	CLoses the RxP socket
	"""
	def close(self):
		print "closing"
		self.terminating = True
		if self.connected: 
			self.connected = False
			self.sendFin()
		
		t0 = time.time()
		while time.time() - t0 >= 1.1:
			if time.time() - t0 >= 1.1: 
				#print "i got here"
				self.sock.close()
			
	"""
	Listens to connects from clients
	"""
	def listen(self, dstAddress):
		self.dstAddress = dstAddress
		self.terminating = False
		while not self.terminating:
			try:
				data, address = self.sock.recvfrom(self.buffer)
			except socket.timeout:
				pass
			else:
				"""
				check packet
				"""
				print "listening"
				good = self.checkChecksum(data)
				if good:
					if struct.unpack("<B", data[10])[0] == self.SYN:
						self.windowSize = struct.unpack("<H", data[8:10])[0]
						self.dstSeq = struct.unpack("<L", data[4:8])[0]
						self.dstAddress = address
						challenge = self.challengeStringGenerator(16)
						pack = self.packet(challenge)
						data, address = self.sendAndWait(pack)
						
						hash = hashlib.md5()
						hash.update(challenge)
						cHash = hash.hexdigest()
						uHash = str(data[16:]) 
						if cHash == uHash:
							l = True
							while l:						
								self.sendAck(self.windowSize, True)
								try: 
									data, address = self.sock.recvfrom(self.buffer)
								except socket.timeout:
									l = False
								else:
									"""
									checksum
									"""
									good = self.checkChecksum(data)
									if good:
										if str(data[16:]) != uHash:
											l = False	
							self.connected = True
							return True
						else:
							#self.sendNack()
							pass
					else: pass
		
	"""
	Helper method that send data using UDP function. 
	"""
	def sendto(self, data):
		self.sock.sendto(data, self.dstAddress)
	"""
	Helper method to send data and wait for data from the other side.
	"""
	def sendAndWait(self, data, init = False):
		numTimes = self.resendLimit
		while numTimes:
			self.sendto(data)
			try:
				data, address = self.sock.recvfrom(self.buffer)
			except socket.timeout:
				numTimes -= 1
				if numTimes <= 0:
					print "To many lost packets"
					self.close()
					sys.exit()
			else:
				"""
				check packet
				"""
				good = self.checkChecksum(data)
				if good:
					if init: return data, address 
					else:
						dataSeq = struct.unpack("<L", data[4:8])[0]
						if dataSeq == self.nextSeq(self.dstSeq):
							self.dstSeq = self.nextSeq(self.dstSeq)
							return data, address
						else: pass
	"""
	Main function to send the data. breaks the data into packets
	"""
	def send(self, data):
		self.done = False
		packetQ = deque()
		for i in range(0, len(data), self.packetDataSize):
			if i + self.packetDataSize >= len(data):
				packetQ.append(self.packet(data[i:], ack = True))
				self.finished = self.seq - 1
			else:
				packetQ.append(self.packet(data[i:i+self.packetDataSize]))
		winTh = threading.Thread(target = self.sendWindow,name = "SendWinTh", args=(packetQ, "a"))
		winTh.daemon = True
		winTh.start()
		ackTh = threading.Thread(target = self.getAck, name = "SendAckTh")
		ackTh.daemon = True
		ackTh.start()
		#winTh.join()
		#ackTh.join()
		while not self.done:
			pass
		if self.done:
			print "Done Sending"
	
	"""
	Helper function for send(). it sends a window and resends if necessary.
	"""
	def sendWindow(self, data, a):
		packetQ = data
		while not self.done: # and not self.timeout:
			while self.windowSize > self.packetDataSize and packetQ:
				p = packetQ.popleft()
				self.sendto(p)
				self.windowSize -= self.packetDataSize
				self.sentQ.append(p)
			if self.resend:
				self.qLock.acquire()
				for i in range(len(self.sentQ)):					
					self.sendto(self.sentQ[i])
				self.qLock.release()
				self.resend = False
	"""
	Helper function for send().  It receives ACKs from the receiver and  removes
	packets from the sentQ as they are already received. It also makes sure to tell 
	sendWindow when to resend(if it does not receive a particular ACK)
	"""
	def getAck(self):
		numTimes = self.resendLimit
		while numTimes:
			try:
				data, address = self.sock.recvfrom(self.buffer)
				numTimes = self.resendLimit
				self.resend = False
			except socket.timeout:
				numTimes -= 1
				self.resend = True
				if numTimes <= 0:
					#self.timeout = True
					self.resend = False
					self.done = True
					return
			else:
				"""
				check packet
				"""
				good = self.checkChecksum(data)
				if good:
					type = struct.unpack("<B", data[10])[0]
					if type == self.ACK:
						s = struct.unpack("<L", data[4:8])[0]
						self.windowSize = struct.unpack("<H", data[8:10])[0]
						self.qLock.acquire()
						l = True
						while l and self.sentQ:
							qS = struct.unpack("<L", self.sentQ[0][4:8])[0]
							if qS <= s:   #doesn't loop the seq
								self.sentQ.popleft()
							else:
								l = False
							if s >= self.finished: 
								#print "finish"
								self.done = True
								self.sentQ.clear()
								self.qLock.release()
								return
						self.qLock.release()
		
	"""
	Main function to receive data. 
	"""
	def receive(self):
		self.doneReceiveing = False
		self.msg = ""
		winTh = threading.Thread(target = self.receiveWin, name = "ReceiveWinTh")
		winTh.daemon = True
		winTh.start()
		ackTh = threading.Thread(target = self.giveAck, name = "ReceiveAckTh")
		ackTh.daemon = True
		ackTh.start()
		#return self.msg
		winTh.join()
		ackTh.join()
		while not self.terminating:
			if self.doneReceiveing:
				return self.msg
	"""
	Helper functoin for receive(). It receives a window of data, and leaves it to 
	giveAck to ACK those packets, reorder and/or drop.
	"""
	def receiveWin(self):
		end = False
		while not self.doneReceiveing:
			try:
				data, address = self.sock.recvfrom(self.buffer)
			except socket.timeout:
				#self.timeout = True
				#end = True
				pass
			else:
				"""
				checksum
				"""
				good = self.checkChecksum(data)
				if good:
					type = struct.unpack("<B", data[10])[0]
					#if type == self.ACK: end = True
					self.qLock.acquire()
					self.receiveQ.append(data)
					self.qLock.release()
	"""
	Helper function for receive(). It ACKs packets, as well as orders them into a 
	message that was send.
	"""
	def giveAck(self):
		numRec = 0 
		sendAckFq = self.windowSize/3
		end = False
		t0 = time.time()
		while not end:# and not self.timeout:
			nextdstSeq = self.nextSeq(self.dstSeq)
			if len(self.receiveQ) >= 10: j = 10
			else: j = len(self.receiveQ)
			#self.qLock.acquire()
			if len(self.receiveQ) > 0:
				for i in range(j):
					pack = self.receiveQ[i]
					if nextdstSeq == struct.unpack("<L", pack[4:8])[0]:
						t0 = time.time()
						self.msg += pack[16:]
						#print pack[16:]
						self.qLock.acquire()
						self.receiveQ.remove(pack)
						self.qLock.release()
						self.dstSeq = nextdstSeq
						numRec += self.packetDataSize
						type = struct.unpack("<B", pack[10])[0]
						if type == self.ACK:
							end = True
							#print "msg:", self.msg
							print "got msg"
						break
					if nextdstSeq > struct.unpack("<L", pack[4:8])[0]:
						t0 = time.time()
						self.sendAck(self.windowSize)
						self.qLock.acquire()
						self.receiveQ.remove(pack)
						self.qLock.release()
			#self.qLock.release()
			if numRec == sendAckFq or end:
				self.sendAck(self.windowSize)
				numRec = 0
				if end:
					l = True
					while l:						
						try: 
							data, address = self.sock.recvfrom(self.buffer)
						except socket.timeout:
							l = False
						else:
							self.sendAck(self.windowSize)
					self.qLock.acquire()
					self.receiveQ.clear()
					self.qLock.release()
			
			if time.time() - t0 >= self.receiveTimeout:
				self.doneReceiveing = True
				end = True
		self.timeout = False
		self.doneReceiveing = True
	"""
	This function send a SYN packet and waits for response
	"""
	def sendSyn(self):
		arr = bytearray()
		#add port number 32 - 4
		arr.extend(self.uint16(self.port))
		arr.extend(self.uint16(self.dstAddress[1]))
		#add seq number 32 - 4
		arr.extend(self.uint32(self.seq))
		#add window size 16 - 2
		arr.extend(self.uint16(self.windowSize))
		#add syn 8 - 1
		arr.append(self.SYN)
		#add other 8 - 1
		arr.append(0)
		#add checksum  32 - 4
		arr.extend(self.uint32(0))
		
		self.seq = self.nextSeq(self.seq)
		newArr = self.makeChecksum(arr)
		try:
			data, address = self.sendAndWait(newArr, True)
		except:
			return None
		return data
	"""
	This function sends ACK packet with a window size
	"""
	def sendAck(self, winSize, selfSeq = False):
		arr = bytearray()
		#add port number 32 - 4
		arr.extend(self.uint16(self.port))
		arr.extend(self.uint16(self.dstAddress[1]))
		#add seq number 32 - 4
		if selfSeq: 
			arr.extend(self.uint32(self.seq))
			self.seq = self.nextSeq(self.seq)
		else: arr.extend(self.uint32(self.dstSeq))
		#add window size 16 - 2
		arr.extend(self.uint16(winSize))
		#add ack 8 - 1
		arr.append(self.ACK)
		#add other 8 - 1
		arr.append(0)
		#add checksum  32 - 4
		arr.extend(self.uint32(0))
		newArr = self.makeChecksum(arr)
		self.sendto(newArr)
	"""
	This function sends FIN packet, signalling the termination of connection.
	"""	
	def sendFin(self):
		arr = bytearray()
		#add port number 32 - 4
		arr.extend(self.uint16(self.port))
		arr.extend(self.uint16(self.dstAddress[1]))
		#add seq number 32 - 4
		arr.extend(self.uint32(self.seq))
		#add window size 16 - 2
		arr.extend(self.uint16(self.windowSize))
		#add fin 8 - 1
		arr.append(self.FIN)
		#add other 8 - 1
		arr.append(0)
		#add checksum  32 - 4
		arr.extend(self.uint32(0))
		
		self.seq = self.nextSeq(self.seq)
		newArr = self.makeChecksum(arr)
		data, address = self.sendAndWait(newArr)

	"""
	This function creates a packet with the given data.
	"""
	def packet(self, data, ack = False):
		arr = bytearray()
		#add port number 32 - 4
		arr.extend(self.uint16(self.port))
		arr.extend(self.uint16(self.dstAddress[1]))
		#add seq number 32 - 4
		arr.extend(self.uint32(self.seq))
		#add window size 16 - 2
		arr.extend(self.uint16(0))
		if ack:
			#add syn 8 - 1
			arr.append(1)
		else: arr.append(0)
		#add other 8 - 1
		arr.append(0)
		#add checksum  32 - 4
		arr.extend(self.uint32(0))
		#add data
		arr.extend(data)
		self.seq = self.nextSeq(self.seq)
		newArr = self.makeChecksum(arr)
		return newArr
	"""
	makes the checksum for the packet using MD5 hash
	"""
	def makeChecksum(self, packet):
		hash = hashlib.md5()
		hash.update(packet)
		checksum = hash.digest()
		newPacket = bytearray()
		data = packet[16:]
		header = packet[:12]
		newPacket.extend(header)
		newPacket.extend(checksum[:4])
		newPacket.extend(data)
		return newPacket
	"""
	Checks the checksum, making sure packet was not corrupted
	It also looks for FIN packets.
	"""
	def checkChecksum(self, packet):
		oldChecksum = packet[12:16]
		header = packet[:12]
		data = packet[16:]
		newPacket = bytearray()
		newPacket.extend(header)
		newPacket.extend(self.uint32(0))
		newPacket.extend(data)
		hash = hashlib.md5()
		hash.update(newPacket)
		newChecksum = hash.digest()
		if oldChecksum == newChecksum[:4]:
			if struct.unpack("<B", packet[10])[0] == self.FIN:
				numTimes = self.resendLimit
				while numTimes:
					self.sendAck
					self.terminating = True
					self.connected = False
					try:
						data, address = self.sock.recvfrom(self.buffer)
					except:
						break
					else:
						if struct.unpack("<B", data[10])[0] == self.FIN:
							numTimes -= 1
				
			return True
		else : False
	"""
	Increments a sequence number and returns it
	"""
	def nextSeq(self, seq):
		if seq == self.MAX_SEQ_NUM:	s = 0
		else : s = seq + 1
		return s
	"""
	Generates a random String of length N.
	@param self, N - size of the string
	@return generated random string
	"""
	def challengeStringGenerator(self,N):
		chars = string.ascii_lowercase
		return ''.join(random.choice(chars) for _ in range(N))
	"""
	Sets the window size to w
	"""
	def setWindowSize(self, w):
		self.windowSize = w*self.packetDataSize
	