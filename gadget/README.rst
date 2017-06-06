Using Umap2 with GadgetFS
=========================

Preface
-------

Umap and Umap2 were developed based on the Facedancer -
it had some advantages over other solutions,
and allowed python emulation of USB devices.
It also enabled any PC to act as a USB device,
by only using a small hardware device that speaks over
a very common channel with the PC (UART over USB).

However, with Umap2, we wanted to decouple the device emulation (e.g. Umap2)
from the physical interface that it speaks over.
Support for GadgetFS is our first attempt to support
a USB device hardware other than Facedancer.

USB Gadget is the Linux Kernel driver for USB devices,
allowing the implementation of USB devices on Linux based machines
(assuming there's hardware support).
GadgetFS is a kernel module that provides user space applications
a File-System based interface to the USB gadget subsystem.

This is a guide on how to run Umap2 on a GadgetFS-enabled device,
it details the limitations and usage for Umap2 on such a device.

Limitations
-----------
- For Raspberry Pi Zero W, only kernel 4.12.0-rc3+ and above seem to work stable, run
  start_gadgetfs_RaspiZeroW.sh to mount gadgetfs. Patching kernel isn't needed.
- Currently we only support **BeagleBone Black** with Robert C. Nelson's Linux
  kernel, you can clone it from it from `here <https://github.com/RobertCNelson/bb-kernel>`_
  and use the branch **am33x-v4.7**.
  Read the installation instructions below for more information.
- Setup request frame data is not supported at the moment,
  this affects couple of devices that will not be emulated properly by Umap2.
- In some cases, a disconnection in the gadget FS stack is not handled properly.
  This causes some devices to malfunction in certain cases.
- The GadgetFS kernel module requires some modifications (provided here)
- You need to run umap2 as root

Installation
------------

Since there are possibly many different platforms that support USB gadget,
we will not provide a detailed instructions for each one.
Instead, we assume that you are already able to build kernel modules
on your platforms.

Since there are differences in the kernel APIs between different kernels,
we provide 2 versions of the patched inode.c (gadgetfs module source):

  - inode.c-v4.4.9 for kernel v4.4.9 which is widely used (at the time)
    for the BeagleBone black
  - inode.c-v4.6_and_up which should be compatible at least up to v4.8-rc5
  - Raspberry Pi W works out of the box with kernel 4.12.0-rc3+, no patching 
    needed, just add "enable_uart=1" and "dtoverlay=dwc2" to /boot/config.txt 
    and add " modules-load=dwc2 " after rootwait string in /boot/config.txt. 
    For shell use UART cable with raspberry pi zero w gpio pins for shell.

**Note:** Currently we assume that all operations are performed as root.

::

  $ pip install -e $UMAP2_HOME
  $ cd $UMAP2_HOME/gadgetfs
  # VERSION is as mentioned above
  $ cp inode.c.VERSION inode.c
  $ make modules
  $ cp gadgetfs.ko /root/

At this point, you should have:

- umap2 installed.
- the kernel module is at: /root/gadgetfs.ko

Running Umap2
-------------

Before you run Umap2, you need to unload each module that uses the USB gadget
subsystem, and load the modified gadgetfs module.
You can use the following script to do that:

::

  $ $UMAP2_HOME/gadget/start_gadgetfs.sh
or for Raspberry Pi Zero W :
  $ $UMAP2_HOME/gadget/start_gadgetfs_RaspiZeroW.sh

Once the new module is loaded,
you can run Umap2 as described in the README.rst in the root of the repository,
But specify ``-P gadgetfs`` in the command line
to use gadgetfs as the physical layer of Umap2.

**HAPPY HACKING :)**
