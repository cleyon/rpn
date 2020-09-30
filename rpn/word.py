'''
#############################################################################
#
#       W O R D   D E F I N I T I O N S
#
#############################################################################
'''

import calendar
import cmath
import datetime
import fcntl
from   fractions import Fraction
import functools
import math
import os
import readline                         # pylint: disable=unused-import
import random
import statistics
import subprocess
import sys
import tempfile         # edit
import termios
import time
import tty

# Check if NumPy is available
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

# Check if Matplotlib is available
try:
    import matplotlib                   # pylint: disable=import-error
except ModuleNotFoundError:
    pass

from   rpn.debug import dbg, typename, whoami
import rpn.flag
import rpn.globl
import rpn.tvm
import rpn.util


class defword():
    """Register the following word definition in the root scope"""

    def __init__(self, **kwargs):
        self._kwargs = kwargs

    def __call__(self, f):
        def wrapped_f(**kwargs):        # pylint: disable=unused-argument
            #print("Decorator args: {}".format(self._kwargs))
            f()
            if "print_x" in self._kwargs and \
               self._kwargs["print_x"] is not None:
                if self._kwargs["print_x"]:
                    rpn.flag.set_flag(rpn.flag.F_SHOW_X)
                else:
                    rpn.flag.clear_flag(rpn.flag.F_SHOW_X)

        if "immediate" in self._kwargs:
            raise rpn.exception.FatalErr("Immediate words cannot be declared with @defword; use @defimmed instead")
        if "name" in self._kwargs and len(self._kwargs["name"]) > 0:
            name = self._kwargs["name"]
            del self._kwargs["name"]
        else:
            raise rpn.exception.RuntimeErr("Missing or invalid \"name\" attribute")
        word = rpn.util.Word(name, wrapped_f, **self._kwargs)
        rpn.globl.root_scope.define_word(name, word)
        return wrapped_f


class defimmed():
    """Register the following immediate word definition in the root scope"""

    def __init__(self, **kwargs):
        self._kwargs = kwargs

    def __call__(self, f):
        def wrapped_f(arg1, **kwargs):        # pylint: disable=unused-argument
            #print("defimmed: arg1={}, kwargs={}".format(repr(arg1), self._kwargs))
            f(arg1)

        self._kwargs["immediate"] = True
        if "name" in self._kwargs and len(self._kwargs["name"]) > 0:
            name = self._kwargs["name"]
            del self._kwargs["name"]
        else:
            raise rpn.exception.RuntimeErr("Missing or invalid \"name\" attribute")
        word = rpn.util.Word(name, wrapped_f, **self._kwargs)
        rpn.globl.root_scope.define_word(name, word)
        return wrapped_f


@defword(name='#->$', args=1, print_x=rpn.globl.PX_IO, doc="""\
Convert top of stack to string  ( n -- )""")
def w_num_to_dollar():
    rpn.globl.string_stack.push(rpn.type.String("{}".format(rpn.globl.fmt(rpn.globl.param_stack.pop(), False))))


@defword(name='#in', print_x=rpn.globl.PX_IO, doc="""\
Read numeric input from the user.  #IN recognizes integers and floats,
but not rationals or complex numbers.  The value is put on the stack.
No prompt is provided.

qv PROMPT""")
def w_number_in():
    x = ""
    while len(x) == 0:
        try:
            x = input()
            dbg(whoami(), 1, "#in: '{}'".format(x))
        except EOFError:
            raise rpn.exception.RuntimeErr()
        finally:
            rpn.globl.sharpout.obj = rpn.type.Integer(0)

    newlexer = rpn.globl.lexer.clone()
    newlexer.input(x)
    tok = newlexer.token()

    if tok.type == 'INTEGER':
        rpn.globl.param_stack.push(rpn.type.Integer(int(tok.value)))
    elif tok.type == 'FLOAT':
        rpn.globl.param_stack.push(rpn.type.Float(float(tok.value)))
    else:
        raise rpn.exception.RuntimeErr("#in: Could not parse '{}'".format(x))


@defword(name='$.', str_args=1, print_x=rpn.globl.PX_IO, doc="""\
Print top item from string stack  [ str -- ]
No extraneous white space or newline is printed.""")
def w_dollar_dot():
    rpn.globl.write(rpn.globl.string_stack.pop().value)


@defword(name='$.!', hidden=True, print_x=rpn.globl.PX_IO, str_args=1)
def w_dollar_dot_bang():
    rpn.globl.lnwriteln(repr(rpn.globl.string_stack.top()))


@defword(name='$in', print_x=rpn.globl.PX_IO, doc="""\
Read a string from the keyboard.  The value is placed on the string stack.
No prompt is provided.""")
def w_dollar_in():
    x = ""
    while len(x) == 0:
        try:
            x = input()
            dbg(whoami(), 1, "$in: '{}'".format(x))
        except EOFError:
            raise rpn.exception.RuntimeErr()
        finally:
            rpn.globl.sharpout.obj = rpn.type.Integer(0)

    rpn.globl.string_stack.push(rpn.type.String(x))



@defword(name='$.s', print_x=rpn.globl.PX_IO, doc="""\
Display string stack.""")
def w_dollar_dot_s():
    if not rpn.globl.string_stack.empty():
        rpn.globl.lnwriteln(rpn.globl.string_stack)


@defword(name='$.s!', print_x=rpn.globl.PX_IO, hidden=True)
def w_dollar_dot_s_bang():
    if not rpn.globl.string_stack.empty():
        rpn.globl.lnwriteln(repr(rpn.globl.string_stack))


@defword(name='$=', str_args=2, print_x=rpn.globl.PX_PREDICATE, doc="""\
Test if two strings are equal  ( -- flag )""")
def w_dollar_equal():
    s1 = rpn.globl.string_stack.pop()
    s2 = rpn.globl.string_stack.pop()
    rpn.globl.param_stack.push(rpn.type.Integer(rpn.globl.bool_to_int(s1.value == s2.value)))


@defword(name='$cat', str_args=2, print_x=rpn.globl.PX_IO, doc="""\
Concatentate two strings.

EXAMPLE:
"foo" "bar" $cat "baz" $cat  =>  "foobarbaz" """)
def w_dollar_cat():
    s1 = rpn.globl.string_stack.pop()
    s2 = rpn.globl.string_stack.pop()
    rpn.globl.string_stack.push(rpn.type.String.from_string(s2.value + s1.value))


@defword(name='$clst', print_x=rpn.globl.PX_CONFIG, doc="""\
Clear the string stack""")
def w_dollar_clst():
    rpn.globl.string_stack.clear()


@defword(name='$depth', print_x=rpn.globl.PX_COMPUTE, doc="""\
String stack depth  ( -- n )""")
def w_dollar_depth():
    rpn.globl.param_stack.push(rpn.type.Integer(rpn.globl.string_stack.size()))


@defword(name='$drop', str_args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
Drop top of string stack  ( -- )""")
def w_dollar_drop():
    rpn.globl.string_stack.pop()


@defword(name='$len', str_args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Length of top element of string stack  ( -- n )""")
def w_dollar_len():
    s = rpn.globl.string_stack.top()
    r = len(s.value)
    rpn.globl.param_stack.push(rpn.type.Integer(r))


@defword(name='$swap', str_args=2, print_x=rpn.globl.PX_CONFIG, doc="""\
Exchange top two string stack elements  [ "y" "x" -- "x" "y" ]""")
def w_dollar_swap():
    sx = rpn.globl.string_stack.pop()
    sy = rpn.globl.string_stack.pop()
    rpn.globl.string_stack.push(sx)
    rpn.globl.string_stack.push(sy)


@defword(name='$time', print_x=rpn.globl.PX_COMPUTE, doc="""\
Current time as string  [ -- HH:MM:SS ]""")
def w_dollar_time():
    t = datetime.datetime.now().strftime("%H:%M:%S")
    rpn.globl.string_stack.push(rpn.type.String(t))


@defword(name='%', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
Percentage  ( base rate -- base percent )

Base is maintained in Y.

DEFINTION:
                 rate
percent = base * ----
                 100""")
def w_percent():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if     type(x) in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float] \
       and type(y) in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
        base = float(y.value)
        rate = float(x.value)
        r = base * rate / 100.0
        if type(x) is rpn.type.Integer and type(y) is rpn.type.Integer and r.is_integer():
            result = rpn.type.Integer(r)
        else:
            result = rpn.type.Float(r)
        result.label = "%"
    else:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("%: Type error ({}, {})".format(typename(y), typename(x)))
    rpn.globl.param_stack.push(y)
    rpn.globl.param_stack.push(result)


@defword(name='%ch', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
Percentage change  ( old new -- %change )

DEFINITION:

          new - old
%Change = --------- * 100
             old

old cannot be zero.""")
def w_percent_ch():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if     type(x) in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float] \
       and type(y) in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
        if y.zerop():
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            raise rpn.exception.ValueErr("%ch: Y cannot be zero")

        old = float(y.value)
        new = float(x.value)
        r = (new - old) * 100.0 / old
        if type(x) is rpn.type.Integer and type(y) is rpn.type.Integer and r.is_integer():
            result = rpn.type.Integer(r)
        else:
            result = rpn.type.Float(r)
        result.label = "%ch"
    else:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("%ch: Type error ({}, {})".format(typename(y), typename(x)))
    # The HP-32SII preserves the Y value (like %) but we do not
    rpn.globl.param_stack.push(result)


@defword(name='%t', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
Percent of total  ( total amount -- %tot )

DEFINITION:

         amount
%Total = ------ * 100
         total

total cannot be zero.""")
def w_percent_t():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if     type(x) in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float] \
       and type(y) in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
        if y.zerop():
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            raise rpn.exception.ValueErr("%t: Y cannot be zero")

        total  = float(y.value)
        amount = float(x.value)
        r = amount * 100.0 / total
        if type(x) is rpn.type.Integer and type(y) is rpn.type.Integer and r.is_integer():
            result = rpn.type.Integer(r)
        else:
            result = rpn.type.Float(r)
        result.label = "%t"
    else:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("%t: Type error ({}, {})".format(typename(y), typename(x)))
    # The HP-32SII preserves the Y value (like %) but we do not
    rpn.globl.param_stack.push(result)


@defword(name='*', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
Multiplication  ( y x -- y*x )""")
def w_star():
    """\
|----------+----------+---------+----------+---------+--------+--------|
| Integer  | Integer  | Float   | Rational | Complex |        |        |
| Float    | Float    | Float   | Float    | Complex |        |        |
| Rational | Rational | Float   | Rational | Complex |        |        |
| Complex  | Complex  | Complex | Complex  | Complex |        |        |
| Vector   |          |         |          |         |        |        |
| Matrix   |          |         |          |         |        |        |
|----------+----------+---------+----------+---------+--------+--------|
| ^Y    X> | Integer  | Float   | Rational | Complex | Vector | Matrix |"""
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if type(x) is rpn.type.Integer and type(y) is rpn.type.Integer:
        result = rpn.type.Integer(y.value * x.value)
    elif    type(x) is rpn.type.Float and type(y) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational] \
         or type(y) is rpn.type.Float and type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        result = rpn.type.Float(float(y.value) * float(x.value))
    elif    type(x) is rpn.type.Rational and type(y) in [rpn.type.Integer, rpn.type.Rational] \
         or type(y) is rpn.type.Rational and type(x) in [rpn.type.Integer, rpn.type.Rational]:
        result = rpn.type.Rational.from_Fraction(y.value * x.value)
    elif    type(x) is rpn.type.Complex and type(y) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational, rpn.type.Complex] \
         or type(y) is rpn.type.Complex and type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational, rpn.type.Complex]:
        result = rpn.type.Complex.from_complex(complex(y.value) * complex(x.value))
    elif type(x) in [rpn.type.Vector, rpn.type.Matrix] or \
         type(y) in [rpn.type.Vector, rpn.type.Matrix]:
        try:
            r = np.dot(y.value, x.value)
        except ValueError:
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            raise rpn.exception.ValueErr("*: Matrix/Vectors are not conformable")
        result = rpn.type.Matrix.from_numpy(r)
    else:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("*: Type error ({}, {})".format(typename(y), typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='*/', args=3, print_x=rpn.globl.PX_COMPUTE, doc="""\
Multiply and divide  ( z y x -- z*y/x )

X cannot be zero.""")
def w_star_slash():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    z = rpn.globl.param_stack.pop()
    if    type(x) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float, rpn.type.Complex] \
       or type(y) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float, rpn.type.Complex] \
       or type(z) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float, rpn.type.Complex]:
        rpn.globl.param_stack.push(z)
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("*/: Type error ({}, {}, {})".format(typename(z), typename(y), typename(x)))
    if z.zerop():
        rpn.globl.param_stack.push(z)
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("*/: X cannot be zero")

    rpn.globl.param_stack.push(z)
    rpn.globl.param_stack.push(y)
    rpn.word.w_star()
    rpn.globl.param_stack.push(x)
    rpn.word.w_slash()


@defword(name='+', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
Addition  ( y x -- y+x )""")
def w_plus():
    """\
|----------+----------+---------+----------+---------+--------+--------|
| Integer  | Integer  | Float   | Rational | Complex | Vector | Matrix |
| Float    | Float    | Float   | Float    | Complex | Vector | Matrix |
| Rational | Rational | Float   | Rational | Complex | Vector | Matrix |
| Complex  | Complex  | Complex | Complex  | Complex | Vector | Matrix |
| Vector   | Vector   | Vector  | Vector   | Vector  | Vector |        |
| Matrix   | Matrix   | Matrix  | Matrix   | Matrix  |        | Matrix |
|----------+----------+---------+----------+---------+--------+--------|
| ^Y    X> | Integer  | Float   | Rational | Complex | Vector | Matrix |"""
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if type(x) is rpn.type.Integer and type(y) is rpn.type.Integer:
        result = rpn.type.Integer(y.value + x.value)
    elif    type(x) is rpn.type.Float and type(y) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational] \
         or type(y) is rpn.type.Float and type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        result = rpn.type.Float(float(y.value) + float(x.value))
    elif    type(x) is rpn.type.Rational and type(y) in [rpn.type.Integer, rpn.type.Rational] \
         or type(y) is rpn.type.Rational and type(x) in [rpn.type.Integer, rpn.type.Rational]:
        result = rpn.type.Rational.from_Fraction(y.value + x.value)
    elif    type(x) is rpn.type.Complex and type(y) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational, rpn.type.Complex] \
         or type(y) is rpn.type.Complex and type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational, rpn.type.Complex]:
        result = rpn.type.Complex.from_complex(complex(y.value) + complex(x.value))
    elif    type(x) is rpn.type.Vector and type(y) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational, rpn.type.Complex] \
         or type(y) is rpn.type.Vector and type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational, rpn.type.Complex]:
        r = np.add(y.value, x.value)
        result = rpn.type.Vector.from_numpy(r)
    elif type(x) is rpn.type.Vector and type(y) is rpn.type.Vector:
        if x.size() != y.size():
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            raise rpn.exception.ValueErr("+: Conformability error: Vectors ({} and {}) are not same size".format(y, x))
        r = np.add(y.value, x.value)
        # print(type(r))
        # print(r)
        result = rpn.type.Vector.from_numpy(r)
    elif    type(x) is rpn.type.Matrix and type(y) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational, rpn.type.Complex] \
         or type(y) is rpn.type.Matrix and type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational, rpn.type.Complex]:
        r = np.add(y.value, x.value)
        result = rpn.type.Matrix.from_numpy(r)
    elif type(x) is rpn.type.Matrix and type(y) is rpn.type.Matrix:
        if x.nrows() != y.nrows() or x.ncols() != y.ncols():
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            raise rpn.exception.ValueErr("+: Conformability error: Matrices ({} and {}) are not same size".format(y, x))
        r = np.add(y.value, x.value)
        # print(type(r))
        # print(r)
        result = rpn.type.Matrix.from_numpy(r)
    else:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("+: Type error ({}, {})".format(typename(y), typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='+loop', print_x=rpn.globl.PX_CONTROL, doc="""\
Execute a definite loop.
<limit> <initial> DO ... <incr> +LOOP

The iteration counter is available via I.  LEAVE will exit the loop early.

Example: 10 0 do I . 2 +loop
prints 0 2 4 6 8

qv DO, I, LEAVE, LOOP""")
def w_ctl_plusloop():
    pass                        # Grammar rules handle this word


@defword(name='-', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
Subtraction  ( y x -- y-x )""")
def w_minus():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if type(x) is rpn.type.Integer and type(y) is rpn.type.Integer:
        result = rpn.type.Integer(y.value - x.value)
    elif    type(x) is rpn.type.Float and type(y) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational] \
         or type(y) is rpn.type.Float and type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        result = rpn.type.Float(float(y.value) - float(x.value))
    elif    type(x) is rpn.type.Rational and type(y) in [rpn.type.Integer, rpn.type.Rational] \
         or type(y) is rpn.type.Rational and type(x) in [rpn.type.Integer, rpn.type.Rational]:
        result = rpn.type.Rational.from_Fraction(y.value - x.value)
    elif    type(x) is rpn.type.Complex and type(y) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational, rpn.type.Complex] \
         or type(y) is rpn.type.Complex and type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational, rpn.type.Complex]:
        result = rpn.type.Complex.from_complex(complex(y.value) - complex(x.value))
    else:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("-: Type error ({}, {})".format(typename(y), typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='.', args=1, print_x=rpn.globl.PX_IO, doc="""\
Print top stack value  ( x -- )
A space is also printed after the number, but no newline.
If you need a newline, call CR.""")
def w_dot():
    rpn.globl.write("{} ".format(rpn.globl.fmt(rpn.globl.param_stack.pop())))


@defword(name='.!', hidden=True, print_x=rpn.globl.PX_IO, args=1)
def w_dot_bang():
    rpn.globl.lnwriteln(repr(rpn.globl.param_stack.top()))


@defword(name='."', print_x=rpn.globl.PX_IO, doc="""\
Display string enclosed by quotation marks.
No newline is printed afterwards.

NOTE: The string begins immediately after the first ", so
  ."Hello, world!"
is correct.  This is different from Forth, where the must be a space after ." """)
def w_dot_quote():
    pass                        # Grammar rules handle this word


@defword(name='.all', args=1, print_x=rpn.globl.PX_IO, doc="""\
Print X in a variety of formats  ( x -- )""")
def w_dot_all():
    x = rpn.globl.param_stack.pop()
    xval = x.value

    out = "{}".format(rpn.globl.fmt(x))
    more = ""
    if type(x) is rpn.type.Integer:
        more += "  Hex={}".format(hex(x.value))
        more += "  Oct={}".format(oct(x.value))

        ascii_char = ["NUL", "SOH", "STX", "ETX", "EOT", "ENQ", "ACK", "BEL",
                      "BS",  "HT",  "LF",  "VT",  "FF",  "CR",  "SO",  "SI",
                      "DLE", "DC1", "DC2", "DC3", "DC4", "NAK", "SYN", "ETB",
                      "CAN", "EM",  "SUB", "ESC", "FS",  "GS",  "RS",  "US",
                      "SP",  "!",   "\"",  "#",   "$",   "%",   "&",   "'",
                      "(",   ")",   "*",   "+",   ",",   "-",   ".",   "/",
                      "0",   "1",   "2",   "3",   "4",   "5",   "6",   "7",
                      "8",   "9",   ":",   ";",   "<",   "=",   ">",   "?",
                      "@",   "A",   "B",   "C",   "D",   "E",   "F",   "G",
                      "H",   "I",   "J",   "K",   "L",   "M",   "N",   "O",
                      "P",   "Q",   "R",   "S",   "T",   "U",   "V",   "W",
                      "X",   "Y",   "Z",   "[",   "\\",  "]",   "^",   "_",
                      "`",   "a",   "b",   "c",   "d",   "e",   "f",   "g",
                      "h",   "i",   "j",   "k",   "l",   "m",   "n",   "o",
                      "p",   "q",   "r",   "s",   "t",   "u",   "v",   "w",
                      "x",   "y",   "z",   "{",   "|",   "}",   "~",   "DEL"]
        #if xval >= 0 and xval <= 127:
        if 0 <= xval < 128:
            more += "  Char={}".format(ascii_char[xval])

    out += more
    rpn.globl.writeln(out)


@defword(name='.bin', args=1, print_x=rpn.globl.PX_IO, doc="""\
Print X in binary  ( i -- )
X must be an integer.""")
def w_dot_bin():
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr(".b: Type error ({})".format(typename(x)))

    rpn.globl.write("{} ".format(bin(x.value)))


@defword(name='.hex', args=1, print_x=rpn.globl.PX_IO, doc="""\
Print X in hexadecimal  ( i -- )
X must be an integer.""")
def w_dot_hex():
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr(".x: Type error ({})".format(typename(x)))

    rpn.globl.write("{} ".format(hex(x.value)))


@defword(name='.oct', args=1, print_x=rpn.globl.PX_IO, doc="""\
Print X in octal  ( i -- )
X must be an integer.""")
def w_dot_oct():
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr(".o: Type error ({})".format(typename(x)))

    rpn.globl.write("{} ".format(oct(x.value)))


@defword(name='.r', args=2, print_x=rpn.globl.PX_IO, doc="""\
Print N right-justified in WIDTH  ( n width -- )

This never outputs more than WIDTH characters, and will silently truncate the
representation to fit.  It is wise to check the size of your values before
printing - you have been warned!  No space is printed after the number.""")
def w_dot_r():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr(".r: Width must be an integer ({})".format(typename(x)))
    width = x.value
    if width < 0:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr(".r: Width must not be negative")
    if width == 0:
        return

    s = rpn.globl.fmt(y, False)       # No label
    if len(s) > width:
        s = s[:width]       # This seems a bit harsh, but it's documented
    rpn.globl.write("{:>{width}}".format(s, width=width))


@defword(name='.s', print_x=rpn.globl.PX_IO, doc="""\
Print stack non-destructively""")
def w_dot_s():
    if not rpn.globl.param_stack.empty():
        rpn.globl.lnwriteln(rpn.globl.param_stack)


@defword(name='.s!', hidden=True, print_x=rpn.globl.PX_IO, doc="""\
Print stack non-destructively""")
def w_dot_s_bang():
    if not rpn.globl.param_stack.empty():
        rpn.globl.lnwriteln(repr(rpn.globl.param_stack))


@defword(name='/', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
Division  ( y x -- y/x )
X cannot be zero.""")
def w_slash():
    """\
|----------+----------+---------+----------+---------+--------+--------|
| Integer  | Float    | Float   | Rational | Complex |        |        |
| Float    | Float    | Float   | Float    | Complex |        |        |
| Rational | Rational | Float   | Rational | Complex |        |        |
| Complex  | Complex  | Complex | Complex  | Complex |        |        |
| Vector   |          |         |          |         |        |        |
| Matrix   |          |         |          |         |        |        |
|----------+----------+---------+----------+---------+--------+--------|
| ^Y    X> | Integer  | Float   | Rational | Complex | Vector | Matrix |"""
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()

    if     type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational, rpn.type.Complex] \
       and x.zerop():
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("/: X cannot be zero")

    if    type(x) is rpn.type.Rational and type(y) in [rpn.type.Integer, rpn.type.Rational] \
       or type(y) is rpn.type.Rational and type(x) in [rpn.type.Integer, rpn.type.Rational]:
        result = rpn.type.Rational.from_Fraction(y.value / x.value)
    elif    type(x) in [rpn.type.Integer, rpn.type.Float] and type(y) in [rpn.type.Integer, rpn.type.Float] \
         or type(x) is rpn.type.Rational and type(y) is rpn.type.Float \
         or type(y) is rpn.type.Rational and type(x) is rpn.type.Float:
        r = float(y.value) / float(x.value)
        if type(x) is rpn.type.Integer and type(y) is rpn.type.Integer and r.is_integer():
            result = rpn.type.Integer(r)
        else:
            result = rpn.type.Float(r)
    elif    type(x) is rpn.type.Complex and type(y) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational, rpn.type.Complex] \
         or type(y) is rpn.type.Complex and type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational, rpn.type.Complex]:
        result = rpn.type.Complex.from_complex(complex(y.value) / complex(x.value))
    else:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("/: Type error ({}, {})".format(typename(y), typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='/mod', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
Division quotient and remainder  ( y x -- remainder quotient )

Divide integers Y by X, returning integer remainder and quotient.
Signs are whatever Python // and % give you.""")
def w_slash_mod():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer or type(y) is not rpn.type.Integer:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("/mod: Type error ({}, {})".format(typename(y), typename(x)))
    if x.zerop():
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("/mod: X cannot be zero")
    rem =  y.value %  x.value
    quot = y.value // x.value
    rpn.globl.param_stack.push(rpn.type.Integer(rem))
    rpn.globl.param_stack.push(rpn.type.Integer(quot))


@defword(name=':', print_x=rpn.globl.PX_CONTROL, doc="""\
Define a new word  ( -- )
: WORD  [def ...]  ;

Define WORD with the specified definition.
Terminate the definition with a semi-colon.

qv SHOW""")
def w_ctl_colon():
    pass                        # Grammar rules handle this word


@defword(name=';', print_x=rpn.globl.PX_CONTROL, doc="""\
Terminate WORD definition  ( -- )
: WORD  [def ...]  ;""")
def w_ctl_semicolon():
    pass                        # Grammar rules handle this word


@defword(name='<', args=2, print_x=rpn.globl.PX_PREDICATE, doc="""\
Test if Y is less than X  ( y x -- flag )""")
def w_less_than():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if     type(x) in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float] \
       and type(y) in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
        yval = float(y.value)
        xval = float(x.value)
        rpn.globl.param_stack.push(rpn.type.Integer(rpn.globl.bool_to_int(yval < xval)))
    else:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("<: Type error ({}, {})".format(typename(y), typename(x)))


