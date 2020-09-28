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
import subprocess
import sys

try:
    import numpy as np                  # pylint: disable=import-error
except ImportError:
    pass

# Check if SciPy is available
try:
    import scipy.integrate              # pylint: disable=import-error
    import scipy.optimize               # pylint: disable=import-error
except ModuleNotFoundError:
    pass

# # Check if Matplotlib is available
# try:
#     import matplotlib                   # pylint: disable=import-error
# except ModuleNotFoundError:
#     pass

from   rpn.debug import dbg, typename, whoami
import rpn.flag
import rpn.globl
import rpn.tvm
import rpn.type
import rpn.util
import rpn.word


force_interactive = False
load_init_file = True


def usage():
    print("""\
Usage: rpn [-d] [-f FILE] [-i] [-l FILE] [-q] cmds...

-d        Enable debugging
-f FILE   Load FILE and exit
-i        Force interactive mode
-l FILE   Load FILE
-q        Do not load init file (~/.rpnrc)""")
    sys.exit(64)                # EX_USAGE


def initialize(argv):
    # Set up low level stuff, stacks, variables
    go_interactive = True
    sys.setrecursionlimit(2000) # default is 10002
    random.seed()
    rpn.globl.disp_stack.push(rpn.util.DisplayConfig())
    rpn.globl.push_scope(rpn.globl.root_scope, "Root scope")
    define_variables()

    # Set up signal handling
    signal.signal(signal.SIGQUIT, sigquit_handler)
    signal.signal(signal.SIGWINCH, sigwinch_handler)
    sigwinch_handler(0, 0)     # Read & define ROWS and COLS via stty(1)

    # Set initial conditions
    rpn.word.w_clreg()
    # rpn.word.clflag()
    rpn.word.w_clfin()
    rpn.word.w_std()
    define_secondary_words()

    # Switch to user mode; words & variables are no longer protected
    rpn.globl.default_protected = False
    define_tertiary_words()

    # Parse command line
    argv = parse_args(argv)

    # Hopefully load the user's init file
    global load_init_file               # pylint: disable=global-statement
    if load_init_file:
        init_file = os.path.expanduser("~/.rpnrc")
        if os.path.isfile(init_file):
            (rpnrc, _) = rpn.globl.lookup_variable('RPNRC')
            rpnrc.set_obj(rpn.type.String(init_file))
            load_file(init_file)

    if len(argv) > 0:
        global force_interactive        # pylint: disable=global-statement
        if not force_interactive:
            go_interactive = False
        s = " ".join(argv)
        rpn.globl.eval_string(s)

    return go_interactive


def define_variables():
    # Variables defined here are all protected=True by default
    rpn.globl.sharpout = rpn.globl.defvar('#OUT',  rpn.type.Integer(0), readonly=True, noshadow=True)
    rpn.tvm.CF = rpn.globl.defvar('CF',    rpn.type.Integer(1), noshadow=True, pre_hooks=[require_int, require_positive],
                                  doc="TVM: Compounding Frequency")
    rpn.globl.scr_cols = rpn.globl.defvar('COLS',  rpn.type.Integer(0), pre_hooks=[require_int, require_positive])
    rpn.tvm.FV = rpn.globl.defvar('FV',    None, noshadow=True, pre_hooks=[require_int_or_float],
                                  doc="TVM: Future Value")
    rpn.tvm.INT = rpn.globl.defvar('INT',   None, noshadow=True, pre_hooks=[require_int_or_float, require_non_negative],
                                   doc="TVM: Interest rate")
    rpn.tvm.N = rpn.globl.defvar('N',     None, noshadow=True, pre_hooks=[require_int_or_float, require_positive],
                                 doc="TVM: Number of payments")
    rpn.globl.defvar('NUMPY', rpn.type.Integer(rpn.globl.bool_to_int(rpn.globl.have_module('numpy'))), readonly=True, noshadow=True)
    if rpn.globl.have_module('numpy'):
        rpn.globl.defvar('NUMPY_VER', rpn.type.String(np.__version__), readonly=True)
    rpn.tvm.PF = rpn.globl.defvar('PF',    rpn.type.Integer(1), noshadow=True, pre_hooks=[require_int, require_positive],
                                  doc="TVM: Payment Frequency")
    rpn.tvm.PMT = rpn.globl.defvar('PMT',   None, noshadow=True, pre_hooks=[require_int_or_float],
                                   doc="TVM: Payment amount")
    rpn.tvm.PV = rpn.globl.defvar('PV',    None, noshadow=True, pre_hooks=[require_int_or_float],
                                  doc="TVM: Present Value")
    rpn.globl.scr_rows = rpn.globl.defvar('ROWS',  rpn.type.Integer(0), pre_hooks=[require_int, require_positive])
    rpn.globl.defvar('RPNRC', rpn.type.String(""), readonly=True, hidden=True)
    rpn.globl.defvar('SCIPY', rpn.type.Integer(rpn.globl.bool_to_int(rpn.globl.have_module('scipy'))), readonly=True, noshadow=True)
    if rpn.globl.have_module('scipy'):
        rpn.globl.defvar('SCIPY_VER', rpn.type.String(scipy.__version__), readonly=True)
    rpn.globl.defvar('SIZE',  rpn.type.Integer(20), noshadow=True, pre_hooks=[validate_size_arg], post_hooks=[clear_newly_unveiled_registers])
    rpn.globl.defvar('VER',   rpn.type.Float(rpn.globl.RPN_VERSION), readonly=True, noshadow=True)


