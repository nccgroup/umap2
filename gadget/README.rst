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

- Currently we only support **BeagleBone Black** with Robert C. Nelson's Linux
  kernel, you can clone it from it from `here <https://github.com/RobertCNelson/bb-kernel>`_ and use the branch **am33x-v4.7**.
  Read the installation instructions below for more information.
- Setup request frame data is not supported at the moment,
  this affects couple of devices that will not be emulated properly by Umap2.
- In some cases, a disconnection in the gadget FS stack is not handled properly.
  This causes some devices to malfunction in certain cases.
- The GadgetFS kernel module requires some modifications
  (provided here)

Installation (BeagleBone Black)
-------------------------------

- Install the standard, latest, debian image for BeagleBone from
  `here <https://beagleboard.org/latest-images>`_
- Clone and build Robert C. Nelson's Linux kernel from here:

  ::

    $ git clone git@github.com:RobertCNelson/bb-kernel.git
    $ cd bb-kernel
    $ git checkout am33x-v4.7
    $ ./build_kernel.sh

- Install the kernel to the device (as explained in Robert's repo)
- Rebuild the gadgetfs module with our modifications and copy it to the device:

  ::

    $ cp $UMAP2_HOME/gadget/inode.c $BB_KERNEL_HOME/KERNEL/drivers/usb/gadget/legacy
    $ cd $BB_KERNEL_HOME/KERNEL
    $ make -j12 ARCH=arm LOCALVERSION=-bone8 CROSS_COMPILE=$BB_KERNEL_HOME/dl/gcc-linaro-5.3-2016.02-x86_64_arm-linux-gnueabihf/bin/arm-linux-gnueabihf-  modules
    $ scp $BB_KERNEL_HOME/KERNEL/drivers/usb/gadget/legacy/gadgetfs.ko root@<BB_IP>:
    $ scp $UMAP2_HOME/gadget/start_gadgetfs.sh root@<BB_IP>:

Now, on the device:

- Install Umap2 on the device (as described in the main README.rst).
- `chmod +x ~/start_gadgetfs.sh`

At this point, you should have Umap2, modified gadgetfs module and a script to
run it on the BeagleBone Black device.

You need to run the **~/start_gadgetfs.sh** before you start running Umap2.
It will unload other drivers that use the gadget subsystem and load
our gadgetfs module instead.

That's it. You can now run Umap2 from the BeagleBone.
Now specify ``-P gadgetfs`` to the umap2 applications
in order to use the gadgetfs module instead of the Facedancer.
