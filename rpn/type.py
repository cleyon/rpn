'''
#############################################################################
#
#       D A T A   T Y P E S
#
#       - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#
#       NB - These aren't the values currently used by TYPE
#
#       | HP-48 OBJECT TYPE |       |
#       |-------------------+-------|
#       | Real number       |     0 |
#       | Complex number    |     1 |
#       | Character string  |     2 |
#       | Real array        |     3 |
#       | Complex array     |     4 |
#       | List              |     5 |
#       | Global name       |     6 |
#       | Local name        |     7 |
#       | Program           |     8 |
#       | Algebraic object  |     9 |
#       | Binary integer    |    10 |
#       | Graphics object   |    11 |
#       | Tagged object     |    12 |
#       | Unit object       |    13 |
#       | XLIB name         |    14 |
#       | Directory         |    15 |
#       | Library           |    16 |
#       | Backup object     |    17 |
#       |-------------------+-------|
#       | Built-in function |    18 |
#       | Built-in command  |    19 |
#       |-------------------+-------|
#       | System binary     |    20 |
#       | Extended real     |    21 |
#       | Extended complex  |    22 |
#       | Linked array      |    23 |
#       | Character         |    24 |
#       | Code object       |    25 |
#       | Library data      |    26 |
#       | External object   | 27-31 |
#
#############################################################################
'''

import copy
from   fractions import Fraction
import datetime

# Check if NumPy is available
try:
    import numpy as np
except ImportError:
    pass

# # Check if SciPy is available
# try:
#     import scipy.integrate
#     import scipy.optimize
# except ModuleNotFoundError:
#     pass
#
# # Check if Matplotlib is available
# try:
#     import matplotlib
# except ModuleNotFoundError:
#     pass

from   rpn.debug     import dbg, typename, whoami
from   rpn.exception import *   # pylint: disable=wildcard-import
import rpn.exe
import rpn.globl
import rpn.unit


T_INTEGER   = 0
T_RATIONAL  = 1
T_FLOAT     = 2
T_COMPLEX   = 3
T_VECTOR    = 4
T_MATRIX    = 5
T_STRING    = 6
T_LIST      = 7         # Not implemented yet
T_SYMBOL    = 8
T_HAS_UNIT  = 1 << 4
T_HAS_LABEL = 1 << 5


class Stackable(rpn.exe.Executable):
    def __init__(self):
        self.name   = None
        self._value = None
        self._label = None
        self._type  = None
        self._uexpr = None

    @property
    def label(self):
        return self._label

    @label.setter
    def label(self, new_label):
        self._label = new_label

    @property
    def uexpr(self):
        return self._uexpr

    @uexpr.setter
    def uexpr(self, new_uexpr):
        self._uexpr = new_uexpr

    def typ(self):
        return self._type

    def has_label_p(self):
        return self.label is not None

    def has_uexpr_p(self):
        return self.uexpr is not None

    def __call__(self, name):
        dbg("trace", 1, "trace({})".format(repr(self)))
        rpn.globl.param_stack.push(self)

    def uexpr_convert(self, new_ustr, name=""):
        if not self.has_uexpr_p():
            raise FatalErr("{}: No uexpr - caller should have checked".format(whoami()))
        ue = rpn.unit.try_parsing(new_ustr)
        if ue is None:
            throw(X_INVALID_UNIT, name, new_ustr)
        if not rpn.unit.units_conform(self.uexpr, ue):
            throw(X_CONFORMABILITY, name, '"{}", "{}"'.format(self.uexpr, ue))
        if type(self) in [rpn.type.Integer, rpn.type.Rational, rpn.type.Float]:
            new_obj = rpn.type.Float()
            new_obj.value = float(self.value)
        elif type(self) is rpn.type.Complex:
            new_obj = rpn.type.Complex()
            new_obj.value = self.value
        else:
            throw(X_ARG_TYPE_MISMATCH, name, "{} does not support units".format(typename(self)))

        new_obj.value *= self.uexpr.base_factor() * (10 ** self.uexpr.exp())
        new_obj.value /= ue.base_factor()
        new_obj.value /= (10 ** ue.exp())
        new_obj.uexpr = ue
        if self.has_label_p():
            new_obj.label = self.label
        return new_obj

    def ubase_convert(self, name=""):
        if not self.has_uexpr_p():
            raise FatalErr("{}: No uexpr - caller should have checked".format(whoami()))
        base_ustr = str(self.uexpr.ubase())
        new_obj = self.uexpr_convert(base_ustr, name)
        return new_obj

    def instfmt(self):          # pylint: disable=no-self-use
        raise FatalErr("{}: Subclass responsibility".format(whoami()))

    def __str__(self):
        s = self.instfmt()
        if self.has_uexpr_p():
            #print("{}: self.uexpr={}".format(whoami(), repr(self.uexpr)))
            s += "_{}".format(str(self.uexpr))
        if self.label is not None:
            s += " \\ {}".format(self.label)
        return s

    def __repr__(self):
        s = self.name + "[{}".format(self.instfmt())
        if self.has_uexpr_p():
            s += ",uexpr={}".format(repr(self.uexpr))
        if self.label is not None:
            s += ",label={}".format(self.label)
        return s + "]"



