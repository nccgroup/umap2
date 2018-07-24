#!/usr/bin/env python
# GoodFET Client Library
# 
# (C) 2013 Philippe Teuwen <phil at teuwen.org>

import spi
import RPi.GPIO as GPIO
import struct
from binascii import hexlify
import logging
from time import sleep

class Raspdancer:
    data=""
    def __init__(self):
        GPIO.setmode(GPIO.BOARD)
        # pin15=GPIO22 is linked to MAX3420 -RST
        GPIO.setup(15, GPIO.OUT)
        GPIO.output(15,GPIO.LOW)
        GPIO.output(15,GPIO.HIGH)
        spi.openSPI(speed=26000000)
    def __del__(self):
        spi.closeSPI()
        GPIO.output(15,GPIO.LOW)
        GPIO.output(15,GPIO.HIGH)
        GPIO.cleanup()
    def transfer(self, data=[]):
        if isinstance(data,str):
            data = [ord(x) for x in data]
        data = tuple(data)
        data = spi.transfer(data)
        self.data = "".join([chr(x) for x in data])
        return self.data