def parse_args(argv):
    try:
        opts, argv = getopt.getopt(argv, "df:il:q")
    except getopt.GetoptError as e:
        print(str(e))           # OK
        usage()

    for opt, arg in opts:
        if opt == "-d":
            rpn.flag.set_flag(rpn.flag.F_DEBUG_ENABLED)
        elif opt == "-f":
            try:
                load_file(arg)
            except FileNotFoundError:
                rpn.globl.lnwriteln("-f: File '{}' does not exist".format(arg))
                sys.exit(1)
            except rpn.exception.RuntimeErr as e:
                rpn.globl.lnwriteln(str(e))
                sys.exit(1)
            else:
                sys.exit(0)
        elif opt == "-i":
            global force_interactive    # pylint: disable=global-statement
            force_interactive = True
        elif opt == "-l":
            try:
                load_file(arg)
            except FileNotFoundError:
                rpn.globl.lnwriteln("-l: File '{}' does not exist".format(arg))
            except rpn.exception.RuntimeErr as e:
                rpn.globl.lnwriteln(str(e))
        elif opt == "-q":
            global load_init_file       # pylint: disable=global-statement
            load_init_file = False
        else:
            print("Unhandled option {}".format(opt)) # OK
            sys.exit(1)

    return argv


def load_file(filename):
    try:
        with open(filename, "r") as file:
            contents = file.read()
    except PermissionError:
        raise rpn.exception.RuntimeErr("load: Cannot read file '{}'".format(filename))
    else:
        rpn.globl.eval_string(contents)


def main_loop():
    rpn.flag.clear_flag(rpn.flag.F_SHOW_X) # Reset, because some argv may have set it to True

    # Non-existence of ~/.rpnrc is indicator of novice mode
    (rpnrc, _) = rpn.globl.lookup_variable("RPNRC")
    if len(rpnrc.obj().value()) == 0:
        rpn.globl.lnwriteln("Type ? for information, help <word> for help on a specific word.")
        rpn.globl.lnwriteln("Type vlist for a list of all words, vars to see your variables.")
        rpn.globl.lnwriteln("Type .s to display the stack non-destructively, and bye to exit.")

    if not rpn.globl.param_stack.empty():
        if rpn.globl.param_stack.size() == 1:
            rpn.word.w_dup()
            rpn.word.w_dot()
            rpn.word.w_cr()
        else:
            rpn.word.w_dot_s()

    while True:
        try:
            (error, tok_list) = generate_token_list()
        except StopIteration:
            return
        except rpn.exception.TopLevel:
            continue
        if error is True:
            rpn.globl.lnwriteln("{}: generate_token_list() error".format(whoami()))
        s = " ".join([t.value for t in tok_list])
        dbg("parse", 1, "s='{}'".format(s))
        rpn.globl.eval_string(s)


def end_program():
    if rpn.globl.sharpout.obj().value() != 0:
        rpn.globl.writeln()

    if not rpn.globl.string_stack.empty():
        if rpn.globl.string_stack.size() == 1:
            rpn.word.w_dollar_dot()
            rpn.word.w_cr()
        else:
            rpn.globl.lnwriteln("Strings:")
            rpn.word.w_dollar_dot_s()

    if not rpn.globl.param_stack.empty():
        if rpn.globl.param_stack.size() == 1:
            rpn.word.w_dot()
            rpn.word.w_cr()
        else:
            rpn.globl.lnwriteln("Stack:")
            rpn.word.w_dot_s()

    sys.exit(0)


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

        # These need a second token or they will be very angry
        if tok.type in ['AT_SIGN', 'CATCH', 'CONSTANT', 'EXCLAM', 'FORGET',
                        'HELP', 'SHOW', 'UNDEF', 'VARIABLE' ]:
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
        # 'IDENTIFIER',
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
    tty_rows = 0
    tty_columns = 0
    if sys.stdin.isatty():
        stty_size = subprocess.check_output(['stty', 'size']).decode().split()
        if len(stty_size) == 2:
            tty_rows, tty_columns = stty_size

    #rpn.globl.lnwriteln("{} x {}".format(tty_rows, tty_columns))
    if int(tty_columns) == 0:
        env_cols = os.getenv("COLUMNS")
        tty_columns = int(env_cols) if env_cols is not None else 80
    if int(tty_rows) == 0:
        env_rows = os.getenv("ROWS")
        tty_rows = int(env_rows) if env_rows is not None else 24
    rpn.globl.scr_rows.set_obj(rpn.type.Integer(tty_rows))
    rpn.globl.scr_cols.set_obj(rpn.type.Integer(tty_columns))


