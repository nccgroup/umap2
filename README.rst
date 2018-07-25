Umap2
=====

Umap2 is the second revision of NCC Group's
python based USB host security assessment tool.

This revision will have all the features that
were supported in the first revision:

- *umap2emulate* - USB device emulation
- *umap2scan* - USB host scanning for device support
- *umap2detect* - USB host OS detection (no implemented yet)
- *umap2fuzz* - USB host fuzzing

In this revision there will be some additional
features:

- USB host fuzzing uses kitty as fuzzing engine
- Umap2 not only contains executable scripts,
  but is also installed as a package
  and may be used as a library

Umap2 is developed by NCC Group and Cisco SAS team.

Warning: umap2 is still an experimental,
alpha stage tool.
The APIs, executable names, etc. are likely to be changed
in the near future.
Use at your own risk.

Support
-------

- IRC: `#umap2 on Freenode <https://webchat.freenode.net/?channels=umap2>`_
Installation
------------

Since this is a very early version,
Umap2 is not yet available from pypi,
instead, use pip to install it directly from github:

::

    $ pip install git+https://github.com/nccgroup/umap2.git#egg=umap2

Python Versions
---------------

Umap2 is python2/3 compatible for most parts.
However, the fuzzer script (**umap2kitty**) runs only on python2.

"Soft" Dependencies
-------------------

Umap2's dependencies are listed in **setup.py** and will be installed with umap2,
however, there are couple of things that you might want to do to add support
for some devices:

Mass Storage
~~~~~~~~~~~~

1. Requires a disk image called **stick.img** in the running directory

MTP
~~~

1. Requires a folder/file called **mtp_fs** in the current directory.
2. Requires the python package pymtpdevice. This package is not on pypi
   at the moment, but can be downloaded and installed from here:
   https://github.com/BinyaminSharet/Mtp

Hardware
--------

- `Facedancer <http://goodfet.sourceforge.net/hardware/facedancer21/>`_
  is the recommended hardware for Umap2.
  Umap2 was developed based on it, and you'll get the most support with it.
- `Raspdancer <http://wiki.yobi.be/wiki/Raspdancer>` is supported on RPi
- **GadgetFS** is partially supported.
  This support is very experimental (even more than the rest of Umap2)
  and limited.
  
  - BeagleboneBlack starting from Linux kernel 4.4.9 with a patched gadgetfs
    driver
  - RaspberryPi Zero W starting from Linux kernel 4.12.0-rc3+ which requires
    no patches
  - Since 4.12.0-rc3+ requires no patches, there might be other devices that
    can be supported, if you know of such device or have made changes to make
    it run on other devices, please send us a word.

If you are interested, read the **gadget/README.rst** for more information.

Usage
-----

Device Emulation
~~~~~~~~~~~~~~~~

Umap2's basic functionallity is emulating a USB device.
You can emulate one of the existing devices
(use **umap2list** to see the available devices):

::

    $ umap2emulate -P fd:/dev/ttyUSB0 -C mass_storage

or emulate your own device:

::

    $ umap2emulate -P fd:/dev/ttyUSB0 -C ~/my_mass_storage.py

A detailed guide to add your device will be added soon,
in the meantime, you can take a look at umap2 devices
under *umap2/dev/*

Device Support Scanning
~~~~~~~~~~~~~~~~~~~~~~~

Umap2 can attempt to detect what types of USB devices
are supported by the host.
It is done by emulating each device that is implemented in Umap2
for a short period of time,
and checking whether a device-specific message was sent.

::

    $ umap2scan -P fd:/dev/ttyUSB0

Vendor Specific Device Support Scanning
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In addition for scanning support of various device classes,
Umap2 can scan the host for support of vendor specific devices.

Vendor specific scanning helps identifying the vendor specific drivers
that are available on the host.

This can be done using the current Umap2 VID-PID DB (still working on it),
or another file in the same format:

::

    $ umap2vsscan -P fd:/dev/ttyUSB0 -d $UMAP2_DIR/data/vid_pid_db.py

Or by scanning a specific vid-pid range -
in this example -
scan for each combination of VID from 0x1001 to 0x1004
and PID from 0x0000 to 0xffff:

::

    $ umap2vsscan -P fd:/dev/ttyUSB0 -s 1001-1004:0000-ffff

Any patches/additions to the vid_pid_db.py file are very welcome!

Fuzzing
~~~~~~~

A detailed guide for fuzzing using Umap2 can be found in 
`docs/fuzzing.rst <https://github.com/nccgroup/umap2/blob/master/docs/fuzzing.rst>`_

Fuzzing with Umap2 is composed of three steps,
which might be unified into a single script in the future.

1. Find out what is the order of messages
   for the host you want to fuzz and the
   USB device that you emulate:

   ::

        $ umap2stages -P fd:/dev/ttyUSB0 -C keyboard -s keyboard.stages

2. Start the kitty fuzzer in a separate shell,
   and provide it with the stages generated in step 1.

   ::

        $ umap2kitty -s keyboard.stages

3. Start the umap2 keyboard emulation in fuzz mode

   ::

        $ umap2fuzz -P fd:/dev/ttyUSB0 -C keyboard

After stage 3 is performed, the fuzzing session will begin.

Note About MTP fuzzing
++++++++++++++++++++++

While umap2 may be used to emulate and discover MTP devices
(see "Soft dependencies" section of this README),
it does not fuzz the MTP layer at this point.
In order to fuzz the MTP layer,
you can use the fuzzer embedded in the MTP library.
We plan to support MTP fuzzing directly from umap2 in future releases.

Host OS Detection
~~~~~~~~~~~~~~~~~

TBD

Toubleshooting
--------------

If you have issues with Umap2, try the
`troubleshooting section <https://github.com/nccgroup/umap2/blob/master/docs/troubleshooting.rst>`_

Raspdancer
--------------
You need SPI-Py <https://github.com/lthiery/SPI-Py> and GPIO python libraries.
Use phy `rd`
