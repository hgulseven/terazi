# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
from ftplib import FTP
import os
from time import sleep


def getopts(argv):
   opts = {}
   while argv:
      if argv[0][0] == '-': # find "-name value" pairs
         opts[argv[0]] = argv[1] # dict key is "-name" arg
         argv = argv[2:]
      else:
         argv = argv[1:]
   return opts

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    from sys import argv
    print("in ftpget ")
    try:
        ftp = FTP('192.168.1.45')
        ftp.set_debuglevel(2)
        ftp.login('emre', 'QAZwsx135')
        ftp.sendcmd('TYPE I')
        ftp.set_pasv(False)
        with open('/home/pi/PycharmProjects/terazi/mainwindow.py', 'wb') as fp:
            ftp.retrbinary('RETR mainwindow.py',fp.write)
        newversion = "loaded"
        print("Yeni versiyon indirildi.Program tekrar başlatılıyor.")
    except Exception as e:
        newversion = "notloaded"
    sleep(5)
    import sys
    command=sys.executable
    i=1
    while i<len(argv):
        print(argv[i])
        command=command + " "+ argv[i]
        i=i+1
    print(command)
    os.system(command)