def sigquit_handler(_signum, _frame):
    rpn.globl.lnwriteln("[Quit]")
    raise rpn.exception.EndProgram()


# def example_pre_hook_func(ident, cur_obj, new_obj):
#     print("example_pre_hook_func:")
#     print("ident  ={}".format(ident))
#     print("cur_obj={}".format(repr(cur_obj)))
#     print("new_obj={}".format(repr(new_obj)))
#     # Check against None first due to undef case
#     if new_obj is not None and new_obj.value() < 0:
#         raise rpn.exception.RuntimeErr("{} cannot be negative".format(ident))
#
# def example_post_hook_func(ident, old_obj, cur_obj):
#     print("example_post_hook_func:")
#     print("ident  ={}".format(ident))
#     print("old_obj={}".format(repr(old_obj)))
#     print("cur_obj={}".format(repr(cur_obj)))

def require_int(identifier, _cur, new):
    if type(new) is not rpn.type.Integer:
        raise rpn.exception.RuntimeErr("!{}: Type error ({})".format(identifier, typename(new)))

def require_int_or_float(identifier, _cur, new):
    if type(new) not in [rpn.type.Integer, rpn.type.Float]:
        raise rpn.exception.RuntimeErr("!{}: Type error ({})".format(identifier, typename(new)))

def require_positive(identifier, _cur, new):
    if new.value() <= 0:
        raise rpn.exception.RuntimeErr("!{}: Must be positive".format(identifier))

def require_non_negative(identifier, _cur, new):
    if new.value() < 0:
        raise rpn.exception.RuntimeErr("!{}: Must be non-negative".format(identifier))

def validate_size_arg(identifier, _cur, new):
    if type(new) is not rpn.type.Integer:
        raise rpn.exception.RuntimeErr("!{}: Type error ({})".format(identifier, typename(new)))
    new_size = new.value()
    if new_size < rpn.globl.REG_SIZE_MIN or new_size > rpn.globl.REG_SIZE_MAX:
        raise rpn.exception.RuntimeErr("!{}: Size {} out of range ({}..{} expected)".format(identifier, new_size, rpn.globl.REG_SIZE_MIN, rpn.globl.REG_SIZE_MAX))

def clear_newly_unveiled_registers(_identifier, old, cur):
    old_size = old.value()
    cur_size = cur.value()
    # If we're increasing the number of registers, zero out the newly
    # available ones.  It is not really necessary to do this when
    # decreasing, because those registers will no longer be accessible.
    if cur_size > old_size:
        for r in range(cur_size - old_size):
            rpn.globl.register[old_size + r] = rpn.type.Float(0.0)