#############################################################################
#
#       C O M P L E X
#
#############################################################################
class Complex(Stackable):
    def __init__(self, real=0.0, imag=0.0):
        super().__init__()
        self.name   = "Complex"
        self._type  = T_COMPLEX
        self._value = complex(float(real), float(imag))
        self._uexpr  = None

    @classmethod
    def from_complex(cls, cplx):
        return cls(cplx.real, cplx.imag)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        if type(new_value) is not complex:
            throw(X_ARG_TYPE_MISMATCH, 'Complex#value()', "({})".format(typename(new_value)))
        self._value = new_value

    def real(self):
        return self.value.real

    def imag(self):
        return self.value.imag

    def zerop(self):
        return self.real() == 0.0 and self.imag() == 0.0

    def instfmt(self):
        return "({},{})".format(rpn.globl.gfmt(self.real()),
                                rpn.globl.gfmt(self.imag()))


#############################################################################
#
#       F L O A T
#
#############################################################################
class Float(Stackable):
    def __init__(self, val=0.0, uexpr=None):
        super().__init__()
        self.name   = "Float"
        self._type  = T_FLOAT
        self._value = float(val)
        self._uexpr  = uexpr

    @classmethod
    def from_string(cls, s):
        if "_" in s:
            try:
                (val, ustr) = s.split("_")
            except ValueError:
                throw(X_INVALID_UNIT, "Float#from_string", s)

            ue = rpn.unit.try_parsing(ustr)
            if ue is None:
                throw(X_INVALID_UNIT, "Float#from_string", ustr)
            return cls(val, ue)

        return cls(s, None)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        if type(new_value) is not float:
            throw(X_ARG_TYPE_MISMATCH, 'Float#value()', "({})".format(typename(new_value)))
        self._value = new_value

    def zerop(self):
        return self.value == 0.0

    def date_info(self):
        """A float in the form MM.DDYYYY might represent a date.
Extract some information about a date formatted this way.
Success:  (True, dateobj, julian)
          dateobj is datetime.date, julian is an int
Failure:  (False, None, None)"""

        match = rpn.globl.DATE_RE.match("%.6f" % self.value)
        if match is None:
            return (False, None, None)

        mm   = match.group(1)
        dd   = match.group(2)
        yyyy = match.group(3)
        try:
            dateobj = datetime.date(int(yyyy), int(mm), int(dd))
        except ValueError:
            return (False, None, None)

        # date.toordinal() returns 1 for 0001-01-01, so compensate
        julian = dateobj.toordinal() + rpn.globl.JULIAN_OFFSET
        return (True, dateobj, julian)

    def time_info(self):
        """A float in the format HH.MMSSssss might represent a time.
Extract some information about a time formatted this way.
Note: This routine can unpack an arbitrary number of hours, potentially
greater than 24, so there may not be a valid timeobj even if it parses okay.
Success:  (True, HH, MM, SS, timeobj)
Failure:  (False, None, None, None, None)"""

        match = rpn.globl.TIME_RE.match("%f" % self.value)
        if match is None:
            return (False, None, None, None, None)

        hh = int(  match.group(1))
        mm = int(  match.group(2))
        ss = float(match.group(3)) / 100.0
        try:
            timeobj = datetime.time(hh, mm, round(ss))
        except ValueError:
            timeobj = None
        return (True, hh, mm, ss, timeobj)

    def instfmt(self):
        return "{}".format(rpn.globl.gfmt(self.value))


