Troubleshooting
===============

Facedancer Communication
------------------------

In some cases, there are communication issues with the facedancer.
It might not be clear that that's the problem at first,
as the error that is raised is
"struct.error: unpack requires a string argument of length 4, line 39 in facedancer.py"
but it indicates that not enough bytes were read from the Facedancer hardware.

This error can be raised by variuos issues:

1. Outdated Firmware

   Download and install an updated firmware on the facedancer, as described here:
   http://int3.cc/blogs/news/8217777-flashing-the-facedancer21

2. Bad driver state

   If unexcpected data was sent to the facedancer, it might lose synchronization.
   Remove and re-insert the USB cables (on both sides of the facedancer).

3. Faulty USB connection

   Sometimes the link is not good enough.
   Replace the USB cable and try different USB port/hub.

4. Faulty hardware

   If the Facedancer was assembled by hand, there might be a loose connection
   on the board, inspect the Facedancer board to make sure all connections are
   stable and that there are no shorts.

