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
import readline                 # pylint: disable=unused-import
import random
import statistics
import subprocess
import sys
import tempfile                 # edit
import termios
import time
import tty


# Check if NumPy is available
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

from   rpn.exception import *   # pylint: disable=wildcard-import
from   rpn.debug import dbg, typename
import rpn.flag
import rpn.globl
import rpn.tvm
import rpn.util


class defword():
    """Register the following word definition in the root scope"""

    def __init__(self, **kwargs):
        self._kwargs = kwargs

    def __call__(self, f):
        def wrapped_f(name, **kwargs): # pylint: disable=unused-argument
            #print("Decorator args: {}".format(self._kwargs))
            f(name)
            if "print_x" in self._kwargs and \
               self._kwargs["print_x"] is not None:
                if self._kwargs["print_x"]:
                    rpn.flag.set_flag(rpn.flag.F_SHOW_X)
                else:
                    rpn.flag.clear_flag(rpn.flag.F_SHOW_X)

        if "name" not in self._kwargs:
            raise FatalErr('Missing "name" attribute')
        if len(self._kwargs["name"]) == 0:
            throw(X_ZERO_LEN_STR)
        name = self._kwargs["name"]
        del self._kwargs["name"]

        word = rpn.util.Word(name, "python", wrapped_f, **self._kwargs)
        rpn.globl.root_scope.define_word(name, word)
        return wrapped_f


@defword(name='#->$', args=1, print_x=rpn.globl.PX_IO, doc="""\
#->$   ( n -- )
Convert top of stack to string.""")
def w_num_to_dollar(name):      # pylint: disable=unused-argument
    rpn.globl.string_stack.push(rpn.type.String(rpn.globl.gfmt(rpn.globl.param_stack.pop())))


@defword(name='#in', print_x=rpn.globl.PX_IO, doc="""\
#in   ( -- n )
Read numeric input from the user.  #IN recognizes integers and floats,
but not rationals or complex numbers.  The value is put on the stack.
No prompt is provided.

See also: prompt""")
def w_number_in(name):
    x = ""
    while len(x) == 0:
        try:
            x = input()
            dbg(name, 1, "#in: '{}'".format(x))
        except EOFError:
            throw(X_EOF, name)
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
        throw(X_SYNTAX, name, "Could not parse '{}'".format(x))


@defword(name='$.', str_args=1, print_x=rpn.globl.PX_IO, doc="""\
$.   [ str -- ]
Print top item from string stack.  No extraneous white space
or newline is printed.""")
def w_dollar_dot(name):         # pylint: disable=unused-argument
    rpn.globl.write(rpn.globl.string_stack.pop().value)


@defword(name='$.!', hidden=True, print_x=rpn.globl.PX_IO, str_args=1)
def w_dollar_dot_bang(name):    # pylint: disable=unused-argument
    rpn.globl.lnwriteln(repr(rpn.globl.string_stack.top()))


@defword(name='$in', print_x=rpn.globl.PX_IO, doc="""\
$in   [ -- str ]
Read a string from the keyboard.  The value is placed on the string stack.
No prompt is provided.""")
def w_dollar_in(name):
    x = ""
    while len(x) == 0:
        try:
            x = input()
            dbg(name, 1, "$in: '{}'".format(x))
        except EOFError:
            throw(X_EOF, name)
        finally:
            rpn.globl.sharpout.obj = rpn.type.Integer(0)

    rpn.globl.string_stack.push(rpn.type.String(x))



@defword(name='$.s', print_x=rpn.globl.PX_IO, doc="""\
$.s
Display string stack.""")
def w_dollar_dot_s(name):       # pylint: disable=unused-argument
    if not rpn.globl.string_stack.empty():
        rpn.globl.lnwriteln(rpn.globl.string_stack)


@defword(name='$.s!', print_x=rpn.globl.PX_IO, hidden=True)
def w_dollar_dot_s_bang(name):  # pylint: disable=unused-argument
    if not rpn.globl.string_stack.empty():
        rpn.globl.lnwriteln(repr(rpn.globl.string_stack))


@defword(name='$=', str_args=2, print_x=rpn.globl.PX_PREDICATE, doc="""\
$=   ( -- flag )
Test if two strings are equal.""")
def w_dollar_equal(name):       # pylint: disable=unused-argument
    s1 = rpn.globl.string_stack.pop()
    s2 = rpn.globl.string_stack.pop()
    rpn.globl.param_stack.push(rpn.type.Integer(rpn.globl.bool_to_int(s1.value == s2.value)))


@defword(name='$cat', str_args=2, print_x=rpn.globl.PX_IO, doc="""\
$cat   [ s2 s1 -- s2s1 ]
Concatentate two strings.

EXAMPLE:
    "foo" "bar" $cat "baz" $cat
"foobarbaz" """)
def w_dollar_cat(name):         # pylint: disable=unused-argument
    s1 = rpn.globl.string_stack.pop()
    s2 = rpn.globl.string_stack.pop()
    rpn.globl.string_stack.push(rpn.type.String.from_string(s2.value + s1.value))


@defword(name='$clst', print_x=rpn.globl.PX_CONFIG, doc="""\
$clst   [ -- ]
Clear the string stack.""")
def w_dollar_clst(name):        # pylint: disable=unused-argument
    rpn.globl.string_stack.clear()


@defword(name='$depth', print_x=rpn.globl.PX_COMPUTE, doc="""\
$depth   ( -- n )
String stack depth.""")
def w_dollar_depth(name):       # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(rpn.globl.string_stack.size()))


@defword(name='$drop', str_args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
$drop   ( -- )
Drop top of string stack.""")
def w_dollar_drop(name):        # pylint: disable=unused-argument
    rpn.globl.string_stack.pop()


@defword(name='$len', str_args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
$len   ( -- n )
Length of top element of string stack.""")
def w_dollar_len(name):         # pylint: disable=unused-argument
    s = rpn.globl.string_stack.top()
    r = len(s.value)
    rpn.globl.param_stack.push(rpn.type.Integer(r))


@defword(name='$swap', str_args=2, print_x=rpn.globl.PX_CONFIG, doc="""\
$swap   [ "y" "x" -- "x" "y" ]
Exchange top two string stack elements.""")
def w_dollar_swap(name):        # pylint: disable=unused-argument
    sx = rpn.globl.string_stack.pop()
    sy = rpn.globl.string_stack.pop()
    rpn.globl.string_stack.push(sx)
    rpn.globl.string_stack.push(sy)


@defword(name='$throw', args=1, str_args=1, print_x=rpn.globl.PX_CONTROL, doc="""\
$throw   ( n -- )  [ msg -- ]
Throw an exception with text.

See also: catch""")
def w_dollar_throw(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    if x.value == 0:
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_ARG, name, "X cannot be zero")
    message = rpn.globl.string_stack.pop().value
    thrown_from = ""
    if not rpn.globl.colon_stack.empty():
        thrown_from = rpn.globl.colon_stack.top().name
    dbg("catch", 1, "{}: Throwing {} from '{}'".format(name, x.value, thrown_from))
    throw(x.value, thrown_from, message)


@defword(name='$time', print_x=rpn.globl.PX_COMPUTE, doc="""\
$time   [ -- HH:MM:SS ]
Current time as string.""")
def w_dollar_time(name):        # pylint: disable=unused-argument
    t = datetime.datetime.now().strftime("%H:%M:%S")
    rpn.globl.string_stack.push(rpn.type.String(t))


@defword(name='$ushow', str_args=1, print_x=rpn.globl.PX_IO, doc="""\
$ushow   [ unit -- ]
Show detailed information about a unit-expression.

See also: units, ushow""")
def w_dollar_ushow(name):
    s = rpn.globl.string_stack.pop()
    ustr = s.value
    ue = rpn.unit.unit_lookup(ustr)

    # See if it's a real unit
    if ue is not None:
        unit = ue.unit
        rpn.globl.lnwrite("\"{}\" refers to the unit '{}'".format(ustr, unit.name))
        if ue.prefix is not None:
            rpn.globl.write(" with prefix '{}' (x10^{})".format(ue.prefix[0], ue.prefix[2]))
        rpn.globl.writeln()
        if ue.unit.base_p:
            rpn.globl.writeln('SI units: "{}" is a base unit'.format(unit.name))
        else:
            defn = "{}".format(unit.factor())
            e = unit.orig_exp
            if e is not None and e != 0:
                defn += " * 10^{}".format(e)
            defn += " {}".format(unit.deriv)
            rpn.globl.writeln("Definition: {}".format(defn))

            x = rpn.type.Integer.from_string("1_{}".format(ustr))
            base_ue = x.uexpr.ubase()
            value = x.uexpr.base_factor() * (10 ** x.uexpr.exp())
            if base_ue.exp() != 0:
                value *= (10 ** base_ue.exp())
            rpn.globl.writeln("SI units: 1 {} = {} {}".format(unit.name, value, base_ue))
        cat = rpn.unit.Category.lookup_by_dim(ue.dim())
        if cat is not None:
            rpn.globl.writeln("It is a measure of {}".format(cat.measure))
        rpn.globl.writeln("It has dimensions = {}".format(ue.dim()))
        return

    # See if it's a valid combination of units
    ue = rpn.unit.try_parsing(ustr)
    if ue is not None:
        rpn.globl.lnwriteln("\"{}\" is a unit expression".format(ustr))
        base_ue = ue.ubase()
        rpn.globl.writeln("SI units: {}".format(base_ue))
        cat = rpn.unit.Category.lookup_by_dim(ue.dim())
        if cat is not None:
            rpn.globl.writeln("It is a measure of {}".format(cat.measure))
        rpn.globl.writeln("It has dimensions = {}".format(ue.dim()))
        return

    # Not valid
    rpn.globl.string_stack.push(s)
    throw(X_INVALID_UNIT, name, ustr)


@defword(name='%', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
%   ( base rate -- base percent )
Percentage.  Base is maintained in Y.

DEFINTION:
                 rate
percent = base * ----
                 100""")
def w_percent(name):
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
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))
    rpn.globl.param_stack.push(y)
    rpn.globl.param_stack.push(result)


@defword(name='%ch', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
%ch   ( old new -- %change )
Percentage change.  Old cannot be zero.

DEFINITION:
          new - old
%Change = --------- * 100
             old""")
def w_percent_ch(name):
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if     type(x) in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float] \
       and type(y) in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
        if y.zerop():
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            throw(X_FP_DIVISION_BY_ZERO, name, "Y (old) cannot be zero")

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
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))
    # The HP-32SII preserves the Y value (like %) but we do not
    rpn.globl.param_stack.push(result)


@defword(name='%t', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
%t   ( total amount -- %tot )
Percent of total.  Total cannot be zero.

DEFINITION:

         amount
%Total = ------ * 100
         total""")
def w_percent_t(name):
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if     type(x) in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float] \
       and type(y) in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
        if y.zerop():
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            throw(X_FP_DIVISION_BY_ZERO, name, "Y (total) cannot be zero")

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
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))
    # The HP-32SII preserves the Y value (like %) but we do not
    rpn.globl.param_stack.push(result)


@defword(name='*', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
*   ( y x -- y*x )
Multiplication.""")
def w_star(name):
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
            print("r=", type(r), r)
            print("r.dtype={}, r.shape={}, r.ndim={}".format(r.dtype, r.shape, r.ndim))
        except ValueError:
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            throw(X_CONFORMABILITY, name)
        result = rpn.type.Matrix.from_numpy(r)
    else:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))

    if x.has_uexpr_p() and not y.has_uexpr_p():
        result.uexpr = x.uexpr
    elif not x.has_uexpr_p() and y.has_uexpr_p():
        result.uexpr = y.uexpr
    elif x.has_uexpr_p() and y.has_uexpr_p():
        result.uexpr = rpn.unit.UProd(y.uexpr, x.uexpr)
    rpn.globl.param_stack.push(result)


@defword(name='*/', args=3, print_x=rpn.globl.PX_COMPUTE, doc="""\
*/   ( z y x -- z*y/x )
Multiply and divide.  X cannot be zero.""")
def w_star_slash(name):
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    z = rpn.globl.param_stack.pop()
    if    type(x) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float, rpn.type.Complex] \
       or type(y) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float, rpn.type.Complex] \
       or type(z) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float, rpn.type.Complex]:
        rpn.globl.param_stack.push(z)
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({} {} {})".format(typename(z), typename(y), typename(x)))
    if z.zerop():
        rpn.globl.param_stack.push(z)
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_FP_DIVISION_BY_ZERO, name, "X cannot be zero")

    rpn.globl.param_stack.push(z)
    rpn.globl.param_stack.push(y)
    rpn.word.w_star('*')
    rpn.globl.param_stack.push(x)
    rpn.word.w_slash('/')


@defword(name='+', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
+   ( y x -- y+x )
Addition.""")
def w_plus(name):
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

    if (x.has_uexpr_p() and not y.has_uexpr_p()) or \
       (y.has_uexpr_p() and not x.has_uexpr_p()):
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_INCONSISTENT_UNITS, name)
    if x.has_uexpr_p() and y.has_uexpr_p():
        if not rpn.unit.units_conform(x.uexpr, y.uexpr):
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            throw(X_CONFORMABILITY, name)
        # Convert Y to the units of X
        new_ustr = str(x.uexpr)
        y = y.uexpr_convert(new_ustr, name)

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
        result = rpn.type.Vector.from_ndarray(r)
    elif type(x) is rpn.type.Vector and type(y) is rpn.type.Vector:
        if x.size() != y.size():
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            throw(X_CONFORMABILITY, name, "Vectors are not same size")
        r = np.add(y.value, x.value)
        # print(type(r))
        # print(r)
        result = rpn.type.Vector.from_ndarray(r)
    elif    type(x) is rpn.type.Matrix and type(y) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational, rpn.type.Complex] \
         or type(y) is rpn.type.Matrix and type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational, rpn.type.Complex]:
        r = np.add(y.value, x.value)
        result = rpn.type.Matrix.from_numpy(r)
    elif type(x) is rpn.type.Matrix and type(y) is rpn.type.Matrix:
        if x.nrows() != y.nrows() or x.ncols() != y.ncols():
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            throw(X_CONFORMABILITY, name, "Vectors are not same size")
        r = np.add(y.value, x.value)
        # print(type(r))
        # print(r)
        result = rpn.type.Matrix.from_numpy(r)
    else:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))

    if x.has_uexpr_p():
        result.uexpr = x.uexpr
    rpn.globl.param_stack.push(result)


@defword(name='+loop', print_x=rpn.globl.PX_CONTROL, doc="""\
+loop
Execute a definite loop.
<limit> <initial> DO ... <incr> +LOOP

The iteration counter is available via I.  LEAVE will exit the loop early.

EXAMPLE:
    10 0 do I . 2 +loop
0 2 4 6 8

See also: do, I, leave, loop""")
def w_plusloop(name):           # pylint: disable=unused-argument
    pass                        # Grammar rules handle this word


@defword(name='-', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
-   ( y x -- y-x )
Subtraction.""")
def w_minus(name):
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()

    if (x.has_uexpr_p() and not y.has_uexpr_p()) or \
       (y.has_uexpr_p() and not x.has_uexpr_p()):
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_INCONSISTENT_UNITS, name)
    if x.has_uexpr_p() and y.has_uexpr_p():
        if not rpn.unit.units_conform(x.uexpr, y.uexpr):
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            throw(X_CONFORMABILITY, name)
        # Convert Y to the units of X
        new_ustr = str(x.uexpr)
        y = y.uexpr_convert(new_ustr, name)

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
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))

    if x.has_uexpr_p():
        result.uexpr = x.uexpr
    rpn.globl.param_stack.push(result)


@defword(name='.', args=1, print_x=rpn.globl.PX_IO, doc="""\
.   ( x -- )
Print top stack value.  A space is also printed after the number,
but no newline.  (If you need a newline, use cr.)""")
def w_dot(name):                # pylint: disable=unused-argument
    rpn.globl.write("{} ".format(str(rpn.globl.param_stack.pop())))


@defword(name='.!', hidden=True, print_x=rpn.globl.PX_IO, args=1)
def w_dot_bang(name):           # pylint: disable=unused-argument
    rpn.globl.lnwriteln(repr(rpn.globl.param_stack.top()))


@defword(name='."', print_x=rpn.globl.PX_IO, doc="""\
."
Display string enclosed by quotation marks.  No newline is printed afterwards.
NOTE: The string begins immediately after the first ", so
  ."Hello, world!"
is correct.  This is different from Forth, where the must be a space after ." """)
def w_dot_quote(name):          # pylint: disable=unused-argument
    pass                        # Grammar rules handle this word


@defword(name='.all', args=1, print_x=rpn.globl.PX_IO, doc="""\
.all   ( x -- )
Print X in a variety of formats.""")
def w_dot_all(name):            # pylint: disable=unused-argument
    x = rpn.globl.param_stack.pop()
    xval = x.value

    out = rpn.globl.gfmt(x)
    more = ""
    if type(x) is rpn.type.Integer:
        more += "  Hex={}".format(hex(x.value))
        more += "  Oct={}".format(oct(x.value))

        ascii_char = ["NUL", "SOH", "STX", "ETX", "EOT", "ENQ", "ACK", "BEL",
                      "BS",  "HT",  "LF",  "VT",  "FF",  "CR",  "SO",  "SI",
                      "DLE", "DC1", "DC2", "DC3", "DC4", "NAK", "SYN", "ETB",
                      "CAN", "EM",  "SUB", "ESC", "FS",  "GS",  "RS",  "US",
                      # 32
                      "SP",  "!",   "\"",  "#",   "$",   "%",   "&",   "'",
                      "(",   ")",   "*",   "+",   ",",   "-",   ".",   "/",
                      "0",   "1",   "2",   "3",   "4",   "5",   "6",   "7",
                      "8",   "9",   ":",   ";",   "<",   "=",   ">",   "?",
                      # 64
                      "@",   "A",   "B",   "C",   "D",   "E",   "F",   "G",
                      "H",   "I",   "J",   "K",   "L",   "M",   "N",   "O",
                      "P",   "Q",   "R",   "S",   "T",   "U",   "V",   "W",
                      "X",   "Y",   "Z",   "[",   "\\",  "]",   "^",   "_",
                      # 96
                      "`",   "a",   "b",   "c",   "d",   "e",   "f",   "g",
                      "h",   "i",   "j",   "k",   "l",   "m",   "n",   "o",
                      "p",   "q",   "r",   "s",   "t",   "u",   "v",   "w",
                      "x",   "y",   "z",   "{",   "|",   "}",   "~",   "DEL"]

        if 0 <= xval < 128:
            glyph = "{}".format(ascii_char[xval])
            if 0 <= xval < 32:
                glyph += " (^{})".format(ascii_char[xval + 64])
            if 33 <= xval < 127:
                glyph = "'" + glyph + "'"
            more += "  Char={}".format(glyph)

    out += more
    rpn.globl.writeln(out)


@defword(name='.bin', args=1, print_x=rpn.globl.PX_IO, doc="""\
.bin   ( i -- )
Print X in binary.  X must be an integer.""")
def w_dot_bin(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))

    rpn.globl.write("{} ".format(bin(x.value)))


@defword(name='.hex', args=1, print_x=rpn.globl.PX_IO, doc="""\
.hex   ( i -- )
Print X in hexadecimal.  X must be an integer.""")
def w_dot_hex(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))

    rpn.globl.write("{} ".format(hex(x.value)))


@defword(name='.oct', args=1, print_x=rpn.globl.PX_IO, doc="""\
.oct   ( i -- )
Print X in octal.  X must be an integer.""")
def w_dot_oct(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))

    rpn.globl.write("{} ".format(oct(x.value)))


@defword(name='.r', args=2, print_x=rpn.globl.PX_IO, doc="""\
.r   ( n width -- )
Print N right-justified in WIDTH.  This never outputs more than WIDTH
characters, and will silently truncate the representation to fit.
It is wise to check the size of your values before printing - you have
been warned!  No space is printed after the number.""")
def w_dot_r(name):
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))
    width = x.value
    if width < 0:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_ARG, name, "X (width) must not be negative")
    if width == 0:
        return

    s = rpn.globl.gfmt(y)
    if len(s) > width:
        s = s[:width]       # This seems a bit harsh, but it's documented
    rpn.globl.write("{:>{width}}".format(s, width=width))


@defword(name='.s', print_x=rpn.globl.PX_IO, doc="""\
.s
Print stack non-destructively.""")
def w_dot_s(name):              # pylint: disable=unused-argument
    if not rpn.globl.param_stack.empty():
        rpn.globl.lnwriteln(rpn.globl.param_stack)


@defword(name='.s!', hidden=True, print_x=rpn.globl.PX_IO, doc="""\
.s!
Print stack non-destructively.""")
def w_dot_s_bang(name):         # pylint: disable=unused-argument
    if not rpn.globl.param_stack.empty():
        rpn.globl.lnwriteln(repr(rpn.globl.param_stack))


