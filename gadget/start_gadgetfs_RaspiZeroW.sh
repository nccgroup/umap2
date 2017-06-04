#!/bin/sh
sudo modprobe gadgetfs
sudo mkdir /dev/gadget
sudo mount -t gadgetfs none /dev/gadget

