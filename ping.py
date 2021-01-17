import socket
import os
import struct
import time
import select
import argparse


ICMP_ECHO_REQUEST = 8


def checksum(packet):
    """
    计算校验和
    :param packet: bytes
    :return: 校验和
    """
    c_sum = 0
    countTo = (len(packet) / 2) * 2
    count = 0
    while count < countTo:
        thisVal = packet[count + 1] * 256 + packet[count]
        c_sum = c_sum + thisVal
        c_sum = c_sum & 0xffffffff
        count = count + 2
    if countTo < len(packet):
        c_sum = c_sum + packet[len(packet) - 1].decode()
        c_sum = c_sum & 0xffffffff
    # 将高16位与低16位相加
    c_sum = (c_sum >> 16) + (c_sum & 0xffff)
    c_sum = c_sum + (c_sum >> 16)
    answer = ~c_sum & 0xffff
    # 主机字节序转网络字节序
    answer = answer >> 8 | (answer << 8 & 0xff00)
    return answer


def send_packet(my_socket, ID, sequence, dest_addr, size):
    """
    发送ICMP request数据包
    :param my_socket: 发送数据包的套接字
    :param ID: 进程ID
    :param sequence: 序号
    :param dest_addr: 目的地址
    :param size: 数据字段大小
    :return: None
    """
    # ICMP头部有 type(8bit) code(8bit) checksum(16bit) ID(16bit) seq(16bit)

    # 初始化头部的checksum为0
    check_sum = 0
    header = struct.pack("!bbHHh", ICMP_ECHO_REQUEST, 0, check_sum, ID, sequence)

    # 数据发送的前8字节为时间戳,之后根据需求对数据进行填充
    data = struct.pack("!d" + "x"*(size-8), time.time())
    # 计算checksu
    check_sum = checksum(header + data)

    header = struct.pack("!bbHHh", ICMP_ECHO_REQUEST, 0, check_sum, ID, sequence)
    packet = header + data

    my_socket.sendto(packet, (dest_addr, 1))


def receive_packet(my_socket, ID, sequence, dest_addr, timeout):
    """
    接收一个ICMP reply数据包
    :param my_socket: 接收数据包的套接字
    :param ID: 进程ID
    :param sequence: 序号
    :param dest_addr: 目的主机
    :param timeout: 超时时间
    :return: 延迟delay, 生存时间TTL, 数据段大小data_size
    """
    while 1:
        start_select = time.time()
        isAble = select.select([my_socket], [], [], timeout)
        select_time = (time.time() - start_select)
        if not isAble[0]:  # 超时
            return None

        timeReceived = time.time()
        recPacket, addr = my_socket.recvfrom(2048)

        header = recPacket[20: 28]
        type, code, c_sum, packetID, sequence = struct.unpack("!bbHHh", header)
        if type == 0 and packetID == ID:  # ICMP reply报文的type为0
            byte_in_double = struct.calcsize("!d")
            data_size = len(recPacket[28:])
            timeSent = struct.unpack("!d", recPacket[28: 28 + byte_in_double])[0]
            delay = timeReceived - timeSent
            ttl = ord(struct.unpack("!c", recPacket[8:9])[0].decode())
            return delay, ttl, data_size

        if timeout - select_time <= 0:
            return None


def do_ping(dest_addr, ID, sequence, timeout, size):
    """
    一次ping命令的执行函数
    :param dest_addr: 目的主机地址
    :param ID: 进程ID
    :param sequence: 序号
    :param timeout: 超时时间
    :param size: 数据大小
    :return: 延迟delay, 生存时间TTL, 数据段大小data_size
    """
    icmp = socket.getprotobyname("ICMP")

    my_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, icmp)

    send_packet(my_socket, ID, sequence, dest_addr, size)
    info = receive_packet(my_socket, ID, sequence, dest_addr, timeout)

    my_socket.close()
    return info


def ping(host, timeout=1, n=4, size=8, signal=0, a_count=0):
    """
    ping命令的执行
    :param host: 手动输入的需要访问的域名/IP地址
    :param timeout: 每次回复的超时时间ms(可选项)
    :param n: 要发送的回显请求数(可选项)
    :param size: ping请求发送的数据大小bytes(可选项)
    :param signal: ping指定主机直至键入Ctrl+C(可选项)
    :param a_count: 将地址解析为主机名(可选项)
    :return: None
    """
    # 超时时间默认为1 如果时间超过timeout则认为发生了丢包
    dest = socket.gethostbyname(host)
    if a_count == 1:
        dest_name = socket.gethostbyaddr(host)[0]

    my_ID = os.getpid() & 0xFFFF
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
            result = do_ping(dest, my_ID, index, timeout, size)
            send_times = send_times + 1
            times = times + 1
            if index == 0 and result:
                print("正在 Ping " + (host if a_count == 0 else dest_name) + " [" + dest + "] 具有 "
                      + str(result[2]) + " 字节的数据:")
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
            # 判断是否死循环
            if signal == 1:
                loop_flag = 1
            index = index + 1
            time.sleep(1)  # 每一秒做一次ping请求
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
    parser.add_argument("input", help="input destination network URL/IP Address")
    parser.add_argument("-n", help="numbers of ICMP request packets to send (default: 4)", default=4)
    parser.add_argument("-l", help="select packet's data segment size(8 bytes least)", default=8)
    parser.add_argument("-t", help="ping destination in an infinite loop while press Ctrl+C",
                        action='count', default=0)
    parser.add_argument("-w", help="set ICMP receive timeout time(ms)", default="1000")
    parser.add_argument("-a", help="parse ip address into hostname", action='count', default=0)
    args = parser.parse_args()
    ping(args.input, n=int(args.n), size=int(args.l), signal=int(args.t), timeout=eval(args.w)/1000, a_count=args.a)