@defword(name='/', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
/   ( y x -- y/x )
Division.  X cannot be zero.""")
def w_slash(name):
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
        throw(X_FP_DIVISION_BY_ZERO, name, "X cannot be zero")

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
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))

    if x.has_uexpr_p() and not y.has_uexpr_p():
        result.uexpr = x.uexpr.invert()
    elif not x.has_uexpr_p() and y.has_uexpr_p():
        result.uexpr = y.uexpr
    elif x.has_uexpr_p() and y.has_uexpr_p():
        result.uexpr = rpn.unit.UQuot(y.uexpr, x.uexpr)

    rpn.globl.param_stack.push(result)


@defword(name='/mod', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
/mod   ( y x -- remainder quotient )
Division quotient and remainder.  Divide integers Y by X, returning integer
remainder and quotient.  Signs are whatever Python // and % give you.""")
def w_slash_mod(name):
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer or type(y) is not rpn.type.Integer:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))
    if x.zerop():
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_FP_DIVISION_BY_ZERO, name, "X cannot be zero")
    rem =  y.value %  x.value
    quot = y.value // x.value
    rpn.globl.param_stack.push(rpn.type.Integer(rem))
    rpn.globl.param_stack.push(rpn.type.Integer(quot))


@defword(name=':', print_x=rpn.globl.PX_CONTROL, doc="""\
:   ( -- )
Define a new word.  Define WORD with the specified definition.
Terminate the definition with a semi-colon.
: WORD  [def ...]  ;

See also: ;, show""")
def w_colon(name):              # pylint: disable=unused-argument
    pass                        # Grammar rules handle this word


@defword(name=';', print_x=rpn.globl.PX_CONTROL, doc="""\
;   ( -- )
Terminate WORD definition.
: WORD  [def ...]  ;

See also: :, show""")
def w_semicolon(name):          # pylint: disable=unused-argument
    pass                        # Grammar rules handle this word


@defword(name='<', args=2, print_x=rpn.globl.PX_PREDICATE, doc="""\
<   ( y x -- flag )
Test if Y is less than X.""")
def w_less_than(name):
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()

    if    type(x) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float] \
       or type(y) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))
    if (x.has_uexpr_p() and not y.has_uexpr_p()) or \
       (y.has_uexpr_p() and not x.has_uexpr_p()):
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_INCONSISTENT_UNITS, name)
    if x.has_uexpr_p() and y.has_uexpr_p():
        if not rpn.unit.units_conform(x.uexpr, y.uexpr):
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            throw(X_CONFORMABILITY, name)
        x = x.ubase_convert(name)
        y = y.ubase_convert(name)

    yval = float(y.value)
    xval = float(x.value)
    rpn.globl.param_stack.push(rpn.type.Integer(rpn.globl.bool_to_int(yval < xval)))


@defword(name='<<', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
<<   ( i2 i1 -- i2 << i1 )
Bitwise left shift.""")
def w_leftshift(name):
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer or type(y) is not rpn.type.Integer:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))

    if x.value < 0:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_ARG, name, "X (shift amount) must not be negative")

    rpn.globl.param_stack.push(rpn.type.Integer(y.value << x.value))


@defword(name='<=', args=2, print_x=rpn.globl.PX_PREDICATE, doc="""\
<=   ( y x -- flag )
Test if Y is less than or equal to X.""")
def w_less_than_or_equal(name):
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()

    if    type(x) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float] \
       or type(y) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))
    if (x.has_uexpr_p() and not y.has_uexpr_p()) or \
       (y.has_uexpr_p() and not x.has_uexpr_p()):
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_INCONSISTENT_UNITS, name)
    if x.has_uexpr_p() and y.has_uexpr_p():
        if not rpn.unit.units_conform(x.uexpr, y.uexpr):
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            throw(X_CONFORMABILITY, name)
        y = y.ubase_convert(name)
        x = x.ubase_convert(name)

    yval = float(y.value)
    xval = float(x.value)
    rpn.globl.param_stack.push(rpn.type.Integer(rpn.globl.bool_to_int(yval <= xval)))


@defword(name='<>', args=2, print_x=rpn.globl.PX_PREDICATE, doc="""\
<>   ( y x -- flag )
Test if Y is not equal to X.""")
def w_not_equal(name):
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()

    if (x.has_uexpr_p() and not y.has_uexpr_p()) or \
       (y.has_uexpr_p() and not x.has_uexpr_p()):
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_INCONSISTENT_UNITS, name)
    if x.has_uexpr_p() and y.has_uexpr_p():
        if not rpn.unit.units_conform(x.uexpr, y.uexpr):
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            throw(X_CONFORMABILITY, name)
        cvt_x = x.ubase_convert(name)
        cvt_y = y.ubase_convert(name)
        equal = equal_helper(cvt_x, cvt_y)
    else:
        equal = equal_helper(x, y)

    if equal == -1:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))
    rpn.globl.param_stack.push(rpn.type.Integer(0 if equal else 1))


@defword(name='=', args=2, print_x=rpn.globl.PX_PREDICATE, doc="""\
=   ( y x -- flag )
Test if Y is equal to X.""")
def w_equal(name):
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()

    if (x.has_uexpr_p() and not y.has_uexpr_p()) or \
       (y.has_uexpr_p() and not x.has_uexpr_p()):
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_INCONSISTENT_UNITS, name)
    if x.has_uexpr_p() and y.has_uexpr_p():
        if not rpn.unit.units_conform(x.uexpr, y.uexpr):
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            throw(X_CONFORMABILITY, name)
        cvt_x = x.ubase_convert(name)
        cvt_y = y.ubase_convert(name)
        equal = equal_helper(cvt_x, cvt_y)
    else:
        equal = equal_helper(x, y)

    if equal == -1:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))
    rpn.globl.param_stack.push(rpn.type.Integer(equal))


@defword(name='>', args=2, print_x=rpn.globl.PX_PREDICATE, doc="""\
>   ( y x -- flag )
Test if Y is greater than X.""")
def w_greater_than(name):
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()

    if    type(x) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float] \
       or type(y) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))
    if (x.has_uexpr_p() and not y.has_uexpr_p()) or \
       (y.has_uexpr_p() and not x.has_uexpr_p()):
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_INCONSISTENT_UNITS, name)
    if x.has_uexpr_p() and y.has_uexpr_p():
        if not rpn.unit.units_conform(x.uexpr, y.uexpr):
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            throw(X_CONFORMABILITY, name)
        y = y.ubase_convert(name)
        x = x.ubase_convert(name)

    yval = float(y.value)
    xval = float(x.value)
    rpn.globl.param_stack.push(rpn.type.Integer(rpn.globl.bool_to_int(yval > xval)))


@defword(name='>=', args=2, print_x=rpn.globl.PX_PREDICATE, doc="""\
>=   ( y x -- flag )
Test if Y is greater than or equal to X.""")
def w_greater_than_or_equal(name):
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()

    if    type(x) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float] \
       or type(y) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))
    if (x.has_uexpr_p() and not y.has_uexpr_p()) or \
       (y.has_uexpr_p() and not x.has_uexpr_p()):
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_INCONSISTENT_UNITS, name)
    if x.has_uexpr_p() and y.has_uexpr_p():
        if not rpn.unit.units_conform(x.uexpr, y.uexpr):
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            throw(X_CONFORMABILITY, name)
        y = y.ubase_convert(name)
        x = x.ubase_convert(name)

    yval = float(y.value)
    xval = float(x.value)
    rpn.globl.param_stack.push(rpn.type.Integer(rpn.globl.bool_to_int(yval >= xval)))


@defword(name='>>', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
>>   ( i2 i1 -- i2 >> i1 )
Bitwise right shift.""")
def w_rightshift(name):
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer or type(y) is not rpn.type.Integer:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))

    if x.value < 0:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_ARG, name, "X (shift amount) must not be negative")

    rpn.globl.param_stack.push(rpn.type.Integer(y.value >> x.value))


@defword(name='>c', args=2, print_x=rpn.globl.PX_CONFIG, doc="""\
>c   ( y x -- (x,y) )
Construct a complex number from two reals.""")
def w_to_c(name):
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if    type(x) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float] \
       or type(y) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))
    rpn.globl.param_stack.push(rpn.type.Complex(float(x.value), float(y.value)))


@defword(name='>debug', args=1, str_args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
>debug   ( level -- )  [ "resource" -- ]
Set debug level for resource.""")
def w_to_debug(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    level = x.value
    if level < 0 or level > 9:
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_ARG, name, "Level {} out of range (0..9 expected)".format(level))
    resource = rpn.globl.string_stack.pop()
    # I really want to crash on an unrecognized resource,
    # so let set_debug_level() do that...
    # if not resource.value in rpn.debug.debug_levels:
    #     rpn.globl.param_stack.push(x)
    #     rpn.globl.string_stack.push(resource)
    #     throw(X_UNDEFINED_WORD, name, "Resource '{}' not recognized".format(resource.value))
    rpn.debug.set_debug_level(resource.value, level)


@defword(name='>disp', print_x=rpn.globl.PX_CONFIG, doc="""\
>disp   ( -- )
Push current display configuration.""")
def w_to_disp(name):            # pylint: disable=unused-argument
    d = rpn.util.DisplayConfig()
    d.style = rpn.globl.disp_stack.top().style
    d.prec = rpn.globl.disp_stack.top().prec
    rpn.globl.disp_stack.push(d)


@defword(name='>label', args=1, str_args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
>label   ( x -- x )  [ "label" -- ]
Set label of X.""")
def w_to_label(name):           # pylint: disable=unused-argument
    x = rpn.globl.param_stack.top()
    label = rpn.globl.string_stack.pop().value
    x.label = label


@defword(name='>r', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
>r   ( x -- )
Push X onto return stack.""")
def w_to_r(name):               # pylint: disable=unused-argument
    rpn.globl.return_stack.push(rpn.globl.param_stack.pop())


@defword(name='>unit', args=1, str_args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
>unit   ( x -- x )  [ "unit" -- ]
Set unit of X.""")
def w_to_unit(name):            # pylint: disable=unused-argument
    strobj = rpn.globl.string_stack.pop()
    ustr = strobj.value
    ue = rpn.unit.try_parsing(ustr)
    if ue is None:
        rpn.globl.string_stack.push(strobj)
        throw(X_INVALID_UNIT, name, ustr)
    rpn.globl.param_stack.top().uexpr = ue


if rpn.globl.have_module('numpy'):
    @defword(name='>v2', args=2, print_x=rpn.globl.PX_CONFIG, doc="""\
>v2   ( y x -- v )
Create a 2-vector from the stack.""")
    def to_v_2(name):
        x = rpn.globl.param_stack.pop()
        y = rpn.globl.param_stack.pop()
        if    type(x) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float, rpn.type.Complex] \
           or type(y) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float, rpn.type.Complex]:
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))
        l = rpn.util.List()
        l.append(y)
        l.append(x)
        v = rpn.type.Vector.from_rpn_List(l)
        rpn.globl.param_stack.push(v)


if rpn.globl.have_module('numpy'):
    @defword(name='>v3', args=3, print_x=rpn.globl.PX_CONFIG, doc="""\
>v3   ( z y x -- v )
Create a 3-vector from the stack.""")
    def to_v_3(name):
        x = rpn.globl.param_stack.pop()
        y = rpn.globl.param_stack.pop()
        z = rpn.globl.param_stack.pop()
        if    type(x) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float, rpn.type.Complex] \
           or type(y) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float, rpn.type.Complex] \
           or type(z) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float, rpn.type.Complex]:
            rpn.globl.param_stack.push(z)
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            throw(X_ARG_TYPE_MISMATCH, name, "({} {} {})".format(typename(z), typename(y), typename(x)))
        l = rpn.util.List()
        l.append(z)
        l.append(y)
        l.append(x)
        v = rpn.type.Vector.from_rpn_List(l)
        rpn.globl.param_stack.push(v)


@defword(name='?', print_x=rpn.globl.PX_IO, doc="""\
?[topic]
Display information on a variety of topics.""")
def w_info(name):               # pylint: disable=unused-argument
    print("""\
rpn is a general-purpose calculator and programming language
based loosely on Forth and Hewlett-Packard calculators.

The following topics provide additional information:
    ?datatypes
    ?variables""")


@defword(name='?datatypes', print_x=rpn.globl.PX_IO, hidden=True, doc="")
def w_info_datatypes(name):     # pylint: disable=unused-argument
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
- String        "This is a sample string"

Strings are placed on a separate string stack.""")


@defword(name='?dup', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
?dup   ( x -- x x | 0 )
Duplicate top stack element if non-zero.""")
def w_query_dup(name):
    x = rpn.globl.param_stack.top()
    if type(x) not in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational, rpn.type.Complex]:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    if not x.zerop():
        rpn.globl.eval_string("dup")


@defword(name='?key', print_x=rpn.globl.PX_IO, doc="""\
?key   ( -- key 1 | 0 | -1 )
Read keystroke with flag.  ?key does not block but returns a success/fail flag
to the stack.  ASCII code of keystroke will also be returned on success.
Keystroke WILL echo.  This works only on Unix/Linux.

EXAMPLE:
    : test?key
      doc:"Display dots until a key is pressed  ( -- key )"
      begin  ?key case
        -1 of cr ."I/O error" cr leave endof
         0 of ."." 0.02 sleep endof
         1 of cr ."Key: " .all leave endof
        otherwise cr ."Found garbage on stack" cr .s leave
      endcase again
    ;

See also: key""")
def w_query_key(name):     # pylint: disable=unused-argument
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
def w_info_variables(name):     # pylint: disable=unused-argument
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
^   ( y x -- y^x )
Exponentiation.""")
def w_caret(name):
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if    type(x) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float, rpn.type.Complex] \
       or type(y) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float, rpn.type.Complex]:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))

    try:
        r = pow(y.value, x.value)
    except OverflowError:
        rpn.globl.param_stack.push(x)
        throw(X_FP_RESULT_OO_RANGE, name)

    if type(r) is int:
        result = rpn.type.Integer(r)
    elif type(r) is float:
        result = rpn.type.Float(r)
    elif type(r) is complex:
        result = rpn.type.Complex.from_complex(r)
    else:
        raise FatalErr("pow() returned a strange type '{}'".format(type(r)))

    if x.has_uexpr_p():
        throw(X_INCONSISTENT_UNITS, name, "X cannot have unit expression")
    if y.has_uexpr_p():
        result.uexpr = rpn.unit.UPow(y.uexpr, x.value)
        if isinstance(result.uexpr, rpn.unit.UNull):
            result.uexpr = None

    rpn.globl.param_stack.push(result)


@defword(name='abort', print_x=rpn.globl.PX_CONTROL, doc="""\
abort   ( -- )
Abort execution and return to top level.

See also: abort", exit, leave""")
def w_abort(name):
    throw(X_ABORT, name)


@defword(name='abort"', print_x=rpn.globl.PX_CONTROL, doc="""\
abort"   ( flag -- )
Conditionally abort execution.  If flag is non-zero, abort execution,
print a message (up to the closing quotation mark), and return to top level.

See also: abort, exit, leave""")
def w_abort_quote(name):        # pylint: disable=unused-argument
    pass                        # Grammar rules handle this word


@defword(name='abs', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
abs   ( x -- |x| )
Absolute value.  For complex numbers, ABS return the modulus (as a float).""")
def w_abs(name):
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
            throw(X_ARG_TYPE_MISMATCH, name, "X cannot be an empty vector")
        sumsq = 0.0
        for val in x.value:
            sumsq += abs(val) ** 2
        r = rpn.globl.to_python_class(sumsq)
        t = type(r)
        if t is float:
            result = rpn.type.Float(math.sqrt(r))
        elif t is complex:
            result = rpn.type.Complex.from_complex(cmath.sqrt(r))
        else:
            raise FatalErr("{}: Cannot handle type {}".format(name, t))
    else:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='acos', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
acos   ( cosine -- angle )
Inverse cosine.  |x| <= 1""")
def w_acos(name):
    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        try:
            r = math.acos(float(x.value))
        except ValueError:
            rpn.globl.param_stack.push(x)
            throw(X_FP_INVALID_ARG, name)
        result = rpn.type.Float(rpn.globl.convert_radians_to_mode(r))
        result.uexpr = rpn.globl.uexpr[rpn.globl.angle_mode_letter()]
    elif type(x) is rpn.type.Complex:
        try:
            r = cmath.acos(x.value)
        except ValueError:
            rpn.globl.param_stack.push(x)
            throw(X_FP_INVALID_ARG, name)
        result = rpn.type.Complex.from_complex(r)
    else:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='acosh', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
acosh   ( cosine_h -- angle )
Inverse hyperbolic cosine.

DEFINITION:
acosh(x) = ln(x + sqrt(x^2 - 1)), x >= 1""")
def w_acosh(name):
    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        try:
            r = math.acosh(float(x.value))
        except ValueError:
            rpn.globl.param_stack.push(x)
            throw(X_FP_INVALID_ARG, name)
        result = rpn.type.Float(r)
    elif type(x) is rpn.type.Complex:
        try:
            r = cmath.acosh(x.value)
        except ValueError:
            rpn.globl.param_stack.push(x)
            throw(X_FP_INVALID_ARG, name)
        result = rpn.type.Complex.from_complex(r)
    else:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='again', print_x=rpn.globl.PX_CONTROL, doc="""\
again   ( -- )
Execute an indefinite loop forever.
begin ... again

leave will exit the loop early.

See also: begin, leave, repeat, until, while""")
def w_again(name):              # pylint: disable=unused-argument
    pass                        # Grammar rules handle this word


@defword(name='alog', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
alog   ( x -- 10^x )
Common exponential (antilogarithm).""")
def w_alog(name):
    x = rpn.globl.param_stack.pop()
    if type(x) not in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational, rpn.type.Complex]:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    r = 10.0 ** x.value
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        result = rpn.type.Float(r)
    elif type(x) is rpn.type.Complex:
        result = rpn.type.Complex.from_complex(r)
    rpn.globl.param_stack.push(result)


@defword(name='and', args=2, print_x=rpn.globl.PX_PREDICATE, doc="""\
and   ( flag flag -- flag )
Logical AND.  This is not a bitwise AND - use bitand for that.""")
def w_logand(name):
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer or type(y) is not rpn.type.Integer:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))

    rpn.globl.param_stack.push(rpn.type.Integer(bool(x.value) and bool(y.value)))


@defword(name='ascii', immediate=True, doc="""\
ascii   ( -- n )
ASCII code of following char.  Returns -1 on any sort of error.""")
def w_ascii(name):              # pylint: disable=unused-argument
    pass


@defword(name='asin', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
asin   ( sine -- angle )
Inverse sine.  |x| <= 1""")
def w_asin(name):
    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        try:
            r = math.asin(float(x.value))
        except ValueError:
            rpn.globl.param_stack.push(x)
            throw(X_FP_INVALID_ARG, name)
        result = rpn.type.Float(rpn.globl.convert_radians_to_mode(r))
        result.uexpr = rpn.globl.uexpr[rpn.globl.angle_mode_letter()]
    elif type(x) is rpn.type.Complex:
        try:
            r = cmath.asin(x.value)
        except ValueError:
            rpn.globl.param_stack.push(x)
            throw(X_FP_INVALID_ARG, name)
        result = rpn.type.Complex.from_complex(r)
    else:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='asinh', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
asinh   ( sine_h -- angle )
Inverse hyperbolic sine.

DEFINITION:
asinh(x) = ln(x + sqrt(x^2 + 1))""")
def w_asinh(name):
    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        try:
            r = math.asinh(float(x.value))
        except ValueError:
            rpn.globl.param_stack.push(x)
            throw(X_FP_INVALID_ARG, name)
        result = rpn.type.Float(r)
    elif type(x) is rpn.type.Complex:
        try:
            r = cmath.asinh(x.value)
        except ValueError:
            rpn.globl.param_stack.push(x)
            throw(X_FP_INVALID_ARG, name)
        result = rpn.type.Complex.from_complex(r)
    else:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='atan', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
atan   ( tangent -- angle )
Inverse tangent.  Consider using atan2 instead,
especially if you are computing atan(y/x).""")
def w_atan(name):
    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        try:
            r = math.atan(float(x.value))
        except ValueError:
            rpn.globl.param_stack.push(x)
            throw(X_FP_INVALID_ARG, name)
        result = rpn.type.Float(rpn.globl.convert_radians_to_mode(r))
        result.uexpr = rpn.globl.uexpr[rpn.globl.angle_mode_letter()]
    elif type(x) is rpn.type.Complex:
        try:
            r = cmath.atan(x.value)
        except ValueError:
            rpn.globl.param_stack.push(x)
            throw(X_FP_INVALID_ARG, name)
        result = rpn.type.Complex.from_complex(r)
    else:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='atan2', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
atan2   ( y x -- angle )
Inverse tangent of y/x.""")
def w_atan2(name):
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        try:
            r = math.atan2(float(y.value), float(x.value))
        except ValueError:
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            throw(X_FP_INVALID_ARG, name)
        result = rpn.type.Float(rpn.globl.convert_radians_to_mode(r))
        result.uexpr = rpn.globl.uexpr[rpn.globl.angle_mode_letter()]
    elif type(x) is rpn.type.Complex:
        # Python cmath doesn't have atan2, so fake it
        if x.zerop():
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            throw(X_FP_INVALID_ARG, name)
        r = cmath.atan(y / x)
        result = rpn.type.Complex.from_complex(r)
    else:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='atanh', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
