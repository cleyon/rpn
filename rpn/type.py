'''
#############################################################################
#
#       D A T A   T Y P E S
#
#############################################################################
'''

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

from   rpn.debug import dbg, whoami
import rpn.globl


class Stackable:
    def __init__(self):
        self._value = None
        self._label = None

    def value(self):
        return self._value

    def set_value(self, val):
        self._value = val

    def label(self):
        return self._label

    def set_label(self, label):
        self._label = label

    def __call__(self):
        dbg("trace", 1, "trace({})".format(repr(self)))
        rpn.globl.param_stack.push(self)

    def patch_recurse(self, _):
        pass


class Complex(Stackable):
    def __init__(self, real=0.0, imag=0.0):
        super().__init__()
        self.set_real_imag(real, imag)

    @classmethod
    def from_complex(cls, cplx):
        return cls(cplx.real, cplx.imag)

    def real(self):
        return self.value().real

    def imag(self):
        return self.value().imag

    def set_real_imag(self, real, imag):
        self.set_value(complex(float(real), float(imag)))

    def zerop(self):
        return self.real() == 0.0 and self.imag() == 0.0

    def __str__(self):
        s = "({},{})".format(rpn.globl.fmt(self.real()), rpn.globl.fmt(self.imag()))
        l = r"  \ " + "{}".format(self.label()) if self.label() is not None else ""
        return s + l

    def __repr__(self):
        return "Complex[{}]".format(repr(self.value()))


class Float(Stackable):
    def __init__(self, val=0.0):
        super().__init__()
        self.set_value(float(val))

    def zerop(self):
        return self.value() == 0.0

    def date_info(self):
        """A float in the form MM.DDYYYY might represent a date.
Extract some information about a date formatted this way.
Success:  (True, dateobj, julian)
          dateobj is datetime.date, julian is an int
Failure:  (False, None, None)"""

        match = rpn.globl.DATE_RE.match("%.6f" % self.value())
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

        match = rpn.globl.TIME_RE.match("%f" % self.value())
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
        l = r"  \ " + "{}".format(self.label()) if self.label() is not None else ""
        s = "{}".format(self.value())
        return s + l

    def __repr__(self):
        return "Float[{}]".format(repr(self.value()))


class Integer(Stackable):
    def __init__(self, val=0):
        super().__init__()
        self.set_value(int(val))

    def zerop(self):
        return self.value() == 0

    def __str__(self):
        s = "{}".format(self.value())
        l = r"  \ " + "{}".format(self.label()) if self.label() is not None else ""
        return s + l

    def __repr__(self):
        return "Integer[{}]".format(repr(self.value()))


class Matrix(Stackable):
    def __init__(self, vals):
        if not rpn.globl.have_module('numpy'):
            raise rpn.exception.RuntimeErr("Matrices require 'numpy' library")
        super().__init__()
        #rpn.globl.lnwriteln("{}: vals={}".format(whoami(), repr(vals)))
        self._nrows = len(vals)
        cols = -1
        vecs = []
        for x in vals.items():
            #rpn.globl.lnwriteln("x={}".format(repr(x)))
            vecs.append(x.value())
            if cols == -1:
                cols = x.size()
            else:
                if x.size() != cols:
                    raise rpn.exception.RuntimeErr("Matrix: Number of columns is not consistent")
        self._ncols = cols
        #rpn.globl.lnwriteln("{} rows x {} columns".format(self.nrows(), self.ncols()))
        #print("vecs", vecs)
        self.set_value(np.array(vecs))
        #print("val",repr(self.value()))

    @classmethod
    def from_numpy(cls, x):
        obj = cls(rpn.util.List())
        obj._nrows, obj._ncols = x.shape
        obj.set_value(x)
        return obj

    def nrows(self):
        return self._nrows

    def ncols(self):
        return self._ncols

    def __str__(self):
        return str(self.value())

    def __repr__(self):
        return "Matrix[{}]".format(repr(self.value()))


class Rational(Stackable):
    def __init__(self, num=0, denom=1):
        super().__init__()
        self.set_value(Fraction(int(num), int(denom)))

    @classmethod
    def from_Fraction(cls, frac):
        return cls(frac.numerator, frac.denominator)

    @classmethod
    def from_string(cls, s):
        match = rpn.globl.RATIONAL_RE.match(s)
        if match is None:
            raise rpn.exception.FatalErr("Rational pattern failed to match '{}'".format(s))
        return cls(match.group(1), match.group(2))

    def numerator(self):
        return self.value().numerator

    def denominator(self):
        return self.value().denominator

    def set_num_denom(self, num, denom):
        self._value = Fraction(int(num), int(denom))

    def zerop(self):
        return self.numerator() == 0

    def __str__(self):
        s = "{}::{}".format(self.numerator(), self.denominator())
        l = r"  \ {}".format(self.label()) if self.label() is not None else ""
        return s + l

    def __repr__(self):
        return "Rational[{}]".format(repr(self.value()))


class String:
    def __init__(self, val):
        self._value = val

    @classmethod
    def from_string(cls, s):
        return cls("{}".format(s))

    def value(self):
        return self._value

    def set_value(self, val):
        self._value = val

    def __call__(self):
        dbg("trace", 1, "trace({})".format(repr(self)))
        rpn.globl.string_stack.push(self)

    def patch_recurse(self, new_word):
        pass

    def __str__(self):
        return "\"{}\"".format(str(self.value()))

    def __repr__(self):
        return "String[{}]".format(repr(self.value()))


class Vector(Stackable):
    def __init__(self, vals):
        if not rpn.globl.have_module('numpy'):
            raise rpn.exception.RuntimeErr("Vectors require 'numpy' library")
        super().__init__()
        if type(vals) is not rpn.util.List:
            raise rpn.exception.FatalErr("{}: {} is not a List".format(whoami(), repr(vals)))
        self.set_value(np.array([elem.value() for elem in vals.listval()]))

    @classmethod
    def from_numpy(cls, x):
        print("rpn.type.Vector.from_numpy: x={}, type={}".format(x, type(x)))
        obj = cls(rpn.util.List())
        # print("from_numpy: {}".format(repr(obj)))
        obj.set_value(x)
        return obj

    def size(self):
        return self.value().size

    def __str__(self):
        if self.size() == 0:
            return "[]"
        return "[ " + " ".join([str(rpn.globl.to_rpn_class(e)) for e in self.value()]) +" ]"

    def __repr__(self):
        return "Vector[{}]".format(repr(self.value()))