@defword(name='<<', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
<<  ( i2 i1 -- i2 << i1 )  Bitwise left shift""")
def w_leftshift():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer or type(y) is not rpn.type.Integer:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("<<: Type error ({}, {})".format(typename(y), typename(x)))

    if x.value < 0:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("<<: Shift amount may not be negative")

    rpn.globl.param_stack.push(rpn.type.Integer(y.value << x.value))


@defword(name='<=', args=2, print_x=rpn.globl.PX_PREDICATE, doc="""\
Test if Y is less than or equal to X  ( y x -- flag )""")
def w_less_than_or_equal():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if     type(x) in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float] \
       and type(y) in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
        yval = float(y.value)
        xval = float(x.value)
        rpn.globl.param_stack.push(rpn.type.Integer(rpn.globl.bool_to_int(yval <= xval)))
    else:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("<=: Type error ({}, {})".format(typename(y), typename(x)))




@defword(name='<>', args=2, print_x=rpn.globl.PX_PREDICATE, doc="""\
Test if Y is not equal to X  ( y x -- flag )""")
def w_not_equal():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()

    equal = equal_helper(x, y)
    if equal == -1:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("<>: Type error ({}, {})".format(typename(y), typename(x)))
    rpn.globl.param_stack.push(rpn.type.Integer(0 if equal else 1))


@defword(name='=', args=2, print_x=rpn.globl.PX_PREDICATE, doc="""\
Test if Y is equal to X  ( y x -- flag )""")
def w_equal():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()

    equal = equal_helper(x, y)
    if equal == -1:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("=: Type error ({}, {})".format(typename(y), typename(x)))
    rpn.globl.param_stack.push(rpn.type.Integer(equal))


@defword(name='>', args=2, print_x=rpn.globl.PX_PREDICATE, doc="""\
Test if Y is greater than X  ( y x -- flag )""")
def w_greater_than():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if     type(x) in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float] \
       and type(y) in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
        yval = float(y.value)
        xval = float(x.value)
        rpn.globl.param_stack.push(rpn.type.Integer(rpn.globl.bool_to_int(yval > xval)))
    else:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr(">: Type error ({}, {})".format(typename(y), typename(x)))


@defword(name='>=', args=2, print_x=rpn.globl.PX_PREDICATE, doc="""\
Test if Y is greater than or equal to X  ( y x -- flag )""")
def w_greater_than_or_equal():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if     type(x) in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float] \
       and type(y) in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
        yval = float(y.value)
        xval = float(x.value)
        rpn.globl.param_stack.push(rpn.type.Integer(rpn.globl.bool_to_int(yval >= xval)))
    else:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr(">=: Type error ({}, {})".format(typename(y), typename(x)))


@defword(name='>>', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
>>  ( i2 i1 -- i2 >> i1 )  Bitwise right shift""")
def w_rightshift():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer or type(y) is not rpn.type.Integer:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr(">>: Type error ({}, {})".format(typename(y), typename(x)))

    if x.value < 0:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr(">>: Shift amount may not be negative")

    rpn.globl.param_stack.push(rpn.type.Integer(y.value >> x.value))


@defword(name='>c', args=2, print_x=rpn.globl.PX_CONFIG, doc="""\
Construct a complex number from two reals  ( y x -- complex[x,y] )""")
def w_to_c():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if    type(x) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float] \
       or type(y) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr(">c: Type error ({}, {})".format(typename(y), typename(x)))
    rpn.globl.param_stack.push(rpn.type.Complex(float(x.value), float(y.value)))


@defword(name='>r', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
Push X onto return stack  ( x -- )""")
def w_to_r():
    rpn.globl.return_stack.push(rpn.globl.param_stack.pop())


if rpn.globl.have_module('numpy'):
    @defword(name='>v2', args=2, print_x=rpn.globl.PX_CONFIG, doc="""\
Create a 2-vector from the stack  ( y x -- v )""")
    def to_v_2():
        x = rpn.globl.param_stack.pop()
        y = rpn.globl.param_stack.pop()
        if    type(x) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float, rpn.type.Complex] \
           or type(y) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float, rpn.type.Complex]:
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            raise rpn.exception.TypeErr(">v2: Type error ({}, {})".format(typename(y), typename(x)))
        l = rpn.util.List()
        l.append(y)
        l.append(x)
        v = rpn.type.Vector(l)
        rpn.globl.param_stack.push(v)


if rpn.globl.have_module('numpy'):
    @defword(name='>v3', args=3, print_x=rpn.globl.PX_CONFIG, doc="""\
Create a 3-vector from the stack  ( z y x -- v )""")
    def to_v_3():
        x = rpn.globl.param_stack.pop()
        y = rpn.globl.param_stack.pop()
        z = rpn.globl.param_stack.pop()
        if    type(x) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float, rpn.type.Complex] \
           or type(y) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float, rpn.type.Complex] \
           or type(z) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float, rpn.type.Complex]:
            rpn.globl.param_stack.push(z)
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            raise rpn.exception.TypeErr(">v3: Type error ({}, {}, {})".format(typename(z), typename(y), typename(x)))
        l = rpn.util.List()
        l.append(z)
        l.append(y)
        l.append(x)
        v = rpn.type.Vector(l)
        rpn.globl.param_stack.push(v)


@defword(name='?', print_x=rpn.globl.PX_IO, doc="""\
?[topic]   Display information on a variety of topics""")
def w_info():
    rpn.globl.writeln("rpn version: {}".format(rpn.globl.RPN_VERSION))

    rpn.globl.write("NumPy:       ")
    if rpn.globl.have_module('numpy'):
        rpn.globl.writeln("{}".format(np.__version__))
    else:
        rpn.globl.writeln("[not found]")

    rpn.globl.write("SciPy:       ")
    if rpn.globl.have_module('scipy'):
        rpn.globl.writeln("{}".format(scipy.__version__))
    else:
        rpn.globl.writeln("[not found]")

    rpn.globl.write("Matplotlib:  ")
    if rpn.globl.have_module('matplotlib'):
        rpn.globl.writeln("{}".format(matplotlib.__version__))
    else:
        rpn.globl.writeln("[not found]")

    print("""\

rpn is a general-purpose calculator and programming language based loosely
on Forth and Hewlett-Packard calculators.

The following topics provide additional information:
    ?datatypes
    ?variables""")


@defword(name='?datatypes', print_x=rpn.globl.PX_IO, hidden=True, doc="")
def w_info_datatypes():
    print("""\
rpn supports the following datatypes, which may be placed directly on the
parameter stack.  Examples are also shown.

- Integer       1234
- Float         3.14159
- Rational      355::113
- Complex       (1.2, 3.4)
- Vector        [1 2 3 4]
- Matrix        [[1 0 0 0]
                 [0 1 0 0]
                 [0 0 1 0]
                 [0 0 0 1]]

Additionally, a String datatype is defined, which are placed on a separate
string stack.  "This is a sample string" """)


@defword(name='?dup', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
Duplicate top stack element if non-zero  ( x -- x x | 0 )""")
def w_query_dup():
    x = rpn.globl.param_stack.top()
    if type(x) not in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational, rpn.type.Complex]:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("?dup: Type error ({})".format(typename(x)))
    if not x.zerop():
        rpn.word.w_dup()


@defword(name='?key', print_x=rpn.globl.PX_IO, doc="""\
Read keystroke with flag ( -- key 1 | 0 | -1 )
?key will NOT block but rather return a success/fail flag to the stack.
ASCII code of keystroke will also be returned on success.
Keystroke WILL echo.  This works only on Unix/Linux.

EXAMPLE:
: test?key
  doc:"Display dots until a key is pressed  ( -- key )"
  begin  ?key case
    -1 of cr ."I/O error" cr leave endof
     0 of ."." 0.02 sleep endof
     1 of cr ."Key: " .all leave endof
    otherwise cr ."Found garbage on stack" cr .s leave
  endcase again  ;

qv key""")
def w_query_key():
    # Input that is not a tty doesn't get to play
    if not sys.stdin.isatty():
        rpn.globl.param_stack.push(rpn.type.Integer(-1))
        return

    fd = sys.stdin.fileno()
    oldattr = termios.tcgetattr(fd)
    newattr = termios.tcgetattr(fd)
    newattr[3] = newattr[3] & ~termios.ICANON
    newattr[3] = newattr[3] & ~termios.ECHO # Doesn't disable echo, not sure why not
    termios.tcsetattr(fd, termios.TCSANOW, newattr)

    oldflags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, oldflags | os.O_NONBLOCK)

    try:
        c = sys.stdin.read(1)
        if c == "":
            rpn.globl.param_stack.push(rpn.type.Integer(0))
            return
        rpn.globl.param_stack.push(rpn.type.Integer(ord(c)))
        rpn.globl.param_stack.push(rpn.type.Integer(1))
    except IOError:
        rpn.globl.param_stack.push(rpn.type.Integer(-1))
    finally:
        termios.tcsetattr(fd, termios.TCSAFLUSH, oldattr)
        fcntl.fcntl(fd, fcntl.F_SETFL, oldflags)


@defword(name='?variables', print_x=rpn.globl.PX_IO, hidden=True, doc="")
def w_info_variables():
    print("""\
Data from the stack may be stored in variables.  The syntax to store an object
is !VAR.  For example, to store the constant Pi (3.14...) into variable "mypi",
type:
        PI !mypi
Note that variables must be declared before they may be used.  To declare a
variable, which is initially created in an undefined state, type:
        variable mypi
Then the above example will work.  Variables local to a function can be defined
as follows:
        : myfunc  | x y z |   . . .  ;
x, y, and z will be locally defined only in the function "myfunc".

Values stored in variables may be pushed onto the stack with @VAR.

Note how this syntax differs from Forth's.  In Forth, one would say
        VAR @
This syntax is not allowed in Rpn because the "address" of a variable is never
exposed, and so it cannot ever be placed, however briefly, on the stack.  This
also means the that problem of accessing illegal memory cannot arise: the
variable is either findable by the system through its name, or it is not.""")


@defword(name='^', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
Exponentiation  ( y x -- y^x )""")
def w_caret():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if    type(x) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float, rpn.type.Complex] \
       or type(y) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float, rpn.type.Complex]:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("^: Type error ({}, {})".format(typename(y), typename(x)))

    r = pow(y.value, x.value)
    if type(r) is int:
        result = rpn.type.Integer(r)
    elif type(r) is float:
        result = rpn.type.Float(r)
    elif type(r) is complex:
        result = rpn.type.Complex.from_complex(r)
    else:
        raise rpn.exception.FatalErr("pow() returned a strange type '{}'".format(type(r)))
    rpn.globl.param_stack.push(result)


@defword(name='abort', print_x=rpn.globl.PX_CONTROL, doc="""\
Abort execution and return to top level

qv ABORT", EXIT, LEAVE""")
def w_abort():
    raise rpn.exception.Abort()


@defword(name='abort"', print_x=rpn.globl.PX_CONTROL, doc="""\
Conditionally abort execution  ( flag -- )
If flag is non-zero, abort execution and print a message
(up to the closing quotation mark) and return to top level

qv ABORT, EXIT, LEAVE""")
def w_abort_quote():
    pass                        # Grammar rules handle this word


@defword(name='abs', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Absolute value  ( x -- |x| )

NOTE: For complex numbers, ABS return the modulus (as a float).""")
def w_abs():
    x = rpn.globl.param_stack.pop()
    if type(x) is rpn.type.Integer:
        result = rpn.type.Integer(abs(x.value))
    elif type(x) in [rpn.type.Float, rpn.type.Complex]:
        result = rpn.type.Float(abs(x.value))
    elif type(x) is rpn.type.Rational:
        result = rpn.type.Rational.from_Fraction(abs(x.value))
    elif type(x) is rpn.type.Vector:
        if x.size() == 0:
            rpn.globl.param_stack.push(x)
            raise rpn.exception.ValueErr("abs: X cannot be an empty vector")
        sumsq = 0.0
        for val in x.value:
            sumsq += val ** 2
        r = rpn.globl.to_python_class(sumsq)
        t = type(r)
        if t is float:
            result = rpn.type.Float(math.sqrt(r))
        elif t is complex:
            result = rpn.type.Complex.from_complex(cmath.sqrt(r))
        else:
            raise rpn.exception.FatalErr("{}: Cannot handle type {}".format(whoami(), t))
    else:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("abs: Type error ({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='acos', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Inverse cosine  ( cosine -- angle )
|x| <= 1""")
def w_acos():
    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        try:
            r = math.acos(float(x.value))
        except ValueError:
            rpn.globl.param_stack.push(x)
            raise rpn.exception.ValueErr("acos: Argument {} out of range".format(x.value))
        result = rpn.type.Float(rpn.globl.convert_radians_to_mode(r))
        result.label = rpn.globl.angle_mode_label()
    elif type(x) is rpn.type.Complex:
        try:
            r = cmath.acos(x.value)
        except ValueError:
            rpn.globl.param_stack.push(x)
            raise rpn.exception.ValueErr("acos: Argument {} out of range".format(x.value))
        result = rpn.type.Complex.from_complex(r)
    else:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("acos: Type error ({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='acosh', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Inverse hyperbolic cosine  ( cosine_h -- angle )

DEFINITION:
acosh(x) = ln(x + sqrt(x^2 - 1)), x >= 1""")
def w_acosh():
    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        try:
            r = math.acosh(float(x.value))
        except ValueError:
            rpn.globl.param_stack.push(x)
            raise rpn.exception.ValueErr("acosh: Argument {} out of range".format(x.value))
        result = rpn.type.Float(r)
    elif type(x) is rpn.type.Complex:
        try:
            r = cmath.acosh(x.value)
        except ValueError:
            rpn.globl.param_stack.push(x)
            raise rpn.exception.ValueErr("acosh: Argument {} out of range".format(x.value))
        result = rpn.type.Complex.from_complex(r)
    else:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("acosh: Type error ({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='again', print_x=rpn.globl.PX_CONTROL, doc="""\
Execute an indefinite loop forever.
BEGIN ... AGAIN

LEAVE will exit the loop early.

qv BEGIN, LEAVE, REPEAT, UNTIL, WHILE""")
def w_again():
    pass                        # Grammar rules handle this word


@defword(name='alog', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Common exponential [antilogarithm]  ( x -- 10^x )""")
def w_alog():
    x = rpn.globl.param_stack.pop()
    if type(x) not in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational, rpn.type.Complex]:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("alog: Type error ({})".format(typename(x)))
    r = 10.0 ** x.value
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        result = rpn.type.Float(r)
    elif type(x) is rpn.type.Complex:
        result = rpn.type.Complex.from_complex(r)
    rpn.globl.param_stack.push(result)


