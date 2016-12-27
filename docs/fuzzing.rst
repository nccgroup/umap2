Fuzzing USB Hosts
=================

This document describes the full process of fuzzing USB hosts with Umap2.

Fuzzing a host consists of three basic steps.
While the fuzzer does not require you to write any code,
there are some options that can be passed to it in order to tune it.
The first section describes those basic steps,
the second section describes how to tune it to a spceific environment
and the third section provides some basic information on how to extend it.


Fuzzing process
---------------

Step 1 - Select Device
~~~~~~~~~~~~~~~~~~~~~~

First, you need to detrmine which driver/subsystem/class you want to fuzz.
You can find out what is supported on the host by running ``umap2scan``:

::

    $ umap2scan -P <PHY>

Step 2 - Record Valid Flow
~~~~~~~~~~~~~~~~~~~~~~~~~~

Now that you know what is supported,
and decided on a device that you want to emulate in your fuzzing,
you need to record the basic communication flow of the host with this device.
This step is essential for effective fuzzing,
as different hosts communicate with the same device in different ways.
The tool to do that is ``umap2stages``:

::

    $ umap2stages -P <PHY> -C <CLASS> -s <STAGES_FILE_NAME>

Step 3 - Start Fuzzing
~~~~~~~~~~~~~~~~~~~~~~

The last step is to actually start fuzzing.
This step is a little more complicated.

First, you need to start the kitty-based fuzzer backend in a separate shell:

::

    $ umap2kitty -s <STAGES_FILE_NAME>

There are some command line options available in kitty,
you can see them in the next section.

Now you need to start the umap2 stack.
Once it is up, it will signal the fuzzer backend
and the fuzzing proces will begin

::

    $ umap2fuzz -P <PHY> -C <CLASS>


Monitor Progress
~~~~~~~~~~~~~~~~

The output from ``umap2kitty`` and ``umap2fuzz`` is not meant as a UI.
If you want to watch the fuzzing session, use Kitty's web UI,
which is available either from the browser at http://localhost:26001.
Or using ``kitty-web-client`` which is a command line tool to retrieve
fuzzing information from kitty.

There you can watch the current status of fuzzing as well as read and retrieve
reports about failed tests.


Fuzzing Options
---------------

By passing command line parameters to ``umap2kitty`` you can achieve a better fuzzing session.
Here are some examples of such parameters.
To see all of the fuzzer options, run

::

    $ umap2kitty -s <STAGES> -k "--help"

           These are the options to the kitty fuzzer object, not the options to the runner.

        Usage:
            fuzzer [options] [-v ...]

        Options:
            -d --delay <delay>              delay between tests in secodes, float number
            -f --session <session-file>     session file name to use
            -n --no-env-test                don't perform environment test before the fuzzing session
            -r --retest <session-file>      retest failed/error tests from a session file
            -t --test-list <test-list>      a comma delimited test list string of the form "-10,12,15-20,30-"
            -v --verbose                    be more verbose in the log

        Removed options:
            end, start - use --test-list instead


Fuzzing Session File
~~~~~~~~~~~~~~~~~~~~

Fuzzing session file allows you to store the results of a run. It has three main uses:

1. Continue a fuzzing session that was stopped for some reason:
    ::

        $ umap2kitty -s <STAGES> -k "-f mysessionfile"
        # closed terminal by mistake :(
        #
        # Continue from the same place :)
        $ umap2kitty -s <STAGES> -k "-f mysessionfile"

2. Review the failures from finished session (If for some reason the reports were not retreived).
3. **Most important** - retest failures. This allows you to retest crashes and make sure that the crash is reproducible, or debug it, or test on a new version.
    ::

        # first run - failures on tests 1,7,10
        $ umap2kitty -s <STAGES> -k "-f mysessionfile"

        # re-run only failures (tests 1,7,10)
        $ umap2kitty -s <STAGES> -k "-r mysessionfile"


Running Only a Subset of the tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Select which tests to run (by number).

For example - run tests 1,2,3,45,7,9 and everything above 100

::

    $ umap2kitty -s <STAGES> -k "-t 1-5,7,9,100-"


