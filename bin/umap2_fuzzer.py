#!/usr/bin/env python
'''
Usage:
    ./fuzzer.py --type=<fuzzing_type> [--disconnect-delays=<pre,post>] [--kitty-options=<kitty-options>]

Options:
    -k --kitty-options <kitty-options>  options for the kitty fuzzer, use --kitty-options=--help to get a full list
    -t --type <fuzzing_type>            type of fuzzing to perform
    --disconnect-delays=<pre,post>      number of seconds to wait in the post_test before and after disconnecting
                                        the device (might be necessary in order for failures to be matched with
                                        the correct test)   [default: 0.0,0.0]

Possible fuzzing types: enmeration, smartcard, mass-storage

This example stores the mutations in files under ./tmp/
It also demonstrate how to use kitty fuzzer command line options.
'''
import docopt
from kitty.remote.rpc import RpcServer
from kitty.fuzzers import ClientFuzzer
from kitty.targets import ClientTarget
from kitty.interfaces import WebInterface
from kitty.model import GraphModel

from katnip.templates.usb import *

from controller import UmapController


def get_model(options):
    fuzzing_type = options['--type']
    model = GraphModel()
    if fuzzing_type == 'enumeration':
        model.connect(device_descriptor)
        model.connect(interface_descriptor)
        model.connect(endpoint_descriptor)
        model.connect(string_descriptor)
        model.connect(string_descriptor_zero)
    elif fuzzing_type == 'smartcard':
        model.connect(smartcard_Escape_response)
        model.connect(smartcard_GetParameters_response)
        model.connect(smartcard_GetSlotStatus_response)
        model.connect(smartcard_IccClock_response)
        model.connect(smartcard_IccPowerOff_response)
        model.connect(smartcard_IccPowerOn_response)
        model.connect(smartcard_SetParameters_response)
        model.connect(smartcard_T0APDU_response)
        model.connect(smartcard_XfrBlock_response)
    elif fuzzing_type == 'mass-storage':
        model.connect(scsi_inquiry_response)
        model.connect(scsi_mode_sense_10_response)
        model.connect(scsi_mode_sense_6_response)
        model.connect(scsi_read_10_response)
        model.connect(scsi_read_capacity_10_response)
        model.connect(scsi_read_format_capacities)
        model.connect(scsi_request_sense_response)
    else:
        msg = '''invalid fuzzing type, should be one of ['enumeration']'''
        raise Exception(msg)
    return model

def get_controller(options):
    try:
        pre_disconnect_delay, post_disconnect_delay = \
            [float(f) for f in options['--disconnect-delays'].split(',')]
    except ValueError:
        msg = 'Please specify the --disconnect_delays as two comma-separated floats'
        raise Exception(msg)
    return UmapController(pre_disconnect_delay,post_disconnect_delay)

def main():
    options = docopt.docopt(__doc__)
    fuzzer = ClientFuzzer(name='UmapFuzzer', option_line=options['--kitty-options'])
    fuzzer.set_interface(WebInterface())

    target = ClientTarget(name='USBTarget')
    target.set_controller(get_controller(options))
    target.set_mutation_server_timeout(10)

    model = get_model(options)
    fuzzer.set_model(model)
    fuzzer.set_target(target)

    remote = RpcServer(host='localhost', port=26007, impl=fuzzer)
    remote.start()


if __name__ == '__main__':
    main()