# Secondary words are protected by default
def define_secondary_words():
    rpn.globl.eval_string(r"""
\ : BEGIN_SECONDARY_WORDS----------------------------- doc:" " ;

: TRUE          doc:"TRUE  ( -- 1 )
Constant: Logical true"
  1
  19 cf ;

: FALSE         doc:"FALSE  ( -- 0 )
Constant: Logical false"
  0
  19 cf ;

: i             doc:"i  ( -- i )  Imaginary unit (0,1)

DEFINITION:
i = sqrt(-1)

Do not confuse this with the I command,
which returns the index of a DO loop."
  (0,1)
  19 cf ;

: PHI           doc:"PHI  ( -- 1.618... )   Golden ratio

DEFINITION:
PHI = (1 + sqrt(5)) / 2"
  5 sqrt 1 + 2 / ;

: BL            doc:"BL  ( -- 32 )   ASCII code for a space character"
  32
  19 cf ;

: ?cr           doc:"?cr  Print a newline only if necessary to return to left margin"
  @#OUT 0 > if
    cr
  then ;

: prompt        doc:"prompt  ( -- n ) [ text -- ]  Prompt for numeric input"
  $depth 0 = if
    ."prompt: Insufficient string parameters (1 required)" cr
  else
    $. #in
  then ;

: space         doc:"space   Display one space character"
  BL emit ;

: spaces        doc:"spaces  ( n -- )   Display N space characters"
  | in:N |
  @N 0 do space loop ;


\ Stack manipulation
: -rot          doc:"-rot  ( z y x -- x z y )  Rotate back
Rotate top stack element back to third spot, pulling others down.
Equivalent to ROT ROT"
  depth 3 < if
    ."-rot: Insufficient parameters (3 required)" cr
  else
    rot rot
  then
  19 cf ;

: nip           doc:"nip  ( y x -- x )
Drop second stack element
Equivalent to SWAP DROP.  J.V. Noble calls this PLUCK."
  depth 2 < if
    ."nip: Insufficient parameters (2 required)" cr
  else
    swap drop
  then
  19 cf ;

: tuck          doc:"tuck  ( y x -- x y x )
Duplicate top stack element into third position
Equivalent to SWAP OVER.  J.V. Noble calls this UNDER."
  depth 2 < if
    ."tuck: Insufficient parameters (2 required)" cr
  else
    swap over
  then
  19 cf ;

: sum           doc:"sum  ( ... -- sum )  Sum all numbers on the stack"
  depth 0= if
      0
  else
      depth 1 > if
          depth 1 - 0 do + loop
      then
  then
;


: debug         doc:"debug  ( -- )  Toggle debugging state"
  20 dup tf  fs? if
    ."Debugging is now ENABLED"
  else
    ."Debugging is now disabled"
  cr then ;

: deg?          doc:"deg?  ( -- flag )  Test if angular mode is degrees"
  42 fc?  43 fc?  and ;

: rad?          doc:"rad?  ( -- flag )  Test if angular mode is radians"
  42 fc?  43 fs?  and ;

: grad?         doc:"grad?  ( -- flag )  Test if angular mode is gradians"
  42 fs?  43 fc?  and ;

: mod           doc:"mod  ( y x -- remainder )  Remainder"
  | in:y in:x |
  @y @x /mod  drop ;


\ Conversion functions
: mm->in doc:"mm->in  ( mm -- inch )  Convert millimeters to inches"
  25.4 / ;

: m->ft  doc:"m->ft  ( m -- ft )  Convert meters to feet"
  1000 * mm->in   12 / ;

: km->mi doc:"km->mi  ( km -- mile )  Convert kilometers to miles"
  1000 *  m->ft 5280 / ;

: in->mm doc:"in->mm  ( inch -- mm )  Convert inches to millimeters"
  25.4 * ;

: ft->m doc:"ft->m  ( ft -- m )  Convert feet to meters"
  12   * in->mm 1000 / ;

: mi->km doc:"mi->km  ( mile -- km )  Convert miles to kilometers"
  5280   * ft->m  1000 / ;

: f->c doc:"f->c  ( f -- c )  Convert degrees fahrenheit to degrees celcius"
  32 - 5 * 9 / ;

: c->f doc:"c->f  ( c -- f )  Convert degrees celcius to degrees fahrenheit"
  9 * 5 / 32 + ;

: g->oz doc:"g->oz  ( g -- oz )  Convert grams to ounces"
  28.349523 / ;

: gal->l  doc:"gal->l  ( gal -- liter )  Convert gallons to liters"
  3.7854118 * ;

: l->gal  doc:"l->gal  ( liter -- gal )  Convert liters to gallons"
  3.7854118 / ;

: kg->lb doc:"kg->lb  ( kg -- lb )  Convert kilograms to pounds"
  0.45359237 / ;

\ : cm3->in3 doc:"cm3->in3  ( cm^3 -- in^3 )  Convert cubic centimeters to cubic inches"
\   16.3871     / ;

: oz->g    doc:"oz->g  ( oz -- g )  Convert ounces to grams"
  28.349523 * ;

: lb->kg   doc:"lb->kg  ( lb -- kg )  Convert pounds to kilograms"
  0.45359237 * ;

\ : in3->cm3  doc:"in3->cm3  ( in^3 -- cm^3 )  Convert cubic inches to cubic centimeters"
\   16.3871     * ;


\ String functions
: $date         doc:"$date  [ -- date ]  Current date as string"
  date d->jd jd->$ ;

: adate         doc:"adate  Append current date to top string stack element"
  $date
  $depth 1 > if $cat then ;

: atime         doc:"atime  Append current time to top string stack element"
  $time
  $depth 1 > if $cat then ;

\ : END_SECONDARY_WORDS----------------------------- doc:" " ;
""")


# Tertiary words are not protected
def define_tertiary_words():
    rpn.globl.eval_string("""
""")
