import socket
import os
import struct
import time
import select
import argparse


ICMP_ECHO_REQUEST = 8


def checksum(str):
    csum = 0
    countTo = (len(str) / 2) * 2
    count = 0
    while count < countTo:
        thisVal = str[count + 1] * 256 + str[count]
        csum = csum + thisVal
        csum = csum & 0xffffffff
        count = count + 2
    if countTo < len(str):
        csum = csum + str[len(str) - 1].decode()
        csum = csum & 0xffffffff
    csum = (csum >> 16) + (csum & 0xffff)
    csum = csum + (csum >> 16)
    answer = ~csum
    answer = answer & 0xffff
    answer = answer >> 8 | (answer << 8 & 0xff00)
    return answer


def receiveOnePing(mySocket, ID, sequence, destAddr, timeout):
    timeLeft = timeout

    while 1:
        startedSelect = time.time()
        whatReady = select.select([mySocket], [], [], timeLeft)
        howLongInSelect = (time.time() - startedSelect)
        if not whatReady[0]:  # Timeout
            return None

        timeReceived = time.time()
        recPacket, addr = mySocket.recvfrom(1024)

        header = recPacket[20: 28]
        type, code, checksum, packetID, sequence = struct.unpack("!bbHHh", header)
        if type == 0 and packetID == ID:  # type should be 0
            byte_in_double = struct.calcsize("!d")
            data_size = len(recPacket[28:])
            timeSent = struct.unpack("!d", recPacket[28: 28 + byte_in_double])[0]
            delay = timeReceived - timeSent
            ttl = ord(struct.unpack("!c", recPacket[8:9])[0].decode())
            return delay, ttl, data_size

        timeLeft = timeLeft - howLongInSelect
        if timeLeft <= 0:
            return None


def sendOnePing(mySocket, ID, sequence, destAddr, size):
    # Header is type (8), code (8), checksum (16), id (16), sequence (16)

    myChecksum = 0
    # Make a dummy header with a 0 checksum.
    # struct -- Interpret strings as packed binary data
    header = struct.pack("!bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, sequence)

    data = struct.pack("!d" + "x"*(size-8), time.time())
    # Calculate the checksum on the data and the dummy header.
    myChecksum = checksum(header + data)

    header = struct.pack("!bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, sequence)
    packet = header + data

    mySocket.sendto(packet, (destAddr, 1))  # AF_INET address must be tuple, not str
    # Both LISTS and TUPLES consist of a number of objects
    # which can be referenced by their position number within the object


def doOnePing(destAddr, ID, sequence, timeout, size):
    icmp = socket.getprotobyname("icmp")

    mySocket = socket.socket(socket.AF_INET, socket.SOCK_RAW, icmp)

    sendOnePing(mySocket, ID, sequence, destAddr, size)
    delay = receiveOnePing(mySocket, ID, sequence, destAddr, timeout)

    mySocket.close()
    return delay


def ping(host, timeout=1, n=4, size=8, signal=0):
    # timeout=1 means: If one second goes by without a reply from the server,
    # the client assumes that either the client’s ping or the server’s pong is lost
    dest = socket.gethostbyname(host)

    # Send ping requests to a server separated by approximately one second

    myID = os.getpid() & 0xFFFF  # Return the current process i
    loss = 0
    send_times = 0
    receive_times = 0
    times = 0
    delays = []

    index = 0
    loop_flag = 1
    # 使用try语句对控制命令进行处理,可以手动终止ping命令
    try:
        while loop_flag:
            result = doOnePing(dest, myID, index, timeout, size)
            send_times = send_times + 1
            times = times + 1
            if index == 0 and result:
                print("正在 Ping " + host + " [" + dest + "] 具有 " + str(result[2]) + " 字节的数据:")
            if not result:
                print("请求超时。")
                loss += 1
            else:
                delay = int(result[0] * 1000)
                ttl = result[1]
                rcv_bytes = result[2]
                receive_times = receive_times + 1
                delays.append(delay)
                print("来自 " + dest + " 的回复: 字节=" + str(rcv_bytes) + " 时间=" + str(delay) + "ms TTL=" + str(ttl))
            # 判断循环退出条件
            if index == (n - 1):
                loop_flag = 0
            if signal == 1:
                loop_flag = 1
            index = index + 1
            time.sleep(1)  # one second
    except KeyboardInterrupt:
        print("手动终止ping命令, 程序结束!")

    # 此判断语句处理了全部请求超时的情况
    if delays:
        sorted_delays = sorted(delays)
        print()
        print(dest + " 的 Ping 统计信息:")
        print("\t数据包: 已发送 = " + str(send_times) + ","
                                                  " 已接收 = " + str(receive_times) + ", 丢失 = " + str(loss)
              + "(" + str(loss / times * 100) + "% 丢失),")
        print("往返行程的估计时间(以毫秒为单位):")
        print("\t最短 = " + str(sorted_delays[0]) + "ms, 最长 = " + str(sorted_delays[-1]) +
              "ms, 平均 = " + str(int(sum(delays) / len(delays))) + "ms")
        return
    else:
        print(dest + " 的 Ping 统计信息:")
        print("\t数据包: 已发送 = " + str(send_times) + ","
                                                  " 已接收 = " + str(receive_times) + ", 丢失 = " + str(loss)
              + "(" + str(loss / times * 100) + "% 丢失),")
        return


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="input destination network URL")
    parser.add_argument("-n", help="numbers of ICMP request to send (default: 4)", default=4)
    parser.add_argument("-l", help="select data size(8 bytes least)", default=8)
    parser.add_argument("-t", help="ping destination while press control c", default=0)
    parser.add_argument("-w", help="set receive time(ms)", default="1000")
    args = parser.parse_args()
    ping(args.input, n=int(args.n), size=int(args.l), signal=int(args.t), timeout=eval(args.w)/1000)
