Umap2 Features
==============

The feature lists below refer to the script **bin/umap2_runner.py**.
However, it is very likely that most features
will require changes/additions in the umap2 package.

Supported features
------------------

1. USB device emulation
    - audio
    - cdc
    - ftdi
    - hub
    - image
    - keyboard
    - mass-storage
    - mtp
    - printer
    - smartcard

Missing features
----------------

1. OS detection - guess the host OS from USB trafic characteristics
2. Scanning - scan the host for supported devices
3. Fuzzing - emulate a USB device, but fuzz the responses to the host
