'''
#############################################################################
#
#       G L O B A L   D E F I N I T I O N S
#
#############################################################################
'''

from   fractions import Fraction
import itertools
import os
import re
import subprocess
import sys
import traceback

# Check if NumPy is available
try:
    import numpy as np                  # pylint: disable=import-error
except ImportError:
    pass

# # Check if SciPy is available
# try:
#     import scipy.integrate              # pylint: disable=import-error
#     import scipy.optimize               # pylint: disable=import-error
# except ModuleNotFoundError:
#     pass

# # Check if Matplotlib is available
# try:
#     import matplotlib                   # pylint: disable=import-error
# except ModuleNotFoundError:
#     pass

from   rpn.debug     import dbg, whoami
from   rpn.exception import *
import rpn.flag
import rpn.parser
import rpn.util


RPN_VERSION     = 15.8

PX_COMPUTE              = True  # Arithmetic/Computed functions print their results
PX_CONFIG               = None  # Stack manip, flags, modes, register, conversions, etc
PX_CONTROL              = None  # Control structures (IF/THEN, DO/LOOP) have no effect
PX_IO                   = False # I/O (.", .s, etc) disable printing
PX_PREDICATE            = True  # Predicates.  (Was None, but I want to try seeing the values)

REG_SIZE_MIN            =  17
REG_SIZE_MAX            = 100   # R00..R99; further restricted by SIZE

disp_stack   = rpn.util.Stack("Display stack", 1)
param_stack  = rpn.util.Stack("Parameter stack")
parse_stack  = rpn.util.Stack("Parse stack")
return_stack = rpn.util.Stack("Return stack")
scope_stack  = rpn.util.Stack("Scope stack", 1)
string_stack = rpn.util.Stack("String stack")
colon_stack  = rpn.util.Stack("Colon stack")

root_scope = rpn.util.Scope("ROOT")

register          = dict()
stat_data         = []
interactive       = None
default_protected = True
got_interrupt     = False
lexer             = None
scr_cols          = None
scr_rows          = None
sharpout          = None
sigint_detected   = False
rpn_parser        = None
uexpr             = dict()


DATE_RE                 = re.compile(r'^(\d{1,2})\.(\d{2})(\d{4})$') # MM.DDYYYY
INTEGER_RE              = re.compile(r'^\d+$')
JULIAN_OFFSET           = 1721424 # date.toordinal() returns 1 for 0001-01-01, so compensate
PRECISION_MAX           =  16
MATRIX_MAX              = 999
RATIONAL_RE             = re.compile(r'^(\d+)::(\d+)(_([a-zA-Z]+))?$')              # ddd::ddd
TIME_RE                 = re.compile(r'^[-+]?(\d+)\.(\d{,2})(\d*)$') # HH.MMSSsss

# DEG_PER_RAD  = 360 / TAU
# E            = Base of natural logarithms = exp(1.0)
# GAMMA        = Euler-Mascheroni constant, approx: 1 - tanh(ln(1.57)) - 0.57/(9!)
# GRAD_PER_RAD = 400 / TAU                      # 1 1.57 ln tanh - 0.57 9 fact / -   => 0.5772156649394624
# LN_2         = ln(2)                          # GAMMA -                            => 3.7929548390991386e-11
# LN_10        = ln(10)
# PHI          = "Golden ratio" = (1 + sqrt(5)) / 2
# PI           = TAU / 2
# RAD_PER_DEG  = TAU / 360
# RAD_PER_GRAD = TAU / 400
# SQRT_2       = Square root of 2
# TAU          = Number of radians in a circle = 2*PI