@defword(name='and', args=2, print_x=rpn.globl.PX_PREDICATE, doc="""\
Logical AND  ( flag flag -- flag )
(This is not a bitwise AND - use BITAND for that.)""")
def w_logand():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer or type(y) is not rpn.type.Integer:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("and: Type error ({}, {})".format(typename(y), typename(y)))

    if x.value not in [0, 1]:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("and: X must be TRUE (1) or FALSE (0), not {}".format(x.value))
    if y.value not in [0, 1]:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("and: Y must be TRUE (1) or FALSE (0), not {}".format(y.value))

    rpn.globl.param_stack.push(rpn.type.Integer(x.value and y.value))


@defword(name='asin', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Inverse sine  ( sine -- angle )
|x| <= 1""")
def w_asin():
    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        try:
            r = math.asin(float(x.value))
        except ValueError:
            rpn.globl.param_stack.push(x)
            raise rpn.exception.ValueErr("asin: Argument {} out of range".format(x.value))
        result = rpn.type.Float(rpn.globl.convert_radians_to_mode(r))
        result.label = rpn.globl.angle_mode_label()
    elif type(x) is rpn.type.Complex:
        try:
            r = cmath.asin(x.value)
        except ValueError:
            rpn.globl.param_stack.push(x)
            raise rpn.exception.ValueErr("asin: Argument {} out of range".format(x.value))
        result = rpn.type.Complex.from_complex(r)
    else:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("asin: Type error ({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='asinh', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Inverse hyperbolic sine  ( sine_h -- angle )

DEFINITION:
asinh(x) = ln(x + sqrt(x^2 + 1))""")
def w_asinh():
    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        try:
            r = math.asinh(float(x.value))
        except ValueError:
            rpn.globl.param_stack.push(x)
            raise rpn.exception.ValueErr("asinh: Argument {} out of range".format(x.value))
        result = rpn.type.Float(r)
    elif type(x) is rpn.type.Complex:
        try:
            r = cmath.asinh(x.value)
        except ValueError:
            rpn.globl.param_stack.push(x)
            raise rpn.exception.ValueErr("asinh: Argument {} out of range".format(x.value))
        result = rpn.type.Complex.from_complex(r)
    else:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("asinh: Type error ({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='atan', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Inverse tangent  ( tangent -- angle )

NOTE:
Consider using atan2 instead, especially if you are computing atan(y/x).""")
def w_atan():
    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        try:
            r = math.atan(float(x.value))
        except ValueError:
            rpn.globl.param_stack.push(x)
            raise rpn.exception.ValueErr("atan: Argument {} out of range".format(x.value))
        result = rpn.type.Float(rpn.globl.convert_radians_to_mode(r))
        result.label = rpn.globl.angle_mode_label()
    elif type(x) is rpn.type.Complex:
        try:
            r = cmath.atan(x.value)
        except ValueError:
            rpn.globl.param_stack.push(x)
            raise rpn.exception.ValueErr("atan: Argument {} out of range".format(x.value))
        result = rpn.type.Complex.from_complex(r)
    else:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("atan: Type error ({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='atan2', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
Inverse tangent of y/x  ( y x -- angle )""")
def w_atan2():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        try:
            r = math.atan2(float(y.value), float(x.value))
        except ValueError:
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            raise rpn.exception.ValueErr("atan2: Invalid arguments ({} {})".format(y.value, x.value))
        result = rpn.type.Float(rpn.globl.convert_radians_to_mode(r))
        result.label = rpn.globl.angle_mode_label()
    elif type(x) is rpn.type.Complex:
        # Python cmath doesn't have atan2, so fake it
        if x.zerop():
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            raise rpn.exception.ValueErr("atan2: Invalid arguments ({} {})".format(y.value, x.value))
        r = cmath.atan(y / x)
        result = rpn.type.Complex.from_complex(r)
    else:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("atan2: Type error ({} {})".format(typename(y), typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='atanh', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Inverse hyperbolic tangent  ( tangent_h -- angle )

DEFINITION:
atanh(x) = 1/2 ln((1+x) / (1-x)), |x| < 1""")
def w_atanh():
    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        try:
            r = math.atanh(float(x.value))
        except ValueError:
            rpn.globl.param_stack.push(x)
            raise rpn.exception.ValueErr("atanh: Argument {} out of range".format(x.value))
        result = rpn.type.Float(r)
    elif type(x) is rpn.type.Complex:
        try:
            r = cmath.atanh(x.value)
        except ValueError:
            rpn.globl.param_stack.push(x)
            raise rpn.exception.ValueErr("atanh: Argument {} out of range".format(x.value))
        result = rpn.type.Complex.from_complex(r)
    else:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("atanh: Type error ({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='beg', print_x=rpn.globl.PX_CONFIG, doc="""\
Set "Begin" (annuity due) financial mode.

Do not confuse this with the "begin" command, which starts a loop.""")
def w_beg():
    rpn.flag.set_flag(rpn.flag.F_TVM_BEGIN_MODE)


@defword(name='begin', print_x=rpn.globl.PX_CONTROL, doc="""\
Execute an indefinite loop.
BEGIN ... AGAIN
BEGIN ... <flag> UNTIL
BEGIN ... <flag> WHILE ... REPEAT

LEAVE will exit the loop early.  Note that the effect of the test in
BEGIN...WHILE is opposite that in BEGIN...UNTIL.  The loop repeats
while something is true, rather than until it becomes true.

Do not confuse this with the "beg" command, which sets 'begin mode' for
Time Value of Money calculations.

qv AGAIN, LEAVE, REPEAT, UNTIL, WHILE""")
def w_begin():
    pass                        # Grammar rules handle this word


@defword(name='binom', args=3, print_x=rpn.globl.PX_COMPUTE, doc="""\
Binomial probability ( n k p -- prob )

Return the probability of an event occurring exactly k times in n attempts,
where the probability of it occurring in a single attempt is p.

DEFINITION:
binom(n,k,p) = comb(n,k) * p^k * (1-p)^(n-k)""")
def w_binom():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    z = rpn.globl.param_stack.pop()
    if    type(x) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float] \
       or type(y) is not rpn.type.Integer \
       or type(z) is not rpn.type.Integer:
        rpn.globl.param_stack.push(z)
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("binom: Type error ({}, {}, {})".format(typename(z), typename(y), typename(x)))
    p = float(x.value)
    k = y.value
    n = z.value

    if p == 0:
        r = 1 if k == 0 else 0
    elif p == 1:
        r = 1 if k == n else 0
    else:
        r = comb_helper(n, k) * p**k * (1.0-p)**(n-k)

    rpn.globl.param_stack.push(rpn.type.Float(r))


@defword(name='bitand', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
bitand  ( i2 i1 -- i2 AND i1 )  Bitwise AND

Perform a bitwise boolean AND on two integers""")
def w_bitand():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer or type(y) is not rpn.type.Integer:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("bitand: Type error ({}, {})".format(typename(y), typename(x)))

    rpn.globl.param_stack.push(rpn.type.Integer(y.value & x.value))


@defword(name='bitnot', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
bitnot  ( i1 -- NOT i1 )  Bitwise NOT

Perform a bitwise boolean NOT on an integer.  Sometimes known as INVERT.""")
def w_bitnot():
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("bitnot: Type error ({})".format(typename(x)))

    rpn.globl.param_stack.push(rpn.type.Integer(~ x.value))


@defword(name='bitor', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
bitor  ( i2 i1 -- i2 OR i1 )  Bitwise OR

Perform a bitwise boolean OR on two integers""")
def w_bitor():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer or type(y) is not rpn.type.Integer:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("bitor: Type error ({}, {})".format(typename(y), typename(x)))

    rpn.globl.param_stack.push(rpn.type.Integer(y.value | x.value))


@defword(name='bitxor', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
bitxor  ( i2 i1 -- i2 XOR i1 )  Bitwise XOR

Perform a bitwise boolean Exclusive OR on two integers""")
def w_bitxor():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer or type(y) is not rpn.type.Integer:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("bitxor: Type error ({}, {})".format(typename(y), typename(x)))

    rpn.globl.param_stack.push(rpn.type.Integer(y.value ^ x.value))


@defword(name='bye', print_x=rpn.globl.PX_CONTROL, doc="""\
Exit program""")
def w_bye():
    raise rpn.exception.EndProgram()


@defword(name='c>', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
c>  ( c -- y x )  Extract imaginary and real parts of a complex number""")
def w_c_from():
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Complex:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("c>: Type error ({})".format(typename(x)))
    rpn.globl.param_stack.push(rpn.type.Float(x.imag()))
    rpn.globl.param_stack.push(rpn.type.Float(x.real()))


@defword(name='case', print_x=rpn.globl.PX_CONTROL, doc="""\
Execute a sequence of words based on stack value.  Once a match is
executed, no other clauses are considered.  OTHERWISE is optional.
<n> and OF labels must be integers.  CASE consumes the top of stack
like any word; however the integer value is available to the sequence
in variable "caseval".

<n> CASE
  <x> OF ... ENDOF
  <y> OF ... ENDOF
  <z> OF ... ENDOF
  [ OTHERWISE ... ]
ENDCASE

qv ENDCASE, ENDOF, OF, OTHERWISE""")
def w_case():
    pass                        # Grammar rules handle this word


@defword(name='catch', print_x=rpn.globl.PX_CONTROL, doc="""\
Catch any exceptions.

catch WORD

qv THROW""")
def w_catch():
    pass                        # Grammar rules handle this word


@defword(name='ceil', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Ceiling  ( x -- ceil )   Smallest integer greater than or equal to X""")
def w_ceil():
    x = rpn.globl.param_stack.pop()
    if type(x) is rpn.type.Integer:
        result = x
    elif type(x) in [rpn.type.Float, rpn.type.Rational]:
        result = rpn.type.Integer(math.ceil(x.value))
    else:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("ceil: Type error ({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='cf', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
Clear flag  ( f -- )

Do not confuse this with "CF", which is for Compounding Frequency""")
def w_cf():
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("cf: Type error ({})".format(typename(x)))
    flag = x.value
    if flag < 0 or flag >= rpn.flag.MAX:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("cf: Flag {} out of range (0..{} expected)".format(flag, rpn.flag.MAX - 1))
    if flag >= rpn.flag.FENCE:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("cf: Flag {} cannot be modified".format(flag))
    rpn.flag.clear_flag(flag)


@defword(name='chr', args=1, print_x=rpn.globl.PX_IO, doc="""\
chr  ( x -- )  Push string for a single ASCII character.""")
def w_chr():
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("chr: Type error ({})".format(typename(x)))
    rpn.globl.string_stack.push(rpn.type.String("{}".format(chr(x.value))))


# Some HP calcs call this NEGATE, but why type 6 characters when 3 will do?
@defword(name='chs', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Negation (change sign)  ( x -- -x )""")
def w_chs():
    x = rpn.globl.param_stack.pop()
    if type(x) is rpn.type.Integer:
        result = rpn.type.Integer(-1 * x.value)
    elif type(x) is rpn.type.Float:
        result = rpn.type.Float(-1.0 * x.value)
    elif type(x) is rpn.type.Rational:
        result = rpn.type.Rational.from_Fraction(Fraction(-1, 1) * x.value)
    elif type(x) is rpn.type.Complex:
        result = rpn.type.Complex(-1.0*x.real(), -1.0*x.imag())
    else:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("chs: Type error ({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='clfin', print_x=rpn.globl.PX_CONFIG, doc="""\
Clear financial variables""")
def w_clfin():
    rpn.flag.clear_flag(rpn.flag.F_TVM_CONTINUOUS)
    rpn.flag.clear_flag(rpn.flag.F_TVM_BEGIN_MODE)

    rpn.tvm.N.obj   = None
    rpn.tvm.INT.obj = None
    rpn.tvm.PV.obj  = None
    rpn.tvm.PMT.obj = None
    rpn.tvm.FV.obj  = None

    rpn.globl.param_stack.push(rpn.type.Integer(1))
    rpn.word.w_cpf()


@defword(name='clflag', print_x=rpn.globl.PX_CONFIG, doc="""\
Clear all flags  ( -- )""")
def w_clflag():
    for i in range(rpn.flag.FENCE):
        rpn.flag.clear_flag(i)


@defword(name='clreg', print_x=rpn.globl.PX_CONFIG, doc="""]
Clear all registers.""")
def w_clreg():
    rpn.globl.register = dict()
    for i in range(rpn.globl.REG_SIZE_MAX):
        rpn.globl.register[i] = rpn.type.Float(0.0)
    rpn.globl.register['I'] = rpn.type.Float(0.0)


@defword(name='clrst', print_x=rpn.globl.PX_CONFIG, doc="""\
Clear the return stack.

Do not confuse this with the "clst" command, which clears the parameter stack.""")
def w_clrst():
    rpn.globl.return_stack.clear()


@defword(name='clstat', print_x=rpn.globl.PX_CONFIG, doc="""\
Clear the statistics array""")
def w_clstat():
    rpn.globl.stat_data = []


@defword(name='clst', print_x=rpn.globl.PX_CONFIG, doc="""\
Clear the stack

Do not confuse this with the "clrst" command, which clears the return stack.

DEFINITION:
: clst  depth 0 do drop loop ;""")
def w_clst():
    rpn.globl.param_stack.clear()


@defword(name='comb', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
Combinations  ( n r -- nCr )
Choose from N objects R at a time, without regard to ordering.

DEFINITION:
          n!
nCr = -----------
      r! * (n-r)!""")
def w_comb():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer or type(y) is not rpn.type.Integer:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("comb: Type error ({}, {})".format(typename(y), typename(x)))

    # Python 3.8 has math.comb()
    n = y.value
    r = x.value
    result = rpn.type.Integer(comb_helper(n, r))

    rpn.globl.param_stack.push(result)


@defword(name='constant', print_x=rpn.globl.PX_CONFIG, doc="""\
Declare a constant variable  ( n -- )
CONSTANT <ccc>""")
def w_constant():
    pass                        # Grammar rules handle this word


@defword(name='cos', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Cosine  ( angle -- cosine )""")
def w_cos():
    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        result = rpn.type.Float(math.cos(rpn.globl.convert_mode_to_radians(float(x.value))))
    elif type(x) is rpn.type.Complex:
        result = rpn.type.Complex.from_complex(cmath.cos(x.value))
    else:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("cos: Type error ({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='cosh', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Hyperbolic cosine  ( angle -- cosine_h )

DEFINITION:
          e^x + e^(-x)
cosh(x) = ------------
               2""")
def w_cosh():
    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        result = rpn.type.Float(math.cosh(float(x.value)))
    elif type(x) is rpn.type.Complex:
        result = rpn.type.Complex.from_complex(cmath.cosh(x.value))
    else:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("cosh: Type error ({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='CPF', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
Set CF and PF to N  ( n -- )""")
def w_cpf():
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("CPF: Type error ({})".format(typename(x)))
    n = x.value
    if n < 1 or n > 365:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("CPF: Argument {} out of range (1..365 expected)".format(n))

    cf = rpn.type.Integer(n)
    cf.label = "CF"
    rpn.tvm.CF.obj = cf

    pf = rpn.type.Integer(n)
    pf.label = "PF"
    rpn.tvm.PF.obj = pf


@defword(name='cr', print_x=rpn.globl.PX_IO, doc="""\
Print a newline""")
def w_cr():
    rpn.globl.writeln()


def w_sum3(y):
    return int(y * 365.25) - int(y / 100) + int(y / 400)

def w_m306(m):
    return int(m * 30.6001)

@defword(name='d->hp', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Convert date to HP day number  ( MM.DDYYYY -- day# )

Day # 0 = October 15, 1582""")
def w_d_to_hp():
    day0_julian = 2299160
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Float:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("d->hp: Type error ({})".format(typename(x)))

    (valid, dateobj, julian) = x.date_info()
    if not valid:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("d->hp: {} is not a valid date".format(x.value))

    if dateobj.month < 3:
        m = dateobj.month + 13
        y = dateobj.year - 1
    else:
        m = dateobj.month + 1
        y = dateobj.year

    daynum = sum3(y) + m306(m) + dateobj.day - 578164
    if julian - daynum + day0_julian != 0:
        rpn.globl.lnwriteln("d->hp: Result differs from Julian")

    result = rpn.type.Integer(daynum)
    result.label = "HP day"
    rpn.globl.param_stack.push(result)


@defword(name='d->jd', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Convert date to Julian day number ( MM.DDYYYY -- julian )""")
def w_d_to_jd():
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Float:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("d->jd: Type error ({})".format(typename(x)))

    (valid, _, julian) = x.date_info() # middle value is dateobj
    if not valid:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("d->jd: {} is not a valid date".format(x.value))

    result = rpn.type.Integer(julian)
    result.label = "Julian day"
    rpn.globl.param_stack.push(result)


@defword(name='d->r', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Convert degrees to radians ( deg -- rad )""")
def w_d_to_r():
    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        result = rpn.type.Float(rpn.globl.convert_mode_to_radians(float(x.value), "d"))
        result.label = "Rad"
    else:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("d->r: Type error ({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='date', print_x=rpn.globl.PX_COMPUTE, doc="""\
Current date  ( -- MM.DDYYYY )""")
def w_date():
    d = datetime.date.today().strftime("%m.%d%Y")
    result = rpn.type.Float(d)
    result.label = "MM.DDYYYY (Current)"
    rpn.globl.param_stack.push(result)


@defword(name='dateinfo', args=1, hidden=True, print_x=rpn.globl.PX_IO, doc="""\
Show date_info() for Float  ( x -- )""")
def w_dateinfo():
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Float:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("dateinfo: Type error ({})".format(typename(x)))
    rpn.globl.writeln("dateinfo: {}".format(x.date_info()))


@defword(name='date+', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
Add N days to date  ( date1 N -- date2 )""")
def w_date_plus():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer or type(y) is not rpn.type.Float:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("date+: Type error ({}, {})".format(typename(y), typename(y)))

    (valid, dateobj, julian) = y.date_info()
    if not valid:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("date+: {} is not a valid date".format(y.value))

    new_julian = julian + x.value
    dateobj = datetime.date.fromordinal(new_julian - rpn.globl.JULIAN_OFFSET)
    result = rpn.type.Float("%d.%02d%04d" % (dateobj.month, dateobj.day, dateobj.year))
    result.label = "DD.MMYYYY"
    rpn.globl.param_stack.push(result)


@defword(name='date-', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
Subtract N days from date  ( date1 N -- date2 )""")
def w_date_minus():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer or type(y) is not rpn.type.Float:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("date-: Type error ({}, {})".format(typename(y), typename(y)))

    (valid, dateobj, julian) = y.date_info()
    if not valid:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("date-: {} is not a valid date".format(y.value))

    new_julian = julian - x.value
    dateobj = datetime.date.fromordinal(new_julian - rpn.globl.JULIAN_OFFSET)
    result = rpn.type.Float("%d.%02d%04d" % (dateobj.month, dateobj.day, dateobj.year))
    result.label = "DD.MMYYYY"
    rpn.globl.param_stack.push(result)


@defword(name='dbg.token', hidden=True, print_x=rpn.globl.PX_CONFIG)
def w_dbg_token():
    rpn.flag.set_flag(rpn.flag.F_DEBUG_ENABLED)
    rpn.debug.set_debug_level("token", 3)


@defword(name='ddays', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
Number of days between two dates  ( date1 date2 -- ddays )
Usually the earlier date is in Y, and later date in X.""")
def w_ddays():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Float or type(y) is not rpn.type.Float:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("ddays: Type error ({}, {})".format(typename(y), typename(y)))

    (valid, _, xjulian) = x.date_info() # middle value is dateobj
    if not valid:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("ddays: {} is not a valid date".format(x.value))

    (valid, _, yjulian) = y.date_info() # middle value is dateobj
    if not valid:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("ddays: {} is not a valid date".format(y.value))

    # Y is expected to be earlier, so we subtract in this order to get a
    # positive value for "later"
    result = rpn.type.Integer(xjulian - yjulian)
    result.label = "Delta days"
    rpn.globl.param_stack.push(rpn.type.Integer(xjulian - yjulian))


@defword(name='DEG', print_x=rpn.globl.PX_COMPUTE, doc="""\
Constant: Degrees per radian  ( -- 57.29577... )

DEFINITION:
DEG == 360/TAU == 180/PI

WARNING:
Do not confuse this with \"deg\" (which sets the angular mode to degrees).""")
def w_DEG():
    result = rpn.type.Float(rpn.globl.DEG_PER_RAD)
    result.label = "Deg/Rad"
    rpn.globl.param_stack.push(result)