#############################################################################
#
#       I N T E G E R
#
#############################################################################
class Integer(Stackable):
    def __init__(self, val, uexpr=None):
        super().__init__()
        self.name   = "Integer"
        self._type  = T_INTEGER
        self._value = int(val)
        self._uexpr  = uexpr

    @classmethod
    def from_string(cls, s):
        if "_" in s:
            try:
                (val, ustr) = s.split("_")
            except ValueError:
                throw(X_INVALID_UNIT, "Integer#from_string", s)

            ue = rpn.unit.try_parsing(ustr)
            if ue is None:
                throw(X_INVALID_UNIT, "Integer#from_string", ustr)
            return cls(val, ue)

        return cls(s, None)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        if type(new_value) is not int:
            throw(X_ARG_TYPE_MISMATCH, 'Integer#value()', "({})".format(typename(new_value)))
        self._value = new_value

    def zerop(self):
        return self.value == 0

    def instfmt(self):
        return "{}".format(rpn.globl.gfmt(self.value))


#############################################################################
#
#       M A T R I X
#
#############################################################################
class Matrix(Stackable):
    def __init__(self, vals):
        if not rpn.globl.have_module('numpy'):
            throw(X_UNSUPPORTED, "", "Matrices require 'numpy' library")
        super().__init__()
        self.name = "Matrix"
        self._type = T_MATRIX
        #rpn.globl.lnwriteln("{}: vals={}".format(whoami(), repr(vals)))
        self._nrows = len(vals)
        cols = -1
        vecs = []
        for x in vals.items():
            #rpn.globl.lnwriteln("x={}".format(repr(x)))
            vecs.append(x.value)
            if cols == -1:
                cols = x.size()
            else:
                if x.size() != cols:
                    throw(X_SYNTAX, "", "Matrix columns not consistent")
        self._ncols = cols
        #rpn.globl.lnwriteln("{} rows x {} columns".format(self.nrows(), self.ncols()))
        #print("vecs", vecs)
        self.value = np.array(vecs)
        #print("val",repr(self.value))

    # XXX --- change this to from_ndarray() soon
    @classmethod
    def from_numpy(cls, x):
        obj = cls(rpn.util.List())
        obj._nrows, obj._ncols = x.shape
        obj.value = x
        return obj

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        # if type(new_value) is not rpn.type.Matrix: # FIXME
        #     throw(X_ARG_TYPE_MISMATCH, 'Matrix#value()', "({})".format(typename(new_value)))
        self._value = new_value

    def has_uexpr_p(self):
        return False

    def nrows(self):
        return self._nrows

    def ncols(self):
        return self._ncols

    def instfmt(self):          # XXX
        return str(self.value)


#############################################################################
#
#       R A T I O N A L
#
#############################################################################
class Rational(Stackable):
    def __init__(self, num=0, denom=1, uexpr=None):
        super().__init__()
        self.name  = "Rational"
        self._type = T_RATIONAL
        self.value = Fraction(int(num), int(denom))
        self._uexpr = uexpr

    @classmethod
    def from_Fraction(cls, frac):
        return cls(frac.numerator, frac.denominator)

    @classmethod
    def from_string(cls, s):
        match = rpn.globl.RATIONAL_RE.match(s)
        if match is None:
            raise FatalErr("Rational pattern failed to match '{}'".format(s))
        #print("m1='{}', m2='{}', m4='{}'".format(match.group(1), match.group(2), match.group(4)))
        return cls(match.group(1), match.group(2), match.group(4))

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        if type(new_value) is not Fraction:
            throw(X_ARG_TYPE_MISMATCH, 'Rational#value()', "({})".format(typename(new_value)))
        self._value = new_value

    def numerator(self):
        return self.value.numerator

    def denominator(self):
        return self.value.denominator

    def set_num_denom(self, num, denom):
        self.value = Fraction(int(num), int(denom))

    def zerop(self):
        return self.numerator() == 0

    def instfmt(self):
        return "{}::{}".format(rpn.globl.gfmt(self.numerator()),
                               rpn.globl.gfmt(self.denominator()))


