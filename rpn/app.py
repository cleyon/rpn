'''
#############################################################################
#
#       M A I N   L O O P   &   P R I M A R Y   F U N C T I O N S
#
#############################################################################
'''

import getopt
import os
import random
import signal
import sys

try:
    import numpy as np          # pylint: disable=import-error
except ImportError:
    pass

# Check if SciPy is available
try:
    import scipy.integrate      # pylint: disable=import-error
    import scipy.optimize       # pylint: disable=import-error
except ModuleNotFoundError:
    pass

# # Check if Matplotlib is available
# try:
#     import matplotlib           # pylint: disable=import-error
# except ModuleNotFoundError:
#     pass

from   rpn.debug     import dbg, typename
from   rpn.exception import *   # pylint: disable=wildcard-import
import rpn.flag
import rpn.globl
import rpn.tvm
import rpn.type
import rpn.unit
import rpn.util
import rpn.word


disable_all_extensions = False
load_init_file = True
want_debug = False


def usage():
    print("""\
Usage: rpn [-d] [-f FILE] [-i] [-l FILE] [-q] [-V] cmds...

-d        Enable debugging
-f FILE   Load FILE and exit
-i        Force interactive mode
-l FILE   Load FILE and continue
-q        Do not load init file (~/.rpnrc)
-Q        Disable all extensions (implies -q)
-V        Display version information""")
    sys.exit(64)                # EX_USAGE


def initialize(rpndir, argv):
    global disable_all_extensions # pylint: disable=global-statement
    global load_init_file         # pylint: disable=global-statement

    # Set up low level stuff, stacks, variables
    sys.setrecursionlimit(2000) # default is 10002
    random.seed()
    rpn.globl.push_scope(rpn.globl.root_scope, "Root scope")
    rpn.globl.disp_stack.push(rpn.util.DisplayConfig())
    reg_set = rpn.util.RegisterSet()
    reg_set.size = 17           # R00..R16
    reg_set.sreg = 11
    rpn.globl.reg_stack.push(reg_set)
    rpn.word.w_std('std')
    rpn.unit.define_units()
    define_variables()

    # Set up signal handling
    signal.signal(signal.SIGINT,   sigint_handler)
    signal.signal(signal.SIGQUIT,  sigquit_handler)
    signal.signal(signal.SIGWINCH, sigwinch_handler)
    sigwinch_handler(0, 0)     # Read & define ROWS and COLS via stty(1)

    # Set initial conditions
    rpn.globl.eval_string("clreg clflag clfin")
    rpn.flag.set_flag(rpn.flag.F_SHOW_PROMPT)

    # Define built-in secondary (protected) words
    if not disable_all_extensions:
        try:
            load_file(os.path.join(rpndir, "secondary.rpn"))
        except RuntimeErr as err_f_opt:
            rpn.globl.lnwriteln(str(err_f_opt))
            sys.exit(1)

    # Switch to user mode, where words and variables are no longer
    # protected, and define built-in tertiary (non-protected) words
    rpn.globl.default_protected = False
    if not disable_all_extensions:
        try:
            load_file(os.path.join(rpndir, "tertiary.rpn"))
        except RuntimeErr as err_f_opt:
            rpn.globl.lnwriteln(str(err_f_opt))
            sys.exit(1)

    # Parse command line
    argv = parse_args(argv)

    # Hopefully load the user's init file
    if load_init_file:
        init_file = os.path.expanduser("~/.rpnrc")
        if os.path.isfile(init_file):
            (rpnrc, _) = rpn.globl.lookup_variable('RPNRC')
            rpnrc.obj = rpn.type.String(init_file)
            load_file(init_file)

    # rpn.globl.lnwriteln("--------------------------------")
    if len(argv) > 0:
        s = " ".join(argv)
        rpn.globl.eval_string(s)
        if rpn.globl.interactive is None:
            rpn.globl.interactive = False
    else:
        # No command args, so maybe go interactive
        if rpn.globl.interactive is None:
            rpn.globl.interactive = True

    return rpn.globl.interactive