RAD_PER_GRAD =  0.0157079632679489661923132169163975144209858469968755291048747229615390820314310449931401741267105853
RAD_PER_DEG  =  0.0174532925199432957692369076848861271344287188854172545609719144017100911460344944368224156963450948
INV_PI       =  0.3183098861837906715377675267450287240689192914809128974953346881177935952684530701802276055325061719
GAMMA        =  0.5772156649015328606065120900824024310421593359399235988057672348848677267776646709369470632917467495
LN_2         =  0.6931471805599453094172321214581765680755001343602552541206900094933936219696947156058633269964186875
SQRT_2       =  1.4142135623730950488016887242096980785696718753769480731766797379907324784621070388503875343276415727
PHI          =  1.6180339887498948482045868343656381177203091798057628621354486227052604628189024497072072041893911375
LN_10        =  2.3025850929940456840179914546843642076011014886287729760333279009675726096773524802359972050895982983
E            =  2.7182818284590452353602874713526624977572470936999595749669676277240766303535475945713821785251664274
PI           =  3.1415926535897932384626433832795028841971693993751058209749445923078164062862089986280348253421170680
TAU          =  6.2831853071795864769252867665590057683943387987502116419498891846156328125724179972560696506842341360
DEG_PER_RAD  = 57.2957795130823208767981548141051703324054724665643215491602438612028471483245526324409689958511109442
GRAD_PER_RAD = 63.6619772367581343075535053490057448137838582961825794990669376235587190536906140360455211065012343824


def angle_mode_letter():
    if rpn.flag.flag_set_p(rpn.flag.F_RAD) and rpn.flag.flag_set_p(rpn.flag.F_GRAD):
        raise FatalErr("angle_mode_letter: Bad angle mode: RAD and GRAD both set")
    if rpn.flag.flag_set_p(rpn.flag.F_RAD):
        return "r"
    if rpn.flag.flag_set_p(rpn.flag.F_GRAD):
        return "g"
    return "d"


def bool_to_int(condition):
    return 1 if condition is True else 0


def convert_mode_to_radians(x, force_mode=None):
    mode = force_mode if force_mode is not None else angle_mode_letter()
    if mode == "r":
        return x
    if mode == "d":
        return x / DEG_PER_RAD
    if mode == "g":
        return x / GRAD_PER_RAD
    raise FatalErr("{}: Bad angle_mode '{}'".format(whoami(), mode))


def convert_radians_to_mode(r, force_mode=None):
    mode = force_mode if force_mode is not None else angle_mode_letter()
    if mode == "r":
        return r
    if mode == "d":
        return r * DEG_PER_RAD
    if mode == "g":
        return r * GRAD_PER_RAD
    raise FatalErr("{}: Bad angle_mode '{}'".format(whoami(), mode))


def defvar(name, value, **kwargs):
    if type(name) is not str:
        raise FatalErr("defvar: name '{}' is not a string ".format(name))
    root_scope.add_vname(rpn.util.VName(name))
    var = rpn.util.Variable(name, value, **kwargs)
    dbg(whoami(), 1, "{}: Creating variable {} at address {} in {}".format(whoami(), name, hex(id(var)), repr(root_scope)))
    root_scope.define_variable(name, var)
    return var


def eval_string(s):
    dbg("eval_string", 1, "eval_string('{}')".format(s))
    scope_stack_size = scope_stack.size()
    rpn.parser.initialize_lexer()
    rpn.parser.initialize_parser()
    try:
        result = rpn_parser.parse(s) # , debug=dbg("eval_string"))
    except ParseErr as e:
        if str(e) != 'EOF':
            rpn.globl.lnwriteln("Parse error: {}".format(str(e)))
    except RuntimeErr as e:
        dbg(whoami(), 1, "{}: Caught RuntimeErr, code={}".format(whoami(), e.code))
        if e.code >= 0:
            raise
        if e.code == X_ABORT or \
           e.code == X_ABORT_QUOTE:
            param_stack.clear()
            string_stack.clear()
            return_stack.clear()
            if e.code == X_ABORT_QUOTE:
                lnwriteln(e.message)
        elif e.code == X_EXIT or \
             e.code == X_INTERRUPT:
            return
        else:
            if rpn.flag.flag_set_p(rpn.flag.F_DEBUG_ENABLED):
                lnwriteln("eval_string: " + str(e))
            else:
                lnwriteln(str(e))
    else:
        if result is not None:
            dbg("eval_string", 1, "result={}".format(result))
    finally:
        if scope_stack.size() > scope_stack_size:
            dbg("eval_string", 1, "Gotta pop {} scopes from the stack".format(scope_stack.size() - scope_stack_size))
        while scope_stack.size() > scope_stack_size:
            pop_scope("Parse failure")