@defword(name='deg', print_x=rpn.globl.PX_CONFIG, doc="""\
Set angular mode to degrees.

WARNING:
Do not confuse this with \"DEG\" (which is the number of degress per radian).""")
def w_deg():
    rpn.flag.clear_flag(rpn.flag.F_RAD)
    rpn.flag.clear_flag(rpn.flag.F_GRAD)


@defword(name='depth', print_x=rpn.globl.PX_COMPUTE, doc="""\
Current number of elements on stack  ( -- n )""")
def w_depth():
    rpn.globl.param_stack.push(rpn.type.Integer(rpn.globl.param_stack.size()))


@defword(name='dim', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Dimension(s) of X.

For integers, floats, and rationals (scalars):
                              return 0
For complex numbers:          return 2
For vectors of length N:      return a vector [N]
For an M-row by N-col matrix: return a vector [M N]""")
def w_dim():
    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        result = rpn.type.Integer(0)
    elif type(x) is rpn.type.Complex:
        result = rpn.type.Integer(2)
    elif type(x) is rpn.type.Vector:
        result = rpn.type.Vector(rpn.util.List(rpn.type.Integer(x.size())))
    elif type(x) is rpn.type.Matrix:
        # Pretty ugly.  Need a better method to append items.  Ugh,
        # things get added at the beginning of the list, so we have to
        # add the cols, THEN the rows in order to end up with
        # [ rows cols ].
        l = rpn.util.List(rpn.type.Integer(x.ncols()))
        l2 = rpn.util.List(rpn.type.Integer(x.nrows()), l)
        result = rpn.type.Vector(l2) # [ rows cols ]
    else:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("dim: Type error ({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='do', print_x=rpn.globl.PX_CONTROL, doc="""\
Execute a definite loop.
<limit> <initial> DO ...        LOOP
<limit> <initial> DO ... <incr> +LOOP

The iteration counter is available via I.  LEAVE will exit the loop early.

Example: 10 0 do I . loop
prints 0 1 2 3 4 5 6 7 8 9

qv I, LEAVE, LOOP, +LOOP""")
def w_do():
    pass                        # Grammar rules handle this word


if rpn.globl.have_module('numpy'):
    @defword(name='dot', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
Vector dot product  ( vec_y vec_x -- real )""")
    def dot_prod():
        x = rpn.globl.param_stack.pop()
        y = rpn.globl.param_stack.pop()
        if type(x) is rpn.type.Vector and type(y) is rpn.type.Vector:
            try:
                r = y.value.dot(x.value)
            except ValueError:
                rpn.globl.param_stack.push(y)
                rpn.globl.param_stack.push(x)
                raise rpn.exception.ValueErr("dot: Conformability error: Vectors ({} and {}) are not same size".format(y, x))

            result = rpn.globl.to_rpn_class(r)
        else:
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            raise rpn.exception.TypeErr("dot: Type error ({}, {})".format(typename(y), typename(x)))

        rpn.globl.param_stack.push(result)


@defword(name='dow', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Day of week  ( MM.DDYYYY -- dow )
1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat, 7=Sun""")
def w_dow():
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Float:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("dow: Type error ({})".format(typename(x)))

    (valid, dateobj, _) = x.date_info() # third value is julian
    if not valid:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("dow: {} is not a valid date".format(x.value))

    result = rpn.type.Integer(dateobj.isoweekday())
    result.label = "Day of week"
    rpn.globl.param_stack.push(result)


@defword(name='dow$', args=1, print_x=rpn.globl.PX_IO, doc="""\
Day of week name  ( dow -- )  [ -- abbrev ]
Return abbreviated day of week name as string.  dow should be between 1 and 7.

qv DOW""")
def w_dow_dollar():
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("dow$: Type error ({})".format(typename(x)))
    dow = x.value
    if dow < 1 or dow > 7:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("dow$: Day of week out of range (1..7 expected)")
    dow_abbrev = { 1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu",
                   5: "Fri", 6: "Sat", 7: "Sun" }
    rpn.globl.string_stack.push(rpn.type.String.from_string(dow_abbrev[dow]))


@defword(name='drop', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
Remove top stack element  ( x -- )""")
def w_drop():
    rpn.globl.param_stack.pop()


@defword(name='dup', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
Duplicate top stack element  ( x -- x x )
Equivalent to 0 PICK""")
def w_dup():
    x = rpn.globl.param_stack.top()
    rpn.globl.param_stack.push(x)


@defword(name='E', print_x=rpn.globl.PX_COMPUTE, doc="""\
Constant: Base of natural logarithms ( -- 2.71828... )""")
def w_E():
    result = rpn.type.Float(rpn.globl.E)
    result.label = "E"
    rpn.globl.param_stack.push(result)


@defword(name='edit', hidden=True, print_x=rpn.globl.PX_CONFIG, doc="""\
Edit some text""")
def w_edit():
    env = os.environ
    if "VISUAL" in env:
        editor = env.get("VISUAL")
    elif "EDITOR" in env:
        editor = env.get("EDITOR")
    else:
        editor = "ed"

    # Set initial value
    initial_value = b"Initial string"

    with tempfile.NamedTemporaryFile(suffix=".tmp") as tf:
        tf.write(initial_value)
        tf.flush()
        subprocess.call([editor, tf.name])
        tf.seek(0)
        edited_message = tf.read()

    print(edited_message.decode("utf-8"))


@defword(name='expm1', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Calculate (e^X)-1 accurately  ( x -- (e^x)-1 )""")
def w_e_x_minus_1():
    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        result = rpn.type.Float(math.expm1(x.value))
    elif type(x) is rpn.type.Complex:
        result = rpn.type.Complex.from_complex(cmath.exp(x.value) - 1.0)
    else:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("expm1: Type error ({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='else', args=1, print_x=rpn.globl.PX_CONTROL, doc="""\
Execute a conditional test.
<flag> IF ... [ ELSE ... ] THEN

qv IF, THEN""")
def w_ctl_else():
    pass                        # Grammar rules handle this word


@defword(name='emit', args=1, print_x=rpn.globl.PX_IO, doc="""\
emit  ( x -- )  Print a single ASCII character
No space or newline is appended.""")
def w_emit():
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("emit: Type error ({})".format(typename(x)))
    rpn.globl.write(chr(x.value))


@defword(name='end', print_x=rpn.globl.PX_CONFIG, doc="""\
Set "End" (ordinary annuity) financial mode.""")
def w_end():
    rpn.flag.clear_flag(rpn.flag.F_TVM_BEGIN_MODE)


@defword(name='endcase', print_x=rpn.globl.PX_CONTROL, doc="""\
Execute a sequence of words based on stack value.  Once a match is
executed, no other clauses are considered.  OTHERWISE is optional.
<n> and OF labels must be integers.

<n> CASE
  <x> OF ... ENDOF
  <y> OF ... ENDOF
  <z> OF ... ENDOF
  [ OTHERWISE ... ]
ENDCASE

qv CASE, ENDOF, OF, OTHERWISE""")
def w_endcase():
    pass                        # Grammar rules handle this word


@defword(name='endof', print_x=rpn.globl.PX_CONTROL, doc="""\
Execute a sequence of words based on stack value.  Once a match is
executed, no other clauses are considered.  OTHERWISE is optional.
<n> and OF labels must be integers.

<n> CASE
  <x> OF ... ENDOF
  <y> OF ... ENDOF
  <z> OF ... ENDOF
  [ OTHERWISE ... ]
ENDCASE

qv CASE, ENDCASE, OF, OTHERWISE""")
def w_endof():
    pass                        # Grammar rules handle this word


@defword(name='eng', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
Set engineering display  ( n -- )

N specifies the total number of significant digits.""")
def w_eng():
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("eng: Type error ({})".format(typename(x)))

    if x.value < 0 or x.value >= rpn.globl.PRECISION_MAX:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("eng: Precision '{}' out of range (0..{} expected)".format(x.value, rpn.globl.PRECISION_MAX - 1))

    rpn.globl.disp_stack.top().style = "eng"
    rpn.globl.disp_stack.top().prec = x.value
    rpn.flag.clear_flag(rpn.flag.F_DISP_FIX)
    rpn.flag.set_flag(rpn.flag.F_DISP_ENG)


@defword(name='epoch', print_x=rpn.globl.PX_COMPUTE, doc="""\
Seconds since epoch  ( -- secs )""")
def w_epoch():
    now = calendar.timegm(time.gmtime())
    result = rpn.type.Integer(now)
    result.label = "Epoch"
    rpn.globl.param_stack.push(result)


@defword(name='erf', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Error function  ( x -- erf[x] )""")
def w_erf():
    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        try:
            r = math.erf(float(x.value))
        except ValueError:
            rpn.globl.param_stack.push(x)
            raise rpn.exception.ValueErr("erf: Invalid argument")
        result = rpn.type.Float(r)
    elif type(x) is rpn.type.Complex:
        if not rpn.globl.have_module('scipy'):
            rpn.globl.param_stack.push(x)
            raise rpn.exception.RuntimeErr("erf: Complex support requires 'scipy' library")
        r = scipy.special.erf(x.value)
        result = rpn.type.Complex.from_complex(r)
    else:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("erf: Type error({})".format(typename(x)))
    result.label = "erf"
    rpn.globl.param_stack.push(result)


@defword(name='erfc', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Complementary error function  ( x -- erfc[x] )

DEFINITION:
erfc(x) = 1 - erf(x)""")
def w_erfc():
    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        try:
            r = math.erfc(float(x.value))
        except ValueError:
            rpn.globl.param_stack.push(x)
            raise rpn.exception.ValueErr("erfc: Invalid argument")
        result = rpn.type.Float(r)
    elif type(x) is rpn.type.Complex:
        if not rpn.globl.have_module('scipy'):
            rpn.globl.param_stack.push(x)
            raise rpn.exception.RuntimeErr("erfc: Complex support requires 'scipy' library")
        r = scipy.special.erfc(x.value)
        result = rpn.type.Complex.from_complex(r)
    else:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("erfc: Type error({})".format(typename(x)))
    result.label = "erfc"
    rpn.globl.param_stack.push(result)


@defword(name='eval', str_args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
Evaluate string on top of stack as a command sequence.""")
def w_eval():
    s = rpn.globl.string_stack.pop().value
    rpn.globl.eval_string(s)


@defword(name='exit', print_x=rpn.globl.PX_CONTROL, doc="""\
Terminate execution of current word""")
def w_exit():
    raise rpn.exception.Exit()


@defword(name='exp', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Natural exponential ( x -- e^x )""")
def w_exp():
    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        result = rpn.type.Float(math.exp(float(x.value)))
    elif type(x) is rpn.type.Complex:
        result = rpn.type.Complex.from_complex(cmath.exp(complex(x.value)))
    else:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("exp: Type error ({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='fact', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Factorial ( x -- x! )

DEFINITION:
x! = x * (x-1) * (x-2) ... * 2 * 1
0! = 1
X cannot be negative.

qv gamma""")
def w_fact():
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("fact: Type error ({})".format(typename(x)))
    if x.value < 0:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("fact: X cannot be negative")
    result = rpn.type.Integer(fact_helper(x.value))
    rpn.globl.param_stack.push(result)


@defword(name='fc?', args=1, print_x=rpn.globl.PX_PREDICATE, doc="""\
Test if flag is clear  ( -- bool )""")
def w_fc_query():
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("fc?: Type error ({})".format(typename(x)))

    flag = x.value
    if flag < 0 or flag >= rpn.flag.MAX:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("fc?: Flag {} out of range (0..{} expected)".format(flag, rpn.flag.MAX - 1))
    result = rpn.type.Integer(rpn.globl.bool_to_int(not rpn.flag.flag_set_p(flag)))
    rpn.globl.param_stack.push(result)


@defword(name='fc?c', args=1, print_x=rpn.globl.PX_PREDICATE, doc="""\
Test if flag is clear, then clear  ( -- bool )""")
def w_fc_query_clear():
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("fc?c: Type error ({})".format(typename(x)))

    flag = x.value
    if flag < 0 or flag >= rpn.flag.MAX:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("fc?c: Flag {} out of range (0..{} expected)".format(flag, rpn.flag.MAX - 1))
    result = rpn.type.Integer(rpn.globl.bool_to_int(not rpn.flag.flag_set_p(flag)))
    rpn.globl.param_stack.push(result)
    if flag < rpn.flag.FENCE:
        rpn.flag.clear_flag(flag)


@defword(name='fc?s', args=1, print_x=rpn.globl.PX_PREDICATE, doc="""\
Test if flag is clear, then set  ( -- bool )""")
def w_fc_query_set():
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("fc?s: Type error ({})".format(typename(x)))

    flag = x.value
    if flag < 0 or flag >= rpn.flag.MAX:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("fc?s: Flag {} out of range (0..{} expected)".format(flag, rpn.flag.MAX - 1))
    result = rpn.type.Integer(rpn.globl.bool_to_int(not rpn.flag.flag_set_p(flag)))
    rpn.globl.param_stack.push(result)
    if flag < rpn.flag.FENCE:
        rpn.flag.set_flag(flag)


@defword(name='fib', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
N'th Fibonacci number  ( n -- fib )

DEFINITION:
fib(0) = 0
fib(1) = 1
fib(n) = fib(n-1) + fib(n-2)

n cannot be negative.""")
def w_fib():
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("fib: Type error ({})".format(typename(x)))
    if x.value < 0:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("fib: X cannot be negative")
    result = rpn.type.Integer(fib_helper(x.value))
    rpn.globl.param_stack.push(result)


@defword(name='fix', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
Set fixed display  ( n -- )

N specifies the number of digits after the decimal point.""")
def w_fix():
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("fix: Type error ({})".format(typename(x)))

    if x.value < 0 or x.value >= rpn.globl.PRECISION_MAX:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("fix: Precision '{}' out of range (0..{} expected)".format(x.value, rpn.globl.PRECISION_MAX - 1))

    rpn.globl.disp_stack.top().style = "fix"
    rpn.globl.disp_stack.top().prec = x.value
    rpn.flag.set_flag(rpn.flag.F_DISP_FIX)
    rpn.flag.clear_flag(rpn.flag.F_DISP_ENG)


@defword(name='floor', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Floor  ( x -- floor )   Largest integer not greater than X""")
def w_floor():
    x = rpn.globl.param_stack.pop()
    if type(x) is rpn.type.Integer:
        result = x
    elif type(x) in [rpn.type.Float, rpn.type.Rational]:
        result = rpn.type.Integer(math.floor(x.value))
    else:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("floor: Type error ({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='fmod', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
Floating point remainder  ( y x -- rem )

Return the remainder of dividing y by x.  Preferred for floats;
'mod' is preferred for integers.""")
def w_fmod():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if    type(x) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float] \
       or type(y) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("fmod: Type error ({}, {})".format(typename(y), typename(x)))
    if x.zerop():
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("fmod: X cannot be zero")
    r = math.fmod(float(y.value), float(x.value))
    rpn.globl.param_stack.push(rpn.type.Float(r))


@defimmed(name='hide', hidden=True, doc="""\
Make the current word hidden.""")
def immed_hide(arg):
    dbg("hide", 1, "hide: arg={}".format(repr(arg)))
    arg.hidden = True
    pass


@defword(name='forget', print_x=rpn.globl.PX_CONFIG, doc="""\
Forget the definition of the following word.""")
def w_forget():
    pass                        # Grammar rules handle this word


# HP-41 calls this FRC, HP-42 calls this FP.  I like FRAC (which appeared
# on the HP-34C) because it is very clear but still short enough.
@defword(name='frac', print_x=rpn.globl.PX_COMPUTE, args=1, doc="""\
Fractional part ( x.q -- 0.q )""")
def w_frac():
    x = rpn.globl.param_stack.pop()
    if type(x) is rpn.type.Integer:
        rpn.globl.param_stack.push(rpn.type.Integer(0))
    elif type(x) in [rpn.type.Rational, rpn.type.Float]:
        result = rpn.type.Float(x.value - int(x.value))
        rpn.globl.param_stack.push(result)
    else:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("frac: Type error ({})".format(typename(x)))


@defword(name='fs?', print_x=rpn.globl.PX_PREDICATE, args=1, doc="""\
Test if flag is set  ( -- bool )""")
def w_fs_query():
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("fs?: Type error ({})".format(typename(x)))

    flag = x.value
    if flag < 0 or flag >= rpn.flag.MAX:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("fs?: Flag {} out of range (0..{} expected)".format(flag, rpn.flag.MAX - 1))
    result = rpn.type.Integer(rpn.globl.bool_to_int(rpn.flag.flag_set_p(flag)))
    rpn.globl.param_stack.push(result)


@defword(name='fs?c', print_x=rpn.globl.PX_PREDICATE, args=1, doc="""\
Test if flag is set, then clear  ( -- bool )""")
def w_fs_query_clear():
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("fs?c: Type error ({})".format(typename(x)))

    flag = x.value
    if flag < 0 or flag >= rpn.flag.MAX:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("fs?c: Flag {} out of range (0..{} expected)".format(flag, rpn.flag.MAX - 1))
    result = rpn.type.Integer(rpn.globl.bool_to_int(rpn.flag.flag_set_p(flag)))
    rpn.globl.param_stack.push(result)
    if flag < rpn.flag.FENCE:
        rpn.flag.clear_flag(flag)


@defword(name='fs?s', print_x=rpn.globl.PX_PREDICATE, args=1, doc="""\
Test if flag is set, then set  ( -- bool )""")
def w_fs_query_set():
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("fs?s: Type error ({})".format(typename(x)))

    flag = x.value
    if flag < 0 or flag >= rpn.flag.MAX:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("fs?s: Flag {} out of range (0..{} expected)".format(flag, rpn.flag.MAX - 1))
    result = rpn.type.Integer(rpn.globl.bool_to_int(rpn.flag.flag_set_p(flag)))
    rpn.globl.param_stack.push(result)
    if flag < rpn.flag.FENCE:
        rpn.flag.set_flag(flag)


@defword(name='fsolve', args=1, str_args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Root solving  ( init.guess -- root )
Name of function must be on string stack.

Implemented via scipy.optimize.fsolve()""")
def w_fsolve():
    x = rpn.globl.param_stack.pop()
    if    type(x) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("fsolve: Type error ({})".format(typename(x)))
    #init_guess = float(x.value)
    func_to_solve = rpn.globl.string_stack.pop().value
    # XXX - look up func_to_solve, error if not defined

    # XXX There are probably error conditions/exceptions I need to catch
    def func(x):
        rpn.globl.param_stack.push(rpn.type.Float(x))
        rpn.globl.eval_string(func_to_solve)
        return rpn.globl.param_stack.pop().value

    r = scipy.optimize.fsolve(func, 3)
    # The return value of fsolve is a numpy array of length n for a root
    # finding problem with n variables.
    result = rpn.type.Float(r[0])
    result.label = "fsolve"
    rpn.globl.param_stack.push(result)


@defword(name='FV', print_x=rpn.globl.PX_COMPUTE, doc="""\
Calculate Future Value (FV)

DEFINITION:
     PMT * k         N    (      PMT * k )
FV = ------- - (1+ip)  * (  PV + -------  )
       ip                 (        ip    )

k = 1 if END, 1+ip if BEGIN""")
def w_FV():
    if any_undefined_p([rpn.tvm.N, rpn.tvm.INT, rpn.tvm.PV, rpn.tvm.PMT]):
        raise rpn.exception.RuntimeErr("FV: Need N, INT, PV, and PMT")

    pv  = rpn.tvm.PV .obj.value
    A   = rpn.tvm.A_helper()
    C   = rpn.tvm.C_helper()

    # FV = -[PV + A(PV + C)]
    fv = -1.0 * (pv + A*(pv + C))
    dbg("tvm", 1, "fv={}".format(fv))

    result = rpn.type.Float(fv)
    result.label = "FV"
    rpn.tvm.FV.obj = result
    rpn.globl.param_stack.push(result)


@defword(name='GAMMA', print_x=rpn.globl.PX_COMPUTE, doc="""\
Constant: Euler-Mascheroni number ( -- 0.5772... )

DEFINITION:
GAMMA = lim(n->inf, (-ln n + SUM(k=1,n, 1/k)))

Do not confuse this with the "gamma" function.""")
def w_GAMMA():
    result = rpn.type.Float(rpn.globl.GAMMA)
    result.label = "GAMMA"
    rpn.globl.param_stack.push(result)


