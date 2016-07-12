#!/bin/sh

unload_driver() {
    if lsmod | grep $1 > /dev/null; then
        echo "- Unloading driver: $1"
        modprobe -r $1
    fi
}

umount_dir() {
    if mount | grep $1 > /dev/null; then
        echo "- Unmounting $1"
        umount $1
    fi
}

echo "- Stoping services"
systemctl stop serial-getty@ttyGS0.service > /dev/null

[ -d /sys/kernel/config ] && umount_dir /sys/kernel/config

echo "- Unloading USB gadget modules"
unload_driver g_multi
unload_driver usb_f_acm
unload_driver u_serial
unload_driver usb_f_rndis
unload_driver usb_f_mass_storage
unload_driver u_ether
unload_driver libcomposite


if [ -d /dev/gadget ]; then
    umount_dir /dev/gadget
    unload_driver gadgetfs
else
    mkdir /dev/gadget
fi
echo "- Loading modified gadgetfs driver"
insmod /root/gadgetfs.ko
echo "- Mounting gadgetfs to /dev/gadget"
mount -t gadgetfs none /dev/gadget

echo "-- System is ready for Umap2 --"
