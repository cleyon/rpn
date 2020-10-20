'''
#############################################################################
#
#       D A T A   T Y P E S
#
#       - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
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

    @property
    def label(self):
        return self._label

    @label.setter
    def label(self, new_label):
        self._label = new_label

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
        self.value = complex(float(real), float(imag))

    @classmethod
    def from_complex(cls, cplx):
        return cls(cplx.real, cplx.imag)

    def typ(self):
        return 3

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
        self.value = float(val)

    def typ(self):
        return 2

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
        self.value = int(val)

    def typ(self):
        return 0

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

    def typ(self):
        return 5

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

    def typ(self):
        return 1

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
        self.value = val

    @classmethod
    def from_string(cls, s):
        return cls("{}".format(s))

    def typ(self):
        return 6

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        if type(new_value) is not str:
            raise rpn.exception.RuntimeErr(rpn.exception.X_ARG_TYPE_MISMATCH, 'String#value()', "({})".format(typename(new_value)))
        self._value = new_value

    def __call__(self, name):
        dbg("trace", 1, "trace({})".format(repr(self)))
        rpn.globl.string_stack.push(self)

    def __str__(self):
        return '"{}"'.format(str(self.value))

    def __repr__(self):
        return 'String["{}"]'.format(self.value)


#############################################################################
#
#       V A L U N I T
#
#############################################################################
class Valunit(Stackable):
    def __init__(self, val, unit_str):
        super().__init__()
        self.name = "Valunit"
        self.ucat = rpn.units.ucat_from_string(unit_str)
        if self.ucat is None:
            raise rpn.exception.RuntimeErr(rpn.exception.X_INVALID_UNIT, "{}_{}".format(val, unit_str))
        match = rpn.globl.INTEGER_RE.match(val)
        self.value = int(val) if match is not None else float(val)
        self.unit_str = unit_str
        self.unit = None
        self.prefix_power = 0
        (unit, prefix_power) = rpn.units.lookup_unit(unit_str)
        if unit is not None:
            self.unit = unit
            self.prefix_power = prefix_power

    @classmethod
    def from_string(cls, s):
        match = rpn.globl.VALUNIT_RE.match(s)
        if match is None:
            raise rpn.exception.FatalErr("Valunit pattern failed to match '{}'".format(s))
        return cls(match.group(1), match.group(2))

    def valunit_in_base_units(self):
        # prefix_power = 0
        # if self.unit is None:
        #     (unit, prefix_power) = rpn.units.lookup_unit(self.unit_str)
        #     if unit is not None:
        #         print("{}('{}'): self.unit={}, prefix_power={}".format(whoami(), self.unit_str, unit, prefix_power))
        #         self.unit = unit
        # if self.unit.base_unit_p():
        #     print("{}: {} is already in base units".format(whoami(), self))
        #     return self
        # if self.unit.primary_p:
        #     # value stays the same, show base units
        #     base_units_s = rpn.units.base_units_string(self.unit.ucat)
        #     print("{}: base units: {}".format(whoami(), base_units_s))
        #     return Valunit(str(10 ** prefix_power * self.value * self.unit.factor), base_units_s)

        #---------------------------------------
        print("{}: self={}".format(whoami(), repr(self)))
        base_units_s = rpn.units.base_units_string(self.ucat)
        print("{}: base units={}".format(whoami(), base_units_s))
        new_val = self.value
        if self.prefix_power is not None:
            new_val *= 10**self.prefix_power
        if self.unit is not None and self.unit.factor is not None:
            new_val *= self.unit.factor
        print("{}: new_val={}".format(whoami(), new_val))
        return Valunit(str(new_val), base_units_s)

    def typ(self):
        if type(self.value) is int:
            t = 0
        # elif type(self.orig_value) is Fraction:
        #     t = 1
        elif type(self.value) is float:
            t = 2
        return (1<<4) + t

    # @property
    # def value(self):
    #     return self._value_in_units
    #
    # @value.setter
    # def value(self, new_value):
    #     if type(new_value) not in (int, float):
    #         raise rpn.exception.RuntimeErr(rpn.exception.X_ARG_TYPE_MISMATCH, 'Valunit#value()', "({})".format(typename(new_value)))
    #     self._value_in_units = new_value

    def zerop(self):
        return self.value == 0

    def __str__(self):
        s = "{}_{}".format(self.value, self.unit_str)
        l = r"  \ {}".format(self.label) if self.label is not None else ""
        return s + l

    def __repr__(self):
        #return "Valunit[{},'{}',ucat={}]".format(repr(self.value), self.unit_str, self.ucat)
        s = "Valunit[{}_{},ucat={}, prefix_power={}".format(self.value, self.unit_str,
                                                            self.ucat, self.prefix_power)
        if self.unit is not None:
            s += ", unit={}".format(str(self.unit))
        return s + "]"


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

    def typ(self):
        return 4

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