@defword(name='gamma', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Gamma function  ( x -- gamma[x] )

Do not confuse this with the constant "GAMMA".""")
def w_gamma():
    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        try:
            r = math.gamma(float(x.value))
        except ValueError:
            rpn.globl.param_stack.push(x)
            raise rpn.exception.ValueErr("gamma: X cannot be a non-positive integer")
        if type(x) is rpn.type.Integer:
            result = rpn.type.Integer(r)
        else:
            result = rpn.type.Float(r)
    elif type(x) is rpn.type.Complex:
        if not rpn.globl.have_module('scipy'):
            rpn.globl.param_stack.push(x)
            raise rpn.exception.RuntimeErr("gamma: Complex support requires 'scipy' library")
        r = scipy.special.gamma(x.value)
        if math.isnan(r.real) or math.isnan(r.imag):
            rpn.globl.param_stack.push(x)
            raise rpn.exception.ValueErr("gamma: X cannot be a non-positive integer")
        result = rpn.type.Complex.from_complex(r)
    else:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("gamma: Type error({})".format(typename(x)))
    result.label = "gamma"
    rpn.globl.param_stack.push(result)


@defword(name='gcd', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
Greatest common divisor ( y x -- gcd )

: gcd  begin ?dup while tuck mod repeat ;""")
def w_gcd():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if    type(x) is not rpn.type.Integer \
       or type(y) is not rpn.type.Integer:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("gcd: Type error ({}, {})".format(typename(y), typename(x)))

    xval = x.value
    yval = y.value
    if xval < 0 or yval < 0:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("gcd: X and Y cannot be negative")
    if xval == 0 or yval == 0:
        rpn.globl.param_stack.push(rpn.type.Integer(0))
    else:
        r = gcd_helper(xval, yval)
        rpn.globl.param_stack.push(rpn.type.Integer(r))


if sys.version_info >= (3, 8):
    @defword(name='gmean', print_x=rpn.globl.PX_COMPUTE, doc="""\
    Print the geometric mean of the statistics data""")
    def gmean():
        if len(rpn.globl.stat_data) == 0:
            raise rpn.exception.RuntimeErr("gmean: No statistics data")
        try:
            m = statistics.geometric_mean(rpn.globl.stat_data)
        except statistics.StatisticsError as e:
            raise rpn.exception.RuntimeErr("gmean: {}".format(str(e)))
        result = rpn.type.Float(m)
        result.label = "gmean"
        rpn.globl.param_stack.push(result)


@defword(name='grad', print_x=rpn.globl.PX_CONFIG, doc="""\
Set angular mode to gradians""")
def w_grad():
    rpn.flag.clear_flag(rpn.flag.F_RAD)
    rpn.flag.set_flag(rpn.flag.F_GRAD)


@defword(name='help', print_x=rpn.globl.PX_IO, doc="""\
Show documentation for the following word.""")
def w_help():
    pass                        # Grammar rules handle this word


@defword(name='hmean', print_x=rpn.globl.PX_COMPUTE, doc="""\
Print the harmonic mean of the statistics data""")
def w_hmean():
    if len(rpn.globl.stat_data) == 0:
        raise rpn.exception.RuntimeErr("hmean: No statistics data")
    try:
        m = statistics.harmonic_mean(rpn.globl.stat_data)
    except statistics.StatisticsError as e:
        raise rpn.exception.RuntimeErr("hmean: {}".format(str(e)))
    result = rpn.type.Float(m)
    result.label = "hmean"
    rpn.globl.param_stack.push(result)


@defword(name='hms', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Convert decimal hours to hours/minutes/seconds  ( HH.nnn -- HH.MMSS )""")
def w_hms():
    x = rpn.globl.param_stack.pop()
    if type(x) is rpn.type.Integer:
        result = rpn.type.Float(x.value)
    elif type(x) in [rpn.type.Float, rpn.type.Rational]:
        negative = x.value < 0
        hr = abs(x.value)
        (minutes, seconds) = divmod(hr * 3600, 60)
        (hours, minutes) = divmod(minutes, 60)
        if negative:
            hours *= -1.0
        result = rpn.type.Float("%d.%02d%02d" % (hours, minutes, seconds))
    else:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("hms: Type error ({})".format(typename(x)))
    result.label = "HH.MMSS"
    rpn.globl.param_stack.push(result)


@defword(name='hms+', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
Add hours/minutes/seconds  ( HH.MMSS HH.MMSS -- HH.MMSS )""")
def w_hms_plus():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if    type(x) not in [rpn.type.Integer, rpn.type.Float] \
       or type(y) not in [rpn.type.Integer, rpn.type.Float]:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("hms+: Type error ({}, {})".format(typename(y), typename(x)))

    #ynegative = y.value < 0
    if type(y) is rpn.type.Integer:
        (yvalid, yhh, ymm, yss, _) = rpn.type.Float(y.value).time_info()
    else:
        (yvalid, yhh, ymm, yss, _) = y.time_info()
    if not yvalid:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("hms+: Time {} is not valid".format(y.value))

    #xnegative = y.value < 0
    if type(x) is rpn.type.Integer:
        (xvalid, xhh, xmm, xss, _) = rpn.type.Float(x.value).time_info()
    else:
        (xvalid, xhh, xmm, xss, _) = x.time_info()
    if not xvalid:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("hms+: Time {} is not valid".format(x.value))

    (hh, mm, ss) = rpn.globl.normalize_hms(yhh + xhh, ymm + xmm, yss + xss)
    #print("hh=",hh,"mm=",mm,"ss=",ss)
    result = rpn.type.Float("%d.%02d%02d" % (hh, mm, ss))
    result.label = "HH.MMSS"
    rpn.globl.param_stack.push(result)


@defword(name='hms-', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
Subtract hours/minutes/seconds  ( HH.MMSS HH.MMSS -- HH.MMSS )""")
def w_hms_minus():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if    type(x) not in [rpn.type.Integer, rpn.type.Float] \
       or type(y) not in [rpn.type.Integer, rpn.type.Float]:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("hms-: Type error ({}, {})".format(typename(y), typename(x)))

    if type(y) is rpn.type.Integer:
        (yvalid, yhh, ymm, yss, _) = rpn.type.Float(y.value).time_info()
    else:
        (yvalid, yhh, ymm, yss, _) = y.time_info()
    if not yvalid:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("hms-: Time {} is not valid".format(y.value))

    if type(x) is rpn.type.Integer:
        (xvalid, xhh, xmm, xss, _) = rpn.type.Float(x.value).time_info()
    else:
        (xvalid, xhh, xmm, xss, _) = x.time_info()
    if not xvalid:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("hms-: Time {} is not valid".format(x.value))

    (hh, mm, ss) = rpn.globl.normalize_hms(yhh - xhh, ymm - xmm, yss - xss)
    #print("hh=",hh,"mm=",mm,"ss=",ss)
    result = rpn.type.Float("%d.%02d%02d" % (hh, mm, ss))
    result.label = "HH.MMSS"
    rpn.globl.param_stack.push(result)


@defword(name='hp->d', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Convert HP day number to date  ( day# -- MM.DDYYYY )

Day # 0 = October 15, 1582""")
def w_hp_to_d():
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("hp->d: Type error ({})".format(typename(x)))

    daynum = x.value
    if daynum < 0 or daynum > datetime.date.max.toordinal():
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("hp->d: X out of range")

    # dateobj = datetime.date.fromordinal(x.value - JULIAN_OFFSET)
    # result = rpn.type.Float("%d.%02d%04d" % (dateobj.month, dateobj.day, dateobj.year))
    d0 = daynum + 578164
    y0 = int((d0 - 121.5) / 365.2425)
    # m0 = int((d0 - sum3(y0)) / 30.6001)
    # while m0 < 4:
    #     y0 -= 1
    #     m0 = int((d0 -
    #
    # result.label = "MM.DDYYYY"
    # rpn.globl.param_stack.push(result)


@defword(name='hr', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Convert hours/minutes/seconds to decimal hours  ( HH.MMSS -- HH.nnn )""")
def w_hr():
    x = rpn.globl.param_stack.pop()
    if type(x) is rpn.type.Integer:
        result = rpn.type.Float(x.value)
    elif type(x) in [rpn.type.Float, rpn.type.Rational]:
        negative = -1.0 if x.value < 0 else 1.0
        hms = rpn.type.Float(abs(float(x.value) if type(x) is rpn.type.Rational else x.value))
        (valid, hh, mm, ss, _) = hms.time_info()
        if not valid:
            rpn.globl.param_stack.push(x)
            raise rpn.exception.ValueErr("hr: Time {} is not valid".format(x.value))

        hr = float(hh) + float(mm)/60.0 + float(ss)/3600.0
        result = rpn.type.Float(negative * hr)
    else:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("hr: Type error ({})".format(typename(x)))
    result.label = "HH.nnn"
    rpn.globl.param_stack.push(result)


@defword(name='hypot', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
hypot  ( y x -- hypot )  Hypotenuse distance

Square root of the sum of squares.

DEFINITION:
hypot = sqrt(x^2 + y^2)""")
def w_hypot():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if    type(x) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float] \
       or type(y) in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("hypot: Type error ({}, {})".format(typename(y), typename(x)))

    yval = float(y.value)
    xval = float(x.value)
    rpn.globl.param_stack.push(rpn.type.Float(math.hypot(xval, yval)))


@defword(name='I', print_x=rpn.globl.PX_CONFIG, doc="""\
Index of DO current loop  ( -- x )

Return the index of the most recent DO loop.

Do not confuse this with the "i" command,
which returns the complex number (0,1).""")
def w_I():
    (_I, _) = rpn.globl.lookup_variable('_I')
    if _I is None:
        raise rpn.exception.RuntimeErr("'I' not valid here, only in DO loops")
    if type(_I.obj) is not rpn.type.Integer:
        raise rpn.exception.FatalErr("I is not an rpn.type.Integer")
    rpn.globl.param_stack.push(_I.obj)


if rpn.globl.have_module('numpy'):
    @defword(name='idn', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Create an NxN identity matrix  ( n -- mat )""")
    def idn():
        x = rpn.globl.param_stack.pop()
        size = 0
        if type(x) is rpn.type.Integer:
            size = x.value
            if size < 1 or size > rpn.globl.MATRIX_MAX:
                rpn.globl.param_stack.push(x)
                raise rpn.exception.ValueErr("idn: X out of range (1..{} expected)".format(rpn.globl.MATRIX_MAX))
        elif type(x) is rpn.type.Vector:
            vsize = x.size()
            if vsize != 2:
                rpn.globl.param_stack.push(x)
                raise rpn.exception.ValueErr("idn: Only matrices can be created")
            if int(x.value[0]) != int(x.value[1]):
                rpn.globl.param_stack.push(x)
                raise rpn.exception.ValueErr("idn: Only square matrices can be created")
            size = x.value[0]
        else:
            rpn.globl.param_stack.push(x)
            raise rpn.exception.TypeErr("idn: Type error ({})".format(typename(x)))


        result = rpn.type.Matrix.from_numpy(np.identity(size, dtype=np.int64))
        rpn.globl.param_stack.push(result)


@defword(name='if', args=1, print_x=rpn.globl.PX_CONTROL, doc="""\
Test condition  ( flag -- )
Execute a conditional test.
<flag> IF ... [ ELSE ... ] THEN

qv ELSE, THEN""")
def w_ctl_if():
    pass                        # Grammar rules handle this word


@defword(name='INT', print_x=rpn.globl.PX_COMPUTE, doc="""\
Calculate INTerest rate (INT)

Do not confuse this with the "int" command, which truncates values to integers.""")
def w_INT():
    if any_undefined_p([rpn.tvm.N, rpn.tvm.PV, rpn.tvm.PMT, rpn.tvm.FV]):
        raise rpn.exception.RuntimeErr("INT: Need N, PV, PMT, and FV")

    n   = rpn.tvm.N  .obj.value
    pv  = rpn.tvm.PV .obj.value
    pmt = rpn.tvm.PMT.obj.value
    fv  = rpn.tvm.FV .obj.value

    # For PMT == 0:
    #   i = (FV/PV)^(1/n) - 1
    # For PMT != 0, i must be solved by iteration
    if pmt == 0:
        # XXX Trap math exceptions
        i_eff = math.expm1(math.log(-1.0*(fv/pv)) / n)
    else:
        i_eff = rpn.tvm.solve_for_interest()

    i = rpn.tvm.int_eff_to_nom(i_eff)
    dbg("tvm", 1, "i={}".format(i))
    result = rpn.type.Float(100.0 * i)
    result.label = "INT"
    rpn.tvm.INT.obj = result
    rpn.globl.param_stack.push(result)


@defword(name='int', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
int  ( x -- int )   Truncate to integer

The result is whatever Python's int() function returns.  Do not confuse this
with the "INT" command, which solves for financial interest rates.
Consider using floor or ceil instead.""")
def w_int():
    x = rpn.globl.param_stack.pop()
    if type(x) is rpn.type.Integer:
        result = x
    elif type(x) in [rpn.type.Float, rpn.type.Rational]:
        result = rpn.type.Integer(int(x.value))
    else:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("int: Type error ({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='J', print_x=rpn.globl.PX_CONFIG, doc="""\
Index of DO outer DO loop  ( -- x )

Return the index of the DO loop enclosing the current one""")
def w_J():
    (_J, _) = rpn.globl.lookup_variable('_I', 2)
    if _J is None:
        raise rpn.exception.RuntimeErr("'J' not valid here, only in nested DO loops")
    if type(_J.obj) is not rpn.type.Integer:
        raise rpn.exception.FatalErr("J is not an rpn.type.Integer")
    rpn.globl.param_stack.push(_J.obj)


@defword(name='jd->$', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
Convert julian day number to ISO date string  ( julian -- ) [ -- "YYYY-MM-DD" ]

EXAMPLE:
2369915 jd->$  ==>  "1776-07-04" """)
def w_jd_to_dollar():
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("jd->$: Type error ({})".format(typename(x)))

    if x.value < 1 or x.value > datetime.date.max.toordinal():
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("jd->$: X out of range (1..{} expected)".format(datetime.date.max.toordinal()))

    dateobj = datetime.date.fromordinal(x.value - rpn.globl.JULIAN_OFFSET)
    result = rpn.type.String("%d-%02d-%02d" % (dateobj.year, dateobj.month, dateobj.day))
    rpn.globl.string_stack.push(result)


@defword(name='jd->d', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Convert julian day number to date  ( julian -- MM.DDYYYY )

EXAMPLE:
2369915 jd->d  ==>  7.041776""")
def w_jd_to_d():
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("jd->d: Type error ({})".format(typename(x)))

    if x.value < 1 or x.value > datetime.date.max.toordinal():
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("jd->d: X out of range (1..{} expected)".format(datetime.date.max.toordinal()))

    dateobj = datetime.date.fromordinal(x.value - rpn.globl.JULIAN_OFFSET)
    result = rpn.type.Float("%d.%02d%04d" % (dateobj.month, dateobj.day, dateobj.year))
    result.label = "MM.DDYYYY"
    rpn.globl.param_stack.push(result)


if rpn.globl.have_module('scipy'):
    @defword(name='Jv', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
Jv  ( order x -- J_v(x) )

Bessel function of the first kind of real order and complex argument.
Implemented via scipy.special.jv(order, x)""")
    def Jv():
        x = rpn.globl.param_stack.pop()
        y = rpn.globl.param_stack.pop()
        if    type(x) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float, rpn.type.Complex] \
           or type(y) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            raise rpn.exception.TypeErr("Jv: Type error ({}, {})".format(typename(y), typename(x)))
        order = float(y.value)
        xval = x.value
        r = scipy.special.jv(order, xval)
        if type(r) is np.float64 and math.isnan(r):
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            raise rpn.exception.TypeErr("Jv: Not a number")

        if type(x) is rpn.type.Complex:
            result = rpn.type.Complex.from_complex(r)
        else:
            result = rpn.type.Float(r)
        rpn.globl.param_stack.push(result)


@defword(name='inv', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Inverse  ( x -- 1/x )
X cannot be zero.""")
def w_inv():
    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational, rpn.type.Complex] \
       and x.zerop():
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("inv: X cannot be zero")

    if type(x) is rpn.type.Integer:
        result = rpn.type.Float(1.0 / float(x.value))
    elif type(x) is rpn.type.Rational:
        result = rpn.type.Rational(x.denominator(), x.numerator())
    elif type(x) is rpn.type.Float:
        result = rpn.type.Float(1.0 / x.value)
    elif type(x) is rpn.type.Complex:
        r = complex(1, 0) / x.value
        result = rpn.type.Complex.from_complex(r)
    elif type(x) is rpn.type.Vector:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("inv: Vectors are not invertible")
    elif type(x) is rpn.type.Matrix:
        try:
            r = np.linalg.inv(x.value)
        except np.linalg.LinAlgError:
            rpn.globl.param_stack.push(x)
            raise rpn.exception.ValueErr("inv: Singular matrix has no inverse")
        result = rpn.type.Matrix.from_numpy(r)
    else:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("inv: Type error ({})".format(typename(x)))

    rpn.globl.param_stack.push(result)


@defword(name='key', print_x=rpn.globl.PX_IO, doc="""\
ASCII code of single keystroke  ( -- key )
key will block until input is provided.  Keystroke is not echoed.

qv ?key""")
def w_key():
    k = _Getch()()
    val = ord(k) if k != "" else 0
    #rpn.globl.lnwriteln("You pressed <{}>, value={}".format(k, val))
    rpn.globl.param_stack.push(rpn.type.Integer(val))


@defword(name='label', args=1, str_args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
Set label of X  ( x -- x )  [ "label" -- ]""")
def w_label():
    x = rpn.globl.param_stack.top()
    label = rpn.globl.string_stack.pop().value
    x.label = label


@defword(name='lcm', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
Least common multiple ( y x -- lcm )

DEFINITION:
              x * y
lcm(x, y) = ---------
            gcd(x, y)""")
def w_lcm():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if    type(x) is not rpn.type.Integer \
       or type(y) is not rpn.type.Integer:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("lcm: Type error ({}, {})".format(typename(y), typename(x)))

    xval = x.value
    yval = y.value
    if xval < 0 or yval < 0:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("lcm: X and Y cannot be negative")
    if xval == 0 or yval == 0:
        rpn.globl.param_stack.push(rpn.type.Integer(0))
    else:
        r = (xval * yval) / gcd_helper(xval, yval)
        rpn.globl.param_stack.push(rpn.type.Integer(r))


@defword(name='leave', print_x=rpn.globl.PX_CONTROL, doc="""\
Exit a DO or BEGIN loop immediately.""")
def w_leave():
    raise rpn.exception.Leave


@defword(name='lg', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Logarithm [base 2]  ( x -- lg )
X cannot be zero.
Use "ln" for the natural logarithm, and "log" for the common logarithm.""")
def w_lg():
    x = rpn.globl.param_stack.pop()
    if     type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational, rpn.type.Complex] \
       and x.zerop():
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("lg: X cannot be zero")

    if    type(x) is rpn.type.Integer  and x.value > 0 \
       or type(x) is rpn.type.Float    and x.value > 0.0 \
       or type(x) is rpn.type.Rational and x.value > 0:
        r = math.log2(float(x.value))
        if type(x) is rpn.type.Integer and r.is_integer():
            result = rpn.type.Integer(r)
        else:
            result = rpn.type.Float(r)
    elif    type(x) is rpn.type.Complex \
         or type(x) is rpn.type.Integer  and x.value < 0 \
         or type(x) is rpn.type.Float    and x.value < 0.0 \
         or type(x) is rpn.type.Rational and x.value < 0:
        result = rpn.type.Complex.from_complex(cmath.log(complex(x.value), 2))
    else:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("lg: Type error ({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='ln', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Natural logarithm [base e]  ( x -- ln )
X cannot be zero.
Use "log" for the common (base 10) logarithm.""")
def w_ln():
    x = rpn.globl.param_stack.pop()
    if     type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational, rpn.type.Complex] \
       and x.zerop():
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("ln: X cannot be zero")

    if    type(x) is rpn.type.Integer  and x.value > 0 \
       or type(x) is rpn.type.Float    and x.value > 0.0 \
       or type(x) is rpn.type.Rational and x.value > 0:
        result = rpn.type.Float(math.log(float(x.value)))
    elif    type(x) is rpn.type.Complex \
         or type(x) is rpn.type.Integer  and x.value < 0 \
         or type(x) is rpn.type.Float    and x.value < 0.0 \
         or type(x) is rpn.type.Rational and x.value < 0:
        result = rpn.type.Complex.from_complex(cmath.log(complex(x.value)))
    else:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("ln: Type error ({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='lnp1', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Calculate ln(1+X) accurately  ( x -- ln(1+x) )""")
