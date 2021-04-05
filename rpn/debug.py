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


debug_enabled = False

debug_levels = {
    "#in"                       : 0,
    "$in"                       : 0,
    "*"                         : 3,
    "+"                         : 3,
    "-"                         : 3,
    "/"                         : 3,
    "DoLoop#__call__"           : 0,
    "List#__call__"             : 0,
    "Scope#define_variable"     : 0,
    "Sequence#__call__"         : 0,
    "Sequence#__init__"         : 0,
    "Symbol#__call__"           : 0,
    "Symbol#eval"               : 0,
    "Word#__init__"             : 0,
    "ascii"                     : 0,
    "catch"                     : 0,
    "cross"                     : 0,
   #"d0"                        : -1,
   #"d1"                        : 1,
   #"d2"                        : 2,
   #"d3"                        : 3,
   #"d4"                        : 4,
   #"d5"                        : 5,
   #"d6"                        : 6,
   #"d7"                        : 7,
   #"d8"                        : 8,
   #"d9"                        : 9,
    "defvar"                    : 0,
    "eval_string"               : 0,
    "execute"                   : 0,
    "from_python_list"          : 0,    # Vector
    "from_rpn_List"             : 0,    # Vector
    "from_string"               : 0,
    "have_module"               : 0,
    "hide"                      : 0,
    "load_file"                 : 0,
    "lookup_variable"           : 0,
    "lookup_vname"              : 0,
    "lookup_word"               : 0,
    "next_token"                : 0,
    "p_colon_define_word"       : 0,
    "p_executable"              : 0,
    "p_executable_list"         : 0,
    "p_execute"                 : 0,
    "p_fetch_var"               : 0,
    "p_locals"                  : 0,
    "p_store_var"               : 0,
    "p_variable"                : 0,
    "parse"                     : 0,
    "prompt"                    : 0,
    "scope"                     : 0,
    "show"                      : 0,
    "to_rpn_class"              : 0,
    "token"                     : 0,
    "trace"                     : 0,
    "tvm"                       : 0,
    "unit"                      : 0,
    "unit#parse"                : 0,
}


def dbg(resource, level=1, text=None):
    '''Note that a level of -1 will always be True and possibly print the text.
This can be useful to quickly turn a debugging statement on unilaterally;
just change "dbg(res,1,xxx)" to "dbg(res,-1,xxx)".'''
    if resource not in debug_levels:
        print("dbg: Resource '{}' not valid".format(resource)) # OK
        traceback.print_stack(file=sys.stderr)
        sys.exit(1)             # Harsh!

    if not debug_enabled or level == 0:
        return False
    flag = debug_levels[resource] >= level
    if flag and text is not None:
        print("{}".format(text), flush=True) # OK
    return flag


def set_debug_level(resource, level=1):
    if resource not in debug_levels:
        print("set_debug_level: Resource '{}' not valid".format(resource)) # OK
        traceback.print_stack(file=sys.stderr)
        sys.exit(1)             # Harsh!

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
