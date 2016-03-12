Svyatoslav Kucheryavykh - skucheryavykh3@gatech.edu

CS 3251, A    Programming Assignment 2

RxP.py - The main transfer protocol. It is a sliding window, byte stream protocol and transfers data reliably between two 
	points.
FxAClient.py - client file transfer application. Uses RxP.py to transfer files between server and client
FxAServer.py - server file transfer application. Uses RxP.py to transfer files between server and client
README.txt - contains details about the files and how to run the program
sample.txt - contains sample output of the running program as an example.

To run the program, running NetEmu.py is necessary.
First to start the server in the directory with the files this instruction should be typed:
	python FxAServer.py P N NP
	where P is server port number (odd)
		N = NetEmu IP
		NP = NetEmu port number
To start a client:
	python FxAClient.py P N NP
	where P is client port number (even)
		N = NetEmu IP
		NP = NetEmu port number
		
Then to connect to the server, client should type in connect.
After that files can be transferred back a forth with command : 
	get F   or   post F 
	where F is a filename of a file that is in the same directory as the code files.
This will create a new file in directory named new + old filename

A disconnect can be typed to disconnect from the server and shutdown the client:
	disconnect
On the server's end terminate can be typed to shutdown the server, after that client should also be shut down with disconnect:
	terminate
A window size can be set for both client and server with:
	window S
	where S is the size of the window in segments (number of packets that fit into one window)
	
For API look into RxPDesignProtocole.pdf