atanh   ( tangent_h -- angle )
Inverse hyperbolic tangent.

DEFINITION:
atanh(x) = 1/2 ln((1+x) / (1-x)), |x| < 1""")
def w_atanh(name):
    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        try:
            r = math.atanh(float(x.value))
        except ValueError:
            rpn.globl.param_stack.push(x)
            throw(X_FP_INVALID_ARG, name)
        result = rpn.type.Float(r)
    elif type(x) is rpn.type.Complex:
        try:
            r = cmath.atanh(x.value)
        except ValueError:
            rpn.globl.param_stack.push(x)
            throw(X_FP_INVALID_ARG, name)
        result = rpn.type.Complex.from_complex(r)
    else:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='begin', print_x=rpn.globl.PX_CONTROL, doc="""\
begin   ( -- )
Execute an indefinite loop.
begin ... again
begin ... <flag> until
begin ... <flag> while ... repeat

leave will exit the loop early.  Note that the effect of the test in
begin...while is opposite that in begin...until (i.e., the loop repeats
while something is true, rather than until it becomes true.)

Do not confuse this with the "beg" command, which sets 'begin mode' for
Time Value of Money calculations.

See also: again, leave, repeat, until, while""")
def w_begin(name):              # pylint: disable=unused-argument
    pass                        # Grammar rules handle this word


@defword(name='binom', args=3, print_x=rpn.globl.PX_COMPUTE, doc="""\
binom   ( n k p -- prob )
Binomial probability.  Return the probability of an event occurring exactly
k times in n attempts, where the probability of it occurring in a single
attempt is p.

DEFINITION:
binom(n,k,p) = comb(n,k) * p^k * (1-p)^(n-k)""")
def w_binom(name):
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    z = rpn.globl.param_stack.pop()
    if    type(x) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float] \
       or type(y) is not rpn.type.Integer \
       or type(z) is not rpn.type.Integer:
        rpn.globl.param_stack.push(z)
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({} {} {})".format(typename(z), typename(y), typename(x)))
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
bitand   ( i2 i1 -- i2 AND i1 )
Bitwise AND.  Perform a bitwise boolean AND on two integers.""")
def w_bitand(name):
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer or type(y) is not rpn.type.Integer:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))

    rpn.globl.param_stack.push(rpn.type.Integer(y.value & x.value))


@defword(name='bitnot', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
bitnot   ( i1 -- NOT i1 )
Bitwise NOT.  Perform a bitwise boolean NOT on an integer.""")
def w_bitnot(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))

    rpn.globl.param_stack.push(rpn.type.Integer(~ x.value))


@defword(name='bitor', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
bitor   ( i2 i1 -- i2 OR i1 )
Bitwise OR.  Perform a bitwise boolean OR on two integers.""")
def w_bitor(name):
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer or type(y) is not rpn.type.Integer:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))

    rpn.globl.param_stack.push(rpn.type.Integer(y.value | x.value))


@defword(name='bitxor', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
bitxor   ( i2 i1 -- i2 XOR i1 )

Bitwise XOR.  Perform a bitwise boolean Exclusive OR on two integers.""")
def w_bitxor(name):
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer or type(y) is not rpn.type.Integer:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))

    rpn.globl.param_stack.push(rpn.type.Integer(y.value ^ x.value))


@defword(name='bye', print_x=rpn.globl.PX_CONTROL, doc="""\
bye   ( -- )
Exit rpn.""")
def w_bye(name):
    raise EndProgram()


@defword(name='c>', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
c>   ( c -- y x )
Extract imaginary and real parts of a complex number.""")
def w_c_from(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Complex:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    rpn.globl.param_stack.push(rpn.type.Float(x.imag()))
    rpn.globl.param_stack.push(rpn.type.Float(x.real()))


@defword(name='case', print_x=rpn.globl.PX_CONTROL, doc="""\
case   ( n -- )
Execute a sequence of words based on stack value.  Once a match is
executed, no other clauses are considered.  otherwise is optional.
<n> and of labels must be integers.  case consumes the top of stack
like any word; however the integer value is available to the sequence
in variable "caseval".

<n> case
  <x> of ... endof
  <y> of ... endof
  <z> of ... endof
  [ otherwise ... ]
endcase

See also: endcase, endof, of, otherwise""")
def w_case(name):               # pylint: disable=unused-argument
    pass                        # Grammar rules handle this word


@defword(name='catch', print_x=rpn.globl.PX_CONTROL, doc="""\
catch   ( -- )
Catch any exceptions.
catch <WORD>

See also: throw""")
def w_catch(name):              # pylint: disable=unused-argument
    pass                        # Grammar rules handle this word


@defword(name='ceil', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
ceil   ( x -- ceil )
Ceiling: smallest integer greater than or equal to X.""")
def w_ceil(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is rpn.type.Integer:
        result = x
    elif type(x) in [rpn.type.Float, rpn.type.Rational]:
        result = rpn.type.Integer(math.ceil(x.value))
    else:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='cf', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
cf   ( f -- )
Clear flag.  Do not confuse this with CF, which is for Compounding Frequency.""")
def w_cf(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    flag = x.value
    if flag < 0 or flag >= rpn.flag.MAX:
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_MEMORY, name, "Flag {} out of range (0..{} expected)".format(flag, rpn.flag.MAX - 1))
    if flag >= rpn.flag.FENCE:
        rpn.globl.param_stack.push(x)
        throw(X_READ_ONLY, name, "Flag {} cannot be modified".format(flag))
    rpn.flag.clear_flag(flag)


@defword(name='chr', args=1, print_x=rpn.globl.PX_IO, doc="""\
chr   ( x -- )
Push string for a single ASCII character.""")
def w_chr(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    rpn.globl.string_stack.push(rpn.type.String("{}".format(chr(x.value))))


# Some HP calcs call this NEGATE, but why type 6 characters when 3 will do?
@defword(name='chs', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
chs   ( x -- -x )
Negation (change sign).""")
def w_chs(name):
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
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='clfin', print_x=rpn.globl.PX_CONFIG, doc="""\
clfin   ( -- )
Clear financial variables.""")
def w_clfin(name):              # pylint: disable=unused-argument
    rpn.flag.clear_flag(rpn.flag.F_TVM_CONTINUOUS)
    rpn.flag.clear_flag(rpn.flag.F_TVM_BEGIN_MODE)

    rpn.tvm.N.obj   = None
    rpn.tvm.INT.obj = None
    rpn.tvm.PV.obj  = None
    rpn.tvm.PMT.obj = None
    rpn.tvm.FV.obj  = None

    rpn.globl.param_stack.push(rpn.type.Integer(1))
    rpn.word.w_cpf('CPF')


@defword(name='clflag', print_x=rpn.globl.PX_CONFIG, doc="""\
clflag   ( -- )
Clear all flags.""")
def w_clflag(name):             # pylint: disable=unused-argument
    for i in range(rpn.flag.FENCE):
        rpn.flag.clear_flag(i)


@defword(name='clreg', print_x=rpn.globl.PX_CONFIG, doc="""]
clreg   ( -- )
Clear all registers.""")
def w_clreg(name):              # pylint: disable=unused-argument
    rpn.globl.register = dict()
    for i in range(rpn.globl.REG_SIZE_MAX):
        rpn.globl.register[i] = rpn.type.Float(0.0)
    rpn.globl.register['I'] = rpn.type.Float(0.0)


@defword(name='clrst', print_x=rpn.globl.PX_CONFIG, doc="""\
clrst   ( -- )
Clear the return stack.  Do not confuse this with the clst command,
which clears the parameter stack.""")
def w_clrst(name):              # pylint: disable=unused-argument
    rpn.globl.return_stack.clear()


@defword(name='clstat', print_x=rpn.globl.PX_CONFIG, doc="""\
clstat   ( -- )
Clear the statistics array.""")
def w_clstat(name):             # pylint: disable=unused-argument
    rpn.globl.stat_data = []


@defword(name='clst', print_x=rpn.globl.PX_CONFIG, doc="""\
clst   ( -- )
Clear the stack.  Do not confuse this with the clrst command,
which clears the return stack.

DEFINITION:
: clst  depth 0 do drop loop ;""")
def w_clst(name):               # pylint: disable=unused-argument
    rpn.globl.param_stack.clear()


@defword(name='comb', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
comb   ( n r -- nCr )
Combinations.  Choose from N objects R at a time, without regard to ordering.

DEFINITION:
          n!
nCr = -----------
      r! * (n-r)!""")
def w_comb(name):
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer or type(y) is not rpn.type.Integer:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))

    # Python 3.8 has math.comb()
    n = y.value
    r = x.value
    result = rpn.type.Integer(comb_helper(n, r))

    rpn.globl.param_stack.push(result)


@defword(name='constant', print_x=rpn.globl.PX_CONFIG, doc="""\
constant   ( n -- )
Declare a constant variable.
CONSTANT <ccc>""")
def w_constant(name):           # pylint: disable=unused-argument
    pass                        # Grammar rules handle this word


@defword(name='convert', args=1, str_args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
convert   ( x -- x' )  [ units -- ]
Convert units of X to those in string.""")
def w_convert(name):
    x = rpn.globl.param_stack.pop()
    if not x.has_uexpr_p():
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_ARG, name, "Not a unit")

    dbg("unit", 2, "{}: orig X={}".format(name, repr(x)))
    s = rpn.globl.string_stack.pop()
    new_ustr = s.value
    try:
        new_x = x.uexpr_convert(new_ustr, name)
    except RuntimeErr as e:
        if e.code == X_INVALID_UNIT:
            rpn.globl.param_stack.push(x)
            rpn.globl.string_stack.push(s)
            throw(X_INVALID_UNIT, name, new_ustr)
        else:
            raise
    dbg("unit", 2, "{}: new X={}".format(name, repr(new_x)))
    rpn.globl.param_stack.push(new_x)


@defword(name='cos', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
cos   ( angle -- cosine )
Cosine.""")
def w_cos(name):
    x = rpn.globl.param_stack.pop()
    if type(x) not in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational, rpn.type.Complex]:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))

    unit_attached = False
    if x.has_uexpr_p() and x.uexpr.dim() != rpn.unit.category["Null"].dim():
        if x.uexpr.dim() != rpn.unit.category["Angle"].dim():
            rpn.globl.param_stack.push(x)
            throw(X_INCONSISTENT_UNITS, name, "'{}' is not an angular unit".format(x.uexpr))
        unit_attached = True

    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        if unit_attached:
            angle = x.ubase_convert(name) # convert to radians
            result = rpn.type.Float(math.cos(float(angle.value)))
        else:
            result = rpn.type.Float(math.cos(rpn.globl.convert_mode_to_radians(float(x.value))))
    elif type(x) is rpn.type.Complex:
        result = rpn.type.Complex.from_complex(cmath.cos(x.value))

    rpn.globl.param_stack.push(result)


@defword(name='cosh', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
cosh   ( angle -- cosine_h )
Hyperbolic cosine.

DEFINITION:
          e^x + e^(-x)
cosh(x) = ------------
               2""")
def w_cosh(name):
    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        result = rpn.type.Float(math.cosh(float(x.value)))
    elif type(x) is rpn.type.Complex:
        result = rpn.type.Complex.from_complex(cmath.cosh(x.value))
    else:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='CPF', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
CPF   ( n -- )
Set CF and PF to N.""")
def w_cpf(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    n = x.value
    if n < 1 or n > 365:
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_ARG, name, "(1..365 expected)")

    cf = rpn.type.Integer(n)
    cf.label = "CF"
    rpn.tvm.CF.obj = cf

    pf = rpn.type.Integer(n)
    pf.label = "PF"
    rpn.tvm.PF.obj = pf


@defword(name='cr', print_x=rpn.globl.PX_IO, doc="""\
cr   ( -- )
Print a newline.""")
def w_cr(name):                 # pylint: disable=unused-argument
    rpn.globl.writeln()


if rpn.globl.have_module('numpy'):
    @defword(name='cross', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
cross   ( vec_y vec_x -- vec )
Vector dot product.""")
    def cross_prod(name):
        x = rpn.globl.param_stack.pop()
        y = rpn.globl.param_stack.pop()
        if type(x) is rpn.type.Vector and type(y) is rpn.type.Vector:
            try:
                r = np.cross(y.value, x.value)
                dbg(name, 3, "r={}, type(r)={}, r.dtype={}, r.shape={}, r.ndim={}" \
                                 .format(r, type(r), r.dtype, r.shape, r.ndim))
            except ValueError as e:
                rpn.globl.param_stack.push(y)
                rpn.globl.param_stack.push(x)
                throw(X_CONFORMABILITY, name, "Vectors are not conformable") # XXX is this message correct?

            result = rpn.globl.to_rpn_class(r)
            dbg(name, 2, "result={}, type(result)={}".format(result, type(result)))
        else:
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))

        rpn.globl.param_stack.push(result)


def w_sum3(y):
    return int(y * 365.25) - int(y / 100) + int(y / 400)

def w_m306(m):
    return int(m * 30.6001)

@defword(name='d->hp', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
d->hp   ( MM.DDYYYY -- day# )
Convert date to HP day number.  Day # 0 = October 15, 1582.""")
def w_d_to_hp(name):
    day0_julian = 2299160
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Float:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))

    (valid, dateobj, julian) = x.date_info()
    if not valid:
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_ARG, name, "{} is not a valid date".format(x.value))

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
d->jd   ( MM.DDYYYY -- julian )
Convert date to Julian day number.""")
def w_d_to_jd(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Float:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))

    (valid, _, julian) = x.date_info() # middle value is dateobj
    if not valid:
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_ARG, name, "{} is not a valid date".format(x.value))

    result = rpn.type.Integer(julian)
    result.label = "Julian day"
    rpn.globl.param_stack.push(result)


@defword(name='d->r', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
d->r   ( deg -- rad )
Convert degrees to radians.  This will actually convert any angle measure
to radians, not just degrees.""")
def w_d_to_r(name):
    x = rpn.globl.param_stack.pop()
    if type(x) not in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))

    if x.has_uexpr_p() and x.uexpr.dim() != rpn.unit.category["Null"].dim():
        if x.uexpr.dim() != rpn.unit.category["Angle"].dim():
            rpn.globl.param_stack.push(x)
            throw(X_INCONSISTENT_UNITS, name, "'{}' is not an angular unit".format(x.uexpr))
        result = x.ubase_convert(name) # convert to radians
    else:
        result = rpn.type.Float(rpn.globl.convert_mode_to_radians(float(x.value)))

    result.uexpr = rpn.globl.uexpr["r"]
    rpn.globl.param_stack.push(result)


@defword(name='date', print_x=rpn.globl.PX_COMPUTE, doc="""\
date   ( -- MM.DDYYYY )
Current date.""")
def w_date(name):               # pylint: disable=unused-argument
    d = datetime.date.today().strftime("%m.%d%Y")
    result = rpn.type.Float(d)
    result.label = "MM.DDYYYY (Current)"
    rpn.globl.param_stack.push(result)


@defword(name='dateinfo', args=1, hidden=True, print_x=rpn.globl.PX_IO, doc="""\
dateinfo   ( x -- )
Show date_info() for Float.""")
def w_dateinfo(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Float:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    rpn.globl.writeln("dateinfo: {}".format(x.date_info()))


@defword(name='date+', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
date+   ( date1 N -- date2 )
Add N days to date.""")
def w_date_plus(name):
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer or type(y) is not rpn.type.Float:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))

    (valid, dateobj, julian) = y.date_info()
    if not valid:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_ARG, name, "{} is not a valid date".format(y.value))

    new_julian = julian + x.value
    dateobj = datetime.date.fromordinal(new_julian - rpn.globl.JULIAN_OFFSET)
    result = rpn.type.Float("%d.%02d%04d" % (dateobj.month, dateobj.day, dateobj.year))
    result.label = "DD.MMYYYY"
    rpn.globl.param_stack.push(result)


@defword(name='date-', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
date-   ( date1 N -- date2 )
Subtract N days from date.""")
def w_date_minus(name):
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer or type(y) is not rpn.type.Float:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))

    (valid, dateobj, julian) = y.date_info()
    if not valid:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_ARG, name, "{} is not a valid date".format(y.value))

    new_julian = julian - x.value
    dateobj = datetime.date.fromordinal(new_julian - rpn.globl.JULIAN_OFFSET)
    result = rpn.type.Float("%d.%02d%04d" % (dateobj.month, dateobj.day, dateobj.year))
    result.label = "DD.MMYYYY"
    rpn.globl.param_stack.push(result)


@defword(name='ddays', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
ddays   ( date1 date2 -- ddays )
Number of days between two dates.  Usually the earlier date is in Y,
and later date in X.""")
def w_ddays(name):
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Float or type(y) is not rpn.type.Float:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))

    (valid, _, xjulian) = x.date_info() # middle value is dateobj
    if not valid:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_ARG, name, "{} is not a valid date".format(x.value))

    (valid, _, yjulian) = y.date_info() # middle value is dateobj
    if not valid:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_ARG, name, "{} is not a valid date".format(y.value))

    # Y is expected to be earlier, so we subtract in this order to get a
    # positive value for "later"
    result = rpn.type.Integer(xjulian - yjulian)
    result.label = "Delta days"
    rpn.globl.param_stack.push(rpn.type.Integer(xjulian - yjulian))


@defword(name='debug>', str_args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
debug>   ( -- lev )  [ "resource" -- ]
Return debug level for resource.""")
def w_debug_from(name):
    resource = rpn.globl.string_stack.pop()
    if not resource.value in rpn.debug.debug_levels:
        rpn.globl.string_stack.push(resource)
        throw(X_UNDEFINED_WORD, name, "Resource '{}' not recognized".format(resource.value))
    rpn.globl.param_stack.push(rpn.type.Integer(rpn.debug.debug_levels[resource.value]))


@defword(name='DEG', print_x=rpn.globl.PX_COMPUTE, doc="""\
DEG   ( -- 57.29577... )
Degrees per radian.  Do not confuse this with deg, which sets
the angular mode to degrees.

DEFINITION:
DEG == 360/TAU == 180/PI""")
def w_DEG(name):                # pylint: disable=unused-argument
    result = rpn.type.Float(rpn.globl.DEG_PER_RAD)
    result.uexpr = rpn.globl.uexpr["deg/r"]
    rpn.globl.param_stack.push(result)


@defword(name='deg', print_x=rpn.globl.PX_CONFIG, doc="""\
deg   ( -- )
Set angular mode to degrees.  Do not confuse this with DEG,
which is the number of degrees per radian.""")
def w_deg(name):                # pylint: disable=unused-argument
    rpn.flag.clear_flag(rpn.flag.F_RAD)
    rpn.flag.clear_flag(rpn.flag.F_GRAD)


@defword(name='depth', print_x=rpn.globl.PX_COMPUTE, doc="""\
depth   ( -- n )
Current number of elements on stack.""")
def w_depth(name):              # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(rpn.globl.param_stack.size()))


@defword(name='dim', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
dim   ( -- )
Dimension(s) of X.

For integers, floats, and rationals (scalars): return 0.
For complex numbers: return 2.
For vectors of length N: return a vector [N].
For an M-row by N-col matrix: return a vector [M N].""")
def w_dim(name):
    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        result = rpn.type.Integer(0)
    elif type(x) is rpn.type.Complex:
        result = rpn.type.Integer(2)
    elif type(x) is rpn.type.Vector:
        result = rpn.type.Vector.from_rpn_List(rpn.util.List(rpn.type.Integer(x.size())))
    elif type(x) is rpn.type.Matrix:
        # Pretty ugly.  Need a better method to append items.  Ugh,
        # things get added at the beginning of the list, so we have to
        # add the cols, THEN the rows in order to end up with
        # [ rows cols ].
        l = rpn.util.List(rpn.type.Integer(x.ncols()))
        l2 = rpn.util.List(rpn.type.Integer(x.nrows()), l)
        result = rpn.type.Vector.from_rpn_List(l2) # [ rows cols ]
    else:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='disp>', print_x=rpn.globl.PX_CONFIG, doc="""\
disp>   ( -- )
Pop current display configuration.""")
def w_disp_from(name):          # pylint: disable=unused-argument
    try:
        rpn.globl.disp_stack.pop()
    except RuntimeErr as e:
        if e.code == X_STACK_UNDERFLOW:
            throw(X_STACK_UNDERFLOW, name, "{} has no display configuration".format(rpn.globl.disp_stack.name()))
        else:
            raise


@defword(name='do', print_x=rpn.globl.PX_CONTROL, doc="""\
do   ( limit initial -- )
Execute a definite loop.
<limit> <initial> do ...        loop
<limit> <initial> do ... <incr> +loop

The iteration counter is available via I.  leave will exit the loop early.

EXAMPLE:
    10 0 do I . loop
0 1 2 3 4 5 6 7 8 9

See also: I, leave, loop, +loop""")
def w_do(name):                 # pylint: disable=unused-argument
    pass                        # Grammar rules handle this word


if rpn.globl.have_module('numpy'):
    @defword(name='dot', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
dot   ( vec_y vec_x -- real )
Vector dot product.""")
    def dot_prod(name):
        x = rpn.globl.param_stack.pop()
        y = rpn.globl.param_stack.pop()
        if type(x) is rpn.type.Vector and type(y) is rpn.type.Vector:
            try:
                r = y.value.dot(x.value)
            except ValueError:
                rpn.globl.param_stack.push(y)
                rpn.globl.param_stack.push(x)
                throw(X_CONFORMABILITY, name, "Vectors are not same size")

            result = rpn.globl.to_rpn_class(r)
        else:
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))

        rpn.globl.param_stack.push(result)


