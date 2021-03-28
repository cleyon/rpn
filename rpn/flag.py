'''
#############################################################################
#
#       F L A G S
#
#############################################################################
'''

import rpn.globl
from   rpn.debug import dbg, typename, whoami
from rpn.exception import *


F_TVM_CONTINUOUS     =   8 # Set: Continuous compounding Clear: Discrete compounding
F_TVM_BEGIN_MODE     =   9 # Set: Begin (annuity due)    Clear: End (ordinary annuity)
F_SHOW_X             =  19 # Set: Show X at prompt       Clear: do not show X
F_DEBUG_ENABLED      =  20
F_PRINTER_ENABLED    =  21
F_DECIMAL_POINT      =  28 # Set: 123,456.123  (US)      Clear: 123.456,123  (Europe)
F_DIGIT_GROUPING     =  29 # Set: 1,234,567.01           Clear: 1234567.01
F_DISP_FIX           =  40 # 40 & 41 Set: STD
F_DISP_ENG           =  41 # 40 & 41 Clear: SCI
F_GRAD               =  42
F_RAD                =  43
F_PRINTER_EXISTS     =  55

FENCE              =  30 # Flags >= FLAG_FENCE cannot set set by the user
MAX                =  56

flags_vec = 0


def clear_flag(flag):
    global flags_vec                    # pylint: disable=global-statement
    if flag < 0 or flag >= MAX:
        raise FatalErr("{}: Flag {} out of range".format(rpn.debug.whoami(), flag))
    if flag == F_DEBUG_ENABLED:
        rpn.debug.debug_enabled = False
    flags_vec &= ~(1<<flag)

def set_flag(flag):
    global flags_vec                    # pylint: disable=global-statement
    if flag < 0 or flag >= MAX:
        raise FatalErr("{}: Flag {} out of range".format(rpn.debug.whoami(), flag))
    if flag == F_DEBUG_ENABLED:
        rpn.debug.debug_enabled = True
    flags_vec |= (1<<flag)

def toggle_flag(flag):
    if flag < 0 or flag >= MAX:
        raise FatalErr("{}: Flag {} out of range".format(rpn.debug.whoami(), flag))
    if flag_set_p(flag):
        clear_flag(flag)
    else:
        set_flag(flag)

def copy_flag(src_flag, dst_flag):
    if src_flag < 0 or src_flag >= MAX:
        raise FatalErr("{}: Flag {} out of range".format(rpn.debug.whoami(), src_flag))
    if dst_flag < 0 or dst_flag >= MAX:
        raise FatalErr("{}: Flag {} out of range".format(rpn.debug.whoami(), dst_flag))
    if flag_set_p(src_flag):
        set_flag(dst_flag)
    else:
        clear_flag(dst_flag)

def flag_int_value(flag):
    if flag < 0 or flag >= MAX:
        raise FatalErr("{}: Flag {} out of range".format(rpn.debug.whoami(), flag))
    return rpn.globl.bool_to_int(flag_set_p(flag))

def flag_set_p(flag):
    if flag < 0 or flag >= MAX:
        raise FatalErr("{}: Flag {} out of range".format(rpn.debug.whoami(), flag))
    return bool(flags_vec & 1<<flag != 0)
