from socket import *
import os
import sys
import struct
import time
import select
import binascii
# noinspection PyUnresolvedReferences
import pandas as pd
import warnings
import numpy as np

warnings.simplefilter(action='ignore', category=FutureWarning)

ICMP_ECHO_REQUEST = 8


def checksum(string):
    csum = 0
    countTo = (len(string) // 2) * 2
    count = 0

    while count < countTo:
        thisVal = (string[count + 1]) * 256 + (string[count])
        csum += thisVal
        csum &= 0xffffffff
        count += 2

    if countTo < len(string):
        csum += (string[len(string) - 1])
        csum &= 0xffffffff

    csum = (csum >> 16) + (csum & 0xffff)
    csum = csum + (csum >> 16)
    answer = ~csum
    answer = answer & 0xffff
    answer = answer >> 8 | (answer << 8 & 0xff00)
    return answer


def receiveOnePing(mySocket, ID, timeout, destAddr):
    timeLeft = timeout #timeout was set to 1 before

    while 1:
        startedSelect = time.time()
        whatReady = select.select([mySocket], [], [], timeLeft)
        howLongInSelect = (time.time() - startedSelect)
        if whatReady[0] == []:  # Timeout
            return "Request timed out."

        timeReceived = time.time() #current time at which packet is received
        recPacket, addr = mySocket.recvfrom(1024) #receive the packet and its contents

        #print(recPacket, addr)
        # Fill in start
        # Fetch the ICMP header from the IP packet
        recHeader = recPacket[20:28] #get header based on position in packet, type starts at bit 160 so byte 20
        recType, recCode, recChecksum, recID, recSequence = struct.unpack("bbHHh", recHeader) #open suitcase

        if recID == ID and recType == 0 and recCode == 0:
            lengthData = struct.calcsize("d") #how many bytes of type d exist in struct
            timeSent = struct.unpack("d", recPacket[28:28 + lengthData])[0]
            delay = timeReceived - timeSent
            response = (lengthData + 8, recPacket[8], addr[0])
            return delay, response

        # Fill in end
        timeLeft = timeLeft - howLongInSelect
        if timeLeft <= 0:
            return "Request timed out."


def sendOnePing(mySocket, destAddr, ID):
    # Header is type (8), code (8), checksum (16), id (16), sequence (16)

    myChecksum = 0
    # Make a dummy header with a 0 checksum
    # struct -- Interpret strings as packed binary data
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    #recall in video the first argument is the type of data, icmp echo request has been set to 8 before, 0 is the code
    #mychecksum is pulling from first function, ID pulled from os
    #bbHHh is for the 5 following arguments where the first 2 are binaries and the others are .. whatever

    data = struct.pack("d", time.time()) #data here is the time at which the packet was sent

    #print("data: " and data)
    # Calculate the checksum on the data and the dummy header.
    myChecksum = checksum(header + data)

    # Get the right checksum, and put in the header

    if sys.platform == 'darwin':
        # Convert 16-bit integers from host to network  byte order
        myChecksum = htons(myChecksum) & 0xffff
    else:
        myChecksum = htons(myChecksum)

    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    #print("+ header being sent out: " and header)
    packet = header + data #putting the two together
    #print("final packet: " and packet)
    mySocket.sendto(packet, (destAddr, 1))  # AF_INET address must be tuple, not str

    # Both LISTS and TUPLES consist of a number of objects
    # which can be referenced by their position number within the object.


def doOnePing(destAddr, timeout):
    #function to send a ping, get a ping and return the delay which will in turn be used for
    #pringint the delay
    icmp = getprotobyname("icmp")

    # SOCK_RAW is a powerful socket type. For more details:   https://sock-raw.org/papers/sock_raw
    mySocket = socket(AF_INET, SOCK_RAW, icmp)

    myID = os.getpid() & 0xFFFF  # Return the current process i
    sendOnePing(mySocket, destAddr, myID) #jump to send function
    print("mySocket: " and mySocket)
    delay = receiveOnePing(mySocket, myID, timeout, destAddr)
    mySocket.close()
    return delay


def ping(host, timeout=1):
    # timeout=1 means: If one second goes by without a reply from the server,
    # the client assumes that either the client's ping or the server's pong is lost
    dest = gethostbyname(host) #returns ip address
    print("\nPinging " + dest + " using Python:") #we see this in terminal if we ping a site
    print("")

    response = pd.DataFrame(columns=['bytes', 'rtt',
                                     'ttl'])  # This creates an empty dataframe with 3 headers with the column specific names declared
    #usually see this in terminal where its ex. 64 bytes sent __, time, time in ms

    #print(response)
    # Send ping requests to a server separated by approximately one second
    # Add something here to collect the delays of each ping in a list so you can calculate vars after your ping
    delayList = []

    for i in range(0, 4):  # Four pings will be sent (loop runs for i=0, 1, 2, 3). just doing first 4
        print("attempt: " and i)
        delay, statistics = doOnePing(dest, timeout)  # what is stored into delay and statistics? check tuples
        delayList.append(delay)
        response = response.append({'bytes': statistics[0], 'rtt': delay,
                                   'ttl': statistics[1]}, ignore_index = True)
        # store your bytes, rtt, and ttle here in your response pandas dataframe. An example is commented out below for vars
        print(delay)
        time.sleep(1)  # wait one second

    packet_lost = 0
    packet_recv = 0
    # fill in start. UPDATE THE QUESTION MARKS
    for index, row in response.iterrows():
        if row["bytes"] == 0:  # access your response df to determine if you received a packet or not
            packet_lost = packet_lost + 1
        else:
            packet_recv =  packet_recv + 1
    # fill in end

    # You should have the values of delay for each ping here structured in a pandas dataframe;
    # fill in calculation for packet_min, packet_avg, packet_max, and stdev
    #delayData =
    packet_min = np.min(delayList)
    packet_avg = np.mean(delayList)
    packet_max = np.max(delayList)
    stdev = np.std(delayList)

    vars = pd.DataFrame(columns=['min', 'avg', 'max', 'stddev'])
    vars = vars.append({'min': float(packet_min), 'avg': float(packet_avg),
                        'max': float(packet_max), 'stddev': float(stdev)},
                       ignore_index=True)
    print(vars)  # make sure your vars data you are returning resembles acceptance criteria. make sure this is converted into ms
    return vars


if __name__ == '__main__':
    ping("google.com")
