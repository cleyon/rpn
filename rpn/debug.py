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
    "#in"                       : 0,
    "$in"                       : 0,
    "DoLoop#__call__"           : 0,
    "Scope#define_variable"     : 1,
    "Sequence#__call__"         : 0,
    "Sequence#__init__"         : 0,
    "Word#__init__"             : 0,
    "ascii"                     : 2,
    "catch"                     : 0,
    "defvar"                    : 1,
    "eval_string"               : 0,
    "have_module"               : 1,
    "hide"                      : 1,
    "load_file"                 : 0,
    "lookup_variable"           : 0,
    "lookup_vname"              : 1,
    "lookup_word"               : 1,
    "p_colon_define_word"       : 1,
    "p_executable"              : 0,
    "p_executable_list"         : 0,
    "p_execute"                 : 0,
    "p_fetch_var"               : 1,
    "p_locals"                  : 1,
    "p_store_var"               : 1,
    "p_variable"                : 1,
    "parse"                     : 0,
    "prompt"                    : 0,
    "scope"                     : 2,
    "show"                      : 0,
    "token"                     : 3,
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
