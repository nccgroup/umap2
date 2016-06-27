'''
Audio device templates
'''
from kitty.model import UInt8, LE16, RandomBytes, BitField
from kitty.model import Template, Repeat
from templates_hid import GenerateHidReport
from templates_generic import Descriptor, SizedPt, DynamicInt
from templates_enum import _DescriptorTypes


class _AC_DescriptorSubTypes:  # AC Interface Descriptor Subtype

    '''Descriptor sub types [audio10.pdf table A-5]'''

    AC_DESCRIPTOR_UNDEFINED = 0x00
    HEADER = 0x01
    INPUT_TERMINAL = 0x02
    OUTPUT_TERMINAL = 0x03
    MIXER_UNIT = 0x04
    SELECTOR_UNIT = 0x05
    FEATURE_UNIT = 0x06
    PROCESSING_UNIT = 0x07
    EXTENSION_UNIT = 0x08


class _AS_DescriptorSubTypes:  # AS Interface Descriptor Subtype

    '''Descriptor sub types [audio10.pdf table A-6]'''

    AS_DESCRIPTOR_UNDEFINED = 0x00
    AS_GENERAL = 0x01
    FORMAT_TYPE = 0x02
    FORMAT_SPECIFIC = 0x03


# TODO: audio_ep2_buffer_available

# TODO: remove?
audio_header_descriptor = Descriptor(
    name='audio_header_descriptor',
    descriptor_type=_DescriptorTypes.CS_INTERFACE,
    fields=[
        UInt8(name='bDesciptorSubType', value=_AC_DescriptorSubTypes.HEADER),
        LE16(name='bcdADC', value=0x0100),
        LE16(name='wTotalLength', value=0x1e),
        UInt8(name='bInCollection', value=0x1),
        Repeat(UInt8(name='baInterfaceNrX', value=1), 0, 247)
    ])

# TODO: remove?
audio_input_terminal_descriptor = Descriptor(
    descriptor_type=_DescriptorTypes.CS_INTERFACE,
    name='audio_input_terminal_descriptor',
    fields=[
        UInt8(name='bDesciptorSubType', value=_AC_DescriptorSubTypes.INPUT_TERMINAL),
        UInt8(name='bTerminalID', value=0x00),
        LE16(name='wTerminalType', value=0x0206),  # termt10.pdf table 2-2
        UInt8(name='bAssocTerminal', value=0x00),
        UInt8(name='bNrChannels', value=0x01),
        LE16(name='wChannelConfig', value=0x0101),
        UInt8(name='iChannelNames', value=0x00),
        UInt8(name='iTerminal', value=0x00)
    ])

# TODO: remove?
audio_output_terminal_descriptor = Descriptor(
    name='audio_output_terminal_descriptor',
    descriptor_type=_DescriptorTypes.CS_INTERFACE,
    fields=[
        UInt8(name='bDesciptorSubType', value=_AC_DescriptorSubTypes.OUTPUT_TERMINAL),
        UInt8(name='bTerminalID', value=0x00),
        LE16(name='wTerminalType', value=0x0307),  # termt10.pdf table 2-3
        UInt8(name='bAssocTerminal', value=0x00),
        UInt8(name='bSourceID', value=0x01),
        UInt8(name='iTerminal', value=0x00)
    ])

# Table 4-7
# TODO: remove?
audio_feature_unit_descriptor = Descriptor(
    name='audio_feature_unit_descriptor',
    descriptor_type=_DescriptorTypes.CS_INTERFACE,
    fields=[
        UInt8(name='bDesciptorSubType', value=_AC_DescriptorSubTypes.FEATURE_UNIT),
        UInt8(name='bUnitID', value=0x00),
        UInt8(name='bSourceID', value=0x00),
        SizedPt(name='bmaControls',
                fields=RandomBytes(name='bmaControlsX', value='\x00', min_length=0, step=17, max_length=249)),
        UInt8(name='iFeature', value=0x00)
    ])


# Table 4-19
# TODO: remove?
audio_as_interface_descriptor = Descriptor(
    name='audio_as_interface_descriptor',
    descriptor_type=_DescriptorTypes.CS_INTERFACE,
    fields=[
        UInt8(name='bDesciptorSubType', value=_AS_DescriptorSubTypes.AS_GENERAL),
        UInt8(name='bTerminalLink', value=0x00),
        UInt8(name='bDelay', value=0x00),
        LE16(name='wFormatTag', value=0x0001)
    ])


# TODO: remove?
audio_as_format_type_descriptor = Descriptor(
    name='audio_as_format_type_descriptor',
    descriptor_type=_DescriptorTypes.CS_INTERFACE,
    fields=[
        UInt8(name='bDesciptorSubType', value=_AS_DescriptorSubTypes.FORMAT_TYPE),
        UInt8(name='bFormatType', value=0x01),
        UInt8(name='bNrChannels', value=0x01),
        UInt8(name='bSubFrameSize', value=0x02),
        UInt8(name='bBitResolution', value=0x10),
        UInt8(name='bSamFreqType', value=0x01),
        BitField(name='tSamFreq', length=24, value=0x01F40)
    ])


audio_hid_descriptor = Descriptor(
    name='audio_hid_descriptor',
    descriptor_type=_DescriptorTypes.HID,
    fields=[
        DynamicInt('bcdHID', LE16(value=0x1001)),
        DynamicInt('bCountryCode', UInt8(value=0x00)),
        DynamicInt('bNumDescriptors', UInt8(value=0x01)),
        DynamicInt('bDescriptorType2', UInt8(value=_DescriptorTypes.HID_REPORT)),
        DynamicInt('wDescriptorLength', LE16(value=0x2b)),
    ]
)

# this descriptor is based on umap
# https://github.com/nccgroup/umap
# commit 3ad812135f8c34dcde0e055d1fefe30500196c0f
audio_report_descriptor = Template(
    name='audio_report_descriptor',
    fields=GenerateHidReport(
        '050C0901A1011500250109E909EA75019502810209E209008106050B092095018142050C09009503810226FF000900750895038102090095049102C0'.decode('hex')
    )
)