def execute(executable):
    dbg(whoami(), 1, "execute: {}/{}".format(type(executable), executable))
    try:
        try:
            if type(executable) is rpn.util.Word and executable.typ == "colon":
                dbg(whoami(), 2, ">>>>  {}  <<<<".format(executable.name))
                rpn.globl.colon_stack.push(executable)
            executable.__call__(executable.name)
        finally:
            if type(executable) is rpn.util.Word and executable.typ == "colon":
                rpn.globl.colon_stack.pop()
    except RecursionError:
        lnwriteln("{}: Excessive recursion".format(executable))
    except RuntimeErr as err_execute:
        if err_execute.code == X_INTERRUPT:
            rpn.globl.lnwriteln(throw_code_text[X_INTERRUPT])
            rpn.globl.sigint_detected = False
            raise
        elif err_execute.code == X_EXIT:
            return
        else:
            raise

# I should really just use __format__() correctly
def gfmt(x):
    return disp_stack.top().dcfmt(x)


def have_module(modname):
    r = modname in sys.modules
    dbg("have_module", 1, "globl.have_module({})={}".format(modname, r))
    return bool(r)


# Jeffrey Magedanz - https://stackoverflow.com/posts/42602689/revisions
def list_in_columns(items, width=79, indent=0, spacing=3):
    """\
Return string listing items along columns.

items : sequence
    List of items to display that must be directly convertible into
    unicode strings.
width : int
    Maximum number of characters per line, including indentation.
indent : int
    Number of spaces in left margin.
spacing : int
    Number of spaces between columns."""

    if not items:
        return u''
    # Ensure all items are strings