@defword(name='dow', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
dow   ( MM.DDYYYY -- dow )
Day of week.  1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat, 7=Sun.""")
def w_dow(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Float:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))

    (valid, dateobj, _) = x.date_info() # third value is julian
    if not valid:
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_ARG, name, "{} is not a valid date".format(x.value))

    result = rpn.type.Integer(dateobj.isoweekday())
    result.label = "Day of week"
    rpn.globl.param_stack.push(result)


@defword(name='dow$', args=1, print_x=rpn.globl.PX_IO, doc="""\
dow$   ( dow -- )  [ -- abbrev ]
Day of week name.  Return abbreviated day of week name as string.
dow should be between 1 and 7.

See also: dow""")
def w_dow_dollar(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    dow = x.value
    if dow < 1 or dow > 7:
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_ARG, name, "Day of week out of range (1..7 expected)")
    dow_abbrev = { 1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu",
                   5: "Fri", 6: "Sat", 7: "Sun" }
    rpn.globl.string_stack.push(rpn.type.String.from_string(dow_abbrev[dow]))


@defword(name='drop', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
drop   ( x -- )
Remove top stack element.""")
def w_drop(name):               # pylint: disable=unused-argument
    rpn.globl.param_stack.pop()


@defword(name='E', print_x=rpn.globl.PX_COMPUTE, doc="""\
E   ( -- 2.71828... )
Base of natural logarithms.""")
def w_E(name):                  # pylint: disable=unused-argument
    result = rpn.type.Float(rpn.globl.E)
    result.label = "E"
    rpn.globl.param_stack.push(result)


@defword(name='edit', hidden=True, print_x=rpn.globl.PX_CONFIG, doc="""\
edit   ( -- )
Edit some text.""")
def w_edit(name):               # pylint: disable=unused-argument
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
expm1   ( x -- (e^x)-1 )
Calculate (e^X)-1 accurately.""")
def w_e_x_minus_1(name):
    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        result = rpn.type.Float(math.expm1(x.value))
    elif type(x) is rpn.type.Complex:
        result = rpn.type.Complex.from_complex(cmath.exp(x.value) - 1.0)
    else:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='else', args=1, print_x=rpn.globl.PX_CONTROL, doc="""\
else   ( -- )
Execute other branch of conditional test.
<flag> if ... [ else ... ] then

See also: if, then""")
def w_else(name):               # pylint: disable=unused-argument
    pass                        # Grammar rules handle this word


@defword(name='emit', args=1, print_x=rpn.globl.PX_IO, doc="""\
emit   ( x -- )
Print a single ASCII character.  No space or newline is appended.""")
def w_emit(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    rpn.globl.write(chr(x.value))


@defword(name='endcase', print_x=rpn.globl.PX_CONTROL, doc="""\
endcase   ( -- )
Execute a sequence of words based on stack value.  Once a match is
executed, no other clauses are considered.  otherwise is optional.
<n> and of labels must be integers.

<n> case
  <x> of ... endof
  <y> of ... endof
  <z> of ... endof
  [ otherwise ... ]
endcase

See also: case, endof, of, otherwise""")
def w_endcase(name):            # pylint: disable=unused-argument
    pass                        # Grammar rules handle this word


@defword(name='endof', print_x=rpn.globl.PX_CONTROL, doc="""\
endof   ( -- )
Execute a sequence of words based on stack value.  Once a match is
executed, no other clauses are considered.  otherwise is optional.
<n> and OF labels must be integers.

<n> case
  <x> of ... endof
  <y> of ... endof
  <z> of ... endof
  [ otherwise ... ]
endcase

See also: case, endcase, of, otherwise""")
def w_endof(name):              # pylint: disable=unused-argument
    pass                        # Grammar rules handle this word


@defword(name='eng', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
eng   ( n -- )
Set engineering display.  N specifies the total number of significant digits.""")
def w_eng(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))

    if x.value < 0 or x.value >= rpn.globl.PRECISION_MAX:
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_ARG, name, "Precision '{}' out of range (0..{} expected)".format(x.value, rpn.globl.PRECISION_MAX - 1))

    rpn.globl.disp_stack.top().style = "eng"
    rpn.globl.disp_stack.top().prec = x.value
    rpn.flag.clear_flag(rpn.flag.F_DISP_FIX)
    rpn.flag.set_flag(rpn.flag.F_DISP_ENG)


@defword(name='epoch', print_x=rpn.globl.PX_COMPUTE, doc="""\
epoch   ( -- secs )
Seconds since epoch.""")
def w_epoch(name):              # pylint: disable=unused-argument
    now = calendar.timegm(time.gmtime())
    result = rpn.type.Integer(now)
    result.label = "Epoch"
    rpn.globl.param_stack.push(result)


@defword(name='erf', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
erf   ( x -- erf[x] )
Error function.""")
def w_erf(name):
    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        try:
            r = math.erf(float(x.value))
        except ValueError:
            rpn.globl.param_stack.push(x)
            throw(X_FP_INVALID_ARG, name)
        result = rpn.type.Float(r)
    elif type(x) is rpn.type.Complex:
        if not rpn.globl.have_module('scipy'):
            rpn.globl.param_stack.push(x)
            throw(X_UNSUPPORTED, name, "Complex support requires 'scipy' library")
        r = scipy.special.erf(x.value)
        result = rpn.type.Complex.from_complex(r)
    else:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    result.label = "erf"
    rpn.globl.param_stack.push(result)


@defword(name='erfc', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
erfc   ( x -- erfc[x] )
Complementary error function.

DEFINITION:
erfc(x) = 1 - erf(x)""")
def w_erfc(name):
    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        try:
            r = math.erfc(float(x.value))
        except ValueError:
            rpn.globl.param_stack.push(x)
            throw(X_FP_INVALID_ARG, name)
        result = rpn.type.Float(r)
    elif type(x) is rpn.type.Complex:
        if not rpn.globl.have_module('scipy'):
            rpn.globl.param_stack.push(x)
            throw(X_UNSUPPORTED, name, "Complex support requires 'scipy' library")
        r = scipy.special.erfc(x.value)
        result = rpn.type.Complex.from_complex(r)
    else:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    result.label = "erfc"
    rpn.globl.param_stack.push(result)


@defword(name='eval', str_args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
eval   [ s --- ]
Evaluate top element of string stack.
If s is a String created with "xxxx", evaluate it as a string of commands.
If x is a Symbol created with 'word', evaluate it as a closure invoking word.""")
def w_eval(name):               # pylint: disable=unused-argument
    s = rpn.globl.string_stack.pop()
    if type(s) is rpn.type.String:
        rpn.globl.eval_string(s.value)
    elif type(s) is rpn.type.Symbol:
        s.eval()
    else:
        rpn.globl.string_stack.push(s)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(s)))


@defword(name='exit', print_x=rpn.globl.PX_CONTROL, doc="""\
exit   ( -- )
Terminate execution of current word.""")
def w_exit(name):               # pylint: disable=unused-argument
    throw(X_EXIT)


@defword(name='exp', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
exp   ( x -- e^x )
Natural exponential.""")
def w_exp(name):
    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        try:
            r = math.exp(float(x.value))
        except OverflowError:
            rpn.globl.param_stack.push(x)
            throw(X_FP_RESULT_OO_RANGE, name)
        result = rpn.type.Float(r)
    elif type(x) is rpn.type.Complex:
        try:
            r = cmath.exp(complex(x.value))
        except OverflowError:
            rpn.globl.param_stack.push(x)
            throw(X_FP_RESULT_OO_RANGE, name)
        result = rpn.type.Complex.from_complex(r)
    else:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='F_DEBUG_ENABLED', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
F_DEBUG_ENABLED   ( -- 20 )
Flag number for Debug enabled.""")
def w_F_DEBUG_ENABLED(name):    # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(rpn.flag.F_DEBUG_ENABLED))


@defword(name='F_GRAD', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
F_GRAD   ( -- 42 )
Flag number for Gradians mode.""")
def w_F_GRAD(name):             # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(rpn.flag.F_GRAD))


@defword(name='F_PRINTER_ENABLED', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
F_PRINTER_ENABLED   ( -- 21 )
Flag number for Printer enabled.""")
def w_F_PRINTER_ENABLED(name):  # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(rpn.flag.F_PRINTER_ENABLED))


@defword(name='F_PRINTER_EXISTS', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
F_PRINTER_EXISTS   ( -- 55 )
Flag number for Printer exists.""")
def w_F_PRINTER_EXISTS(name):   # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(rpn.flag.F_PRINTER_EXISTS))


@defword(name='F_RAD', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
F_RAD   ( -- 43 )
Flag number for Radians mode.""")
def w_F_RAD(name):              # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(rpn.flag.F_RAD))


@defword(name='F_SHOW_PROMPT', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
F_SHOW_PROMPT   ( -- 18 )
Flag number for Show Prompt.""")
def w_F_SHOW_PROMPT(name):           # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(rpn.flag.F_SHOW_PROMPT))


@defword(name='F_SHOW_X', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
F_SHOW_X   ( -- 19 )
Flag number for Show X.""")
def w_F_SHOW_X(name):           # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(rpn.flag.F_SHOW_X))


@defword(name='F_TVM_BEGIN_MODE', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
F_TVM_BEGIN_MODE   ( -- 9 )
Flag number for TVM Begin mode.""")
def w_F_TVM_BEGIN_MODE(name):   # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(rpn.flag.F_TVM_BEGIN_MODE))


@defword(name='F_TVM_CONTINUOUS', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
F_TVM_CONTINUOUS   ( -- 8 )
Flag number for TVM Continuous mode.""")
def w_F_TVM_CONTINUOUS(name):   # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(rpn.flag.F_TVM_CONTINUOUS))


@defword(name='fact', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
fact   ( x -- x! )
Factorial.  X cannot be negative.

DEFINITION:
x! = x * (x-1) * (x-2) ... * 2 * 1
0! = 1

See also: gamma""")
def w_fact(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    if x.value < 0:
        rpn.globl.param_stack.push(x)
        throw(X_FP_INVALID_ARG, name, "X cannot be negative")
    result = rpn.type.Integer(fact_helper(x.value))
    rpn.globl.param_stack.push(result)


@defword(name='fc?', args=1, print_x=rpn.globl.PX_PREDICATE, doc="""\
fc?   ( -- bool )
Test if flag is clear.""")
def w_fc_query(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))

    flag = x.value
    if flag < 0 or flag >= rpn.flag.MAX:
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_MEMORY, name, "Flag {} out of range (0..{} expected)".format(flag, rpn.flag.MAX - 1))
    result = rpn.type.Integer(rpn.globl.bool_to_int(not rpn.flag.flag_set_p(flag)))
    rpn.globl.param_stack.push(result)


@defword(name='fc?c', args=1, print_x=rpn.globl.PX_PREDICATE, doc="""\
fc?c   ( -- bool )
Test if flag is clear, then clear it.""")
def w_fc_query_clear(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))

    flag = x.value
    if flag < 0 or flag >= rpn.flag.MAX:
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_MEMORY, name, "Flag {} out of range (0..{} expected)".format(flag, rpn.flag.MAX - 1))
    result = rpn.type.Integer(rpn.globl.bool_to_int(not rpn.flag.flag_set_p(flag)))
    rpn.globl.param_stack.push(result)
    if flag < rpn.flag.FENCE:
        rpn.flag.clear_flag(flag)


@defword(name='fc?s', args=1, print_x=rpn.globl.PX_PREDICATE, doc="""\
fc?s   ( -- bool )
Test if flag is clear, then set it.""")
def w_fc_query_set(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))

    flag = x.value
    if flag < 0 or flag >= rpn.flag.MAX:
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_MEMORY, name, "Flag {} out of range (0..{} expected)".format(flag, rpn.flag.MAX - 1))
    result = rpn.type.Integer(rpn.globl.bool_to_int(not rpn.flag.flag_set_p(flag)))
    rpn.globl.param_stack.push(result)
    if flag < rpn.flag.FENCE:
        rpn.flag.set_flag(flag)


@defword(name='fib', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
fib   ( n -- fib )
Nth Fibonacci number.  N cannot be negative.

DEFINITION:
fib(0) = 0
fib(1) = 1
fib(n) = fib(n-1) + fib(n-2)""")
def w_fib(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    if x.value < 0:
        rpn.globl.param_stack.push(x)
        throw(X_FP_INVALID_ARG, name, "X cannot be negative")
    result = rpn.type.Integer(fib_helper(x.value))
    rpn.globl.param_stack.push(result)


@defword(name='fix', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
fix   ( n -- )
Set fixed display.  N specifies the number of digits after the decimal point.""")
def w_fix(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))

    if x.value < 0 or x.value >= rpn.globl.PRECISION_MAX:
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_ARG, name, "Precision '{}' out of range (0..{} expected)".format(x.value, rpn.globl.PRECISION_MAX - 1))

    rpn.globl.disp_stack.top().style = "fix"
    rpn.globl.disp_stack.top().prec = x.value
    rpn.flag.set_flag(rpn.flag.F_DISP_FIX)
    rpn.flag.clear_flag(rpn.flag.F_DISP_ENG)


@defword(name='floor', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
floor   ( x -- floor )
Floor.  Largest integer not greater than X.""")
def w_floor(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is rpn.type.Integer:
        result = x
    elif type(x) in [rpn.type.Float, rpn.type.Rational]:
        result = rpn.type.Integer(math.floor(x.value))
    else:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='fmod', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
fmod   ( y x -- rem )
Floating point remainder.  Return the remainder of dividing y by x.  This is
preferred for floats, while mod is preferred for integers.""")
def w_fmod(name):
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if    type(x) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float] \
       or type(y) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))
    if x.zerop():
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_FP_DIVISION_BY_ZERO, name, "X cannot be zero")
    r = math.fmod(float(y.value), float(x.value))
    rpn.globl.param_stack.push(rpn.type.Float(r))


@defword(name='hide', print_x=rpn.globl.PX_CONFIG, doc="""\
hide   ( -- )
Make the following word hidden.  Only user-defined words can be hidden.

WARNING: there is no way to "unhide" a word!""")
def w_hide(name):               # pylint: disable=unused-argument
    pass                        # Grammar rules handle this word


@defword(name='forget', print_x=rpn.globl.PX_CONFIG, doc="""\
forget   ( -- )
Forget the definition of the following word.""")
def w_forget(name):             # pylint: disable=unused-argument
    pass                        # Grammar rules handle this word


# HP-41 calls this FRC, HP-42 calls this FP.  I like FRAC (which appeared
# on the HP-34C) because it is very clear but still short enough.
@defword(name='frac', print_x=rpn.globl.PX_COMPUTE, args=1, doc="""\
frac   ( x.q -- 0.q )
Fractional part.""")
def w_frac(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is rpn.type.Integer:
        rpn.globl.param_stack.push(rpn.type.Integer(0))
    elif type(x) in [rpn.type.Rational, rpn.type.Float]:
        result = rpn.type.Float(x.value - int(x.value))
        rpn.globl.param_stack.push(result)
    else:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))


@defword(name='fs?', print_x=rpn.globl.PX_PREDICATE, args=1, doc="""\
fc?   ( -- bool )
Test if flag is set.""")
def w_fs_query(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))

    flag = x.value
    if flag < 0 or flag >= rpn.flag.MAX:
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_MEMORY, name, "Flag {} out of range (0..{} expected)".format(flag, rpn.flag.MAX - 1))
    result = rpn.type.Integer(rpn.globl.bool_to_int(rpn.flag.flag_set_p(flag)))
    rpn.globl.param_stack.push(result)


@defword(name='fs?c', print_x=rpn.globl.PX_PREDICATE, args=1, doc="""\
fs?c   ( -- bool )
Test if flag is set, then clear it.""")
def w_fs_query_clear(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))

    flag = x.value
    if flag < 0 or flag >= rpn.flag.MAX:
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_MEMORY, name, "Flag {} out of range (0..{} expected)".format(flag, rpn.flag.MAX - 1))
    result = rpn.type.Integer(rpn.globl.bool_to_int(rpn.flag.flag_set_p(flag)))
    rpn.globl.param_stack.push(result)
    if flag < rpn.flag.FENCE:
        rpn.flag.clear_flag(flag)


@defword(name='fs?s', print_x=rpn.globl.PX_PREDICATE, args=1, doc="""\
fs?s   ( -- bool )
Test if flag is set, then set it.""")
def w_fs_query_set(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))

    flag = x.value
    if flag < 0 or flag >= rpn.flag.MAX:
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_MEMORY, name, "Flag {} out of range (0..{} expected)".format(flag, rpn.flag.MAX - 1))
    result = rpn.type.Integer(rpn.globl.bool_to_int(rpn.flag.flag_set_p(flag)))
    rpn.globl.param_stack.push(result)
    if flag < rpn.flag.FENCE:
        rpn.flag.set_flag(flag)


if rpn.globl.have_module('scipy'):
    @defword(name='fsolve', args=1, str_args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
fsolve   ( init.guess -- root )  [ func -- ]
Solving for root.  Name of function must be on string stack.
Implemented via scipy.optimize.fsolve()""")
    def w_fsolve(name):
        func_to_solve = rpn.globl.string_stack.pop().value
        (word, _) = rpn.globl.lookup_word(func_to_solve)
        if word is None:
            throw(X_UNDEFINED_WORD, name, "'{}'".format(func_to_solve))

        x = rpn.globl.param_stack.pop()
        if    type(x) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
            rpn.globl.param_stack.push(x)
            throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
        #init_guess = float(x.value)

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
FV   ( -- fv )
Calculate Future Value (FV).

DEFINITION:
     PMT * k         N    (      PMT * k )
FV = ------- - (1+ip)  * (  PV + -------  )
       ip                 (        ip    )

k = 1 if END, 1+ip if BEGIN""")
def w_FV(name):
    if any_undefined_p([rpn.tvm.N, rpn.tvm.INT, rpn.tvm.PV, rpn.tvm.PMT]):
        throw(X_BAD_DATA, name, "Need N, INT, PV, and PMT")

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
GAMMA   ( -- 0.5772... )
Euler-Mascheroni number.  Do not confuse this with the gamma function.

DEFINITION:
GAMMA = lim(n->inf, (-ln n + SUM(k=1,n, 1/k)))""")
def w_GAMMA(name):              # pylint: disable=unused-argument
    result = rpn.type.Float(rpn.globl.GAMMA)
    result.label = "GAMMA"
    rpn.globl.param_stack.push(result)


@defword(name='gamma', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
gamma   ( x -- gamma[x] )
Gamma function.  Do not confuse this with the constant GAMMA.""")
def w_gamma(name):
    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        try:
            r = math.gamma(float(x.value))
        except ValueError:
            rpn.globl.param_stack.push(x)
            throw(X_FP_INVALID_ARG, name, "X cannot be a non-positive integer")
        if type(x) is rpn.type.Integer:
            result = rpn.type.Integer(r)
        else:
            result = rpn.type.Float(r)
    elif type(x) is rpn.type.Complex:
        if not rpn.globl.have_module('scipy'):
            rpn.globl.param_stack.push(x)
            throw(X_UNSUPPORTED, name, "Complex support requires 'scipy' library")
        r = scipy.special.gamma(x.value)
        if math.isnan(r.real) or math.isnan(r.imag):
            rpn.globl.param_stack.push(x)
            throw(X_FP_INVALID_ARG, name, "X cannot be a non-positive integer")
        result = rpn.type.Complex.from_complex(r)
    else:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    result.label = "gamma"
    rpn.globl.param_stack.push(result)


