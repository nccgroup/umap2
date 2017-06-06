#!/bin/sh
modprobe gadgetfs
mkdir /dev/gadget
mount -t gadgetfs none /dev/gadget