def define_variables():
    # Variables defined here are all protected=True by default
    rpn.globl.sharpout = rpn.globl.defvar('#OUT', rpn.type.Integer(0),
                                          readonly=True, noshadow=True)
    rpn.tvm.CF = rpn.globl.defvar('CF', rpn.type.Integer(1),
                                  noshadow=True,
                                  pre_hooks=[pre_require_int, pre_require_positive],
                                  post_hooks=[post_label_with_identifier],
                                  doc="Compounding Frequency")
    rpn.globl.scr_cols = rpn.globl.defvar('COLS', rpn.type.Integer(0),
                                          pre_hooks=[pre_require_int, pre_require_positive])
    rpn.tvm.FV = rpn.globl.defvar('FV', None,
                                  noshadow=True,
                                  pre_hooks=[pre_require_int_or_float],
                                  post_hooks=[post_label_with_identifier],
                                  doc="Future Value")
    rpn.tvm.INT = rpn.globl.defvar('INT', None,
                                   noshadow=True,
                                   pre_hooks=[pre_require_int_or_float, pre_require_non_negative],
                                   post_hooks=[post_label_with_identifier],
                                   doc="Interest rate")
    rpn.tvm.N = rpn.globl.defvar('N', None,
                                 noshadow=True,
                                 pre_hooks=[pre_require_int_or_float, pre_require_positive],
                                 post_hooks=[post_label_with_identifier],
                                 doc="Number of payments")
    rpn.globl.defvar('NUMPY', rpn.type.Integer(rpn.globl.bool_to_int(rpn.globl.have_module('numpy'))),
                     readonly=True, noshadow=True)
    if rpn.globl.have_module('numpy'):
        rpn.globl.defvar('NUMPY_VER', rpn.type.String(np.__version__),
                         readonly=True)
    rpn.tvm.PF = rpn.globl.defvar('PF', rpn.type.Integer(1),
                                  noshadow=True,
                                  pre_hooks=[pre_require_int, pre_require_positive],
                                  post_hooks=[post_label_with_identifier],
                                  doc="Payment Frequency")
    rpn.tvm.PMT = rpn.globl.defvar('PMT', None,
                                   noshadow=True,
                                   pre_hooks=[pre_require_int_or_float],
                                   post_hooks=[post_label_with_identifier],
                                   doc="Payment amount")
    rpn.tvm.PV = rpn.globl.defvar('PV', None,
                                  noshadow=True,
                                  pre_hooks=[pre_require_int_or_float],
                                  post_hooks=[post_label_with_identifier],
                                  doc="Present Value")
    rpn.globl.scr_rows = rpn.globl.defvar('ROWS', rpn.type.Integer(0),
                                          pre_hooks=[pre_require_int, pre_require_positive])
    rpn.globl.defvar('RPNRC', rpn.type.String(""),
                     readonly=True, hidden=True)
    rpn.globl.defvar('SCIPY', rpn.type.Integer(rpn.globl.bool_to_int(rpn.globl.have_module('scipy'))),
                     readonly=True, noshadow=True)
    if rpn.globl.have_module('scipy'):
        rpn.globl.defvar('SCIPY_VER', rpn.type.String(scipy.__version__),
                         readonly=True)
    rpn.globl.defvar('SIZE', rpn.type.Integer(rpn.globl.reg_stack.top().size),
                     noshadow=True, readonly=True,
                     # pre_hooks=[pre_validate_size_arg],
                     # post_hooks=[post_clear_newly_unveiled_registers]
                    )
    rpn.globl.defvar('SREG', rpn.type.Integer(rpn.globl.reg_stack.top().sreg),
                     pre_hooks=[pre_validate_sreg_arg])
    rpn.globl.defvar('VER', rpn.type.Float(rpn.globl.RPN_VERSION),
                     readonly=True, noshadow=True)