def w_ln_1_plus_x():
    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        if float(x.value) == -1.0:
            rpn.globl.param_stack.push(x)
            raise rpn.exception.ValueErr("lnp1: X cannot be -1")
        result = rpn.type.Float(math.log1p(x.value))
    elif type(x) is rpn.type.Complex:
        if x.value == complex(-1, 0):
            rpn.globl.param_stack.push(x)
            raise rpn.exception.ValueErr("lnp1: X cannot be (-1,0)")
        result = rpn.type.Complex.from_complex(cmath.log(x.value + complex(1,0)))
    else:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("lnp1: Type error ({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='load', str_args=1, print_x=rpn.globl.PX_CONTROL, doc="""\
Load file specified on string stack  [ file -- ]""")
def w_load():
    filename = rpn.globl.string_stack.pop().value
    if not os.path.isfile(filename):
        rpn.globl.lnwriteln("load: Invalid file '{}'".format(filename))
    else:
        rpn.app.load_file(filename)


@defword(name='log', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Common logarithm [base 10]  ( x -- log )
X cannot be zero.
Use "ln" for the natural (base e) logarithm.""")
def w_log():
    x = rpn.globl.param_stack.pop()
    if     type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational, rpn.type.Complex] \
       and x.zerop():
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("log: X cannot be zero")

    if    type(x) is rpn.type.Integer  and x.value > 0 \
       or type(x) is rpn.type.Float    and x.value > 0.0 \
       or type(x) is rpn.type.Rational and x.value > 0:
        r = math.log10(float(x.value))
        if type(x) is rpn.type.Integer and r.is_integer():
            result = rpn.type.Integer(r)
        else:
            result = rpn.type.Float(r)
    elif    type(x) is rpn.type.Complex \
         or type(x) is rpn.type.Integer  and x.value < 0 \
         or type(x) is rpn.type.Float    and x.value < 0.0 \
         or type(x) is rpn.type.Rational and x.value < 0:
        result = rpn.type.Complex.from_complex(cmath.log10(complex(x.value)))
    else:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("log: Type error ({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='loop', print_x=rpn.globl.PX_CONTROL, doc="""\
Execute a definite loop.
<limit> <initial> DO ... LOOP

The iteration counter is available via I.  LEAVE will exit the loop early.

Example: 10 0 do I . loop
prints 0 1 2 3 4 5 6 7 8 9

qv DO, I, LEAVE, +LOOP""")
def w_loop():
    pass                        # Grammar rules handle this word


@defword(name='max', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
Smaller of X or Y  ( y x -- max )""")
def w_max():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if     type(x) in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float] \
       and type(y) in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
        yval = float(y.value)
        xval = float(x.value)
        rpn.globl.param_stack.push(x if xval > yval else y)
    else:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("max: Type error ({}, {})".format(typename(y), typename(x)))


@defword(name='mean', print_x=rpn.globl.PX_COMPUTE, doc="""\
Print the arithmetic mean of the statistics data""")
def w_mean():
    if len(rpn.globl.stat_data) == 0:
        raise rpn.exception.RuntimeErr("mean: No statistics data")
    try:
        m = statistics.mean(rpn.globl.stat_data)
    except statistics.StatisticsError as e:
        raise rpn.exception.RuntimeErr("mean: {}".format(str(e)))
    result = rpn.type.Float(m)
    result.label = "mean"
    rpn.globl.param_stack.push(result)


@defword(name='median', print_x=rpn.globl.PX_COMPUTE, doc="""\
Print the median of the statistics data""")
def w_median():
    if len(rpn.globl.stat_data) == 0:
        raise rpn.exception.RuntimeErr("median: No statistics data")
    try:
        m = statistics.median(rpn.globl.stat_data)
    except statistics.StatisticsError as e:
        raise rpn.exception.RuntimeErr("median: {}".format(str(e)))
    result = rpn.type.Float(m)
    result.label = "median"
    rpn.globl.param_stack.push(result)


@defword(name='min', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
Smaller of X or Y  ( y x -- min )""")
def w_min():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if     type(x) in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float] \
       and type(y) in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
        yval = float(y.value)
        xval = float(x.value)
        rpn.globl.param_stack.push(x if xval < yval else y)
    else:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("min: Type error ({}, {})".format(typename(y), typename(x)))


@defword(name='N', print_x=rpn.globl.PX_COMPUTE, doc="""\
Calculate Number of payments (N)

DEFINITION:
    log((FV*i)/(PV*i))
N = ------------------
        log(1 + i)""")
def w_N():
    if any_undefined_p([rpn.tvm.INT, rpn.tvm.PV, rpn.tvm.PMT, rpn.tvm.FV]):
        raise rpn.exception.RuntimeErr("N: Need INT, PV, PMT, and FV")

    fv = rpn.tvm.FV.obj.value
    pv = rpn.tvm.PV.obj.value
    C  = rpn.tvm.C_helper()
    i  = rpn.tvm.i_helper()

    # n = ln[(C-FV)/(C+PV)] / ln(1+i)
    n = math.log((C - fv) / (C + pv)) / math.log1p(i)
    dbg("tvm", 1, "n={}".format(n))

    result = rpn.type.Float(n)
    result.label = "N"
    rpn.tvm.N.obj = result
    rpn.globl.param_stack.push(result)


@defword(name='not', args=1, print_x=rpn.globl.PX_PREDICATE, doc="""\
Logical not  ( flag -- !flag )

Invert a flag - return TRUE (1) if x is zero, otherwise FALSE (0).
NOT is intended for boolean manipulations and is only defined on truth
integers (0,1).  0= is meant to compare a number to zero, and works for
all number types.

NOTE: This is not a bitwise not - use BITNOT for that.""")
def w_lognot():
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("not: Type error ({})".format(typename(x)))
    if x.value not in [0, 1]:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("not: X must be TRUE (1) or FALSE (0), not {}".format(x.value))

    rpn.globl.param_stack.push(rpn.type.Integer(rpn.globl.bool_to_int(x.zerop())))


@defword(name='of', print_x=rpn.globl.PX_CONTROL, doc="""\
Execute a sequence of words based on stack value.  Once a match is
executed, no other clauses are considered.  OTHERWISE is optional.
<n> and OF labels must be integers.

<n> CASE
  <x> OF ... ENDOF
  <y> OF ... ENDOF
  <z> OF ... ENDOF
  [ OTHERWISE ... ]
ENDCASE

qv CASE, ENDCASE, ENDOF, OTHERWISE""")
def w_of():
    pass                        # Grammar rules handle this word


@defword(name='or', args=2, print_x=rpn.globl.PX_PREDICATE, doc="""\
Logical OR  ( flag flag -- flag )
NOTE: This is not a bitwise OR - use BITOR for that.""")
def w_logor():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer or type(y) is not rpn.type.Integer:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("or: Type error ({}, {})".format(typename(y), typename(y)))

    if x.value not in [0, 1]:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("or: X must be TRUE (1) or FALSE (0), not {}".format(x.value))
    if y.value not in [0, 1]:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("or: Y must be TRUE (1) or FALSE (0), not {}".format(y.value))

    rpn.globl.param_stack.push(rpn.type.Integer(x.value or y.value))


@defword(name='otherwise', print_x=rpn.globl.PX_CONTROL, doc="""\
Execute a sequence of words based on stack value.  Once a match is
executed, no other clauses are considered.  OTHERWISE is optional.
<n> and OF labels must be integers.

<n> CASE
  <x> OF ... ENDOF
  <y> OF ... ENDOF
  <z> OF ... ENDOF
  [ OTHERWISE ... ]
ENDCASE

qv CASE, ENDCASE, ENDOF, OF""")
def w_otherwise():
    pass                        # Grammar rules handle this word


@defword(name='over', args=2, print_x=rpn.globl.PX_CONFIG, doc="""\
Duplicate second stack element  ( y x -- y x y )
Equivalent to 1 PICK""")
def w_over():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    rpn.globl.param_stack.push(y)
    rpn.globl.param_stack.push(x)
    rpn.globl.param_stack.push(y)


@defword(name='p->r', print_x=rpn.globl.PX_COMPUTE, doc="""\
Convert polar coordinates to rectangular.
The parameter(s) can be either two reals, or one complex.

Real:      ( theta r   -- y x   )
Complex:   ( (r,theta) -- (x,y) )

DEFINITION:
x = r * cos(theta)
y = r * sin(theta)""")
def w_p_to_r():
    if rpn.globl.param_stack.empty():
        raise rpn.exception.RuntimeErr("p->r: Insufficient parameters (1 or 2 required)")
    x = rpn.globl.param_stack.pop()
    if type(x) is rpn.type.Complex:
        r      = x.real()
        theta  = rpn.globl.convert_mode_to_radians(x.imag())
        result = rpn.type.Complex.from_complex(cmath.rect(r, theta))
        rpn.globl.param_stack.push(result)
    elif type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        if rpn.globl.param_stack.empty():
            rpn.globl.param_stack.push(x)
            raise rpn.exception.RuntimeErr("p->r: Insufficient parameters (2 required)")
        y = rpn.globl.param_stack.pop()
        if type(y) not in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            raise rpn.exception.TypeErr("p->r: Type error({}, {})".format(typename(y), typename(x)))

        r     = float(x.value)
        theta = rpn.globl.convert_mode_to_radians(float(y.value))
        xval  = r * math.cos(theta)
        yval  = r * math.sin(theta)
        rpn.globl.param_stack.push(rpn.type.Float(yval))
        rpn.globl.param_stack.push(rpn.type.Float(xval))
    else:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("p->r: Type error({})".format(typename(x)))


@defword(name='perm', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
Permutations  ( n r -- nPr )
Choose from N objects R at a time, with regard to ordering.

DEFINITION:
        n!
nPr = ------
      (n-r)!""")
def w_perm():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if type(y) is not rpn.type.Integer or type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("perm: Type error ({}, {})".format(typename(y), typename(x)))

    # Python 3.8 has math.perm()
    n = y.value
    r = x.value
    if r > n or r < 0:
        result = rpn.type.Integer(0)
    else:
        t = 1
        while r > 0:
            r -= 1
            t *= n
            n -= 1
        result = rpn.type.Integer(t)

    rpn.globl.param_stack.push(result)


@defword(name='PI', print_x=rpn.globl.PX_COMPUTE, doc="""\
Constant: Pi  ( -- 3.14159... )

DEFINITION:
PI == TAU/2

Consider using TAU instead of PI to simplify your equations.""")
def w_PI():
    result = rpn.type.Float(rpn.globl.PI)
    result.label = "PI"
    rpn.globl.param_stack.push(result)


@defword(name='pick', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
Pick an element from the stack  ( x -- )
0 PICK ==> DUP, 1 PICK ==> OVER""")
def w_pick():
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("pick: Type error ({})".format(typename(x)))

    if x.value < 0 or x.value >= rpn.globl.param_stack.size():
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("pick: Index out of range (0..{} expected)".format(rpn.globl.param_stack.size()-2))

    result = rpn.globl.param_stack.pick(x.value)
    rpn.globl.param_stack.push(result)


@defword(name='plot', args=2, str_args=1, print_x=rpn.globl.PX_IO, doc="""\
Simple ASCII function plot ( xlow xhigh -- ) [ FN -- ]
FN is the (string) name of a function which must implement ( x -- y ).
Y-axis is autoscaled.

EXAMPLE:
rad  80 !COLS  24 !ROWS
TAU chs TAU "sin" plot  =>

      1.000 :------------------------------------*---------------------:
            :     ****                   |     ** *                    :
            :    *    *                  |    *    *                   :
            :   *      *                 |          *                  :
            :                            |   *       *                 :
            :  *        *                |  *                          :
            : *                          |            *                :
            :            *               | *                           :
            :*                           |             *               :
            :             *              |*                            :
            *                            |              *              :
            :==============*=============+=============================*
            :                            *               *             :
            :               *            |                            *:
            :                           *|                *            :
            :                *           |                           * :
            :                          * |                 *        *  :
            :                 *       *  |                             :
            :                  *         |                  *      *   :
            :                   *    *   |                   *    *    :
     =1.000 :--------------------****-------------------------****-----:
             -6.283                                                   6.283""")
def w_plot():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if    type(x) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float] \
       or type(y) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("plot: Type error ({}, {})".format(typename(y), typename(x)))
    func_to_plot = rpn.globl.string_stack.pop().value
    # XXX - look up func_to_plot, error if not defined
    x_high = float(x.value)
    x_low  = float(y.value)

    # XXX There are probably error conditions/exceptions I need to catch
    def func(x):
        rpn.globl.param_stack.push(rpn.type.Float(x))
        rpn.globl.eval_string(func_to_plot)
        return rpn.globl.param_stack.pop().value

    plot_helper(func, x_low, x_high)


@defword(name='PMT', print_x=rpn.globl.PX_COMPUTE, doc="""\
Calculate PayMenT amount (PMT)

DEFINITION:
       (         PV + FV     )    -ip
PMT = (  PV + --------------  ) * ---
       (       (1+ip)^N - 1  )     k

k = 1 if END, 1+ip if BEGIN""")
def w_PMT():
    if any_undefined_p([rpn.tvm.N, rpn.tvm.INT, rpn.tvm.PV, rpn.tvm.FV]):
        raise rpn.exception.RuntimeErr("PMT: Need N, INT, PV, and FV")

    PV = rpn.tvm.PV.obj.value
    FV = rpn.tvm.FV.obj.value
    A  = rpn.tvm.A_helper()
    B  = rpn.tvm.B_helper()

    # PMT = -[FV + PV(A+1)] / (A*B)
    pmt = -1.0 * ((FV + PV*(A+1.0)) / (A * B))
    dbg("tvm", 1, "pmt={}".format(pmt))

    result = rpn.type.Float(pmt)
    result.label = "PMT"
    rpn.tvm.PMT.obj = result
    rpn.globl.param_stack.push(result)


@defword(name='popdisp', print_x=rpn.globl.PX_CONFIG, doc="""\
Pop current display configuration.""")
def w_popdisp():
    try:
        rpn.globl.disp_stack.pop()
    except rpn.exception.StackUnderflow:
        raise rpn.exception.RuntimeErr("popdisp: No display configuration")


@defword(name='pushdisp', print_x=rpn.globl.PX_CONFIG, doc="""\
Stash current display configuration.""")
def w_pushdisp():
    d = rpn.util.DisplayConfig()
    d.style = rpn.globl.disp_stack.top().style
    d.prec = rpn.globl.disp_stack.top().prec
    rpn.globl.disp_stack.push(d)


@defword(name='PV', print_x=rpn.globl.PX_COMPUTE, doc="""\
Calculate Present Value (PV)

DEFINITION:
      ( PMT * k      )       1         PMT * k
PV = (  ------- - FV  ) * --------  -  -------
      (   ip         )    (1+ip)^N       ip

k = 1 if END, 1+ip if BEGIN""")
def w_PV():
    if any_undefined_p([rpn.tvm.N, rpn.tvm.INT, rpn.tvm.PMT, rpn.tvm.FV]):
        raise rpn.exception.RuntimeErr("PV: Need N, INT, PMT, and FV")

    fv = rpn.tvm.FV.obj.value
    A  = rpn.tvm.A_helper()
    C  = rpn.tvm.C_helper()
    # PV = -[FV + (A*C)] / (A+1)
    pv = -1.0 * ((fv + (A * C)) / (A + 1.0))
    dbg("tvm", 1, "pv={}".format(pv))

    result = rpn.type.Float(pv)
    result.label = "PV"
    rpn.tvm.PV.obj = result
    rpn.globl.param_stack.push(result)


if rpn.globl.have_module('scipy'):
    @defword(name='quad', args=2, str_args=1, print_x=rpn.globl.PX_COMPUTE, doc=r"""\
Numerical integration  ( lower upper -- err.est integral )
Name of function must be on string stack.

Implemented via scipy.integrate.quad()

EXAMPLE: Integrate a bessel function jv(2.5, x) along the interval [0,4.5]:

: J2.5  2.5 swap Jv ;
0 4.5 "J2.5" quad .s  =>
1: 7.866317216380692e-09  \ error
0: 1.1178179380783249  \ quad""")
    def quad():
        x = rpn.globl.param_stack.pop()
        y = rpn.globl.param_stack.pop()
        if    type(x) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float] \
           or type(y) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            raise rpn.exception.TypeErr("quad: Type error ({}, {})".format(typename(y), typename(x)))
        lower = float(y.value)
        upper = float(x.value)
        func_to_integrate = rpn.globl.string_stack.pop().value
        # XXX - look up func_to_integrate, error if not defined

        # XXX There are probably error conditions/exceptions I need to catch
        def func(x):
            rpn.globl.param_stack.push(rpn.type.Float(x))
            rpn.globl.eval_string(func_to_integrate)
            return rpn.globl.param_stack.pop().value

        (res, err) = scipy.integrate.quad(func, lower, upper)
        err_obj = rpn.type.Float(err)
        err_obj.label = "error"
        rpn.globl.param_stack.push(err_obj)
        res_obj = rpn.type.Float(res)
        res_obj.label = "quad"
        rpn.globl.param_stack.push(res_obj)


@defword(name='r->d', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Convert radians to degrees ( rad -- deg )""")
def w_r_to_d():
    x = rpn.globl.param_stack.pop()
    if type(x) not in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("r->d: Type error ({})".format(typename(x)))
    result = rpn.type.Float(rpn.globl.convert_radians_to_mode(float(x.value), "d"))
    result.label = "Deg"
    rpn.globl.param_stack.push(result)


@defword(name='r->p', print_x=rpn.globl.PX_COMPUTE, doc="""\
Convert rectangular coordinates to polar.
The parameter(s) can be either two reals, or one complex.

Real:      ( y x   -- theta r   )
Complex:   ( (x,y) -- (r,theta) )

DEFINITION:
r     = hypot(x, y) == sqrt(x^2 + y^2)
theta = atan(y / x) == atan2(y, x)""")
def w_r_to_p():
    if rpn.globl.param_stack.empty():
        raise rpn.exception.RuntimeErr("r->p: Insufficient parameters (1 or 2 required)")
    x = rpn.globl.param_stack.pop()
    if type(x) is rpn.type.Complex:
        (r, theta) = cmath.polar(x.value)
        result = rpn.type.Complex(r, rpn.globl.convert_radians_to_mode(theta))
        rpn.globl.param_stack.push(result)
    elif type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        if rpn.globl.param_stack.empty():
            rpn.globl.param_stack.push(x)
            raise rpn.exception.RuntimeErr("r->p: Insufficient parameters (2 required)")
        y = rpn.globl.param_stack.pop()
        if type(y) not in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            raise rpn.exception.TypeErr("r->p: Type error({}, {})".format(typename(y), typename(x)))

        theta = math.atan2(y.value, x.value)
        theta_obj = rpn.type.Float(rpn.globl.convert_radians_to_mode(theta))
        theta_obj.label = "theta_" + rpn.globl.angle_mode_label()

        r = math.hypot(y.value, x.value)
        r_obj = rpn.type.Float(r)
        r_obj.label = "r"

        rpn.globl.param_stack.push(theta_obj)
        rpn.globl.param_stack.push(r_obj)
    else:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("r->p: Type error({})".format(typename(x)))


@defword(name='r.s', print_x=rpn.globl.PX_IO, doc="""\
Display return stack""")
def w_r_dot_s():
    for (i, item) in rpn.globl.return_stack.items_bottom_to_top():
        # Prefix with "r" to prevent confusion with .s
        rpn.globl.lnwriteln("r{}: {}".format(i, item))


@defword(name='r>', print_x=rpn.globl.PX_CONFIG, doc="""\
Pop return stack onto parameter stack  ( -- x )""")
def w_r_from():
    if rpn.globl.return_stack.empty():
        raise rpn.exception.RuntimeErr("r>: Empty return stack")
    rpn.globl.param_stack.push(rpn.globl.return_stack.pop())