#############################################################################
#
#       S T R I N G
#
#       - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#
#       String is included here, even though it's a non Stackable class.
#
#############################################################################
class String(rpn.exe.Executable):
    def __init__(self, val):
        self.name = "String"
        self._type = T_STRING
        self.value = val

    @classmethod
    def from_string(cls, s):
        return cls("{}".format(s))

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        if type(new_value) is not str:
            throw(X_ARG_TYPE_MISMATCH, 'String#value()', "({})".format(typename(new_value)))
        self._value = new_value

    def typ(self):
        return self._type

    def __call__(self, name):
        dbg("trace", 1, "trace({})".format(repr(self)))
        rpn.globl.string_stack.push(self)

    def __str__(self):
        return '"{}"'.format(str(self.value))

    def __repr__(self):
        return 'String["{}"]'.format(self.value)


#############################################################################
#
#       S Y M B O L
#
#       - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#
#       Symbol is included here, even though it's a non Stackable class.
#
#############################################################################
class Symbol(rpn.exe.Executable):
    def __init__(self, name, word):
        self.name  = "Symbol"
        self._type = T_SYMBOL
        self._name = name
        self._word = word
        self._scope_stack = None
        self.value = name

    # @classmethod
    # def from_string(cls, s):
    #     return cls("{}".format(s))

    def typ(self):
        return self._type

    def __call__(self, name):
        dbg("trace", 1, "trace({})".format(repr(self)))
        dbg(whoami(), 3, "{}: (parse_time) orig scope stack\n{}".format(whoami(), repr(rpn.globl.scope_stack)))
        copy_scope_stack = copy.deepcopy(rpn.globl.scope_stack)
        dbg(whoami(), 3, "{}: (parse_time) copy scope stack\n{}".format(whoami(), repr(copy_scope_stack)))
        self._scope_stack = copy_scope_stack
        rpn.globl.string_stack.push(self)

    def eval(self):
        dbg("trace", 1, "trace({})".format(repr(self)))
        dbg(whoami(), 1, "{}: name={}, word={}".format(whoami(), self._name, self._word))
        if self._scope_stack is None:
            raise FatalErr("{}: Symbol {} has no scope stack".format(whoami(), str(self)))

        try:
            old_scope_stack = rpn.globl.scope_stack
            dbg(whoami(), 3, "{}: (eval time) old scope stack\n{}".format(whoami(), repr(old_scope_stack)))
            rpn.globl.scope_stack = self._scope_stack
            dbg(whoami(), 3, "{}: (eval time) new scope stack\n{}".format(whoami(), repr(rpn.globl.scope_stack)))
            self._word.__call__(self._name)
        finally:
            rpn.globl.scope_stack = old_scope_stack

    def __str__(self):
        return "'{}'".format(str(self._name))

    def __repr__(self):
        return "Symbol['{}']".format(self._name)


#############################################################################
#
#       V E C T O R
#
#############################################################################
class Vector(Stackable):
    def __init__(self):
        if not rpn.globl.have_module('numpy'):
            throw(X_UNSUPPORTED, "", "Vectors require 'numpy' library")
        super().__init__()
        self.name = "Vector"
        self._type = T_VECTOR
        self._uexpr = None
        self._value = None

    @classmethod
    def from_ndarray(cls, x):
        if x.ndim != 1:
            throw(X_INVALID_ARG, whoami(), "ndim is {}, expected 1".format(x.ndim))
        obj = cls()
        obj.value = x
        return obj

    @classmethod
    def from_rpn_List(cls, x):
        dbg(whoami(), 1, "{}: x={}".format(whoami(), x))
        obj = cls()
        obj.value = np.array([elem.value for elem in x.listval()])
        return obj

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        #numpy.ndarray ok
        # if type(new_value) is not rpn.type.Vector: # FIXME
        #     throw(X_ARG_TYPE_MISMATCH, 'Vector#value()', "({})".format(typename(new_value)))
        self._value = new_value

    def has_uexpr_p(self):
        return False

    def size(self):
        if type(self.value) is np.ndarray:
            shape = self.value.shape
            return shape[0]
        elif type(self.value) is rpn.util.List:
            #print("{}: size={}".format(whoami(), len(self.value)))
            return len(self.value)

    def instfmt(self):
        if self.size() == 0:
            return "[]"
        return "[ " + " ".join([str(rpn.globl.to_rpn_class(e)) for e in self.value]) +" ]"
