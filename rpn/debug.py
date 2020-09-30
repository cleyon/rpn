'''
#############################################################################
#
#       D E B U G G I N G
#
#############################################################################
'''

import inspect
import sys
import traceback

import rpn.flag


debug_levels = {
    "catch"                     : 0,
    "defvar"                    : 0,
    "dollar_in"                 : 0,
    "eval_string"               : 0,
    "have_module"               : 1,
    "hide"                      : 1,
    "load_file"                 : 0,
    "lookup_varname"            : 0,
    "lookup_variable"           : 0,
    "number_in"                 : 0,
    "p_define_word"             : 1,
    "p_executable"              : 0,
    "p_executables_list"        : 0,
    "p_execute"                 : 0,
    "p_fetch_var"               : 0,
    "p_locals_scope"            : 1,
    "p_store_var"               : 0,
    "p_variable"                : 0,
    "parse"                     : 0,
    "prompt"                    : 0,
    "Do_Loop#__call__"          : 0,
    "Scope#define_variable"     : 0,
    "Sequence#__call__"         : 0,
    "Sequence#__init__"         : 0,
    "Word#__init__"             : 0,
    "scope"                     : 0,
    "show"                      : 0,
    "token"                     : 0,
    "trace"                     : 0,
    "tvm"                       : 0,
}


def dbg(resource, level=1, text=None):
    '''Note that a level of -1 will always be True and possibly print the text.
This can be useful to quickly turn a debugging statement on unilaterally;
just change "dbg(res,1,xxx)" to "dbg(res,-1,xxx)".'''
    # global debug_levels

    if resource not in debug_levels:
        print("dbg: Resource '{}' not valid".format(resource)) # OK
        traceback.print_stack(file=sys.stderr)
        sys.exit(1)             # Harsh!

    if not rpn.flag.flag_set_p(rpn.flag.F_DEBUG_ENABLED) or level == 0:
        return False
    flag = debug_levels[resource] >= level
    if flag and text is not None:
        print("{}".format(text), flush=True) # OK
    return flag


def set_debug_level(resource, level=1):
    # global debug_levels

    if resource not in debug_levels:
        print("set_debug_level: Resource '{}' not valid".format(resource)) # OK
        traceback.print_stack(file=sys.stderr)
        sys.exit(1)             # Harsh!

    if level < 0 or level > 9:
        raise rpn.exception.FatalErr("set_debug_level: Level {} out of range (0..9 expected)".format(level))
    debug_levels[resource] = level


def typename(s):
    t = type(s).__name__
    return t


def whoami():
    who_i_am = ""
    previous_frame = inspect.currentframe().f_back
    if "self" in previous_frame.f_locals:
        who_i_am += previous_frame.f_locals["self"].__class__.__name__ + "#"
    who_i_am += previous_frame.f_code.co_name
    if who_i_am[:2] == "w_":
        who_i_am = who_i_am[2:]
    return who_i_am