@defword(name='gcd', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
gcd   ( y x -- gcd )
Greatest common divisor.

DEFINITION:
: gcd  begin ?dup while tuck mod repeat ;""")
def w_gcd(name):
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if    type(x) is not rpn.type.Integer \
       or type(y) is not rpn.type.Integer:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))

    xval = x.value
    yval = y.value
    if xval < 0 or yval < 0:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_FP_INVALID_ARG, name, "Neither X nor Y can be negative")
    if xval == 0 or yval == 0:
        rpn.globl.param_stack.push(rpn.type.Integer(0))
    else:
        r = gcd_helper(xval, yval)
        rpn.globl.param_stack.push(rpn.type.Integer(r))


if sys.version_info >= (3, 8):
    @defword(name='gmean', print_x=rpn.globl.PX_COMPUTE, doc="""\
gmean   ( -- gmean )
Calculate the geometric mean of the statistics data.""")
    def gmean(name):
        if len(rpn.globl.stat_data) == 0:
            throw(X_BAD_DATA, name, "No statistics data")
        try:
            m = statistics.geometric_mean(rpn.globl.stat_data)
        except statistics.StatisticsError as e:
            throw(X_BAD_DATA, name, "{}".format(str(e)))
        result = rpn.type.Float(m)
        result.label = "gmean"
        rpn.globl.param_stack.push(result)


@defword(name='grad', print_x=rpn.globl.PX_CONFIG, doc="""\
grad   ( -- )
Set angular mode to gradians.""")
def w_grad(name):               # pylint: disable=unused-argument
    rpn.flag.clear_flag(rpn.flag.F_RAD)
    rpn.flag.set_flag(rpn.flag.F_GRAD)


@defword(name='help', print_x=rpn.globl.PX_IO, doc="""\
help   ( -- )
Show documentation for the following word.""")
def w_help(name):               # pylint: disable=unused-argument
    pass                        # Grammar rules handle this word


@defword(name='hmean', print_x=rpn.globl.PX_COMPUTE, doc="""\
hmean   ( -- hmean )
Return the harmonic mean of the statistics data.""")
def w_hmean(name):
    if len(rpn.globl.stat_data) == 0:
        throw(X_BAD_DATA, name, "No statistics data")
    try:
        m = statistics.harmonic_mean(rpn.globl.stat_data)
    except statistics.StatisticsError as e:
        throw(X_BAD_DATA, name, "{}".format(str(e)))
    result = rpn.type.Float(m)
    result.label = "hmean"
    rpn.globl.param_stack.push(result)


@defword(name='hms', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
hms   ( HH.nnn -- HH.MMSS )
Convert decimal hours to hours/minutes/seconds.""")
def w_hms(name):
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
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    result.label = "HH.MMSS"
    rpn.globl.param_stack.push(result)


@defword(name='hms+', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
hms+   ( HH.MMSS HH.MMSS -- HH.MMSS )
Add hours/minutes/seconds.""")
def w_hms_plus(name):
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if    type(x) not in [rpn.type.Integer, rpn.type.Float] \
       or type(y) not in [rpn.type.Integer, rpn.type.Float]:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))

    #ynegative = y.value < 0
    if type(y) is rpn.type.Integer:
        (yvalid, yhh, ymm, yss, _) = rpn.type.Float(y.value).time_info()
    else:
        (yvalid, yhh, ymm, yss, _) = y.time_info()
    if not yvalid:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_ARG, name, "{} is not a valid time".format(y.value))

    #xnegative = y.value < 0
    if type(x) is rpn.type.Integer:
        (xvalid, xhh, xmm, xss, _) = rpn.type.Float(x.value).time_info()
    else:
        (xvalid, xhh, xmm, xss, _) = x.time_info()
    if not xvalid:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_ARG, name, "{} is not a valid time".format(x.value))

    (hh, mm, ss) = rpn.globl.normalize_hms(yhh + xhh, ymm + xmm, yss + xss)
    #print("hh=",hh,"mm=",mm,"ss=",ss)
    result = rpn.type.Float("%d.%02d%02d" % (hh, mm, ss))
    result.label = "HH.MMSS"
    rpn.globl.param_stack.push(result)


@defword(name='hms-', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
hms-   ( HH.MMSS HH.MMSS -- HH.MMSS )
Subtract hours/minutes/seconds.""")
def w_hms_minus(name):
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if    type(x) not in [rpn.type.Integer, rpn.type.Float] \
       or type(y) not in [rpn.type.Integer, rpn.type.Float]:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))

    if type(y) is rpn.type.Integer:
        (yvalid, yhh, ymm, yss, _) = rpn.type.Float(y.value).time_info()
    else:
        (yvalid, yhh, ymm, yss, _) = y.time_info()
    if not yvalid:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_ARG, name, "{} is not a valid time".format(y.value))

    if type(x) is rpn.type.Integer:
        (xvalid, xhh, xmm, xss, _) = rpn.type.Float(x.value).time_info()
    else:
        (xvalid, xhh, xmm, xss, _) = x.time_info()
    if not xvalid:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_ARG, name, "{} is not a valid time".format(x.value))

    (hh, mm, ss) = rpn.globl.normalize_hms(yhh - xhh, ymm - xmm, yss - xss)
    #print("hh=",hh,"mm=",mm,"ss=",ss)
    result = rpn.type.Float("%d.%02d%02d" % (hh, mm, ss))
    result.label = "HH.MMSS"
    rpn.globl.param_stack.push(result)


@defword(name='hp->d', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
hp->d   ( day# -- MM.DDYYYY )
Convert HP day number to date.  Day # 0 = October 15, 1582.""")
def w_hp_to_d(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))

    daynum = x.value
    if daynum < 0 or daynum > datetime.date.max.toordinal():
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_ARG, name, "{} is not a valid day number".format(x.value))

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
hr   ( HH.MMSS -- HH.nnn )
Convert hours/minutes/seconds to decimal hours.""")
def w_hr(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is rpn.type.Integer:
        result = rpn.type.Float(x.value)
    elif type(x) in [rpn.type.Float, rpn.type.Rational]:
        negative = -1.0 if x.value < 0 else 1.0
        hms = rpn.type.Float(abs(float(x.value) if type(x) is rpn.type.Rational else x.value))
        (valid, hh, mm, ss, _) = hms.time_info()
        if not valid:
            rpn.globl.param_stack.push(x)
            throw(X_INVALID_ARG, name, "{} is not a valid time".format(x.value))

        hr = float(hh) + float(mm)/60.0 + float(ss)/3600.0
        result = rpn.type.Float(negative * hr)
    else:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    result.label = "HH.nnn"
    rpn.globl.param_stack.push(result)


@defword(name='hypot', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
hypot   ( y x -- hypot )
Hypotenuse distance.  Calculated as square root of the sum of squares.

DEFINITION:
hypot = sqrt(x^2 + y^2)""")
def w_hypot(name):
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if    type(x) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float] \
       or type(y) in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))

    yval = float(y.value)
    xval = float(x.value)
    rpn.globl.param_stack.push(rpn.type.Float(math.hypot(xval, yval)))


@defword(name='I', print_x=rpn.globl.PX_CONFIG, doc="""\
I   ( -- x )
Index of DO current loop.  Return the index of the most recent DO loop.  Do not
confuse this with the "i" command, which returns the complex number (0,1).""")
def w_I(name):
    (_I, _) = rpn.globl.lookup_variable('_I')
    if _I is None:
        throw(X_LOOP_PARAMS, name, "'I' not valid here, only in DO loops")
    if type(_I.obj) is not rpn.type.Integer:
        raise FatalErr("I is not an rpn.type.Integer")
    rpn.globl.param_stack.push(_I.obj)


if rpn.globl.have_module('numpy'):
    @defword(name='idn', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
idn   ( n -- mat )
Create an NxN identity matrix.""")
    def idn(name):
        x = rpn.globl.param_stack.pop()
        size = 0
        if type(x) is rpn.type.Integer:
            size = x.value
            if size < 1 or size > rpn.globl.MATRIX_MAX:
                rpn.globl.param_stack.push(x)
                throw(X_INVALID_ARG, name, "X out of range (1..{} expected)".format(rpn.globl.MATRIX_MAX))
        elif type(x) is rpn.type.Vector:
            vsize = x.size()
            if vsize != 2:
                rpn.globl.param_stack.push(x)
                throw(X_INVALID_ARG, name, "Only matrices can be created")
            if int(x.value[0]) != int(x.value[1]):
                rpn.globl.param_stack.push(x)
                throw(X_INVALID_ARG, name, "Only square matrices can be created")
            size = x.value[0]
        else:
            rpn.globl.param_stack.push(x)
            throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))


        result = rpn.type.Matrix.from_numpy(np.identity(size, dtype=np.int64))
        rpn.globl.param_stack.push(result)


@defword(name='if', args=1, print_x=rpn.globl.PX_CONTROL, doc="""\
if   ( flag -- )
Test condition.  Execute a conditional test.
<flag> if ... [ else ... ] then

See also: else, then""")
def w_if(name):                 # pylint: disable=unused-argument
    pass                        # Grammar rules handle this word


@defword(name='INT', print_x=rpn.globl.PX_COMPUTE, doc="""\
INT   ( -- int )
Calculate INTerest rate (INT).  Do not confuse this with the int command,
which truncates values to integers.""")
def w_INT(name):
    if any_undefined_p([rpn.tvm.N, rpn.tvm.PV, rpn.tvm.PMT, rpn.tvm.FV]):
        throw(X_BAD_DATA, name, "Need N, PV, PMT, and FV")

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
int   ( x -- int )
Truncate to integer.  The result is whatever Python's int() function returns.
Do not confuse this with the INT command, which solves for financial interest
rates.  Consider using floor or ceil instead.""")
def w_int(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is rpn.type.Integer:
        result = x
    elif type(x) in [rpn.type.Float, rpn.type.Rational]:
        result = rpn.type.Integer(int(x.value))
    else:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='J', print_x=rpn.globl.PX_CONFIG, doc="""\
J   ( -- x )
Index of DO outer DO loop.  Return the index of the DO loop enclosing
the current one.""")
def w_J(name):
    (_J, _) = rpn.globl.lookup_variable('_I', 2)
    if _J is None:
        throw(X_LOOP_PARAMS, name, "'J' not valid here, only in nested DO loops")
    if type(_J.obj) is not rpn.type.Integer:
        raise FatalErr("J is not an rpn.type.Integer")
    rpn.globl.param_stack.push(_J.obj)


@defword(name='jd->$', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
jd->$   ( julian -- ) [ -- "YYYY-MM-DD" ]
Convert julian day number to ISO date string.

EXAMPLE:
    2369915 jd->$
"1776-07-04" """)
def w_jd_to_dollar(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))

    if x.value < 1 or x.value > datetime.date.max.toordinal():
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_ARG, name, "X out of range (1..{} expected)".format(datetime.date.max.toordinal()))

    dateobj = datetime.date.fromordinal(x.value - rpn.globl.JULIAN_OFFSET)
    result = rpn.type.String("%d-%02d-%02d" % (dateobj.year, dateobj.month, dateobj.day))
    rpn.globl.string_stack.push(result)


@defword(name='jd->d', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
jd->d   ( julian -- MM.DDYYYY )
Convert julian day number to date.

EXAMPLE:
    2369915 jd->d
7.041776""")
def w_jd_to_d(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))

    if x.value < 1 or x.value > datetime.date.max.toordinal():
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_ARG, name, "X out of range (1..{} expected)".format(datetime.date.max.toordinal()))

    dateobj = datetime.date.fromordinal(x.value - rpn.globl.JULIAN_OFFSET)
    result = rpn.type.Float("%d.%02d%04d" % (dateobj.month, dateobj.day, dateobj.year))
    result.label = "MM.DDYYYY"
    rpn.globl.param_stack.push(result)


if rpn.globl.have_module('scipy'):
    @defword(name='Jv', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
Jv   ( order x -- J_v(x) )
Bessel function of the first kind of real order and complex argument.
Implemented via scipy.special.jv(order, x)""")
    def Jv(name):
        x = rpn.globl.param_stack.pop()
        y = rpn.globl.param_stack.pop()
        if    type(x) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float, rpn.type.Complex] \
           or type(y) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))
        order = float(y.value)
        xval = x.value
        r = scipy.special.jv(order, xval)
        if type(r) is np.float64 and math.isnan(r):
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            throw(X_FP_NAN, name)

        if type(x) is rpn.type.Complex:
            result = rpn.type.Complex.from_complex(r)
        else:
            result = rpn.type.Float(r)
        rpn.globl.param_stack.push(result)


@defword(name='inv', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
inv   ( x -- 1/x )
Inverse.  X cannot be zero.""")
def w_inv(name):
    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational, rpn.type.Complex] \
       and x.zerop():
        rpn.globl.param_stack.push(x)
        throw(X_FP_DIVISION_BY_ZERO, name, "X cannot be zero")

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
        throw(X_ARG_TYPE_MISMATCH, name, "Vectors are not invertible")
    elif type(x) is rpn.type.Matrix:
        try:
            r = np.linalg.inv(x.value)
        except np.linalg.LinAlgError:
            rpn.globl.param_stack.push(x)
            throw(X_FP_INVALID_ARG, name, "Singular matrix has no inverse")
        result = rpn.type.Matrix.from_numpy(r)
    else:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))

    if x.has_uexpr_p():
        result.uexpr = x.uexpr.invert()

    rpn.globl.param_stack.push(result)


@defword(name='key', print_x=rpn.globl.PX_IO, doc="""\
key   ( -- key )
ASCII code of single keystroke.  key will block until input is provided.
Keystroke is not echoed.

See also: ?key""")
def w_key(name):                # pylint: disable=unused-argument
    try:
        k = _Getch()()
    except termios.error as e:
        throw(X_CHAR_IO, name, e.args[1])
    val = ord(k) if k != "" else 0
    #rpn.globl.lnwriteln("You pressed <{}>, value={}".format(k, val))
    rpn.globl.param_stack.push(rpn.type.Integer(val))


@defword(name='label>', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
label>   ( x -- x' )  [ -- label ]
Separate a label from the stack element.""")
def w_label_from(name):
    x = rpn.globl.param_stack.top()
    if not x.has_label_p():
        throw(X_INVALID_ARG, name, "X does not have a label")
    rpn.globl.string_stack.push(rpn.type.String(x.label))
    x.label = None


@defword(name='label?', args=1, print_x=rpn.globl.PX_PREDICATE, doc="""\
label?   ( x -- bool )
Test if X has a label.""")
def w_label_query(name):        # pylint: disable=unused-argument
    x = rpn.globl.param_stack.pop()
    rc = x.has_label_p()
    result = rpn.type.Integer(rc)
    rpn.globl.param_stack.push(result)


@defword(name='lcm', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
lcm   ( y x -- lcm )
Least common multiple.

DEFINITION:
              x * y
lcm(x, y) = ---------
            gcd(x, y)""")
def w_lcm(name):
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if    type(x) is not rpn.type.Integer \
       or type(y) is not rpn.type.Integer:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))

    xval = x.value
    yval = y.value
    if xval < 0 or yval < 0:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_FP_INVALID_ARG, name, "Neither X nor Y can be negative")
    if xval == 0 or yval == 0:
        rpn.globl.param_stack.push(rpn.type.Integer(0))
    else:
        r = (xval * yval) / gcd_helper(xval, yval)
        rpn.globl.param_stack.push(rpn.type.Integer(r))


@defword(name='leave', print_x=rpn.globl.PX_CONTROL, doc="""\
leave   ( -- )
Exit a do or begin loop immediately.""")
def w_leave(name):              # pylint: disable=unused-argument
    throw(X_LEAVE)


@defword(name='lg', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
lg   ( x -- lg )
Logarithm [base 2].  X cannot be zero.  Use ln for the natural logarithm,
and log for the common logarithm.""")
def w_lg(name):
    x = rpn.globl.param_stack.pop()
    if     type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational, rpn.type.Complex] \
       and x.zerop():
        rpn.globl.param_stack.push(x)
        throw(X_FP_INVALID_ARG, name, "X cannot be zero")

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
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='ln', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
ln   ( x -- ln )
Natural logarithm [base e].  X cannot be zero.  Use log for the common
(base 10) logarithm.""")
def w_ln(name):
    x = rpn.globl.param_stack.pop()
    if     type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational, rpn.type.Complex] \
       and x.zerop():
        rpn.globl.param_stack.push(x)
        throw(X_FP_INVALID_ARG, name, "X cannot be zero")

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
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='lnp1', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
lnp1   ( x -- ln(1+x) )
Calculate ln(1+X) accurately.""")
def w_ln_1_plus_x(name):
    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        if float(x.value) == -1.0:
            rpn.globl.param_stack.push(x)
            throw(X_FP_INVALID_ARG, name, "X cannot be -1")
        result = rpn.type.Float(math.log1p(x.value))
    elif type(x) is rpn.type.Complex:
        if x.value == complex(-1, 0):
            rpn.globl.param_stack.push(x)
            throw(X_FP_INVALID_ARG, name, "X cannot be (-1,0)")
        result = rpn.type.Complex.from_complex(cmath.log(x.value + complex(1,0)))
    else:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='load', str_args=1, print_x=rpn.globl.PX_CONTROL, doc="""\
load   [ file -- ]
Load file specified on string stack.""")
def w_load(name):               # pylint: disable=unused-argument
    filename = rpn.globl.string_stack.pop().value
    try:
        rpn.app.load_file(filename)
    except RuntimeErr as err_f_opt:
        rpn.globl.lnwriteln("load: " + str(err_f_opt))


@defword(name='log', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
log   ( x -- log )
Common logarithm [base 10].  X cannot be zero.  Use ln for the natural
(base e) logarithm.""")
def w_log(name):
    x = rpn.globl.param_stack.pop()
    if     type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational, rpn.type.Complex] \
       and x.zerop():
        rpn.globl.param_stack.push(x)
        throw(X_FP_INVALID_ARG, name, "X cannot be zero")

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
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='loop', print_x=rpn.globl.PX_CONTROL, doc="""\
loop   ( limit initial -- )
Execute a definite loop.
<limit> <initial> do ... loop
The iteration counter is available via I.  leave will exit the loop early.

EXAMPLE:
    10 0 do I . loop
0 1 2 3 4 5 6 7 8 9

See also: do, I, leave, +loop""")
def w_loop(name):               # pylint: disable=unused-argument
    pass                        # Grammar rules handle this word


@defword(name='max', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
max   ( y x -- max )
Larger of X or Y.""")
def w_max(name):
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
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))


@defword(name='mean', print_x=rpn.globl.PX_COMPUTE, doc="""\
mean   ( -- mean )
Return the arithmetic mean of the statistics data.""")
def w_mean(name):
    if len(rpn.globl.stat_data) == 0:
        throw(X_BAD_DATA, name, "No statistics data")
    try:
        m = statistics.mean(rpn.globl.stat_data)
    except statistics.StatisticsError as e:
        throw(X_BAD_DATA, name, "{}".format(str(e)))
    result = rpn.type.Float(m)
    result.label = "mean"
    rpn.globl.param_stack.push(result)


@defword(name='median', print_x=rpn.globl.PX_COMPUTE, doc="""\
median   ( -- median )
Return the median of the statistics data.""")
def w_median(name):
    if len(rpn.globl.stat_data) == 0:
        throw(X_BAD_DATA, name, "No statistics data")
    try:
        m = statistics.median(rpn.globl.stat_data)
    except statistics.StatisticsError as e:
        throw(X_BAD_DATA, name, "{}".format(str(e)))
    result = rpn.type.Float(m)
    result.label = "median"
    rpn.globl.param_stack.push(result)


@defword(name='min', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
min   ( y x -- min )
Smaller of X or Y.""")
def w_min(name):
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
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))


@defword(name='N', print_x=rpn.globl.PX_COMPUTE, doc="""\
N   ( -- n )
Calculate Number of payments (N).

DEFINITION:
    log((FV*i)/(PV*i))
N = ------------------
        log(1 + i)""")
def w_N(name):
    if any_undefined_p([rpn.tvm.INT, rpn.tvm.PV, rpn.tvm.PMT, rpn.tvm.FV]):
        throw(X_BAD_DATA, name, "Need INT, PV, PMT, and FV")

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
not   ( flag -- !flag )
Logical not.  Invert a flag: return TRUE (1) if x is zero, otherwise FALSE (0).
not is intended for boolean manipulations and is only defined on truth
integers (0,1).  0 = is meant to compare a number to zero, and works for
all number types.

NOTE: This is not a bitwise not - use bitnot for that.""")
def w_lognot(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))

    rpn.globl.param_stack.push(rpn.type.Integer(not bool(x.value)))


@defword(name='of', print_x=rpn.globl.PX_CONTROL, doc="""\
of   ( x -- )
Execute a sequence of words based on stack value.  Once a match is
executed, no other clauses are considered.  otherwise is optional.
<n> and of labels must be integers.

<n> case
  <x> of ... endof
  <y> of ... endof
  <z> of ... endof
  [ otherwise ... ]
endcase

See also: case, endcase, endof, otherwise""")
def w_of(name):                 # pylint: disable=unused-argument
    pass                        # Grammar rules handle this word


@defword(name='or', args=2, print_x=rpn.globl.PX_PREDICATE, doc="""\
or   ( flag flag -- flag )
Logical OR.

NOTE: This is not a bitwise OR - use BITOR for that.""")
def w_logor(name):
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer or type(y) is not rpn.type.Integer:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))

    rpn.globl.param_stack.push(rpn.type.Integer(bool(x.value) or bool(y.value)))


@defword(name='otherwise', print_x=rpn.globl.PX_CONTROL, doc="""\
otherwise   ( -- )
Execute a sequence of words based on stack value.  Once a match is
executed, no other clauses are considered.  otherwise is optional.
<n> and of labels must be integers.

<n> case
  <x> of ... endof
  <y> of ... endof
  <z> of ... endof
  [ otherwise ... ]
endcase

See also: case, endcase, endof, of""")
def w_otherwise(name):          # pylint: disable=unused-argument
    pass                        # Grammar rules handle this word


@defword(name='p->r', print_x=rpn.globl.PX_COMPUTE, doc="""\
p->r   ( theta r   -- y x   ) for Real
p->r   ( (r,theta) -- (x,y) ) for Complex
Convert polar coordinates to rectangular.  The parameter(s) can be either
two reals, or one complex.