@defword(name='r@', print_x=rpn.globl.PX_CONFIG, doc="""\
Copy top of return stack  ( -- x )""")
def w_r_fetch():
    if rpn.globl.return_stack.empty():
        raise rpn.exception.RuntimeErr("r@: Empty return stack")
    rpn.globl.param_stack.push(rpn.globl.return_stack.top())


@defword(name='rad', print_x=rpn.globl.PX_CONFIG, doc="""\
Set angular mode to radians""")
def w_rad():
    rpn.flag.set_flag(rpn.flag.F_RAD)
    rpn.flag.clear_flag(rpn.flag.F_GRAD)


@defword(name='rand', print_x=rpn.globl.PX_COMPUTE, doc="""\
Random number  ( -- r )
r is a float in range: 0 <= r < 1

qv RANDINT""")
def w_rand():
    rpn.globl.param_stack.push(rpn.type.Float(random.random()))


@defword(name='randint', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Random integer between 1 and n  ( n -- r )
r is an integer in range: 1 <= r <= n

EXAMPLE:
: threeD6  3 0 do 6 randint loop + + ;

qv RAND""")
def w_randint():
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("randint: Type error ({})".format(typename(x)))

    if x.value < 1:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("randint: n must be positive")

    r = random.randint(1, x.value)
    rpn.globl.param_stack.push(rpn.type.Integer(r))


@defword(name='rcl', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Recall value of register X  ( reg -- val )""")
def w_rcl():
    (reg_size, _) = rpn.globl.lookup_variable("SIZE")

    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("rcl: Type error ({})".format(typename(x)))
    reg = x.value
    if reg < 0 or reg >= reg_size.obj.value:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("rcl: Register '{}' out of range (0..{} expected)".format(reg, reg_size.obj.value - 1))
    rpn.globl.param_stack.push(rpn.globl.register[reg])


@defword(name='rclI', print_x=rpn.globl.PX_COMPUTE, doc="""\
Recall value of register I  ( -- val )""")
def w_rclI():
    rpn.globl.param_stack.push(rpn.globl.register['I'])


@defword(name='rct->sph', args=3, print_x=rpn.globl.PX_COMPUTE, doc="""\
Convert rectangular coordinates to spherical  ( z y x -- phi theta r )

DEFINITION:
phi   = atan(y/x)      == atan2(y, x)
theta = acos(z / r)
r     = hypot(x, y, z) == sqrt(x^2 + y^2 + z^2)""")
def w_rct_to_sph():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    z = rpn.globl.param_stack.pop()
    if    type(x) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float] \
       or type(y) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float] \
       or type(z) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
        rpn.globl.param_stack.push(z)
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("rct->sph: Type error ({}, {}, {})".format(typename(z), typename(y), typename(x)))
    if x.zerop() and y.zerop() and z.zerop():
        rpn.globl.param_stack.push(z)
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        return

    xval = float(x.value)
    yval = float(y.value)
    zval = float(z.value)

    r     = math.sqrt(xval**2 + yval**2 + zval**2)
    r_obj = rpn.type.Float(r)
    r_obj.label = "r"

    theta     = math.acos(zval / r)
    theta_obj = rpn.type.Float(rpn.globl.convert_radians_to_mode(theta))
    theta_obj.label = "theta_" + rpn.globl.angle_mode_label()

    phi     = math.atan2(yval, xval)
    phi_obj = rpn.type.Float(rpn.globl.convert_radians_to_mode(phi))
    phi_obj.label = "phi_" + rpn.globl.angle_mode_label()

    rpn.globl.param_stack.push(phi_obj)
    rpn.globl.param_stack.push(theta_obj)
    rpn.globl.param_stack.push(r_obj)


@defword(name='rdepth', print_x=rpn.globl.PX_COMPUTE, doc="""\
Current number of elements on return stack  ( -- n )""")
def w_rdepth():
    rpn.globl.param_stack.push(rpn.type.Integer(rpn.globl.return_stack.size()))


@defword(name='rdrop', print_x=rpn.globl.PX_CONFIG, doc="""\
Drop the top item from the return stack.""")
def w_rdrop():
    if rpn.globl.return_stack.empty():
        raise rpn.exception.RuntimeErr("rdrop: Empty return stack")
    rpn.globl.return_stack.pop()


@defword(name='recurse', print_x=rpn.globl.PX_CONTROL, doc="""\
Recurse into current word.  Only valid in a colon definition.""")
def w_recurse():
    pass                        # Grammar rules handle this word


@defword(name='repeat', print_x=rpn.globl.PX_CONTROL, doc="""\
Execute an indefinite loop while a condition is satisfied.
BEGIN ... <flag> WHILE ... REPEAT

LEAVE will exit the loop early.  Note that the effect of the test in
BEGIN...WHILE is opposite that in BEGIN...UNTIL.  The loop repeats
while something is true, rather than until it becomes true.

qv BEGIN, AGAIN, LEAVE, UNTIL, WHILE""")
def w_repeat():
    pass                        # Grammar rules handle this word


@defword(name='rms', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Root Mean Square  ( v -- rms )

DEFINITION:
            2    2    2          2
           x1 + x2 + x3 + ... + xn
rms = sqrt(-----------------------)
                      n""")
def w_rms():
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Vector:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("rms: Type error ({})".format(typename(x)))

    n = x.size()
    if n == 0:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("rms: X cannot be an empty vector")
    sumsq = 0.0
    for val in x.value:
        sumsq += val ** 2
    sumsq /= n
    rval = rpn.globl.to_python_class(sumsq)
    t = type(rval)
    if t is float:
        result = rpn.type.Float(math.sqrt(rval))
    elif t is complex:
        result = rpn.type.Complex.from_complex(cmath.sqrt(rval))
    else:
        raise rpn.exception.FatalErr("{}: Cannot handle type {}".format(whoami(), t))

    result.label = "rms"
    rpn.globl.param_stack.push(result)


@defword(name='rnd', args=2, print_x=rpn.globl.PX_CONFIG, doc="""\
Round N to PLACES number of decimal places  ( n places -- rounded )

NOTE: This is implemented using Python's round() function.  The behavior
of rnd can be surprising: for example, "2.675 2 rnd" gives 2.67 instead
of the expected 2.68.  This is not a bug: it's a result of the fact that
most decimal fractions can't be represented exactly as a float.""")
def w_rnd():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if    type(x) is not rpn.type.Integer \
       or type(y) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float, rpn.type.Complex]:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("rnd: Type error ({}, {})".format(typename(y), typename(x)))
    places = x.value
    if places < 0:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("rnd: Round places may not be negative")

    if type(y) in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
        r = round(float(y.value), places)
        result = rpn.type.Integer(r) if places == 0 else rpn.type.Float(r)
    else:
        new_real = round(float(y.real()), places)
        new_imag = round(float(y.imag()), places)
        result = rpn.type.Complex(new_real, new_imag)
    rpn.globl.param_stack.push(result)


@defword(name='roll', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
Roll stack elements  ( x -- )
1 ROLL ==> SWAP, 2 ROLL ==> ROT""")
def w_roll():
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("roll: Type error ({})".format(typename(x)))

    if x.value < 0 or x.value >= rpn.globl.param_stack.size():
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("roll: Index out of range (0..{} expected)".format(rpn.globl.param_stack.size()-2))

    rpn.globl.param_stack.roll(x.value)


@defword(name='rot', args=3, print_x=rpn.globl.PX_CONFIG, doc="""\
Rotate third stack element to the top, rolling others up  ( z y x -- y x z )
Equivalent to 2 ROLL""")
def w_rot():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    z = rpn.globl.param_stack.pop()
    rpn.globl.param_stack.push(y)
    rpn.globl.param_stack.push(x)
    rpn.globl.param_stack.push(z)


@defword(name='S+', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
Add an element to the statistics list""")
def w_s_plus():
    x = rpn.globl.param_stack.pop()
    if type(x) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("S+: Type error ({})".format(typename(x)))

    val = float(x.value)
    rpn.globl.stat_data.append(val)


@defword(name='sci', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
Set scientific display  ( n -- )

N specifies the number of digits after the decimal point.""")
def w_sci():
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("sci: Type error ({})".format(typename(x)))

    if x.value < 0 or x.value >= rpn.globl.PRECISION_MAX:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("fix: Precision '{}' out of range (0..{} expected)".format(x.value, rpn.globl.PRECISION_MAX - 1))

    rpn.globl.disp_stack.top().style = "sci"
    rpn.globl.disp_stack.top().prec = x.value
    rpn.flag.clear_flag(rpn.flag.F_DISP_FIX)
    rpn.flag.clear_flag(rpn.flag.F_DISP_ENG)


@defword(name='scopes', print_x=rpn.globl.PX_IO, doc="""\
Print information on all available scopes.""")
def w_scopes():
    for (i, item) in rpn.globl.scope_stack.items_bottom_to_top():
        rpn.globl.lnwriteln("{}: {}".format(i, item))


@defword(name='setdebug', args=1, str_args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
Set debug level  ( lev -- )  [ "facility" -- ]""")
def w_setdebug():
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("setdebug: Type error ({})".format(typename(x)))
    level = x.value
    if level < 0 or level > 9:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("setdebug: Level {} out of range (0..9 expected)".format(level))
    resource = rpn.globl.string_stack.pop()
    if not resource.value in rpn.debug.debug_levels:
        rpn.globl.param_stack.push(x)
        rpn.globl.string_stack.push(resource)
        raise rpn.exception.ValueErr("{}: Resource '{}' is not valid".format(whoami(), resource.value))
    rpn.debug.set_debug_level(resource.value, level)


@defword(name='sf', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
Set flag  ( f -- )""")
def w_sf():
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("sf: Type error ({})".format(typename(x)))
    flag = x.value
    if flag < 0 or flag >= rpn.flag.MAX:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("sf: Flag {} out of range (0..{} expected)".format(flag, rpn.flag.MAX - 1))
    if flag >= rpn.flag.FENCE:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("sf: Flag {} cannot be modified".format(flag))
    rpn.flag.set_flag(flag)


@defword(name='shdebug', print_x=rpn.globl.PX_IO, doc="""\
Show all debug levels""")
def w_showdebug():
    rpn.globl.lnwriteln("Debugging is {}".format("ENABLED" if rpn.flag.flag_set_p(rpn.flag.F_DEBUG_ENABLED) else "disabled"))

    dbgs = dict()
    for (resource, level) in rpn.debug.debug_levels.items():
        dbgs[resource] = "{}={}".format(resource, level)
    sorted_dbgs = []
    for key in sorted(dbgs, key=str.casefold):
        sorted_dbgs.append(dbgs[key])
    rpn.globl.list_in_columns(sorted_dbgs, rpn.globl.scr_cols.obj.value - 1)


@defword(name='shfin', print_x=rpn.globl.PX_IO, doc="""\
Show financial variables""")
def w_shfin():
    rpn.globl.lnwrite()
    rpn.globl.writeln("N:   {}".format(rpn.globl.fmt(rpn.tvm.N  .obj.value) if rpn.tvm.N  .defined() else "[Not set]"))
    rpn.globl.writeln("INT: {}".format(rpn.globl.fmt(rpn.tvm.INT.obj.value) if rpn.tvm.INT.defined() else "[Not set]"))
    rpn.globl.writeln("PV:  {}".format(rpn.globl.fmt(rpn.tvm.PV. obj.value) if rpn.tvm.PV .defined() else "[Not set]"))
    rpn.globl.writeln("PMT: {}".format(rpn.globl.fmt(rpn.tvm.PMT.obj.value) if rpn.tvm.PMT.defined() else "[Not set]"))
    rpn.globl.writeln("FV:  {}".format(rpn.globl.fmt(rpn.tvm.FV .obj.value) if rpn.tvm.FV .defined() else "[Not set]"))
    rpn.globl.writeln("--------------")
    rpn.globl.writeln("CF:  {}".format(rpn.globl.fmt(rpn.tvm.CF .obj.value) if rpn.tvm.CF .defined() else "[Not set]"))
    rpn.globl.writeln("PF:  {}".format(rpn.globl.fmt(rpn.tvm.PF .obj.value) if rpn.tvm.PF .defined() else "[Not set]"))

    rpn.globl.writeln("{} compounding (flag {} is {})".format("CONTINUOUS" if rpn.flag.flag_set_p(rpn.flag.F_TVM_CONTINUOUS) else "DISCRETE",
                                                              rpn.flag.F_TVM_CONTINUOUS,
                                                              "set" if rpn.flag.flag_set_p(rpn.flag.F_TVM_CONTINUOUS) else "clear"))
    rpn.globl.writeln("{} mode (flag {} is {})".format("BEGIN" if rpn.flag.flag_set_p(rpn.flag.F_TVM_BEGIN_MODE) else "END",
                                                       rpn.flag.F_TVM_BEGIN_MODE,
                                                       "set" if rpn.flag.flag_set_p(rpn.flag.F_TVM_BEGIN_MODE) else "clear"))
    if dbg("tvm"):
        i = rpn.tvm.i_helper()
        A = rpn.tvm.B_helper()
        B = rpn.tvm.B_helper()
        C = rpn.tvm.C_helper()
        X = rpn.tvm.X_helper()
        rpn.globl.writeln("----------")
        rpn.globl.writeln("i: {}".format(i if i is not None else "[undef]"))
        rpn.globl.writeln("A: {}".format(A if A is not None else "[undef]"))
        rpn.globl.writeln("B: {}".format(B if B is not None else "[undef]"))
        rpn.globl.writeln("C: {}".format(C if C is not None else "[undef]"))
        rpn.globl.writeln("X: {} ({} mode)".format(X if X is not None else "[undef]",
                                                   "BEGIN" if rpn.flag.flag_set_p(rpn.flag.F_TVM_BEGIN_MODE) else "END"))


@defword(name='shflag', print_x=rpn.globl.PX_IO, doc="""\
Show status of all flags ( -- )""")
def w_shflag():
    flags = []
    for f in range(rpn.flag.MAX):
        flags.append("%02d:%s" % (f, "YES" if rpn.flag.flag_set_p(f) else "no "))

    rpn.globl.list_in_columns(flags, rpn.globl.scr_cols.obj.value - 1)


@defword(name='show', print_x=rpn.globl.PX_IO, doc="""\
Show the definition of the following word.""")
def w_show():
    pass                        # Grammar rules handle this word


@defword(name='shstat', print_x=rpn.globl.PX_IO, doc="""\
Print the statistics list""")
def w_shstat():
    if len(rpn.globl.stat_data) == 0:
        rpn.globl.writeln("No statistics data")
    else:
        rpn.globl.writeln(rpn.globl.stat_data)


@defword(name='shreg', print_x=rpn.globl.PX_IO, doc="""\
Show status of all registers ( -- )""")
def w_shreg():
    (reg_size, _) = rpn.globl.lookup_variable("SIZE")
    regs = []
    regs.append("I=%s" % rpn.globl.fmt(rpn.globl.register['I']))
    for r in range(reg_size.obj.value):
        regs.append("R%02d=%s" % (r, rpn.globl.fmt(rpn.globl.register[r])))

    rpn.globl.list_in_columns(regs, rpn.globl.scr_cols.obj.value - 1)


@defword(name='sign', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Signum  ( n -- sign )
Returns -1, 0, or 1.""")
def w_sign():
    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        if x.value < 0:
            r = -1
        elif x.value > 0:
            r = +1
        else:
            r = 0
        result = rpn.type.Integer(r)
    else:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("sign: Type error ({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='sin', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Sine  ( angle -- sine )""")
def w_sin():
    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        result = rpn.type.Float(math.sin(rpn.globl.convert_mode_to_radians(float(x.value))))
    elif type(x) is rpn.type.Complex:
        result = rpn.type.Complex.from_complex(cmath.sin(x.value))
    else:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("sin: Type error ({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='sinc', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Sine cardinal (sampling function)  ( x -- sinc )

DEFINITION:
           sin x
sinc(x) = -------
             x

sinc(0) == 1""")
def w_sinc():
    x = rpn.globl.param_stack.pop()
    if type(x) not in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational, rpn.type.Complex]:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("sinc: Type error ({})".format(typename(x)))
    if type(x) is rpn.type.Complex:
        if x.zerop():
            r = complex(1.0, 0.0)
        else:
            r = cmath.sin(x.value) / x.value
        result = rpn.type.Complex.from_complex(r)
    else:
        if x.zerop():
            r = 1.0
        else:
            r = math.sin(rpn.globl.convert_mode_to_radians(float(x.value))) / x.value
        result = rpn.type.Float(r)

    result.label = "sinc"
    rpn.globl.param_stack.push(result)


@defword(name='sinh', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Hyperbolic sine  ( angle -- sine_h )

DEFINITION:
          e^x - e^(-x)
sinh(x) = ------------
               2""")
def w_sinh():
    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        result = rpn.type.Float(math.sinh(float(x.value)))
    elif type(x) is rpn.type.Complex:
        result = rpn.type.Complex.from_complex(cmath.sinh(x.value))
    else:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("sinh: Type error ({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='sleep', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
Sleep for N seconds  ( n -- )
N may be fractional.""")
def w_sleep():
    x = rpn.globl.param_stack.pop()
    if type(x) not in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("sleep: Type error ({})".format(typename(x)))
    sleep_time = float(x.value)
    time.sleep(sleep_time)


@defword(name='sph->rct', args=3, print_x=rpn.globl.PX_COMPUTE, doc="""\
Convert spherical coordinates to rectangular  ( phi theta r -- z y x )

DEFINITION:
x = r * sin(theta) * cos(phi)
y = r * sin(theta) * sin(phi)
z = r * cos(theta)""")
def w_sph_to_rct():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    z = rpn.globl.param_stack.pop()
    if    type(x) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float] \
       or type(y) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float] \
       or type(z) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
        rpn.globl.param_stack.push(z)
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("sph->rct: Type error ({}, {}, {})".format(typename(z), typename(y), typename(x)))
    if x.zerop() and y.zerop() and z.zerop():
        rpn.globl.param_stack.push(z)
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        return

    r     = float(x.value)
    theta = rpn.globl.convert_mode_to_radians(float(y.value))
    phi   = rpn.globl.convert_mode_to_radians(float(z.value))

    x_coord = r * math.sin(theta) * math.cos(phi)
    y_coord = r * math.sin(theta) * math.sin(phi)
    z_coord = r * math.cos(theta)

    rpn.globl.param_stack.push(rpn.type.Float(z_coord))
    rpn.globl.param_stack.push(rpn.type.Float(y_coord))
    rpn.globl.param_stack.push(rpn.type.Float(x_coord))


@defword(name='sq', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Square  ( x -- x^2 )""")
def w_sq():
    x = rpn.globl.param_stack.pop()
    if type(x) is rpn.type.Integer:
        result = rpn.type.Integer(x.value ** 2)
    elif type(x) is rpn.type.Rational:
        result = rpn.type.Rational(x.numerator() ** 2, x.denominator() ** 2)
    elif type(x) is rpn.type.Float:
        result = rpn.type.Float(x.value ** 2)
    elif type(x) is rpn.type.Complex:
        r = complex(x.value ** 2)
        result = rpn.type.Complex.from_complex(r)
    else:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("sq: Type error ({})".format(typename(x)))

    rpn.globl.param_stack.push(result)


