# Ping

## Intro

This is a program that imitates the ping function in Windows OS. The cede skeleton is from book 'Computer Network Top Down Approach', I took part of code here([Click this for more information](https://github.com/moranzcw/Computer-Networking-A-Top-Down-Approach-NOTES)).

## Instruction

Run ping.py in Window command like:

```
python ping.py [-n] [-l] [-t] [-w] [-a] URL/Destnation IP Address
```

- Optional params:

[-n] : numbers of ICMP requests to send (default: 4).

[-l] : select data size(8 bytes least), default=8.

[-t] : ping destination in an infinite loop while press control c.

[-w] : set receive time(ms), default=1000(ms).

[-a] : parse IP address into hostname.

## More

Im a college student and this is my course final hw, this ping application is based on ICMP, you can capture ICMP packets in Wireshark when you run this. 

Hopefully this works for you! :)