def parse_args(argv):
    global want_debug             # pylint: disable=global-statement
    global load_init_file         # pylint: disable=global-statement
    global disable_all_extensions # pylint: disable=global-statement

    try:
        opts, argv = getopt.getopt(argv, "dDf:il:qQV")
    except getopt.GetoptError as e:
        print(str(e))           # OK
        usage()

    for opt, arg in opts:
        if opt == "-d":         # Sets debug only when main_loop is ready
            want_debug = True
        elif opt == "-D":
            rpn.flag.set_flag(rpn.flag.F_DEBUG_ENABLED) # Debug immediately, useful for built-in words
        elif opt == "-f":
            if rpn.globl.interactive is None:
                rpn.globl.interactive = False
            try:
                load_file(arg)
            except RuntimeErr as err_f_opt:
                rpn.globl.lnwriteln(str(err_f_opt))
        elif opt == "-i":
            rpn.globl.interactive = True
        elif opt == "-l":
            try:
                load_file(arg)
            except RuntimeErr as err_l_opt:
                rpn.globl.lnwriteln(str(err_l_opt))
        elif opt == "-q":
            load_init_file = False
        elif opt == "-Q":
            load_init_file = False
            disable_all_extensions = True
        elif opt == "-V":
            rpn.globl.show_version_info()
            if rpn.globl.interactive is None:
                rpn.globl.interactive = False
        else:
            print("Unhandled option {}".format(opt)) # OK
            sys.exit(1)

    return argv


def load_file(filename):
    fn = filename
    if not os.path.isfile(fn):
        fn += ".rpn"
        if not os.path.isfile(fn):
            throw(X_NON_EXISTENT_FILE, "load", filename)

    try:
        with open(fn, "r") as file:
            contents = file.read()
    except PermissionError:
        throw(X_FILE_IO, "load", "Cannot open file '{}'".format(fn))
    else:
        dbg("load_file", 3, "load_file({})='{}'".format(fn, contents))
        rpn.globl.eval_string(contents)


def main_loop():
    global want_debug             # pylint: disable=global-statement
    global disable_all_extensions # pylint: disable=global-statement

    rpn.flag.clear_flag(rpn.flag.F_SHOW_X) # Reset, because some argv may have set it to True

    # Non-existence of ~/.rpnrc is indicator of novice mode
    (rpnrc, _) = rpn.globl.lookup_variable("RPNRC")
    if len(rpnrc.obj.value) == 0 and not disable_all_extensions:
        rpn.globl.lnwriteln("Type ? for information, help <word> for help on a specific word.")
        rpn.globl.lnwriteln("Type vlist for a list of all words, vars to see your variables.")
        rpn.globl.lnwriteln("Type .s to display the stack non-destructively, and bye to exit.")

    if not rpn.globl.param_stack.empty():
        if rpn.globl.param_stack.size() == 1:
            rpn.globl.eval_string("dup . cr")
        else:
            rpn.word.w_dot_s('.s')

    if want_debug:
        rpn.flag.set_flag(rpn.flag.F_DEBUG_ENABLED)
    while True:
        try:
            (error, tok_list) = generate_token_list()
        except StopIteration:
            return
        except TopLevel:
            continue
        if error is True:
            rpn.globl.lnwriteln("main_loop: Parse error: Could not get next token")
        s = " ".join([t.value for t in tok_list])
        dbg("parse", 1, "s='{}'".format(s))
        rpn.globl.eval_string(s)


def end_program():
    if rpn.globl.sharpout.obj.value != 0:
        rpn.globl.writeln()

    if not rpn.globl.string_stack.empty():
        if rpn.globl.string_stack.size() == 1:
            rpn.word.w_dollar_dot('$.')
            rpn.word.w_cr('cr')
        else:
            rpn.globl.lnwriteln("Strings:")
            rpn.word.w_dollar_dot_s('$.s')

    if not rpn.globl.param_stack.empty():
        if rpn.globl.param_stack.size() == 1:
            rpn.word.w_dot('.')
            rpn.word.w_cr('cr')
        else:
            rpn.globl.lnwriteln("Stack:")
            rpn.word.w_dot_s('.s')


