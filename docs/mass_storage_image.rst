Emulating Mass Storage Device
=============================

In order to emulate a mass storafe device umap needs a disk image,
below are instruction on how to create such an image under linux.

Note that those actions should be performed as root.

::

    # fallocate -l 100M stick.img
    # fdisk stick.img
    # losetup -f --show stick.img
    # kpartx -a /dev/loopX
    # mkfs.XXX /dev/mapper/loopXpY
    # mount /dev/mapper/loopXpY /mnt/point
        do stuff on /mnt/point
    # umount /mnt/point
    # kpartx -d /dev/loopX
    # losetup -d /dev/loopX