DEFINITION:
x = r * cos(theta)
y = r * sin(theta)""")
def w_p_to_r(name):
    if rpn.globl.param_stack.empty():
        throw(X_INSUFF_PARAMS, name, "(1 or 2 required)")
    x = rpn.globl.param_stack.pop()
    if type(x) is rpn.type.Complex:
        r      = x.real()
        theta  = rpn.globl.convert_mode_to_radians(x.imag())
        result = rpn.type.Complex.from_complex(cmath.rect(r, theta))
        rpn.globl.param_stack.push(result)
    elif type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        if rpn.globl.param_stack.empty():
            rpn.globl.param_stack.push(x)
            throw(X_INSUFF_PARAMS, name, "(2 required)")
        y = rpn.globl.param_stack.pop()
        if type(y) not in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))

        r     = float(x.value)
        theta = rpn.globl.convert_mode_to_radians(float(y.value))
        xval  = r * math.cos(theta)
        yval  = r * math.sin(theta)
        rpn.globl.param_stack.push(rpn.type.Float(yval))
        rpn.globl.param_stack.push(rpn.type.Float(xval))
    else:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))


@defword(name='perm', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
perm   ( n r -- nPr )
Permutations.  Choose from N objects R at a time, with regard to ordering.

DEFINITION:
        n!
nPr = ------
      (n-r)!""")
def w_perm(name):
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if type(y) is not rpn.type.Integer or type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))

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
PI   ( -- 3.14159... )

DEFINITION:
PI == TAU/2

Consider using TAU instead of PI to simplify your equations.""")
def w_PI(name):                 # pylint: disable=unused-argument
    result = rpn.type.Float(rpn.globl.PI)
    result.label = "PI"
    rpn.globl.param_stack.push(result)


@defword(name='pick', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
pick   ( x -- x' )
Pick an element from the stack.
1 pick is equivalent to dup.
2 pick is equivalent to over.""")
def w_pick(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))

    if x.value == 0:
        return
    if x.value < 0 or x.value > rpn.globl.param_stack.size():
        msg = "Stack index out of range"
        if not rpn.globl.param_stack.empty():
            msg += " (1..{} expected)".format(rpn.globl.param_stack.size())
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_MEMORY, name, msg)

    result = rpn.globl.param_stack.pick(x.value)
    rpn.globl.param_stack.push(result)


@defword(name='plot', args=2, str_args=1, print_x=rpn.globl.PX_IO, doc="""\
plot   ( xlow xhigh -- ) [ FN -- ]
Simple ASCII function plot.  FN is the (string) name of a function which
implements ( x -- y ).  Y-axis is autoscaled.

EXAMPLE:
    rad  80 !COLS  24 !ROWS
    TAU chs TAU "sin"  plot
      1.000 |------------------------------------*---------------------|
            |     ****                   :     ** *                    |
            |    *    *                  :    *    *                   |
            |   *      *                 :          *                  |
            |                            :   *       *                 |
            |  *        *                :  *                          |
            | *                          :            *                |
            |            *               : *                           |
            |*                           :             *               |
            |             *              :*                            |
            *                            :              *              |
            |..............*.............+.............................*
            |                            *               *             |
            |               *            :                            *|
            |                           *:                *            |
            |                *           :                           * |
            |                          * :                 *        *  |
            |                 *       *  :                             |
            |                  *         :                  *      *   |
            |                   *    *   :                   *    *    |
     -1.000 |--------------------****-------------------------****-----|
             -6.283                                                   6.283""")
def w_plot(name):
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if    type(x) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float] \
       or type(y) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))
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
PMT   ( -- pmt )
Calculate PayMenT amount (PMT).

DEFINITION:
       (         PV + FV     )    -ip
PMT = (  PV + --------------  ) * ---
       (       (1+ip)^N - 1  )     k

k = 1 if END, 1+ip if BEGIN""")
def w_PMT(name):
    if any_undefined_p([rpn.tvm.N, rpn.tvm.INT, rpn.tvm.PV, rpn.tvm.FV]):
        throw(X_BAD_DATA, name, "Need N, INT, PV, and FV")

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


@defword(name='price', args=2, print_x=rpn.globl.PX_COMPUTE, doc="""\
price   ( markup purch_cost -- price )
Compute selling price given purchase cost and percent markup.

If you are given the markup based on cost and the selling price of an
item, and want to compute the original purchase cost, simply change the
sign of the markup percentage.

DEFINITION:

        purch_cost
Price = ----------
            markup
        1 - ------
             100""")
def w_price(name):              # pylint: disable=unused-argument
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if    type(x) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float] \
       or type(y) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))

    markup     = float(y.value)
    purch_cost = float(x.value)
    result = rpn.type.Float(purch_cost / (1.0 - (markup / 100.0)))
    result.label = "price"
    # The HP-32SII preserves the Y value (like %) but we do not
    rpn.globl.param_stack.push(result)


@defword(name='PV', print_x=rpn.globl.PX_COMPUTE, doc="""\
PV   ( -- pv )
Calculate Present Value (PV).

DEFINITION:
      ( PMT * k      )       1         PMT * k
PV = (  ------- - FV  ) * --------  -  -------
      (   ip         )    (1+ip)^N       ip

k = 1 if END, 1+ip if BEGIN""")
def w_PV(name):
    if any_undefined_p([rpn.tvm.N, rpn.tvm.INT, rpn.tvm.PMT, rpn.tvm.FV]):
        throw(X_BAD_DATA, name, "Need N, INT, PMT, and FV")

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
quad   ( lower upper -- err.est integral )  [ FN -- ]
Numerical integration.  Name of function must be on string stack.
Implemented via scipy.integrate.quad()

EXAMPLE: Integrate a bessel function jv(2.5, x) along the interval [0,4.5]:
    : J2.5  2.5 swap Jv ;
    0 4.5 "J2.5" quad .s
1: 7.866317216380692e-09 \ error
0: 1.1178179380783249 \ quad""")
    def quad(name):
        func_to_integrate = rpn.globl.string_stack.pop().value
        (word, _) = rpn.globl.lookup_word(func_to_integrate)
        if word is None:
            throw(X_UNDEFINED_WORD, name, "'{}'".format(func_to_integrate))

        x = rpn.globl.param_stack.pop()
        y = rpn.globl.param_stack.pop()
        if    type(x) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float] \
           or type(y) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))
        lower = float(y.value)
        upper = float(x.value)

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
r->d   ( rad -- deg )
Convert radians to degrees.  This will actually convert any angle measure
to degrees, not just radians.""")
def w_r_to_d(name):
    x = rpn.globl.param_stack.pop()
    if type(x) not in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))

    if x.has_uexpr_p() and x.uexpr.dim() != rpn.unit.category["Null"].dim():
        if x.uexpr.dim() != rpn.unit.category["Angle"].dim():
            rpn.globl.param_stack.push(x)
            throw(X_INCONSISTENT_UNITS, name, "'{}' is not an angular unit".format(x.uexpr))
        x = x.ubase_convert(name) # convert to radians

    result = rpn.type.Float(rpn.globl.convert_radians_to_mode(float(x.value), "d"))
    result.uexpr = rpn.globl.uexpr["d"]
    rpn.globl.param_stack.push(result)


@defword(name='r->p', print_x=rpn.globl.PX_COMPUTE, doc="""\
r->p   ( y x   -- theta r   ) for Real
r->p   ( (x,y) -- (r,theta) ) for Complex
Convert rectangular coordinates to polar.  The parameter(s) can be either
two reals, or one complex.

DEFINITION:
r     = hypot(x, y) == sqrt(x^2 + y^2)
theta = atan(y / x) == atan2(y, x)""")
def w_r_to_p(name):
    if rpn.globl.param_stack.empty():
        throw(X_INSUFF_PARAMS, name, "(1 or 2 required)")
    x = rpn.globl.param_stack.pop()
    if type(x) is rpn.type.Complex:
        (r, theta) = cmath.polar(x.value)
        result = rpn.type.Complex(r, rpn.globl.convert_radians_to_mode(theta))
        rpn.globl.param_stack.push(result)
    elif type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        if rpn.globl.param_stack.empty():
            rpn.globl.param_stack.push(x)
            throw(X_INSUFF_PARAMS, name, "(2 required)")
        y = rpn.globl.param_stack.pop()
        if type(y) not in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))

        theta = math.atan2(y.value, x.value)
        theta_obj = rpn.type.Float(rpn.globl.convert_radians_to_mode(theta))
        theta_obj.uexpr = rpn.globl.uexpr[rpn.globl.angle_mode_letter()]
        theta_obj.label = "theta"

        r = math.hypot(y.value, x.value)
        r_obj = rpn.type.Float(r)
        r_obj.label = "r"

        rpn.globl.param_stack.push(theta_obj)
        rpn.globl.param_stack.push(r_obj)
    else:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))


@defword(name='r.s', print_x=rpn.globl.PX_IO, doc="""\
r.x   ( -- )
Display return stack.""")
def w_r_dot_s(name):            # pylint: disable=unused-argument
    for (i, item) in rpn.globl.return_stack.items_bottom_to_top():
        # Prefix with "r" to prevent confusion with .s
        rpn.globl.lnwriteln("r{}: {}".format(i, item))


@defword(name='r>', print_x=rpn.globl.PX_CONFIG, doc="""\
r>   ( -- x )
Pop return stack onto parameter stack.""")
def w_r_from(name):
    if rpn.globl.return_stack.empty():
        throw(X_RSTACK_UNDERFLOW, name)
    rpn.globl.param_stack.push(rpn.globl.return_stack.pop())


@defword(name='r@', print_x=rpn.globl.PX_CONFIG, doc="""\
r@   ( -- x )
Copy top of return stack.""")
def w_r_fetch(name):
    if rpn.globl.return_stack.empty():
        throw(X_RSTACK_UNDERFLOW, name)
    rpn.globl.param_stack.push(rpn.globl.return_stack.top())


@defword(name='rad', print_x=rpn.globl.PX_CONFIG, doc="""\
rad   ( -- )
Set angular mode to radians.""")
def w_rad(name):                # pylint: disable=unused-argument
    rpn.flag.set_flag(rpn.flag.F_RAD)
    rpn.flag.clear_flag(rpn.flag.F_GRAD)


@defword(name='rand', print_x=rpn.globl.PX_COMPUTE, doc="""\
rand   ( -- r )
Random number.  r is a float in range: 0 <= r < 1.

See also: randint""")
def w_rand(name):               # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Float(random.random()))


@defword(name='randint', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
randint   ( n -- r )
Random integer between 1 and n.  r is an integer in range: 1 <= r <= n.

EXAMPLE:
    : threeD6  3 0 do 6 randint loop + +  ;

See also: rand""")
def w_randint(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))

    if x.value < 1:
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_ARG, name, "X cannot be negative")

    r = random.randint(1, x.value)
    rpn.globl.param_stack.push(rpn.type.Integer(r))


@defword(name='rcl', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
rcl   ( reg -- val )
Recall value of register X.""")
def w_rcl(name):
    (reg_size, _) = rpn.globl.lookup_variable("SIZE")

    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    reg = x.value
    if reg < 0 or reg >= reg_size.obj.value:
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_MEMORY, name, "Register {} out of range (0..{} expected)".format(reg, reg_size.obj.value - 1))
    rpn.globl.param_stack.push(rpn.globl.register[reg])


@defword(name='rclI', print_x=rpn.globl.PX_COMPUTE, doc="""\
rclI   ( -- reg[I] )
Recall value of register I.  Do not confuse this with rcli, which recalls
the contents of the register referenced by I.""")
def w_rclI(name):               # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.globl.register['I'])


@defword(name='rcli', print_x=rpn.globl.PX_CONFIG, doc="""\
rcli   ( -- reg[(i)] )
Recall contents of the register referenced by I.  Do not confuse this with
rclI, which recalls the value of register I directly.""")
def w_rcli(name):
    (reg_size, _) = rpn.globl.lookup_variable("SIZE")

    I = rpn.globl.register['I']
    if type(I) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(I)))
    Ival = int(I.value)
    if Ival < 0 or Ival >= reg_size.obj.value:
        throw(X_INVALID_MEMORY, name, "Register {} out of range (0..{} expected)".format(Ival, reg_size.obj.value - 1))

    rpn.globl.param_stack.push(rpn.globl.register[Ival])


@defword(name='rct->sph', args=3, print_x=rpn.globl.PX_COMPUTE, doc="""\
rct->sph   ( z y x -- phi theta r )
Convert rectangular coordinates to spherical.

DEFINITION:
phi   = atan(y/x)      == atan2(y, x)
theta = acos(z / r)
r     = hypot(x, y, z) == sqrt(x^2 + y^2 + z^2)""")
def w_rct_to_sph(name):
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    z = rpn.globl.param_stack.pop()
    if    type(x) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float] \
       or type(y) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float] \
       or type(z) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
        rpn.globl.param_stack.push(z)
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({} {} {})".format(typename(z), typename(y), typename(x)))
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
    theta_obj.uexpr = rpn.globl.uexpr[rpn.globl.angle_mode_letter()]
    theta_obj.label = "theta"

    phi     = math.atan2(yval, xval)
    phi_obj = rpn.type.Float(rpn.globl.convert_radians_to_mode(phi))
    phi_obj.uexpr = rpn.globl.uexpr[rpn.globl.angle_mode_letter()]
    phi_obj.label = "phi"

    rpn.globl.param_stack.push(phi_obj)
    rpn.globl.param_stack.push(theta_obj)
    rpn.globl.param_stack.push(r_obj)


@defword(name='rdepth', print_x=rpn.globl.PX_COMPUTE, doc="""\
rdepth   ( -- n )
Current number of elements on return stack.""")
def w_rdepth(name):             # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(rpn.globl.return_stack.size()))


@defword(name='rdrop', print_x=rpn.globl.PX_CONFIG, doc="""\
rdrop   ( -- )
Drop the top item from the return stack.""")
def w_rdrop(name):
    if rpn.globl.return_stack.empty():
        throw(X_RSTACK_UNDERFLOW, name)
    rpn.globl.return_stack.pop()


@defword(name='recurse', print_x=rpn.globl.PX_CONTROL, doc="""\
recurse
Recurse into current word.  Only valid in a colon definition.""")
def w_recurse(name):            # pylint: disable=unused-argument
    pass                        # Grammar rules handle this word


@defword(name='repeat', print_x=rpn.globl.PX_CONTROL, doc="""\
repeat   ( flag -- )
Execute an indefinite loop while a condition is satisfied.
begin ... <flag> while ... repeat

leave will exit the loop early.  Note that the effect of the test in
begin...while is opposite that in begin...until: the loop repeats
while something is true, rather than until it becomes true.

See also: begin, again, leave, until, while""")
def w_repeat(name):             # pylint: disable=unused-argument
    pass                        # Grammar rules handle this word


@defword(name='resize', print_x=rpn.globl.PX_CONFIG, doc="""\
resize   ( -- )
Reset ROWS and COLS to actual values.""")
def w_resize(name):             # pylint: disable=unused-argument
    rpn.globl.update_screen_size()


@defword(name='rms', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
rms   ( v -- rms )
Root mean square.

DEFINITION:
            2    2    2          2
           x1 + x2 + x3 + ... + xn
rms = sqrt(-----------------------)
                      n""")
def w_rms(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Vector:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))

    n = x.size()
    if n == 0:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "X cannot be an empty vector")
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
        raise FatalErr("{}: Cannot handle type {}".format(name, t))

    result.label = "rms"
    rpn.globl.param_stack.push(result)


@defword(name='rnd', args=2, print_x=rpn.globl.PX_CONFIG, doc="""\
rnd   ( n places -- rounded )
Round N to PLACES number of decimal places.

NOTE: This is implemented using Python's round() function.  The behavior
of rnd can be surprising: for example, "2.675 2 rnd" gives 2.67 instead
of the expected 2.68.  This is not a bug: it is a result of the fact that
most decimal fractions cannot be represented exactly as a float.""")
def w_rnd(name):
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if    type(x) is not rpn.type.Integer \
       or type(y) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float, rpn.type.Complex]:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))
    places = x.value
    if places < 0:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_ARG, name, "X (places) may not be negative")

    if type(y) in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
        r = round(float(y.value), places)
        result = rpn.type.Integer(r) if places == 0 else rpn.type.Float(r)
    else:
        new_real = round(float(y.real()), places)
        new_imag = round(float(y.imag()), places)
        result = rpn.type.Complex(new_real, new_imag)
    rpn.globl.param_stack.push(result)


@defword(name='roll', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
roll   ( ... x -- ... )
Roll stack elements.
2 roll is equivalent to swap.
3 roll is equivalent to rot.""")
def w_roll(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))

    if x.value == 0:
        return
    if x.value < 0 or x.value > rpn.globl.param_stack.size():
        msg = "Stack index out of range"
        if not rpn.globl.param_stack.empty():
            msg += " (1..{} expected)".format(rpn.globl.param_stack.size())
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_MEMORY, name, msg)

    rpn.globl.param_stack.roll(x.value)


@defword(name='S+', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
S+   ( n -- )
Add an element to the statistics list.""")
def w_s_plus(name):
    x = rpn.globl.param_stack.pop()
    if type(x) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))

    val = float(x.value)
    rpn.globl.stat_data.append(val)


@defword(name='sci', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
sci   ( n -- )
Set scientific display.  N specifies the number of digits after
the decimal point.""")
def w_sci(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))

    if x.value < 0 or x.value >= rpn.globl.PRECISION_MAX:
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_ARG, name, "Precision '{}' out of range (0..{} expected)".format(x.value, rpn.globl.PRECISION_MAX - 1))

    rpn.globl.disp_stack.top().style = "sci"
    rpn.globl.disp_stack.top().prec = x.value
    rpn.flag.clear_flag(rpn.flag.F_DISP_FIX)
    rpn.flag.clear_flag(rpn.flag.F_DISP_ENG)


@defword(name='scopes', hidden=True, print_x=rpn.globl.PX_IO, doc="""\
scopes   ( -- )
Print information on all available scopes.""")
def w_scopes(name):             # pylint: disable=unused-argument
    for (i, item) in rpn.globl.scope_stack.items_bottom_to_top():
        rpn.globl.lnwrite("{} Scope \"{}\": ".format(i, item.name))
        rpn.globl.writeln("Vars={}".format([str(x) for x in item.variables().values()]))
        #rpn.globl.lnwriteln("Words: {}".format([str(x) for x in item.words().values()]))

@defword(name='sf', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
sf   ( f -- )
Set flag.""")
def w_sf(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    flag = x.value
    if flag < 0 or flag >= rpn.flag.MAX:
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_MEMORY, name, "Flag {} out of range (0..{} expected)".format(flag, rpn.flag.MAX - 1))
    if flag >= rpn.flag.FENCE:
        rpn.globl.param_stack.push(x)
        throw(X_READ_ONLY, name, "Flag {} cannot be modified".format(flag))
    rpn.flag.set_flag(flag)


@defword(name='shdebug', print_x=rpn.globl.PX_IO, doc="""\
shdebug   ( -- )
Show active debug levels.""")
def w_showdebug(name):          # pylint: disable=unused-argument
    rpn.globl.lnwriteln("Debugging is {}".format("enabled" if rpn.flag.flag_set_p(rpn.flag.F_DEBUG_ENABLED) else "disabled"))

    dbgs = dict()
    for (resource, level) in rpn.debug.debug_levels.items():
        if level != 0:
            dbgs[resource] = "{}={}".format(resource, level)
    sorted_dbgs = []
    for key in sorted(dbgs, key=str.casefold):
        sorted_dbgs.append(dbgs[key])
    rpn.globl.list_in_columns(sorted_dbgs, rpn.globl.scr_cols.obj.value - 1)


@defword(name='shdebug!', print_x=rpn.globl.PX_IO, hidden=True, doc="""\
shdebug   ( -- )
Show all debug levels.""")
def w_showdebug_bang(name):     # pylint: disable=unused-argument
    rpn.globl.lnwriteln("Debugging is {}".format("enabled" if rpn.flag.flag_set_p(rpn.flag.F_DEBUG_ENABLED) else "disabled"))

    dbgs = dict()
    for (resource, level) in rpn.debug.debug_levels.items():
        dbgs[resource] = "{}={}".format(resource, level)
    sorted_dbgs = []
    for key in sorted(dbgs, key=str.casefold):
        sorted_dbgs.append(dbgs[key])
    rpn.globl.list_in_columns(sorted_dbgs, rpn.globl.scr_cols.obj.value - 1)


@defword(name='shdisp', print_x=rpn.globl.PX_CONFIG, doc="""\
shdisp   ( -- )
Show current display setting.""")
def w_shdisp(name):             # pylint: disable=unused-argument
    rpn.globl.writeln(rpn.globl.disp_stack.top())