def generate_token_list():
    '''Returns a tuple (flag, list)
flag is True if initial parse error, False if no error'''

    initial_parse_error = False
    rpn.globl.parse_stack.clear()
    tok_list = []
    depth = {
        'BRACKET' : 0,
        'PAREN'   : 0
    }

    while True:
        # Get next token
        tok = next(rpn.util.TokenMgr.next_token())
        dbg("token", 1, "token({},{})".format(tok.type, repr(tok.value)))

        # See if it's an immediate word; if so, call it
        if tok.type == 'IDENTIFIER':
            (word, _) = rpn.globl.lookup_word(tok.value)
            if word is not None and word.immediate():
                dbg("token", 3, "Word {} is immediate, calling...".format(word))
                word.__call__(word.name)
                continue
            tok_list.append(tok)

        # These need a second token or they will be very angry
        elif tok.type in ['AT_SIGN', 'CATCH', 'CONSTANT', 'EXCLAM', 'FORGET',
                          'HELP', 'HIDE', 'SHOW', 'UNDEF', 'VARIABLE' ]:
            rpn.globl.parse_stack.push(tok.type)
            try:
                tok2 = next(rpn.util.TokenMgr.next_token())
                dbg("token", 1, "token({},{})".format(tok2.type, repr(tok2.value)))
            except StopIteration:
                initial_parse_error = True
                dbg("token", 1, "{}: No more tokens, exiting".format(tok.type))
                break
            finally:
                tok_list.append(tok)
                rpn.globl.parse_stack.pop()
            tok_list.append(tok2)

        elif tok.type in ['OPEN_BRACKET', 'CLOSE_BRACKET',
                          'OPEN_PAREN',   'CLOSE_PAREN']:
            tok_list.append(tok)
            # borp == "bracket or paren"
            (open_close, borp) = tok.type.split("_")
            #print("borp={}".format(borp))
            if borp == 'PAREN':
                c = '('
            elif borp == 'BRACKET':
                c = '['

            if open_close == 'OPEN':
                if borp == 'PAREN' and depth[borp] > 0:
                    rpn.globl.lnwriteln("{}: Embedded {} not allowed".format(tok.type, c))
                    initial_parse_error = True
                else:
                    rpn.globl.parse_stack.push(c)
                    depth[borp] += 1

            if open_close == 'CLOSE':
                if rpn.globl.parse_stack.empty() or \
                        borp == 'BRACKET' and rpn.globl.parse_stack.top() != c or \
                        borp == 'PAREN'   and rpn.globl.parse_stack.top() != '(,':
                    rpn.globl.lnwriteln("{}: {} lost".format(tok.type, c))
                    initial_parse_error = True
                else:
                    rpn.globl.parse_stack.pop()
                    depth[borp] -= 1

        elif tok.type == 'COMMA':
            if rpn.globl.parse_stack.empty() or rpn.globl.parse_stack.top() != '(':
                rpn.globl.lnwriteln("{}: no matching (".format(tok.type))
                initial_parse_error = True
            else:
                tok_list.append(tok)
                rpn.globl.parse_stack.pop()
                rpn.globl.parse_stack.push('(,')

        elif tok.type in ['BEGIN', 'CASE', 'COLON', 'DO', 'IF']:
            tok_list.append(tok)
            rpn.globl.parse_stack.push(tok.type)

        elif tok.type in ['AGAIN', 'UNTIL']:
            if rpn.globl.parse_stack.empty() or rpn.globl.parse_stack.top() != 'BEGIN':
                rpn.globl.lnwriteln("{}: no matching BEGIN".format(tok.type))
                initial_parse_error = True
            else:
                tok_list.append(tok)
                rpn.globl.parse_stack.pop()

        elif tok.type == 'ELSE':
            if rpn.globl.parse_stack.empty() or rpn.globl.parse_stack.top() != 'IF':
                rpn.globl.lnwriteln("ELSE: no matching IF")
                initial_parse_error = True
            else:
                tok_list.append(tok)
                rpn.globl.parse_stack.pop()
                rpn.globl.parse_stack.push(tok.type)

        elif tok.type == 'ENDCASE':
            if rpn.globl.parse_stack.empty() or rpn.globl.parse_stack.top() not in ['CASE', 'OTHERWISE']:
                rpn.globl.lnwriteln("ENDCASE: no matching CASE")
                initial_parse_error = True
            else:
                tok_list.append(tok)
                rpn.globl.parse_stack.pop()

        elif tok.type == 'ENDOF':
            if rpn.globl.parse_stack.empty() or rpn.globl.parse_stack.top() != 'OF':
                rpn.globl.lnwriteln("ENDOF: no matching OF")
                initial_parse_error = True
            else:
                tok_list.append(tok)
                rpn.globl.parse_stack.pop()
                rpn.globl.parse_stack.push('CASE')

        elif tok.type == 'ERROR':
            rpn.globl.lnwriteln("ERROR {}".format(tok))
            initial_parse_error = True

        elif tok.type in ['LOOP', 'PLUS_LOOP']:
            if rpn.globl.parse_stack.empty() or rpn.globl.parse_stack.top() != 'DO':
                rpn.globl.lnwriteln("{}: no matching DO".format(tok.type))
                initial_parse_error = True
            else:
                tok_list.append(tok)
                rpn.globl.parse_stack.pop()

        elif tok.type in ['OF', 'OTHERWISE']:
            if rpn.globl.parse_stack.empty() or rpn.globl.parse_stack.top() != 'CASE':
                rpn.globl.lnwriteln("{}: no matching CASE".format(tok.type))
                initial_parse_error = True
            else:
                tok_list.append(tok)
                rpn.globl.parse_stack.pop()
                rpn.globl.parse_stack.push(tok.type)

        elif tok.type == 'REPEAT':
            if rpn.globl.parse_stack.empty() or rpn.globl.parse_stack.top() != 'WHILE':
                rpn.globl.lnwriteln("REPEAT: no matching WHILE")
                initial_parse_error = True
            else:
                tok_list.append(tok)
                rpn.globl.parse_stack.pop()

        elif tok.type == 'SEMICOLON':
            if rpn.globl.parse_stack.empty() or rpn.globl.parse_stack.top() != 'COLON':
                rpn.globl.lnwriteln("SEMICOLON: no matching COLON")
                initial_parse_error = True
            else:
                tok_list.append(tok)
                rpn.globl.parse_stack.pop()

        elif tok.type == 'THEN':
            if rpn.globl.parse_stack.empty() or rpn.globl.parse_stack.top() not in ['IF', 'ELSE']:
                rpn.globl.lnwriteln("THEN: no matching IF")
                initial_parse_error = True
            else:
                tok_list.append(tok)
                rpn.globl.parse_stack.pop()

        elif tok.type == 'WHILE':
            if rpn.globl.parse_stack.empty() or rpn.globl.parse_stack.top() != 'BEGIN':
                rpn.globl.lnwriteln("WHILE: no matching BEGIN")
                initial_parse_error = True
            else:
                tok_list.append(tok)
                rpn.globl.parse_stack.pop()
                rpn.globl.parse_stack.push(tok.type)

        else:
        # 'ABORT_QUOTE',
        # 'DOC_STR',
        # 'DOT_QUOTE',
        # 'VBAR',
        # 'WS',
            tok_list.append(tok)

        # Here's what breaks the while True loop, sauf StopIteration
        if rpn.globl.parse_stack.empty() and depth['PAREN'] == 0 and depth['BRACKET'] == 0:
            break

    return (initial_parse_error, tok_list)


