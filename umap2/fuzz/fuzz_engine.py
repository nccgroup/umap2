#!/usr/bin/env python
'''
Usage:
    umap2kitty -s <stage-file> [-d <pre,post>] [-k <options>]

Options:
    -k --kitty-options <options>        options for the kitty fuzzer, use -k -h to get a full list
    -d --disconnect-delays=<pre,post>   number of seconds to wait in the post_test before and after
                                        disconnecting the device (might be necessary in order for
                                        failures to be matched with the correct test) [default: 0.0,0.0]
    -s --stage-file <stage-file>        path to stage trace from umap emulation run
'''
import docopt
from kitty.remote.rpc import RpcServer
from kitty.fuzzers import ClientFuzzer
from kitty.targets import ClientTarget
from kitty.interfaces import WebInterface
from kitty.model import GraphModel
from kitty.model import Template, Meta, String, UInt32

import katnip.templates.usb as usb_templates

from controller import UmapController


def enumerate_templates(module):
    '''
    :return: a list of templates that are in a module
    '''
    member_names = sorted(dir(module))
    templates = {}
    for name in member_names:
        member = getattr(module, name)
        if isinstance(member, Template):
            templates[member.name] = member
        elif isinstance(member, dict):
            for k, item in member.items():
                if isinstance(item, Template):
                    templates[item.name] = item
        elif isinstance(member, list):
            for item in member:
                if isinstance(item, Template):
                    templates[item.name] = item
    return templates


def get_stages(stage_file):
    with open(stage_file, 'r') as f:
        stages = [l.rstrip() for l in f.readlines()]
    stage_count = {}
    for stage in stages:
        stage_count[stage] = stages.count(stage)
    return stage_count


def add_stage(g, stage, template, count):
    '''
    :param g: the GraphModel object
    :param stage: stage name
    :param template: the actual template
    :param count: the stage count

    :example:

        for the call add_stage(g, 'X', x, 4) we will create the following
        graph:

        ::

            x
            p1 -> x
            p1 -> p2 -> x
            p1 -> p2 -> p3 -> x
    '''
    g.connect(template)
    pseudos = [
        # workaround for a PseudoTemplate bug in kitty 0.6.9
        # TODO: move to PseudoTemplate in next kitty version
        Template(
            name=stage,
            fields=Meta(fields=[
                String(value=stage),
                UInt32(value=i)
            ]),
            fuzzable=False
        ) for i in range(count - 1)
    ]
    if pseudos:
        g.connect(pseudos[0])
        for i in range(len(pseudos) - 1):
            g.connect(pseudos[i], pseudos[i + 1])
            g.connect(pseudos[i], template)
        g.connect(pseudos[-1], template)


def get_model(options):
    stage_file = options['--stage-file']
    stages = get_stages(stage_file)
    templates = enumerate_templates(usb_templates)
    g = GraphModel('usb model (%s)' % (stage_file))
    for stage in stages:
        if stage in templates:
            stage_template = templates[stage]
            stage_count = min(stages[stage], 4)
            add_stage(g, stage, stage_template, stage_count)
    return g


def get_controller(options):
    try:
        pre_disconnect_delay, post_disconnect_delay = \
            [float(f) for f in options['--disconnect-delays'].split(',')]
    except ValueError:
        msg = 'Please specify the --disconnect_delays as two comma-separated floats'
        raise Exception(msg)
    return UmapController(pre_disconnect_delay, post_disconnect_delay)


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