@defword(name='shfin', print_x=rpn.globl.PX_IO, doc="""\
shfin   ( -- )
Show financial variables.""")
def w_shfin(name):              # pylint: disable=unused-argument
    rpn.globl.lnwrite()
    rpn.globl.writeln("N:   {}".format(rpn.globl.gfmt(rpn.tvm.N  .obj.value) if rpn.tvm.N  .defined() else "[Not set]"))
    rpn.globl.writeln("INT: {}".format(rpn.globl.gfmt(rpn.tvm.INT.obj.value) if rpn.tvm.INT.defined() else "[Not set]"))
    rpn.globl.writeln("PV:  {}".format(rpn.globl.gfmt(rpn.tvm.PV. obj.value) if rpn.tvm.PV .defined() else "[Not set]"))
    rpn.globl.writeln("PMT: {}".format(rpn.globl.gfmt(rpn.tvm.PMT.obj.value) if rpn.tvm.PMT.defined() else "[Not set]"))
    rpn.globl.writeln("FV:  {}".format(rpn.globl.gfmt(rpn.tvm.FV .obj.value) if rpn.tvm.FV .defined() else "[Not set]"))
    rpn.globl.writeln("--------------")
    rpn.globl.writeln("CF:  {}".format(rpn.globl.gfmt(rpn.tvm.CF .obj.value) if rpn.tvm.CF .defined() else "[Not set]"))
    rpn.globl.writeln("PF:  {}".format(rpn.globl.gfmt(rpn.tvm.PF .obj.value) if rpn.tvm.PF .defined() else "[Not set]"))

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
shflag   ( -- )
Show status of all flags.""")
def w_shflag(name):             # pylint: disable=unused-argument
    flags = []
    for f in range(rpn.flag.MAX):
        flags.append("%02d:%s" % (f, "YES" if rpn.flag.flag_set_p(f) else "no "))

    rpn.globl.list_in_columns(flags, rpn.globl.scr_cols.obj.value - 1)


@defword(name='show', print_x=rpn.globl.PX_IO, doc="""\
show   ( -- )
Show the definition of the following word.""")
def w_show(name):               # pylint: disable=unused-argument
    pass                        # Grammar rules handle this word


@defword(name='shreg', print_x=rpn.globl.PX_IO, doc="""\
shreg   ( -- )
Show status of all registers.""")
def w_shreg(name):              # pylint: disable=unused-argument
    (reg_size, _) = rpn.globl.lookup_variable("SIZE")
    regs = []
    regs.append("I=%s" % rpn.globl.gfmt(rpn.globl.register['I']))
    for r in range(reg_size.obj.value):
        regs.append("R%02d=%s" % (r, rpn.globl.gfmt(rpn.globl.register[r])))

    rpn.globl.list_in_columns(regs, rpn.globl.scr_cols.obj.value - 1)


@defword(name='shstat', print_x=rpn.globl.PX_IO, doc="""\
shstat   ( -- )
Print the statistics list.""")
def w_shstat(name):             # pylint: disable=unused-argument
    if len(rpn.globl.stat_data) == 0:
        rpn.globl.writeln("No statistics data")
    else:
        rpn.globl.writeln(rpn.globl.stat_data)


@defword(name='sign', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
sign   ( n -- sign )
Signum function.  Returns -1, 0, or 1.""")
def w_sign(name):
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
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='sin', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
sin   ( angle -- sine )
Sine.""")
def w_sin(name):
    x = rpn.globl.param_stack.pop()
    if type(x) not in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational, rpn.type.Complex]:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))

    unit_attached = False
    if x.has_uexpr_p() and x.uexpr.dim() != rpn.unit.category["Null"].dim():
        if x.uexpr.dim() != rpn.unit.category["Angle"].dim():
            rpn.globl.param_stack.push(x)
            throw(X_INCONSISTENT_UNITS, name, "'{}' is not an angular unit".format(x.uexpr))
        unit_attached = True

    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        if unit_attached:
            angle = x.ubase_convert(name) # convert to radians
            result = rpn.type.Float(math.sin(float(angle.value)))
        else:
            result = rpn.type.Float(math.sin(rpn.globl.convert_mode_to_radians(float(x.value))))
    elif type(x) is rpn.type.Complex:
        result = rpn.type.Complex.from_complex(cmath.sin(x.value))

    rpn.globl.param_stack.push(result)


@defword(name='sinc', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
sinc   ( x -- sinc )
Sine cardinal, aka sampling function.

DEFINITION:
           sin x
sinc(x) = -------
             x

sinc(0) == 1""")
def w_sinc(name):
    x = rpn.globl.param_stack.pop()
    if type(x) not in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational, rpn.type.Complex]:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
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
sinh   ( angle -- sine_h )
Hyperbolic sine.

DEFINITION:
          e^x - e^(-x)
sinh(x) = ------------
               2""")
def w_sinh(name):
    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        result = rpn.type.Float(math.sinh(float(x.value)))
    elif type(x) is rpn.type.Complex:
        result = rpn.type.Complex.from_complex(cmath.sinh(x.value))
    else:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='sleep', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
sleep   ( n -- )
Sleep for N seconds.  N may be fractional.""")
def w_sleep(name):
    x = rpn.globl.param_stack.pop()
    if type(x) not in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    sleep_time = float(x.value)
    time.sleep(sleep_time)


@defword(name='sph->rct', args=3, print_x=rpn.globl.PX_COMPUTE, doc="""\
sph->rct   ( phi theta r -- z y x )
Convert spherical coordinates to rectangular.

DEFINITION:
x = r * sin(theta) * cos(phi)
y = r * sin(theta) * sin(phi)
z = r * cos(theta)""")
def w_sph_to_rct(name):
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    z = rpn.globl.param_stack.pop()
    if    type(x) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float] \
       or type(y) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float] \
       or type(z) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
        rpn.globl.param_stack.push(z)
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({} {} {})".format(typename(z), typename(y), typename(x)))
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
sq   ( x -- x^2 )
Square.""")
def w_sq(name):
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
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))

    if x.has_uexpr_p():
        result.uexpr = x.uexpr.raise_to_power(2)
    rpn.globl.param_stack.push(result)


@defword(name='sqrt', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
sqrt   ( x -- sqrt[x] )
Square root.  Negative X returns a complex number.""")
def w_sqrt(name):
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
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='std', print_x=rpn.globl.rpn.globl.PX_CONFIG, doc="""\
std   ( -- )
Set display mode to standard.""")
def w_std(name):                # pylint: disable=unused-argument
    rpn.globl.disp_stack.top().style = "std"
    rpn.flag.set_flag(rpn.flag.F_DISP_FIX)
    rpn.flag.set_flag(rpn.flag.F_DISP_ENG)
    for bit in range(4):
        rpn.flag.clear_flag(39 - bit)


@defword(name='stdev', print_x=rpn.globl.PX_COMPUTE, doc="""\
stdev   ( -- st.dev )
Return the sample standard deviation of the statistics data.""")
def w_stdev(name):
    if len(rpn.globl.stat_data) < 2:
        throw(X_BAD_DATA, name, "Insufficient statistics data (2 required)")
    try:
        s = statistics.stdev(rpn.globl.stat_data)
    except statistics.StatisticsError as e:
        throw(X_BAD_DATA, name, "{}".format(str(e)))
    result = rpn.type.Float(s)
    result.label = "stdev"
    rpn.globl.param_stack.push(result)


@defword(name='sto', args=2, print_x=rpn.globl.PX_CONFIG, doc="""\
sto   ( y reg -- )
Store value Y into register X.""")
def w_sto(name):
    (reg_size, _) = rpn.globl.lookup_variable("SIZE")

    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))
    reg = x.value
    if reg < 0 or reg >= reg_size.obj.value:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_MEMORY, name, "Register {} out of range (0..{} expected)".format(reg, reg_size.obj.value - 1))
    if type(y) in [rpn.type.Float, rpn.type.Complex]:
        rpn.globl.register[reg] = y
    else:
        rpn.globl.register[reg] = rpn.type.Float(y.value)


@defword(name='stoI', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
stoI   ( x -- )
Store X into register I.  Do not confuse this with stoi, which
stores X into the register referenced by I.""")
def w_stoI(name):               # pylint: disable=unused-argument
    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Float, rpn.type.Complex]:
        rpn.globl.register['I'] = x
    else:
        rpn.globl.register['I'] = rpn.type.Float(x.value)


@defword(name='stoi', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
stoi   ( x -- )
Store X into the register referenced by I.  Do not confuse this with
stoI, which stores X directly into the I register.""")
def w_stoi(name):
    (reg_size, _) = rpn.globl.lookup_variable("SIZE")

    I = rpn.globl.register['I']
    if type(I) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(I)))
    Ival = int(I.value)
    if Ival < 0 or Ival >= reg_size.obj.value:
        throw(X_INVALID_MEMORY, name, "Register {} out of range (0..{} expected)".format(Ival, reg_size.obj.value - 1))

    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Float, rpn.type.Complex]:
        rpn.globl.register[Ival] = x
    else:
        rpn.globl.register[Ival] = rpn.type.Float(x.value)


@defword(name='T_COMPLEX', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
T_COMPLEX   ( -- 3 )
Type number for Complex.""")
def w_T_COMPLEX(name):          # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(rpn.type.T_COMPLEX))


@defword(name='T_FLOAT', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
T_FLOAT   ( -- 2 )
Type number for Float.""")
def w_T_FLOAT(name):            # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(rpn.type.T_FLOAT))


@defword(name='T_INTEGER', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
T_INTEGER   ( -- 0 )
Type number for Integer.""")
def w_T_INTEGER(name):          # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(rpn.type.T_INTEGER))


@defword(name='T_LIST', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
T_LIST   ( -- 7 )
Type number for List.""")
def w_T_LIST(name):             # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(rpn.type.T_LIST))


@defword(name='T_MATRIX', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
T_MATRIX   ( -- 5 )
Type number for Matrix.""")
def w_T_MATRIX(name):           # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(rpn.type.T_MATRIX))


@defword(name='T_RATIONAL', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
T_RATIONAL   ( -- 1 )
Type number for Rational.""")
def w_T_RATIONAL(name):         # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(rpn.type.T_RATIONAL))


@defword(name='T_STRING', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
T_STRING   ( -- 6 )
Type number for String.""")
def w_T_STRING(name):           # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(rpn.type.T_STRING))


@defword(name='T_VECTOR', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
T_VECTOR   ( -- 4 )
Type number for Vector.""")
def w_T_VECTOR(name):           # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(rpn.type.T_VECTOR))


@defword(name='tan', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
tan   ( angle -- tangent )
Tangent.

WARNING:
Angle must not be 90 degrees (TAU/4 radians).""")
def w_tan(name):
    x = rpn.globl.param_stack.pop()
    if type(x) not in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational, rpn.type.Complex]:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))

    unit_attached = False
    if x.has_uexpr_p() and x.uexpr.dim() != rpn.unit.category["Null"].dim():
        if x.uexpr.dim() != rpn.unit.category["Angle"].dim():
            rpn.globl.param_stack.push(x)
            throw(X_INCONSISTENT_UNITS, name, "'{}' is not an angular unit".format(x.uexpr))
        unit_attached = True

    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        if unit_attached:
            angle = x.ubase_convert(name).value
        else:
            angle = rpn.globl.convert_mode_to_radians(x.value)
        try:
            r = math.tan(angle)
        except ValueError:
            rpn.globl.param_stack.push(x)
            throw(X_FP_INVALID_ARG, name)
        result = rpn.type.Float(r)
    elif type(x) is rpn.type.Complex:
        try:
            r = cmath.tan(x.value)
        except ValueError:
            rpn.globl.param_stack.push(x)
            throw(X_FP_INVALID_ARG, name)
        result = rpn.type.Complex.from_complex(r)

    rpn.globl.param_stack.push(result)


@defword(name='tanh', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
tanh   ( angle -- tangent_h )
Hyperbolic tangent.

DEFINITION:
tanh(x) = sinh(x) / cosh(x)""")
def w_tanh(name):
    x = rpn.globl.param_stack.pop()
    if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational]:
        result = rpn.type.Float(math.tanh(x.value))
    elif type(x) is rpn.type.Complex:
        result = rpn.type.Complex.from_complex(cmath.tanh(x.value))
    else:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    rpn.globl.param_stack.push(result)


@defword(name='TAU', print_x=rpn.globl.PX_COMPUTE, doc="""\
TAU   ( -- 6.28318... )

DEFINITION:
Number of radians in a circle.""")
def w_TAU(name):                # pylint: disable=unused-argument
    result = rpn.type.Float(rpn.globl.TAU)
    result.uexpr = rpn.globl.uexpr["r"]
    result.label = "TAU"
    rpn.globl.param_stack.push(result)


@defword(name='tf', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
tf   ( f -- )
Toggle flag.""")
def w_tf(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    flag = x.value
    if flag < 0 or flag >= rpn.flag.MAX:
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_MEMORY, name, "Flag {} out of range (0..{} expected)".format(flag, rpn.flag.MAX - 1))
    if flag >= rpn.flag.FENCE:
        rpn.globl.param_stack.push(x)
        throw(X_READ_ONLY, name, "Flag {} cannot be modified".format(flag))
    rpn.flag.toggle_flag(flag)


@defword(name='then', args=1, print_x=rpn.globl.PX_CONTROL, doc="""\
then   ( flag -- )
Execute a conditional test.
<flag> if ... [ else ... ] then

See also: else, if""")
def w_then(name):               # pylint: disable=unused-argument
    pass                        # Grammar rules handle this word


@defword(name='throw', args=1, print_x=rpn.globl.PX_CONTROL, doc="""\
throw   ( n -- )
Throw an exception.

See also: catch""")
def w_throw(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    if x.value == 0:
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_ARG, name, "X cannot be zero")
    thrown_from = ""
    if not rpn.globl.colon_stack.empty():
        thrown_from = rpn.globl.colon_stack.top().name
    dbg("catch", 1, "{}: Throwing {} from '{}'".format(name, x.value, thrown_from))
    throw(x.value, thrown_from)


@defword(name='time', print_x=rpn.globl.PX_COMPUTE, doc="""\
time   ( -- HH.MMSS )
Current time.""")
def w_time(name):               # pylint: disable=unused-argument
    t = datetime.datetime.now().strftime("%H.%M%S")
    result = rpn.type.Float(t)
    result.label = "HH.MMSS (Current)"
    rpn.globl.param_stack.push(result)


@defword(name='time!', print_x=rpn.globl.PX_COMPUTE, doc="""\
time!   ( -- HH.MMSSssss )
High precision clock time.""")
def w_time_bang(name):          # pylint: disable=unused-argument
    t = datetime.datetime.now().strftime("%H.%M%S%f")
    result = rpn.type.Float(t)
    result.label = "HH.MMSSssss (Current)"
    rpn.globl.param_stack.push(result)


@defword(name='timeinfo', args=1, hidden=True, print_x=rpn.globl.PX_IO, doc="""\
timeinfo   ( x -- )
Show time_info() for Float.""")
def w_timeinfo(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Float:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    rpn.globl.writeln("timeinfo: {}".format(x.time_info()))


@defword(name='trn', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
trn   ( mat -- mat_T )
Transpose a matrix.""")
def w_trn(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is rpn.type.Vector:
        # Transposing a vector is allowed but has no effect.
        # It does NOT "convert a 1-D array into a 2D column vector".
        rpn.globl.param_stack.push(x)
        return
    if type(x) is not rpn.type.Matrix:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    t = rpn.type.Matrix.from_numpy(np.matrix.transpose(x.value))
    rpn.globl.param_stack.push(t)


@defword(name='type', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
type   ( x -- x code )
Return a code for the type of the value in X.  Unlike most other words,
type preserves the top of stack, assuming that you will still want to
operate on the value later.

__0000 - Integer  = 0
__0001 - Rational = 1
__0010 - Float    = 2
__0011 - Complex  = 3
__0100 - Vector   = 4
__0101 - Matrix   = 5
__0110 - String   = 6
__0111 - List     = 7  (not implemented)
__1000 - Symbol   = 8
__1001 - [Reserved]
__101_ - [Reserved]
__11__ - [Reserved]
_1____ - Has Unit  (type + 16)
1_____ - Has Label (type + 32)""")
def w_type(name):               # pylint: disable=unused-argument
    x = rpn.globl.param_stack.top()
    t = x.typ()
    if x.has_uexpr_p():
        t += rpn.type.T_HAS_UNIT
    if x.label is not None:
        t += rpn.type.T_HAS_LABEL
    rpn.globl.param_stack.push(rpn.type.Integer(t))


@defword(name='ubase', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
ubase   ( x -- x' )
Convert a unit-object into base (SI) units.""")
def w_ubase(name):
    x = rpn.globl.param_stack.pop()
    if not x.has_uexpr_p():
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_ARG, name, "Not a unit")

    dbg("unit", 1, "{}: Old_x={}".format(name, repr(x)))
    new_x = x.ubase_convert(name)
    dbg("unit", 1, "{}: New_x={}".format(name, repr(new_x)))
    rpn.globl.param_stack.push(new_x)


@defword(name='udim', args=1, print_x=rpn.globl.PX_IO, hidden=True, doc="""\
udim   ( x -- x )
Print unit dimension vector.""")
def w_udim(name):
    x = rpn.globl.param_stack.top()
    if not x.has_uexpr_p():
        throw(X_INVALID_ARG, name, "Not a unit")
    rpn.globl.lnwriteln(x.uexpr.dim())


# FIXME - Not done
# XXX Double check example and general algorthm in HP48 manual
@defword(name='ufact', args=1, str_args=1, print_x=rpn.globl.PX_COMPUTE, hidden=True, doc="""\
ufact   ( x -- x' )  [ unit -- ]
Factor out one unit from another.

EXAMPLE:
    1_J "N" ufact
1_m""")
def w_ufact(name):
    x = rpn.globl.param_stack.pop()
    if not x.has_uexpr_p():
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_ARG, name, "Not a unit")
    dbg("unit", 2, "{}: orig X={}".format(name, repr(x)))

    ustr = rpn.globl.string_stack.pop()
    ue = rpn.unit.try_parsing(ustr.value)
    if ue is None:
        rpn.globl.param_stack.push(x)
        rpn.globl.string_stack.push(ustr)
        throw(X_INVALID_UNIT, name, ustr.value)

    print("{}: X ={}".format(name, repr(x.uexpr)))
    print("{}: ue={}".format(name, repr(ue)))
    new_ue = rpn.unit.UExpr()
    print("{}: new_ue={}".format(name, repr(new_ue)))
    new_dim = [ adim - bdim  for adim, bdim in zip(x.uexpr.dim(), ue.dim()) ]
    print("{}: new_dim={}".format(name, repr(new_dim)))


@defword(name='undef', print_x=rpn.globl.PX_CONFIG, doc="""\
undef   ( -- )
Undefine a variable, removing it from the current scope.
undef <var>""")
def w_undef(name):              # pylint: disable=unused-argument
    pass                        # Grammar rules handle this word