# Simple SIGWINCH handler can become overwhelmed and crash if window
# changes come too fast.  Consider using shutil.get_terminal_size()
def sigwinch_handler(_signum, _frame):
    rpn.globl.update_screen_size()


def sigint_handler(_signam, _frame):
    rpn.globl.sigint_detected = True
    # It is NOT safe to do I/O inside a signal handler.
    # Can crash with error:
    #   RuntimeError: reentrant call inside <_io.BufferedWriter name='<stdout>'>
    # sys.stderr.write("^C")
    # sys.stderr.flush()
    # rpn.globl.eval_string("?cr")
    throw(X_INTERRUPT)

def sigquit_handler(_signum, _frame):
    rpn.globl.lnwriteln("[Quit]")
    raise EndProgram()


# def example_pre_hook_func(ident, cur_obj, new_obj):
#     print("example_pre_hook_func:")
#     print("ident  ={}".format(ident))
#     print("cur_obj={}".format(repr(cur_obj)))
#     print("new_obj={}".format(repr(new_obj)))
#     # Check against None first due to undef case
#     if new_obj is not None and new_obj.value < 0:
#         throw(X_INVALID_ARG, "!{}".format(identifier), "Must be positive")
#
# def example_post_hook_func(ident, old_obj, cur_obj):
#     print("example_post_hook_func:")
#     print("ident  ={}".format(ident))
#     print("old_obj={}".format(repr(old_obj)))
#     print("cur_obj={}".format(repr(cur_obj)))

