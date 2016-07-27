ccflags-y := -I$(srctree)/drivers/usb/gadget/
ccflags-y += -I$(srctree)/drivers/usb/gadget/udc/
ccflags-y += -I$(srctree)/drivers/usb/gadget/function/

#
# We need this trick to set the name of the module to
# gadgetfs and not inode
#
obj-m+=gadgetfs.o
gadgetfs-objs=inode.o
codepath=/lib/modules/$(shell uname -r)/build/
aux=
modules:
	make $(aux) -C $(codepath) M=$(PWD) modules
clean:
	make $(aux) -C $(codepath) M=$(PWD) clean