@defword(name='unit>', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
unit>   ( x -- x' )  [ -- ustr ]
Separate a unit expression from the stack into its value and unit string.""")
def w_unit_from(name):
    x = rpn.globl.param_stack.top()
    if not x.has_uexpr_p():
        throw(X_INVALID_ARG, name, "X does not have a unit expression")
    ue = x.uexpr
    rpn.globl.string_stack.push(rpn.type.String(str(ue)))
    x.uexpr = None


@defword(name='unit?', args=1, print_x=rpn.globl.PX_PREDICATE, doc="""\
unit?   ( x -- bool )
Test if X has a unit expression.""")
def w_unit_query(name):         # pylint: disable=unused-argument
    x = rpn.globl.param_stack.pop()
    rc = x.has_uexpr_p()
    result = rpn.type.Integer(rc)
    rpn.globl.param_stack.push(result)


@defword(name='units', print_x=rpn.globl.PX_IO, doc="""\
units   ( -- )
List all units.

See also: ushow""")
def w_units(name):              # pylint: disable=unused-argument
    units = dict()
    for u in rpn.unit.units.values():
        if u.hidden:
            continue
        ident = u.abbrev if u.abbrev is not None else u.name
        units[ident] = ident
    sorted_units = []
    for key in sorted(units, key=str.casefold):
        sorted_units.append(units[key])
    rpn.globl.list_in_columns(sorted_units, rpn.globl.scr_cols.obj.value - 1)


@defword(name='units!', print_x=rpn.globl.PX_IO, doc="""\
units!   ( -- )
List all units with more details.""")
def w_units_bang(name):         # pylint: disable=unused-argument
    units = dict()
    for u in rpn.unit.units.values():
        cat = rpn.unit.Category.lookup_by_dim(u.dim())
        ident = str(u)
        if u.abbrev is not None:
            s = u.abbrev + " ({}".format(u.name)
            if cat is not None:
                s += ", {}".format(cat.measure)
            s += ")"
        else:
            s = u.name
            if cat is not None:
                s += " ({})".format(cat.measure)
        units[ident] = s
    sorted_units = []
    for key in sorted(units, key=str.casefold):
        sorted_units.append(units[key])
    rpn.globl.list_in_columns(sorted_units, rpn.globl.scr_cols.obj.value - 1)


@defword(name='until', print_x=rpn.globl.PX_CONTROL, doc="""\
until   ( bool -- )
Execute an indefinite loop until a condition is satisfied.
begin ... <flag> until

leave will exit the loop early.  Note that the effect of the test in
begin...while is opposite that in begin...until: the loop repeats
while something is true, rather than until it becomes true.

See also: again, begin, leave, repeat, while""")
def w_until(name):              # pylint: disable=unused-argument
    pass                        # Grammar rules handle this word


if rpn.globl.have_module('numpy'):
    @defword(name='v>', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
v>   ( v -- ... )
Decompose a vector into stack elements.""")
    def v_from(name):
        x = rpn.globl.param_stack.pop()
        if type(x) is not rpn.type.Vector:
            rpn.globl.param_stack.push(x)
            throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
        for elem in x.value:
            rpn.globl.param_stack.push(rpn.globl.to_rpn_class(elem))


@defword(name='var', print_x=rpn.globl.PX_COMPUTE, doc="""\
var   ( -- var )
Return the sample variance of the statistics data.""")
def w_var(name):
    if len(rpn.globl.stat_data) < 2:
        throw(X_BAD_DATA, name, "Insufficient statistics data (2 required)")
    try:
        v = statistics.variance(rpn.globl.stat_data)
    except statistics.StatisticsError as e:
        throw(X_BAD_DATA, name, "{}".format(str(e)))
    rpn.globl.param_stack.push(rpn.type.Float(v))


@defword(name='variable', print_x=rpn.globl.PX_CONFIG, doc="""\
variable   ( -- )
Declare a variable.  Initial state is undefined.
variable <var>""")
def w_variable(name):           # pylint: disable=unused-argument
    pass                        # Grammar rules handle this word


@defword(name='vars', print_x=rpn.globl.PX_IO, doc="""\
vars   ( -- )
List variables and their values.""")
def w_vars(name):               # pylint: disable=unused-argument
    for (_, scope) in rpn.globl.scope_stack.items_top_to_bottom():
        if rpn.globl.scope_stack.size() > 1:
            rpn.globl.lnwriteln("Scope {}:".format(scope.name))
        my_vars = dict()
        for v in scope.variables():
            var = scope.variable(v)
            if var.hidden:
                continue
            if not var.defined():
                disp = ':[undef]'
            elif typename(var.obj) == "String":
                disp = '="{}"'.format(var.obj.value)
            else:
                disp = '={}'.format(var.obj.value)
            my_vars[var.name] = "{}{}".format(var.name, disp)
        sorted_vars = []
        for key in sorted(my_vars, key=str.casefold):
            sorted_vars.append(my_vars[key])
        rpn.globl.list_in_columns(sorted_vars, rpn.globl.scr_cols.obj.value - 1)


@defword(name='ver!', print_x=rpn.globl.PX_IO, hidden=True, doc="""\
ver!   ( -- )
Print version information for rpn and Python modules""")
def w_ver_bang(name):           # pylint: disable=unused-argument
    rpn.globl.show_version_info()


@defword(name='vlist', print_x=rpn.globl.PX_IO, doc="""\
vlist   ( -- )
Print the list of defined words.  Only words in the root scope are shown.

See also: words""")
def w_vlist(name):            # pylint: disable=unused-argument
    # This is nice, but it shows hidden words:
    # rpn.globl.list_in_columns(sorted([x for x in root_scope.words()],
    #                           key=str.casefold), rpn.globl.scr_cols.obj.value - 1)
    words = dict()
    for wordname in rpn.globl.root_scope.words():
        word = rpn.globl.root_scope.word(wordname)
        if word.hidden:
            continue
        words[word.name] = word.name
    sorted_words = []
    for key in sorted(words, key=str.casefold):
        sorted_words.append(words[key])
    rpn.globl.list_in_columns(sorted_words, rpn.globl.scr_cols.obj.value - 1)


@defword(name='vlist!', hidden=True, print_x=rpn.globl.PX_IO, doc="""\
vlist!   ( -- )
Print the list of defined words.  Only words in the root scope are shown.

See also: vlist, words""")
def w_vlist_bang(name):       # pylint: disable=unused-argument
    words = dict()
    for wordname in rpn.globl.root_scope.words():
        word = rpn.globl.root_scope.word(wordname)
        words[word.name] = word.name
    sorted_words = []
    for key in sorted(words, key=str.casefold):
        sorted_words.append(words[key])
    rpn.globl.list_in_columns(sorted_words, rpn.globl.scr_cols.obj.value - 1)


@defword(name='while', print_x=rpn.globl.PX_CONTROL, doc="""\
while   ( bool -- )
Execute an indefinite loop while a condition is satisfied.
begin ... <flag> while ... repeat

leave will exit the loop early.  Note that the effect of the test in
begin...while is opposite that in begin...until: the loop repeats
while something is true, rather than until it becomes true.

See also: again, begin, leave, repeat, until""")
def w_while(name):              # pylint: disable=unused-argument
    pass                        # Grammar rules handle this word


@defword(name='words', print_x=rpn.globl.PX_IO, doc="""\
word   ( -- )
Print the list of user-defined words.

See also: vlist""")
def w_words(name):              # pylint: disable=unused-argument
    rpn.globl.list_in_columns(sorted([x[0] for x in rpn.globl.root_scope.unprotected_words()],
                                     key=str.casefold), rpn.globl.scr_cols.obj.value - 1)


@defword(name='x<>I', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
x<>I   ( x -- I )
Exchange X with the value of register I.  Do not confuse this with x<>i,
which exchanges X with the contents of the register referenced by I.""")
def w_x_exchange_I(name):       # pylint: disable=unused-argument
    x = rpn.globl.param_stack.pop()
    rpn.globl.param_stack.push(rpn.globl.register['I'])
    if type(x) in [rpn.type.Float, rpn.type.Complex]:
        rpn.globl.register['I'] = x
    else:
        rpn.globl.register['I'] = rpn.type.Float(x.value)


@defword(name='x<>i', args=1, print_x=rpn.globl.PX_CONFIG, doc="""\
x<>i   ( x -- (i) )
Exchange X with contents of the register referenced by I.
Do not confuse this with x<>I, which exchanges X with I directly.""")
def w_x_exchange_indirect_i(name):
    (reg_size, _) = rpn.globl.lookup_variable("SIZE")

    I = rpn.globl.register['I']
    if type(I) not in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(I)))
    Ival = int(I.value)
    if Ival < 0 or Ival >= reg_size.obj.value:
        throw(X_INVALID_MEMORY, name, "Register {} out of range (0..{} expected)".format(Ival, reg_size.obj.value - 1))

    x = rpn.globl.param_stack.pop()
    rpn.globl.param_stack.push(rpn.globl.register[Ival])
    if type(x) in [rpn.type.Float, rpn.type.Complex]:
        rpn.globl.register[Ival] = x
    else:
        rpn.globl.register[Ival] = rpn.type.Float(x.value)


@defword(name='X_ABORT', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
ABORT""")
def w_X_ABORT(name):            # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_ABORT))

@defword(name='X_ABORT_QUOTE', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
ABORT" """)
def w_X_ABORT_QUOTE(name):      # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_ABORT_QUOTE))

@defword(name='X_STACK_OVERFLOW', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Stack overflow""")
def w_X_STACK_OVERFLOW(name):   # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_STACK_OVERFLOW))

@defword(name='X_STACK_UNDERFLOW', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Stack underflow""")
def w_X_STACK_UNDERFLOW(name):  # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_STACK_UNDERFLOW))

@defword(name='X_RSTACK_OVERFLOW', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Return stack overflow""")
def w_X_RSTACK_OVERFLOW(name):  # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_RSTACK_OVERFLOW))

@defword(name='X_RSTACK_UNDERFLOW', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Return stack underflow""")
def w_X_RSTACK_UNDERFLOW(name): # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_RSTACK_UNDERFLOW))

@defword(name='X_DO_NESTING', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
DO-loops nested too deeply during execution""")
def w_X_DO_NESTING(name):       # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_DO_NESTING))

@defword(name='X_DICT_OVERFLOW', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Dictionary overflow""")
def w_X_DICT_OVERFLOW(name):    # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_DICT_OVERFLOW))

@defword(name='X_INVALID_MEMORY', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Invalid memory address""")
def w_X_INVALID_MEMORY(name):   # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_INVALID_MEMORY))

@defword(name='X_DIVISION_BY_ZERO', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Division by zero""")
def w_X_DIVISION_BY_ZERO(name): # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_DIVISION_BY_ZERO))

@defword(name='X_RESULT_OO_RANGE', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Result out of range""")
def w_X_RESULT_OO_RANGE(name):  # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_RESULT_OO_RANGE))

@defword(name='X_ARG_TYPE_MISMATCH', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Argument type mismatch""")
def w_X_ARG_TYPE_MISMATCH(name): # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_ARG_TYPE_MISMATCH))

@defword(name='X_UNDEFINED_WORD', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Undefined word""")
def w_X_UNDEFINED_WORD(name):   # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_UNDEFINED_WORD))

@defword(name='X_COMPILE_ONLY', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Interpreting a compile-only word""")
def w_X_COMPILE_ONLY(name):     # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_COMPILE_ONLY))

@defword(name='X_INVALID_FORGET', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Invalid FORGET
(Do not use, prefer X_PROTECTED)""")
def w_X_INVALID_FORGET(name):   # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_INVALID_FORGET))

@defword(name='X_ZERO_LEN_STR', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Attempt to use a zero-length string as a name""")
def w_X_ZERO_LEN_STR(name):     # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_ZERO_LEN_STR))

@defword(name='X_PIC_STRING_OVERFLOW', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Pictured numeric output string overflow""")
def w_X_PIC_STRING_OVERFLOW(name): # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_PIC_STRING_OVERFLOW))

@defword(name='X_STRING_OVERFLOW', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Parsed string overflow""")
def w_X_STRING_OVERFLOW(name):  # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_STRING_OVERFLOW))

@defword(name='X_NAME_TOO_LONG', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Definition name too long""")
def w_X_NAME_TOO_LONG(name):    # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_NAME_TOO_LONG))

@defword(name='X_READ_ONLY', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Write to a read-only location""")
def w_X_READ_ONLY(name):        # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_READ_ONLY))

@defword(name='X_UNSUPPORTED', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Unsupported operation""")
def w_X_UNSUPPORTED(name):      # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_UNSUPPORTED))

@defword(name='X_CTL_STRUCTURE', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Control structure mismatch""")
def w_X_CTL_STRUCTURE(name):    # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_CTL_STRUCTURE))

@defword(name='X_ALIGNMENT', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Address alignment exception""")
def w_X_ALIGNMENT(name):        # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_ALIGNMENT))

@defword(name='X_INVALID_ARG', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Invalid argument""")
def w_X_INVALID_ARG(name):      # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_INVALID_ARG))

@defword(name='X_RSTACK_IMBALANCE', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Return stack imbalance""")
def w_X_RSTACK_IMBALANCE(name): # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_RSTACK_IMBALANCE))

@defword(name='X_LOOP_PARAMS', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Loop parameters unavailable""")
def w_X_LOOP_PARAMS(name):      # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_LOOP_PARAMS))

@defword(name='X_INVALID_RECURSION', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Invalid recursion""")
def w_X_INVALID_RECURSION(name): # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_INVALID_RECURSION))

@defword(name='X_INTERRUPT', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
User interrupt""")
def w_X_INTERRUPT(name):        # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_INTERRUPT))

@defword(name='X_NESTING', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Compiler nesting""")
def w_X_NESTING(name):          # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_NESTING))

@defword(name='X_OBSOLETE', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Obsolescent feature""")
def w_X_OBSOLETE(name):         # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_OBSOLETE))

@defword(name='X_BODY', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
>BODY used on a non-CREATEd definition""")
def w_X_BODY(name):             # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_BODY))

@defword(name='X_INVALID_NAME', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Invalid name argument""")
def w_X_INVALID_NAME(name):     # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_INVALID_NAME))

@defword(name='X_BLK_READ', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Block read exception""")
def w_X_BLK_READ(name):         # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_BLK_READ))

@defword(name='X_BLK_WRITE', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Block write exception""")
def w_X_BLK_WRITE(name):        # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_BLK_WRITE))

@defword(name='X_INVALID_BLK_NUM', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Invalid block number""")
def w_X_INVALID_BLK_NUM(name):  # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_INVALID_BLK_NUM))

@defword(name='X_INVALID_FILE_POS', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Invalid file position""")
def w_X_INVALID_FILE_POS(name): # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_INVALID_FILE_POS))

@defword(name='X_FILE_IO', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
File I/O exception""")
def w_X_FILE_IO(name):          # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_FILE_IO))

@defword(name='X_NON_EXISTENT_FILE', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Non-existent file""")
def w_X_NON_EXISTENT_FILE(name): # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_NON_EXISTENT_FILE))

@defword(name='X_EOF', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Unexpected end of file""")
def w_X_EOF(name):              # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_EOF))

@defword(name='X_INVALID_BASE', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Invalid BASE for floating point conversion""")
def w_X_INVALID_BASE(name):     # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_INVALID_BASE))

@defword(name='X_PRECISION_LOSS', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Loss of precision""")
def w_X_PRECISION_LOSS(name):   # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_PRECISION_LOSS))

@defword(name='X_FP_DIVISION_BY_ZERO', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Floating-point divide by zero""")
def w_X_FP_DIVISION_BY_ZERO(name): # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_FP_DIVISION_BY_ZERO))

@defword(name='X_FP_RESULT_OO_RANGE', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Floating-point result out of range""")
def w_X_FP_RESULT_OO_RANGE(name): # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_FP_RESULT_OO_RANGE))

@defword(name='X_FP_STACK_OVERFLOW', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Floating-point stack overflow""")
def w_X_FP_STACK_OVERFLOW(name): # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_FP_STACK_OVERFLOW))

@defword(name='X_FP_STACK_UNDERFLOW', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Floating-point stack underflow""")
def w_X_FP_STACK_UNDERFLOW(name): # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_FP_STACK_UNDERFLOW))

@defword(name='X_FP_INVALID_ARG', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Floating-point invalid argument""")
def w_X_FP_INVALID_ARG(name):   # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_FP_INVALID_ARG))

@defword(name='X_COMP_WORD_DEL', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Compilation word list deleted""")
def w_X_COMP_WORD_DEL(name):    # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_COMP_WORD_DEL))

@defword(name='X_INVALID_POSTPONE', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Invalid POSTPONE""")
def w_X_INVALID_POSTPONE(name): # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_INVALID_POSTPONE))

@defword(name='X_SO_OVERFLOW', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Search-order overflow""")
def w_X_SO_OVERFLOW(name):      # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_SO_OVERFLOW))

@defword(name='X_SO_UNDERFLOW', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Search-order underflow""")
def w_X_SO_UNDERFLOW(name):     # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_SO_UNDERFLOW))

@defword(name='X_COMP_WORD_CHG', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Compilatin word list changed""")
def w_X_COMP_WORD_CHG(name):    # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_COMP_WORD_CHG))

@defword(name='X_CTL_STACK_OVERFLOW', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Control-flow stack overflow""")
def w_X_CTL_STACK_OVERFLOW(name): # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_CTL_STACK_OVERFLOW))

@defword(name='X_XSTACK_OVERFLOW', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Exception stack overflow""")
def w_X_XSTACK_OVERFLOW(name):  # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_XSTACK_OVERFLOW))

@defword(name='X_FP_UNDERFLOW', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Floating-point underflow""")
def w_X_FP_UNDERFLOW(name):     # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_FP_UNDERFLOW))

@defword(name='X_FP_FAULT', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Floating-point unidentified fault""")
def w_X_FP_FAULT(name):         # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_FP_FAULT))

@defword(name='X_QUIT', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
QUIT""")
def w_X_QUIT(name):             # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_QUIT))

@defword(name='X_CHAR_IO', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Exception in sending or receiving a character""")
def w_X_CHAR_IO(name):          # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_CHAR_IO))

@defword(name='X_IF_THEN', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
[IF], [ELSE], or [THEN] exception""")
def w_X_IF_THEN(name):          # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_IF_THEN))

@defword(name='X_LEAVE', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
LEAVE""")
def w_X_LEAVE(name):            # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_LEAVE))

@defword(name='X_EXIT', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
EXIT""")
def w_X_EXIT(name):             # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_EXIT))

@defword(name='X_FP_NAN', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Floating-point Not a Number""")
def w_X_FP_NAN(name):           # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_FP_NAN))

@defword(name='X_INSUFF_PARAMS', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Insufficient parameters""")
def w_X_INSUFF_PARAMS(name):    # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_INSUFF_PARAMS))

@defword(name='X_INSUFF_STR_PARAMS', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Insufficient string parameters""")
def w_X_INSUFF_STR_PARAMS(name): # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_INSUFF_STR_PARAMS))

@defword(name='X_CONFORMABILITY', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Comformability error""")
def w_X_CONFORMABILITY(name):   # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_CONFORMABILITY))

@defword(name='X_BAD_DATA', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Bad data""")
def w_X_BAD_DATA(name):         # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_BAD_DATA))

@defword(name='X_SYNTAX', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Syntax error""")
def w_X_SYNTAX(name):           # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_SYNTAX))

@defword(name='X_NO_SOLUTION', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
No solution""")
def w_X_NO_SOLUTION(name):      # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_NO_SOLUTION))

@defword(name='X_UNDEFINED_VARIABLE', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Undefined variable""")
def w_X_UNDEFINED_VARIABLE(name): # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_UNDEFINED_VARIABLE))

@defword(name='X_PROTECTED', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Protected""")
def w_X_PROTECTED(name):        # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_PROTECTED))

@defword(name='X_INVALID_UNIT', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Invalid unit""")
def w_X_INVALID_UNIT(name):     # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_INVALID_UNIT))

@defword(name='X_INCONSISTENT_UNITS', hidden=True, print_x=rpn.globl.PX_COMPUTE, doc="""\
Inconsistent units""")
def w_X_INCONSISTENT_UNITS(name): # pylint: disable=unused-argument
    rpn.globl.param_stack.push(rpn.type.Integer(X_INCONSISTENT_UNITS))


@defword(name='xor', args=2, print_x=rpn.globl.PX_PREDICATE, doc="""\
xor   ( flag flag -- flag )
Logical XOR (exclusive OR).

NOTE: This is not a bitwise XOR - use bitxor for that.""")
def w_logxor(name):
    x = rpn.globl.param_stack.pop()
    y = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Integer or type(y) is not rpn.type.Integer:
        rpn.globl.param_stack.push(y)
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({} {})".format(typename(y), typename(x)))

    rpn.globl.param_stack.push(rpn.type.Integer(bool(x.value) != bool(y.value)))


@defword(name='zer', args=1, print_x=rpn.globl.PX_COMPUTE, doc="""\
zer   ( v -- m )
Create a zero vector or matrix.""")
def w_zer(name):
    x = rpn.globl.param_stack.pop()
    if type(x) is not rpn.type.Vector:
        rpn.globl.param_stack.push(x)
        throw(X_ARG_TYPE_MISMATCH, name, "({})".format(typename(x)))
    xs = x.size()

    if xs == 1:
        size = int(x.value.item(0))
        if size <= 0:
            rpn.globl.param_stack.push(x)
            throw(X_INVALID_ARG, name, "Dimension must be positive")
        z = rpn.type.Vector.from_ndarray(np.zeros(size))
        rpn.globl.param_stack.push(z)
    elif xs == 2:
        rows = int(x.value.item(0))
        cols = int(x.value.item(1))
        if rows <= 0 or cols <= 0:
            rpn.globl.param_stack.push(x)
            throw(X_INVALID_ARG, name, "Dimensions must be positive")
        z = rpn.type.Matrix.from_numpy(np.zeros((rows, cols)))
        rpn.globl.param_stack.push(z)
    else:
        rpn.globl.param_stack.push(x)
        throw(X_INVALID_ARG, name, "Dimension vector must have only 1 or 2 elements")



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
# Parameters are Rpn objects, not values.  Units are NOT considered.
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

    BLANK  = ' '
    HFRAME = '-'
    MARK   = '*'
    ORIGIN = '+'
    VFRAME = '|'
    X_AXIS = '.'
    Y_AXIS = ':'

    ISCR   = cols - 20
    JSCR   = rows -  3
    scr = [[BLANK for i in range(1,JSCR+2)] for j in range(1,ISCR+2)]

    # Build frame
    for j in range(1, JSCR+1):
        scr[1][j] = VFRAME
        scr[ISCR][j] = VFRAME
    for i in range(2, ISCR):
        scr[i][1] = HFRAME
        scr[i][JSCR] = HFRAME
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
                scr[i][j] = Y_AXIS
            if j == jz:
                scr[i][j] = X_AXIS
            if i == iz and j == jz:
                scr[i][j] = ORIGIN

    # Populate data points
    for i in range(1, ISCR+1):
        j = 1 + int((y[i] - ysml) * dyj)
        scr[i][j] = MARK

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
class _Getch_windows:
    def __init__(self):
        import msvcrt # pylint: disable=import-error,import-outside-toplevel,unused-import

    def __call__(self):
        import msvcrt # pylint: disable=import-error,import-outside-toplevel
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
