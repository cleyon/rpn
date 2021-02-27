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

from   fractions import Fraction
import datetime

T_INTEGER   = 0
T_RATIONAL  = 1
T_FLOAT     = 2
T_COMPLEX   = 3
T_VECTOR    = 4
T_MATRIX    = 5
T_STRING    = 6
T_LIST      = 7                  # Not implemented yet
T_HAS_UNIT  = 1 << 4
T_HAS_LABEL = 1 << 5

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

from   rpn.debug import dbg, typename, whoami
import rpn.exe
import rpn.globl


class Stackable(rpn.exe.Executable):
    def __init__(self):
        self._value = None
        self._label = None
        self._type  = None

    @property
    def label(self):
        return self._label

    @label.setter
    def label(self, new_label):
        self._label = new_label

    def typ(self):
        return self._type

    def __call__(self, name):
        dbg("trace", 1, "trace({})".format(repr(self)))
        rpn.globl.param_stack.push(self)


#############################################################################
#
#       C O M P L E X
#
#############################################################################
class Complex(Stackable):
    def __init__(self, real=0.0, imag=0.0):
        super().__init__()
        self.name = "Complex"
        self._type = T_COMPLEX
        self.value = complex(float(real), float(imag))

    @classmethod
    def from_complex(cls, cplx):
        return cls(cplx.real, cplx.imag)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        if type(new_value) is not complex:
            raise rpn.exception.RuntimeErr(rpn.exception.X_ARG_TYPE_MISMATCH, 'Complex#value()', "({})".format(typename(new_value)))
        self._value = new_value

    def real(self):
        return self.value.real

    def imag(self):
        return self.value.imag

    def zerop(self):
        return self.real() == 0.0 and self.imag() == 0.0

    def __str__(self):
        s = "({},{})".format(rpn.globl.fmt(self.real()), rpn.globl.fmt(self.imag()))
        l = r"  \ " + "{}".format(self.label) if self.label is not None else ""
        return s + l

    def __repr__(self):
        return "Complex[{}]".format(repr(self.value))


#############################################################################
#
#       F L O A T
#
#############################################################################
class Float(Stackable):
    def __init__(self, val=0.0):
        super().__init__()
        self.name = "Float"
        self._type = T_FLOAT
        self.value = float(val)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        if type(new_value) is not float:
            raise rpn.exception.RuntimeErr(rpn.exception.X_ARG_TYPE_MISMATCH, 'Float#value()', "({})".format(typename(new_value)))
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

    def __str__(self):
        l = r"  \ " + "{}".format(self.label) if self.label is not None else ""
        s = "{}".format(self.value)
        return s + l

    def __repr__(self):
        return "Float[{}]".format(repr(self.value))


#############################################################################
#
#       I N T E G E R
#
#############################################################################
class Integer(Stackable):
    def __init__(self, val=0):
        super().__init__()
        self.name = "Integer"
        self._type = T_INTEGER
        self.value = int(val)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        if type(new_value) is not int:
            raise rpn.exception.RuntimeErr(rpn.exception.X_ARG_TYPE_MISMATCH, 'Integer#value()', "({})".format(typename(new_value)))
        self._value = new_value

    def zerop(self):
        return self.value == 0

    def __str__(self):
        s = "{}".format(self.value)
        l = r"  \ " + "{}".format(self.label) if self.label is not None else ""
        return s + l

    def __repr__(self):
        return "Integer[{}]".format(repr(self.value))


#############################################################################
#
#       M A T R I X
#
#############################################################################
class Matrix(Stackable):
    def __init__(self, vals):
        if not rpn.globl.have_module('numpy'):
            raise rpn.exception.RuntimeErr(rpn.exception.X_UNSUPPORTED, "", "Matrices require 'numpy' library")
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
                    raise rpn.exception.RuntimeErr(rpn.exception.X_SYNTAX, "", "Matrix columns not consistent")
        self._ncols = cols
        #rpn.globl.lnwriteln("{} rows x {} columns".format(self.nrows(), self.ncols()))
        #print("vecs", vecs)
        self.value = np.array(vecs)
        #print("val",repr(self.value))

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
        #     raise rpn.exception.RuntimeErr(rpn.exception.X_ARG_TYPE_MISMATCH, 'Matrix#value()', "({})".format(typename(new_value)))
        self._value = new_value

    def nrows(self):
        return self._nrows

    def ncols(self):
        return self._ncols

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return "Matrix[{}]".format(repr(self.value))


#############################################################################
#
#       R A T I O N A L
#
#############################################################################
class Rational(Stackable):
    def __init__(self, num=0, denom=1):
        super().__init__()
        self.name = "Rational"
        self._type = T_RATIONAL
        self.value = Fraction(int(num), int(denom))

    @classmethod
    def from_Fraction(cls, frac):
        return cls(frac.numerator, frac.denominator)

    @classmethod
    def from_string(cls, s):
        match = rpn.globl.RATIONAL_RE.match(s)
        if match is None:
            raise rpn.exception.FatalErr("Rational pattern failed to match '{}'".format(s))
        return cls(match.group(1), match.group(2))

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        if type(new_value) is not Fraction:
            raise rpn.exception.RuntimeErr(rpn.exception.X_ARG_TYPE_MISMATCH, 'Rational#value()', "({})".format(typename(new_value)))
        self._value = new_value

    def numerator(self):
        return self.value.numerator

    def denominator(self):
        return self.value.denominator

    def set_num_denom(self, num, denom):
        self.value = Fraction(int(num), int(denom))

    def zerop(self):
        return self.numerator() == 0

    def __str__(self):
        s = "{}::{}".format(self.numerator(), self.denominator())
        l = r"  \ {}".format(self.label) if self.label is not None else ""
        return s + l

    def __repr__(self):
        return "Rational[{}]".format(repr(self.value))


#############################################################################
#
#       S T R I N G
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
            raise rpn.exception.RuntimeErr(rpn.exception.X_ARG_TYPE_MISMATCH, 'String#value()', "({})".format(typename(new_value)))
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
#       V E C T O R
#
#############################################################################
class Vector(Stackable):
    def __init__(self, vals):
        if not rpn.globl.have_module('numpy'):
            raise rpn.exception.RuntimeErr(rpn.exception.X_UNSUPPORTED, "", "Vectors require 'numpy' library")
        super().__init__()
        self.name = "Vector"
        self._type = T_VECTOR
        if type(vals) is not rpn.util.List:
            raise rpn.exception.FatalErr("{}: {} is not a List".format(whoami(), repr(vals)))
        self.value = np.array([elem.value for elem in vals.listval()])

    @classmethod
    def from_numpy(cls, x):
        #print("rpn.type.Vector.from_numpy: x={}, type={}".format(x, type(x)))
        obj = cls(rpn.util.List())
        # print("from_numpy: {}".format(repr(obj)))
        obj.value = x
        return obj

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        #numpy.ndarray ok
        # if type(new_value) is not rpn.type.Vector: # FIXME
        #     raise rpn.exception.RuntimeErr(rpn.exception.X_ARG_TYPE_MISMATCH, 'Vector#value()', "({})".format(typename(new_value)))
        self._value = new_value

    def size(self):
        return self.value.size

    def __str__(self):
        if self.size() == 0:
            return "[]"
        return "[ " + " ".join([str(rpn.globl.to_rpn_class(e)) for e in self.value]) +" ]"

    def __repr__(self):
        return "Vector[{}]".format(repr(self.value))