def pre_require_int(identifier, _cur, new):
    if type(new) is not rpn.type.Integer:
        throw(X_ARG_TYPE_MISMATCH, "!{}".format(identifier), "({})".format(typename(new)))

def pre_require_int_or_float(identifier, _cur, new):
    if type(new) not in [rpn.type.Integer, rpn.type.Float]:
        throw(X_ARG_TYPE_MISMATCH, "!{}".format(identifier), "({})".format(typename(new)))

def pre_require_positive(identifier, _cur, new):
    if new.value <= 0:
        throw(X_INVALID_ARG, "!{}".format(identifier), "Must be positive")

def pre_require_non_negative(identifier, _cur, new):
    if new.value < 0:
        throw(X_INVALID_ARG, "!{}".format(identifier), "Must be non-negative")

def pre_validate_sreg_arg(identifier, _cur, new):
    if type(new) is not rpn.type.Integer:
        throw(X_ARG_TYPE_MISMATCH, "!{}".format(identifier), "({})".format(typename(new)))
    new_sreg = new.value
    (size_var, _) = rpn.globl.lookup_variable("SIZE")
    if new_sreg < 0 or new_sreg > size_var.obj.value - 6:
        throw(X_INVALID_ARG, "!{}".format(identifier), "SREG {} out of range (0..{} expected); check SIZE".format(new_sreg, size_var.obj.value - 6))

# def pre_validate_size_arg(identifier, _cur, new):
#     if type(new) is not rpn.type.Integer:
#         throw(X_ARG_TYPE_MISMATCH, "!{}".format(identifier), "({})".format(typename(new)))
#     new_size = new.value
#     if new_size < rpn.globl.SIZE_MIN or new_size > rpn.globl.SIZE_MAX:
#         throw(X_INVALID_ARG, "!{}".format(identifier), "Size {} out of range ({}..{} expected)".format(new_size, rpn.globl.SIZE_MIN, rpn.globl.SIZE_MAX))
#     (sreg_var, _) = rpn.globl.lookup_variable("SREG")
#     if new_size < sreg_var.obj.value + 6:
#         throw(X_INVALID_ARG, "!{}".format(identifier), "SIZE {} too small for SREG ({})".format(new_size, sreg_var.obj.value))

# def post_clear_newly_unveiled_registers(_identifier, old, cur):
#     old_size = old.value
#     cur_size = cur.value
#     # If we're increasing the number of registers, zero out the newly
#     # available ones.  It is not really necessary to do this when
#     # decreasing, because those registers will no longer be accessible.
#     if cur_size > old_size:
#         for r in range(cur_size - old_size):
#             rpn.globl.reg_stack.top().register[old_size + r] = rpn.type.Float(0.0)

def post_label_with_identifier(identifier, _old, cur):
    cur.label = identifier