@defword(name='sqrt', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Square root  ( x -- sqrt(x) )
Negative X returns a complex number""")
def w_sqrt():
    x = rpn.globl.param_stack.pop()
    if type(x) is rpn.type.Integer and x.zerop():
        result = rpn.type.Integer(0)
    elif type(x) in [rpn.type.Float, rpn.type.Rational] and x.zerop():
        result = rpn.type.Float(0.0)
    elif type(x) is rpn.type.Complex and x.zerop():
        result = rpn.type.Complex()
    elif    type(x) is rpn.type.Integer  and x.value > 0 \
         or type(x) is rpn.type.Float    and x.value > 0.0 \
         or type(x) is rpn.type.Rational and x.value > 0:
        r = math.sqrt(float(x.value))
        if type(x) is rpn.type.Integer and r.is_integer():
            result = rpn.type.Integer(r)
        else:
            result = rpn.type.Float(r)
    elif    type(x) is rpn.type.Complex \
         or type(x) is rpn.type.Integer  and x.value < 0 \
         or type(x) is rpn.type.Float    and x.value < 0.0 \
         or type(x) is rpn.type.Rational and x.value < 0:
        result = rpn.type.Complex.from_complex(cmath.sqrt(complex(x.value)))
    else:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("sqrt: Type error ({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='std', print_x=rpn.globl.rpn.globl.PX_CONFIG, doc="""\
std  ( -- )

Set display mode to standard.""")
def w_std():
    rpn.globl.disp_stack.top().style = "std"
    rpn.flag.set_flag(rpn.flag.F_DISP_FIX)
    rpn.flag.set_flag(rpn.flag.F_DISP_ENG)
    for bit in range(4):
        rpn.flag.clear_flag(39 - bit)


@defword(name='stdev', print_x=rpn.globl.PX_COMPUTE, doc="""\
Print the sample standard deviation of the statistics data""")
def w_stdev():
    if len(rpn.globl.stat_data) < 2:
        raise rpn.exception.RuntimeErr("stdev: Insufficient statistics data (2 required)")
    try:
        s = statistics.stdev(rpn.globl.stat_data)
    except statistics.StatisticsError as e:
        raise rpn.exception.RuntimeErr("stdev: {}".format(str(e)))
    result = rpn.type.Float(s)
    result.label = "stdev"
    rpn.globl.param_stack.push(result)


@defword(name='sto', args=2, print_x=rpn.globl.PX_CONFIG, doc="""\
Store value Y into register X  ( y reg -- )""")
def w_sto():
    (reg_size, _) = rpn.globl.lookup_variable("SIZE")

    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("sto: Type error ({}, {})".format(typename(y), typename(x)))
    reg = x.value
    if reg < 0 or reg >= reg_size.obj.value:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("sto: Register '{}' out of range (0..{} expected)".format(reg, reg_size.obj.value - 1))
    if type(y) in [rpn.type.Float, rpn.type.Complex]:
        rpn.globl.register[reg] = y
    else:
        rpn.globl.register[reg] = rpn.type.Float(y.value)


@defword(name='stoI', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
Store X value into register I  ( x -- )""")
def w_stoI():
    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Float, rpn.type.Complex]:
        rpn.globl.register['I'] = x
    else:
        rpn.globl.register['I'] = rpn.type.Float(x.value)


@defword(name='swap', args=2, print_x=rpn.globl.PX_CONFIG, doc="""\
Exchange top two stack elements  ( y x -- x y )
Equivalent to 1 ROLL""")
def w_swap():
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    rpn.globl.param_stack.push(x)
    rpn.globl.param_stack.push(y)


@defword(name='tan', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Tangent  ( angle -- tangent )

NOTE:
Angle must not be 90 degrees (TAU/4 radians)""")
def w_tan():
    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        try:
            r = math.tan(rpn.globl.convert_mode_to_radians(x.value))
        except ValueError:
            rpn.globl.param_stack.push(x)
            raise rpn.exception.ValueErr("tan: Argument {} out of range".format(x.value))
        result = rpn.type.Float(r)
    elif type(x) is rpn.type.Complex:
        try:
            r = cmath.tan(x.value)
        except ValueError:
            rpn.globl.param_stack.push(x)
            raise rpn.exception.ValueErr("tan: Argument {} out of range".format(x.value))
        result = rpn.type.Complex.from_complex(r)
    else:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("tan: Type error ({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='tanh', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Hyperbolic tangent  ( angle -- tangent_h )

DEFINITION:
tanh(x) = sinh(x) / cosh(x)""")
def w_tanh():
    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        result = rpn.type.Float(math.tanh(x.value))
    elif type(x) is rpn.type.Complex:
        result = rpn.type.Complex.from_complex(cmath.tanh(x.value))
    else:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("tanh: Type error ({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='TAU', print_x=rpn.globl.PX_COMPUTE, doc="""\
Constant: Tau ( -- 6.28318... )

DEFINITION:
Number of radians in a circle.""")
def w_TAU():
    result = rpn.type.Float(rpn.globl.TAU)
    result.label = "TAU"
    rpn.globl.param_stack.push(result)


@defword(name='tf', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
Toggle flag  ( f -- )""")
def w_tf():
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("tf: Type error ({})".format(typename(x)))
    flag = x.value
    if flag < 0 or flag >= rpn.flag.MAX:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("tf: Flag {} out of range (0..{} expected)".format(flag, rpn.flag.MAX - 1))
    if flag >= rpn.flag.FENCE:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.ValueErr("tf: Flag {} cannot be modified".format(flag))
    rpn.flag.toggle_flag(flag)


@defword(name='then', args=1, print_x=rpn.globl.PX_CONTROL, doc="""\
Execute a conditional test.
<flag> IF ... [ ELSE ... ] THEN

qv ELSE, IF""")
def w_ctl_then():
    pass                        # Grammar rules handle this word


@defword(name='throw', args=1, print_x=rpn.globl.PX_CONTROL, doc="""\
Throw an exception  ( n -- )

N must be positive.

qv CATCH""")
def w_throw():
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("throw: Type error ({})".format(typename(x)))
    if x.value <= 0:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.RuntimeErr("throw: X must be positive")
    dbg("catch", 1, "{}: Throwing {}".format(whoami(), x.value))
    raise rpn.exception.Throw(x.value)


@defword(name='time', print_x=rpn.globl.PX_COMPUTE, doc="""\
Current time  ( -- HH.MMSS )""")
def w_time():
    t = datetime.datetime.now().strftime("%H.%M%S")
    result = rpn.type.Float(t)
    result.label = "HH.MMSS (Current)"
    rpn.globl.param_stack.push(result)


@defword(name='time!', print_x=rpn.globl.PX_COMPUTE, doc="""\
High precision clock time  ( -- HH.MMSSssss )""")
def w_time_bang():
    t = datetime.datetime.now().strftime("%H.%M%S%f")
    result = rpn.type.Float(t)
    result.label = "HH.MMSSssss (Current)"
    rpn.globl.param_stack.push(result)


@defword(name='timeinfo', args=1, hidden=True, print_x=rpn.globl.PX_IO, doc="""\
Show time_info() for Float  ( x -- )""")
def w_timeinfo():
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Float:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("timeinfo: Type error ({})".format(typename(x)))
    rpn.globl.writeln("timeinfo: {}".format(x.time_info()))


@defword(name='trace', print_x=rpn.globl.PX_CONFIG, doc="""\
Toggle tracing state""")
def w_trace():
    if dbg("trace"):
        rpn.debug.set_debug_level("trace", 0)
        rpn.globl.lnwriteln("trace: Tracing is now disabled")
    else:
        rpn.flag.set_flag(rpn.flag.F_DEBUG_ENABLED)
        rpn.debug.set_debug_level("trace", 1)
        rpn.globl.lnwriteln("trace: Tracing is now ENABLED")


@defword(name='trn', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
Transpose a matrix  ( mat -- mat_T )""")
def w_trn():
    x = rpn.globl.param_stack.pop()
    if type(x) is rpn.type.Vector:
        # Transposing a vector is allowed but has no effect.
        # It does NOT "convert a 1-D array into a 2D column vector".
        rpn.globl.param_stack.push(x)
        return
    if type(x) is not rpn.type.Matrix:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("trn: Type error ({})".format(typename(x)))
    t = rpn.type.Matrix.from_numpy(np.matrix.transpose(x.value))
    rpn.globl.param_stack.push(t)


@defword(name='undef', print_x=rpn.globl.PX_CONFIG, doc="""\
Undefine a variable, removing it from the current scope.
UNDEF <var>""")
def w_undef():
    pass                        # Grammar rules handle this word


@defword(name='until', print_x=rpn.globl.PX_CONTROL, doc="""\
Execute an indefinite loop until a condition is satisfied.
BEGIN ... <flag> UNTIL

LEAVE will exit the loop early.  Note that the effect of the test in
BEGIN...WHILE is opposite that in BEGIN...UNTIL.  The loop repeats
while something is true, rather than until it becomes true.

qv AGAIN, BEGIN, LEAVE, REPEAT, WHILE""")
def w_ctl_until():
    pass                        # Grammar rules handle this word


if rpn.globl.have_module('numpy'):
    @defword(name='v>', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
Decompose a vector into stack elements""")
    def v_from():
        x = rpn.globl.param_stack.pop()
        if type(x) is not rpn.type.Vector:
            rpn.globl.param_stack.push(x)
            raise rpn.exception.TypeErr("v>: Type error ({})".format(typename(x)))
        for elem in x.value:
            rpn.globl.param_stack.push(rpn.globl.to_rpn_class(elem))


@defword(name='var', print_x=rpn.globl.PX_COMPUTE, doc="""\
Print the sample variance of the statistics data""")
def w_var():
    if len(rpn.globl.stat_data) < 2:
        raise rpn.exception.RuntimeErr("var: Insufficient statistics data (2 required)")
    try:
        v = statistics.variance(rpn.globl.stat_data)
    except statistics.StatisticsError as e:
        raise rpn.exception.RuntimeErr("var: {}".format(str(e)))
    rpn.globl.param_stack.push(rpn.type.Float(v))


@defword(name='variable', print_x=rpn.globl.PX_CONFIG, doc="""\
Declare a variable.  Initial state is undefined.
VARIABLE <var>""")
def w_variable():
    pass                        # Grammar rules handle this word


@defword(name='vars', print_x=rpn.globl.PX_IO, doc="""\
List variables and their values""")
def w_vars():
    for (_, scope) in rpn.globl.scope_stack.items_top_to_bottom():
        if rpn.globl.scope_stack.size() > 1:
            rpn.globl.lnwriteln("Scope {}".format(scope.name()))
        my_vars = dict()
        for varname in scope.variables():
            var = scope.variable(varname)
            if var.hidden:
                continue
            my_vars[var.name()] = "{}:[undef]".format(var.name()) if not var.defined() else \
                                  "{}={}{}".format(var.name(),
                                                   var.obj.value,
                                                   "(" + typename(var.obj) + ")" if rpn.flag.flag_set_p(rpn.flag.F_DEBUG_ENABLED) else "")
        sorted_vars = []
        for key in sorted(my_vars, key=str.casefold):
            sorted_vars.append(my_vars[key])
        rpn.globl.list_in_columns(sorted_vars, rpn.globl.scr_cols.obj.value - 1)


@defword(name='vlist', print_x=rpn.globl.PX_IO, doc="""\
Print the list of defined words.
Only words in the root scope are shown.

qv WORDS""")
def w_vlist():
    # This is nice, but it shows hidden words:
    # rpn.globl.list_in_columns(sorted([x for x in root_scope.words()],
    #                           key=str.casefold), rpn.globl.scr_cols.obj.value - 1)
    words = dict()
    for wordname in rpn.globl.root_scope.words():
        word = rpn.globl.root_scope.word(wordname)
        if word.hidden:
            continue
        words[word.name()] = word.name()
    sorted_words = []
    for key in sorted(words, key=str.casefold):
        sorted_words.append(words[key])
    rpn.globl.list_in_columns(sorted_words, rpn.globl.scr_cols.obj.value - 1)


@defword(name='while', print_x=rpn.globl.PX_CONTROL, doc="""\
Execute an indefinite loop while a condition is satisfied.
BEGIN ... <flag> WHILE ... REPEAT

LEAVE will exit the loop early.  Note that the effect of the test in
BEGIN...WHILE is opposite that in BEGIN...UNTIL.  The loop repeats
while something is true, rather than until it becomes true.

qv AGAIN, BEGIN, LEAVE, REPEAT, UNTIL""")
def w_ctl_while():
    pass                        # Grammar rules handle this word


@defword(name='words', print_x=rpn.globl.PX_IO, doc="""\
Print the list of user-defined words.

qv VLIST""")
def w_words():
    rpn.globl.list_in_columns(sorted([x[0] for x in rpn.globl.root_scope.unprotected_words()],
                                     key=str.casefold), rpn.globl.scr_cols.obj.value - 1)


@defword(name='x<>I', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
x<>I  ( x -- I )  Exchange X with register I""")
def w_x_exchange_I():
    x = rpn.globl.param_stack.pop()
    rpn.globl.param_stack.push(rpn.globl.register['I'])
    rpn.globl.register['I'] = x


@defword(name='x<>i', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
x<>i  ( x -- (i) )  Exchange X with register referenced by I""")
def w_x_exchange_indirect_i():
    (reg_size, _) = rpn.globl.lookup_variable("SIZE")

    I = rpn.globl.register['I']
    if type(I) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
        raise rpn.exception.TypeErr("x<>i: Type error I ({})".format(typename(I)))
    Ival = int(I.value)
    if Ival < 0 or Ival >= reg_size.obj.value:
        raise rpn.exception.ValueErr("x<>i: Register {} out of range (0..{} expected)".format(Ival, reg_size.obj.value - 1))

    x = rpn.globl.param_stack.pop()
    rpn.globl.param_stack.push(rpn.globl.register[Ival])
    rpn.globl.register[Ival] = x


@defword(name='zer', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
zer  ( v -- m )  Create a zero vector or matrix""")
def w_zer():
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Vector:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.TypeErr("zer: Type error ({})".format(typename(x)))
    xs = x.size()

    if xs == 1:
        size = int(x.value.item(0))
        if size <= 0:
            rpn.globl.param_stack.push(x)
            raise rpn.exception.ValueErr("zer: Dimension must be positive")
        z = rpn.type.Vector.from_numpy(np.zeros(size))
        rpn.globl.param_stack.push(z)
    elif xs == 2:
        rows = int(x.value.item(0))
        cols = int(x.value.item(1))
        if rows <= 0 or cols <= 0:
            rpn.globl.param_stack.push(x)
            raise rpn.exception.ValueErr("zer: Dimensions must be positive")
        z = rpn.type.Matrix.from_numpy(np.zeros((rows, cols)))
        rpn.globl.param_stack.push(z)
    else:
        rpn.globl.param_stack.push(x)
        raise rpn.exception.RuntimeErr("zero: Dimension vector must have only 1 or 2 elements")



#############################################################################
#
#       H E L P E R   F U N C T I O N S
#
#############################################################################
def memoize(f):
    memoized = {}
    def helper(x):
        if x not in memoized:
            memoized[x] = f(x)
        return memoized[x]
    return helper


def any_undefined_p(var_list):
    for var in var_list:
        if not var.defined():
            return True
    return False


def comb_helper(n, r):
    if r > n or r < 0:
        return 0
    if n - r < r:
        r = n - r

    result = 1
    j = 1
    while j <= r:
        result *= n
        n -= 1
        result /= j
        j += 1
    return result


def equal_helper(x, y):
    """\
# Parameters are Rpn objects, not values
# Return values:
#    1 : Values are equal
#    0 : Values are not equal
#   -1 : Type error

|----------+----------+---------+----------+---------+--------+--------|
| Integer  |   xxxx   |  xxx    |  xxxx    | xxxx    |        |        |
| Float    |   xxxxx  |  xxx    |   xxxx   | xxx     |        |        |
| Rational |   xxxx   |  xxx    |  xxxxx   | xxxx    |        |        |
| Complex  |    xxxx  |  xxx    |   xxx    | xxx     |        |        |
| Vector   |          |         |          |         | xxxx   |        |
| Matrix   |          |         |          |         |        |        |
|----------+----------+---------+----------+---------+--------+--------|
| ^Y    X> | Integer  | Float   | Rational | Complex | Vector | Matrix |"""
    flag = None
    if type(x) is rpn.type.Integer and type(y) is rpn.type.Integer:
        flag = y.value == x.value
    elif type(x) is rpn.type.Float and type(y) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational] \
      or type(y) is rpn.type.Float and type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        # Beware floating point equality lossage!
        # Should use a relative comparison here...
        flag = float(y.value) == float(x.value)
    elif type(x) is rpn.type.Rational and type(y) in [rpn.type.Integer, rpn.type.Rational] \
      or type(y) is rpn.type.Rational and type(x) in [rpn.type.Integer, rpn.type.Rational]:
        flag = Fraction(y.value) == Fraction(x.value)
    elif type(x) is rpn.type.Complex and type(y) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational, rpn.type.Complex] \
      or type(y) is rpn.type.Complex and type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational, rpn.type.Complex]:
        flag = complex(y.value) == complex(x.value)
    elif type(x) is rpn.type.Vector and type(y) is rpn.type.Vector:
        if x.size() != y.size():
            flag = False
        else:
            r = functools.reduce(lambda i, j: i and j,
                                 map(lambda m, k: m == k, x.value, y.value), True)
            flag = bool(r) # True if r else False
    elif type(x) is rpn.type.Matrix and type(y) is rpn.type.Matrix:
        flag = np.array_equal(x.value, y.value)

    if flag is None:
        return -1
    return rpn.globl.bool_to_int(flag)


@memoize
def fact_helper(x):
    result = 1
    while x > 1:
        result *= x
        x -= 1
    return result


@memoize
def fib_helper(n):
    if n == 0:
        return 0
    if n == 1:
        return 1
    return fib_helper(n-1) + fib_helper(n-2)


def gcd_helper(x, y):
    while x != 0:
        y, x = x, y % x
    return y


def plot_helper(func, x_low, x_high):
    cols = rpn.globl.scr_cols.obj.value
    rows = rpn.globl.scr_rows.obj.value

    ISCR   = cols - 20
    JSCR   = rows -  3
    BLANK  = ' '
    VERT   = ':'
    VZERO  = '|'
    HORIZ  = '-'
    HZERO  = '='
    ORIGIN = '+'
    FF     = '*'
    scr = [[BLANK for i in range(1,JSCR+2)] for j in range(1,ISCR+2)]

    # Build frame
    for j in range(1, JSCR+1):
        scr[1][j] = VERT
        scr[ISCR][j] = VERT
    for i in range(2, ISCR):
        scr[i][1] = HORIZ
        scr[i][JSCR] = HORIZ
        for j in range(2, JSCR):
            scr[i][j] = BLANK

    if x_low > x_high:
        x_low, x_high = x_high, x_low
    x = x_low
    dx = (x_high - x_low) / (ISCR - 1)
    dxi = (ISCR - 1) / (x_high - x_low)
    iz = 1 - int(x_low * dxi)

    y = [0.0] * (ISCR+1)
    ysml, ybig = 0.0, 0.0
    for i in range(1, ISCR+1):
        y[i] = func(x)
        ysml = min(ysml, y[i])
        ybig = max(ybig, y[i])
        x += dx

    if ybig == ysml:
        ybig = ysml + 1.0
    dyj = (JSCR - 1) / (ybig - ysml)
    jz = 1 - int(ysml * dyj)

    # Build axes
    for i in range(2, ISCR):
        for j in range(2, JSCR):
            if i == iz:
                scr[i][j] = VZERO
            if j == jz:
                scr[i][j] = HZERO
            if i == iz and j == jz:
                scr[i][j] = ORIGIN

    # Populate data points
    for i in range(1, ISCR+1):
        j = 1 + int((y[i] - ysml) * dyj)
        scr[i][j] = FF

    # Display plot
    rpn.globl.write(" {:10.3f} ".format(ybig))
    for i in range(1, ISCR+1):
        rpn.globl.write(scr[i][JSCR])
    rpn.globl.writeln()
    for j in range(JSCR-1, 1, -1):
        rpn.globl.write(" " * 12)
        for i in range(1, ISCR+1):
            rpn.globl.write(scr[i][j])
        rpn.globl.writeln()
    rpn.globl.write(" {:10.3f} ".format(ysml))
    for i in range(1, ISCR+1):
        rpn.globl.write(scr[i][1])
    rpn.globl.lnwriteln("         {:10.3f} {} {:10.3f}".format(x_low, " "*(cols-36), x_high))


# Helper routines for KEY
class _Getch_Windows:
    def __init__(self):
        import msvcrt                   # pylint: disable=import-error,import-outside-toplevel,unused-import

    def __call__(self):
        import msvcrt                   # pylint: disable=import-error,import-outside-toplevel
        return msvcrt.getch()

class _Getch_unix:
    def __init__(self):
        pass

    def __call__(self):
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

class _Getch:
    """Gets a single character from standard input.  Does not echo to the screen."""

    def __init__(self):
        try:
            self.impl = _Getch_windows() # pylint: disable=undefined-variable
        except ImportError:
            self.impl = _Getch_unix()


    def __call__(self):
        return self.impl()