### items = [unicode(item) for item in items]
    # Estimate number of columns based on shortest and longest items
    minlen = min(len(item) for item in items)
    maxlen = max(len(item) for item in items)
    # Assume one column with longest width, remaining with shortest.
    # Use negative numbers for ceiling division.
    ncols = 1 - (-(width - indent - maxlen) // (spacing + min(1, minlen)))
    ncols = max(1, min(len(items), ncols))

    # Reduce number of columns until items fit (or only one column)
    while ncols >= 1:
        # Determine number of rows by ceiling division
        nrows = -(-len(items) // ncols)
        # Readjust to avoid empty last column
        ncols = -(-len(items) // nrows)
        # Split items into columns, and test width
        columns = [items[i*nrows:(i+1)*nrows] for i in range(ncols)]
        totalwidth = indent - spacing + sum(
            spacing + max(len(item) for item in column)
            for column in columns)
        # Stop if columns fit. Otherwise, reduce number of columns and
        # try again.
        if totalwidth <= width:
            break
        ncols -= 1

    # Pad all items to column width
    for i, column in enumerate(columns):
        colwidth = max(len(item) for item in column)
        columns[i] = [
            item + ' ' * (colwidth - len(item))
            for item in column
            ]

    # Transpose into rows, and return joined rows
    rows = list(itertools.zip_longest(*columns, fillvalue=''))
    out = '\n'.join(' ' * indent + (u' ' * spacing).join(row).rstrip()
                    for row in rows)
    writeln(out)


def separate_decorations(ident):
    decoration = ""
    if ident[:3] == 'in:':
        decoration = "in"
        ident = ident[3:]
    elif ident[:4] == 'out:':
        decoration = "out"
        ident = ident[4:]
    elif ident[:6] == 'inout:':
        decoration = "inout"
        ident = ident[6:]
    return (decoration, ident)


def lookup_variable(name, how_many=1):
    for (_, scope) in scope_stack.items_top_to_bottom():
        dbg(whoami(), 1, "{}: Looking for variable {} in {}...".format(whoami(), name, scope.name))
        dbg(whoami(), 3, "{} has variables: {}".format(scope.name, scope.variables()))
        var = scope.variable(name)
        if var is None:
            continue
        how_many -= 1
        if how_many > 0:
            continue
        dbg(whoami(), 2, "{}: Found variable {} in {}: {}".format(whoami(), name, repr(scope), repr(var)))
        return (var, scope)
    dbg(whoami(), 2, "{}: Variable {} not found".format(whoami(), name))
    #traceback.print_stack(file=sys.stderr)
    return (None, None)


def lookup_vname(ident):
    if type(ident) is not str:
        raise FatalErr("lookup_vname: ident '{}' is not a string".format(ident))
    for (_, scope) in scope_stack.items_top_to_bottom():
        dbg(whoami(), 1, "{}: Looking for vname {} in {}...".format(whoami(), ident, repr(scope)))
        dbg(whoami(), 3, "{} has vnames: {}".format(scope, scope.vnames()))
        if scope.has_vname_named(ident):
            dbg(whoami(), 2, "{}: Found vname {} in {}".format(whoami(), ident, repr(scope)))
            return (scope.vname(ident), scope)
    dbg(whoami(), 2, "{}: VName {} not found".format(whoami(), ident))
    return (None, None)


def lookup_word(name):
    for (_, scope) in scope_stack.items_top_to_bottom():
        dbg(whoami(), 1, "{}: Looking for word {} in {}...".format(whoami(), name, scope))
        dbg(whoami(), 3, "{} has words: {}".format(scope, scope.words))
        word = scope.word(name)
        if word is not None and not word.smudge():
            dbg(whoami(), 2, "{}: Found word {} in {}: {}".format(whoami(), name, scope, word))
            return (word, scope)
    dbg(whoami(), 2, "{}: Word {} not found".format(whoami(), name))
    return (None, None)


def normalize_hms(hh, mm, ss):
    while ss < 0:
        mm -=  1
        ss += 60
    while ss >= 60:
        mm +=  1
        ss -= 60
    while mm < 0:
        hh -=  1
        mm += 60
    while mm >= 60:
        hh +=  1
        mm -= 60
    return (hh, mm, ss)


def pop_scope(why):
    try:
        scope = scope_stack.pop()
    except RuntimeErr as e:
        if e.code == X_STACK_UNDERFLOW:
            traceback.print_stack(file=sys.stderr)
            raise FatalErr("Attempting to pop Root scope!") from e
        else:
            raise

    dbg("scope", 2, "Pop  {} due to {}".format(repr(scope), why))
    #dbg("scope", 1, "Pop  {}".format(repr(scope)))
    if scope == root_scope:
        traceback.print_stack(file=sys.stderr)
        raise FatalErr("Attempting to pop Root scope!")


def push_scope(scope, why):
    dbg("scope", 2, "Push {} due to {}".format(repr(scope), why))
    rpn.globl.scope_stack.push(scope)


def update_screen_size():
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
    rpn.globl.scr_rows.obj = rpn.type.Integer(tty_rows)
    rpn.globl.scr_cols.obj = rpn.type.Integer(tty_columns)


def to_python_class(n):
    t = type(n)
    if t is np.int64:
        return int(n)
    if t is np.float64:
        return float(n)
    if t is np.complex128:
        return complex(n)
    raise FatalErr("{}: Cannot handle type {}".format(whoami(), t))


def to_rpn_class(n):
    t = type(n)
    if t in [int, np.int64]:
        return rpn.type.Integer(n)
    if t in [float, np.float64]:
        return rpn.type.Float(n)
    if t is Fraction:
        return rpn.type.Rational.from_Fraction(n)
    if t in [complex, np.complex128]:
        return rpn.type.Complex.from_complex(n)
    raise FatalErr("{}: Cannot handle type {}".format(whoami(), t))


def write(s=""):
    if len(s) == 0:
        return
    outval = rpn.globl.sharpout.obj.value
    newline = s.find("\n")
    while newline != -1:
        substring = s[:newline]
        print(substring)       # OK
        outval = 0
        s = s[newline+1:]
        newline = s.find("\n")
    outval += len(s)
    print(s, end='', flush=True) # OK
    rpn.globl.sharpout.obj = rpn.type.Integer(outval)

def writeln(s=""):
    print(s, flush=True)       # OK
    rpn.globl.sharpout.obj = rpn.type.Integer(0)

def lnwrite(s=""):
    if rpn.globl.sharpout.obj.value != 0:
        writeln()
    write(s)

def lnwriteln(s=""):
    if rpn.globl.sharpout.obj.value != 0:
        writeln()
    writeln(s)
