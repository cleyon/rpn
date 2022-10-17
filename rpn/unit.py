'''RPN Units'''

import ply.lex  as lex
import ply.yacc as yacc

from   rpn.debug     import dbg, whoami
from   rpn.exception import *   # pylint: disable=wildcard-import
import rpn.globl


#############################################################################
#
#       L E X I N G
#
#############################################################################
tokens = ('ASTERISK', 'CARET', 'LPAREN', 'NUMBER', 'RPAREN', 'SLASH', 'UNIT')

t_ASTERISK = r'\*'
t_CARET    = r'\^'
t_LPAREN   = r'\('
t_NUMBER   = r'-?[.0-9]+'
t_RPAREN   = r'\)'
t_SLASH    = r'/'

def t_UNIT(t):
    r'[a-zA-Z$1ÅΩ]+'
    return t

def t_error(t):
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)

ulexer = lex.lex()




#############################################################################
#
#       C A T E G O R Y
#
#############################################################################
category = dict()
dim_size = 10

class Category:
    '''Not every category has an associated unit.
For example, there is no distinct unit for "acceleration" --
it's simply a CompositeUnit "m/s^2".'''
    def __init__(self, measure_name, dimension):
        self.measure = measure_name
        self._dim = dimension
        self.base_unit = None

    def dim(self):
        return self._dim

    def __str__(self):
        return self.measure

    def __repr__(self):
        return "Category['{}',dim={}]".format(self.measure, self.dim())

    @classmethod
    def lookup_by_dim(cls, dimension):
        me = whoami()
        if type(dimension) is not list:
            raise FatalErr("{}: dimension is not a List".format(me))
        if len(dimension) != dim_size:
            raise FatalErr("{}: len(dimension) != {}".format(me, dim_size))

        my_cats = list(filter(lambda c: list(c.dim()) == dimension, category.values()))
        if len(my_cats) == 0:
            return None
        if len(my_cats) == 1:
            return my_cats[0]
        raise FatalErr("{}: More than one category matched dimension {}".format(me, dimension))

def defcategory(measure_name, dimension):
    cat = Category(measure_name, dimension)
    category[measure_name] = cat
    return cat

def deriv_category(measure_name, uexpr):
    defcategory(measure_name, uexpr.dim())


def define_categories():
    #                    kg  m   A   s   cd  sr  mol r   K   $
    defcategory("Null", [0,  0,  0,  0,  0,  0,  0,  0,  0,  0])

    category_name = ["Mass", "Length", "Current", "Time", "LuminousIntensity",
                     "SolidAngle", "Amount", "Angle", "Temperature", "Money" ]
    for x in range(dim_size):
        unit_dim = [ item for sbl in [ [0]*x, [1], [0]*(dim_size-1-x) ]
                     for item in sbl ]
        defcategory(category_name[x], unit_dim)
    # -------------------------------------------------------------------------
    deriv_category("Area",                UPow(category["Length"], 2))
    deriv_category("Charge",              UProd(category["Current"], category["Time"]))
    deriv_category("Equivalent dose",     UQuot(UPow(category["Length"], 2),
                                                UPow(category["Time"], 2)))
    deriv_category("Force",               UQuot(UProd(category["Mass"], category["Length"]),
                                                UPow(category["Time"], 2)))
    deriv_category("Frequency",           UQuot(UNull(), category["Time"]))
    deriv_category("Linear density",      UQuot(category["Mass"],
                                                category["Length"]))
    deriv_category("Luminous flux",       UProd(category["LuminousIntensity"], category["SolidAngle"]))
    deriv_category("Speed",               UQuot(category["Length"],
                                                category["Time"]))
    deriv_category("Volume",              UPow(category["Length"], 3))
    # -------------------------------------------------------------------------
    deriv_category("Acceleration",        UQuot(category["Speed"],
                                                category["Time"]))
    deriv_category("Density",             UQuot(category["Mass"],
                                                category["Volume"]))
    deriv_category("Dynamic viscosity",   UQuot(UProd(category["Force"], category["Time"]),
                                                category["Area"]))
    deriv_category("Electric field",      UQuot(category["Force"],
                                                category["Charge"]))
    deriv_category("Energy",              UProd(category["Force"], category["Length"]))
    deriv_category("Exposure",            UQuot(category["Charge"],
                                                category["Mass"]))
    deriv_category("Grammage",            UQuot(category["Mass"],       # e.g., paper
                                                category["Area"]))
    deriv_category("Illuminance",         UQuot(category["Luminous flux"],
                                                category["Area"]))
    deriv_category("Luminance",           UQuot(category["LuminousIntensity"],
                                                category["Area"]))
    deriv_category("Luminous energy",     UProd(category["Luminous flux"], category["Time"]))
    deriv_category("Magnetic induction",  UQuot(category["Mass"],       # aka Magnetic fild
                                                UProd(category["Charge"], category["Time"])))
    deriv_category("Pressure",            UQuot(category["Force"],      # aka Stress
                                                category["Area"]))
    # -------------------------------------------------------------------------
    deriv_category("Kinematic viscosity", UQuot(category["Dynamic viscosity"],
                                                category["Density"]))
    deriv_category("Magnetic flux",       UProd(category["Magnetic induction"], category["Area"]))
    deriv_category("Power",               UQuot(category["Energy"],
                                                category["Time"]))
    # -------------------------------------------------------------------------
    deriv_category("Electric potential",  UQuot(category["Power"],
                                                category["Current"]))
    deriv_category("Inductance",          UQuot(category["Magnetic flux"],
                                                category["Current"]))
    deriv_category("Magnetic reluctance", UQuot(category["Current"],
                                                category["Magnetic flux"]))
    # -------------------------------------------------------------------------
    deriv_category("Capacitance",         UQuot(category["Charge"],
                                                category["Electric potential"]))
    deriv_category("Conductance",         UQuot(category["Current"],
                                                category["Electric potential"]))
    deriv_category("Elastance",           UQuot(category["Electric potential"],
                                                category["Charge"]))
    deriv_category("Resistance",          UQuot(category["Electric potential"],
                                                category["Current"]))
    # -------------------------------------------------------------------------
    deriv_category("Restivity",           UProd(category["Resistance"], category["Length"])) # Preece
    # -------------------------------------------------------------------------



def pp_dim(dim):
    if dim is None or dim == []:
        return "Invalid dimensions!"

    if dim == [0,  0,  0,  0,  0,  0,  0,  0,  0,  0]:
        return "(Dimensionless)"

    ds = []
    for x in range(dim_size):
        if dim[x] != 0:
            unit_dim = [ item for sbl in [ [0]*x, [1], [0]*(dim_size-1-x) ]
                         for item in sbl ]
            s = str(Category.lookup_by_dim(unit_dim))
            if dim[x] != 1:
                s += f"^{dim[x]}"
            ds.append(s)
    return " ".join(ds)




#############################################################################
#
#       U N I T   E X P R
#
#############################################################################
class UExpr:
    '''UExprs are objects which are attached to Rpn Stackable objects.
They are created with the x_UNIT syntax.  They are similar to Units in that
they have dimensions, but also they carry along an exp.  They can be created
on the fly, and do not necessarily have to relate to "real world" units.
For example, it is perfectly valid to specify "3_m^4".

There are attributes for unit and prefix, but these are not necessary for
use in the general case -- they are only populated by specific searches,
and are often None.'''
    def __init__(self):
        self.dim(category["Null"].dim())
        self._exp = 0
        self._base_factor = None
        self.ustr = ""
        self.unit = None
        self.prefix = None

    # Extremely simple equality check, only looks at dimension vector
    # and whether string representations are same.  Could be much more
    # intelligent.  For example, ft should be considered equal to kft
    # with appropriate exp adjustment.
    def __eq__(self, other):
        return self.dim() == other.dim() and \
               str(self)  == str(other)

    def invert(self):
        return UQuot(UNull(), self)

    def ubase(self):
        '''Return a new UExpr equivalent to self but in base units.'''
        me = whoami()
        numer = []
        denom = []
        for x in range(dim_size):
            if self._dim[x] == 0:
                continue
            unit_dim = [ item for sbl in [ [0]*x, [1], [0]*(dim_size-1-x) ]
                           for item in sbl ]
            # Silence pylint "W0640: Cell variable unit_dim defined in loop (cell-var-from-loop)"
            # pylint: disable=cell-var-from-loop
            unit_match_list = list(filter(lambda unit: unit.dim() == unit_dim and \
                                                       unit.base_p, units.values()))
            if len(unit_match_list) == 0 or len(unit_match_list) > 1:
                raise FatalErr("{}: Found {} unit matches for dim {}: {}".format(me, len(unit_match_list), unit_dim, unit_match_list))
            base_unit = unit_match_list[0]
            dbg("unit", 2, "{}: base unit for dimension x is {}".format(me, base_unit))
            abbr = base_unit.abbrev
            pwr = self._dim[x]
            # if base_unit.name == "gram":
            #     abbr = "kg"
            #     self._exp -= 3 * (abs(pwr) + 1)
            if pwr > 1 or pwr < -1:
                abbr += "^" + str(abs(pwr))
            if pwr > 0:
                numer.append(abbr)
            else:
                denom.append(abbr)

        if len(numer) == 0:
            s = "1"
        else:
            s = "*".join(numer)
        if len(denom) > 0:
            s += "/" + "*".join(denom)
        ue = try_parsing(s)
        if ue is None:
            raise FatalErr("{}: Could not parse base unit string '{}'".format(me, s))

        dbg("unit", 1, "{}: Returning {}".format(me, ue))
        return ue

    def dim(self, new_dim=None):
        if new_dim is not None:
            self._dim = new_dim
        return self._dim

    # XXX - This should be calculated once (on demand) then cached
    def dim_repr(self):
        '''Drop often-not-used trailing 0 elements'''
        dr = self.dim().copy()
        while len(dr) > 0 and dr[-1] == 0:
            dr.pop()
        return dr

    def exp(self, new_exp=None):
        if new_exp is not None:
            self._exp = new_exp
        return self._exp

    def base_factor(self, new_base_factor=None):
        if new_base_factor is not None:
            self._base_factor = new_base_factor
        return self._base_factor

    def raise_to_power(self, p):
        return UPow(self, p)

    def __repr__(self):
        return 'UExpr["{}",base_factor={},exp={},dim={}]' \
            .format(str(self), self.base_factor(), self.exp(), self.dim_repr())

    def __str__(self):
        s = ""
        if self.unit is not None:
            if self.prefix is not None:
                s += self.prefix[1]
            #print(repr(self.unit))
            s += str(self.unit)
        return s



#############################################################################
#
#       T R E E   S T R U C T U R E
#
#############################################################################
class UNull:
    def __init__(self):
        pass
    def __str__(self):
        return "1"
    def __repr__(self):
        return "UNull[]"
    def dim(self):              # pylint: disable=no-self-use
        return category["Null"].dim()
    def exp(self):              # pylint: disable=no-self-use
        return 0
    def base_factor(self):      # pylint: disable=no-self-use
        return 1
    def raise_to_power(self, _):
        return self
    def invert(self):
        return self
    def ubase(self):
        return self

class UQuot:
    def __new__(cls, numer, denom):
        if isinstance(denom, UNull):
            return numer
        if isinstance(denom, UQuot):
            return UProd(numer, denom.invert())
        if isinstance(numer, UQuot):
            numer.denom = UProd(numer.denom, denom)
            return numer
        if numer == denom:
            return None
        obj = object.__new__(cls)
        obj.numer = numer
        obj.denom = denom
        return obj
    def __str__(self):
        return str(self.numer) + "/" + str(self.denom)
    def dim(self):
        return [ adim - bdim  for adim, bdim in zip(self.numer.dim(), self.denom.dim()) ]
    def exp(self):
        return self.numer.exp() - self.denom.exp()
    def base_factor(self):
        return self.numer.base_factor() / self.denom.base_factor()
    def __repr__(self):
        return "UQuot[{},{}]".format(repr(self.numer), repr(self.denom))
    def raise_to_power(self, p):
        return UQuot(self.numer.raise_to_power(p),
                     self.denom.raise_to_power(p))
    def ubase(self):
        return UQuot(self.numer.ubase(), self.denom.ubase())
    def invert(self):
        if isinstance(self.numer, UNull):
            return self.denom
        return UQuot(self.denom, self.numer)

class UProd:
    def __new__(cls, lhs, rhs):
        if isinstance(lhs, UNull):
            return rhs
        if isinstance(rhs, UNull):
            return lhs
        if isinstance(lhs, UQuot) and isinstance(rhs, UExpr):
            lhs.numer = UProd(lhs.numer, rhs)
            return lhs
        if isinstance(lhs, UExpr) and isinstance(rhs, UQuot):
            rhs.numer = UProd(lhs, rhs.numer)
            return rhs
        if isinstance(lhs, UQuot) and isinstance(rhs, UQuot):
            return UQuot(UProd(lhs.numer, rhs.numer),
                         UProd(lhs.denom, rhs.denom))
        if lhs == rhs:
            return UPow(lhs, 2)
        obj = object.__new__(cls)
        obj.lhs = lhs
        obj.rhs = rhs
        return obj
    def __str__(self):
        return str(self.lhs) + "*" + str(self.rhs)
    def __repr__(self):
        return "UProd[{},{}]".format(repr(self.lhs), repr(self.rhs))
    def dim(self):
        return [ adim + bdim  for adim, bdim in zip(self.lhs.dim(), self.rhs.dim()) ]
    def exp(self):
        return self.lhs.exp() + self.rhs.exp()
    def base_factor(self):
        return self.lhs.base_factor() * self.rhs.base_factor()
    def raise_to_power(self, p):
        return UProd(self.lhs.raise_to_power(p),
                     self.rhs.raise_to_power(p))
    def ubase(self):
        return UProd(self.lhs.ubase(), self.rhs.ubase())
    def invert(self):
        return UQuot(UNull(), self)

class UPow:
    def __new__(cls, mantissa, power):
        if int(power) == 0:
            return UNull()
        if int(power) == 1:
            return mantissa
        if isinstance(mantissa, UPow):
            mantissa.power *= int(power)
            return mantissa
        if isinstance(mantissa, (UExpr, Category)):
            obj = object.__new__(cls)
            obj.mantissa = mantissa
            obj.power = int(power)
            return obj
        if isinstance(mantissa, UQuot):
            return UQuot(UPow(mantissa.numer, power), UPow(mantissa.denom, power))
        if isinstance(mantissa, UProd):
            return UProd(UPow(mantissa.lhs, power), UPow(mantissa.rhs, power))
        if isinstance(mantissa, UParen):
            return UParen(UPow(mantissa.inner, power))
        if isinstance(mantissa, UNull):
            return UNull()

        print("UPow fell through -- should not happen")
        obj = object.__new__(cls)
        obj.mantissa = UParen(mantissa)
        obj.power = int(power)
        return obj
    def __str__(self):
        return str(self.mantissa) + "^" + str(self.power)
    def __repr__(self):
        return "UPow[{},{}]".format(repr(self.mantissa), self.power)
    def exp(self):
        return self.mantissa.exp() * self.power
    def dim(self):
        return [ x * self.power  for x in self.mantissa.dim() ]
    def base_factor(self):
        return self.mantissa.base_factor() ** self.power
    def raise_to_power(self, power):
        return UPow(self.mantissa, self.power + power)
    def ubase(self):
        return UPow(self.mantissa.ubase(), self.power)
    def invert(self):
        return UQuot(UNull(), self)

class UParen:
    def __new__(cls, inner):
        if isinstance(inner, (UExpr, UNull)):
            return inner
        obj = object.__new__(cls)
        obj.inner = inner
        return obj
    def __str__(self):
        return "(" + str(self.inner) + ")"
    def __repr__(self):
        return "UParen[{}]".format(repr(self.inner))
    def exp(self):
        return self.inner.exp()
    def dim(self):
        return self.inner.dim()
    def base_factor(self):
        return self.inner.base_factor()
    def raise_to_power(self, p):
        return UParen(self.inner.raise_to_power(p))
    def ubase(self):
        return UParen(self.inner.ubase())
    def invert(self):
        return UParen(self.inner.invert())

#############################################################################
#
#       P A R S I N G
#
#############################################################################
def p_error(p):
    raise ParseErr(p if p is not None else '???')

def unit_lookup(text):
    '''Look up a Unit by matching text to unit name, abbrev, or synonym.
Optional prefix is also considered.  Returns a UExpr object with appropriate
dim, exp, and base_factor.  This only is used to find Units, not UExprs,
which do not have names.

One annoyance of this algorithm is that I often (mistakenly) enter "hr"
expecting 'hours', but this returns hectoradians.'''

    # 0. Check for Null unit
    if text == "1":
        ue = UNull()
        return ue

    # 1. Proper name ("second")
    for u in units.values():
        if u.name == text:
            ue = UExpr()
            ue.dim(u.dim())
            ue.exp(u.exp())
            ue.base_factor(u.base_factor())
            ue.unit = u
            return ue

    # 2. Proper name with any prefix ("kilosecond", "ksecond")
    for u in units.values():
        for p in prefix_list:
            for i in range(1):
                if len(text) - len(p[i]) <= 0:
                    continue
                if text[:len(p[i])] == p[i] and text[len(p[i]):] == u.name:
                    ue = UExpr()
                    ue.dim(u.dim())
                    ue.exp(u.exp() + p[2])
                    ue.base_factor(u.base_factor())
                    ue.unit = u
                    ue.prefix = p
                    return ue

    # 3. Abbrev ("s")
    for u in units.values():
        if u.abbrev is None:
            continue
        if u.abbrev == text:
            ue = UExpr()
            ue.dim(u.dim())
            ue.exp(u.exp())
            ue.base_factor(u.base_factor())
            ue.unit = u
            return ue

    # 4. Abbrev with short prefix ("ks").
    # NB - Abbrev with long prefix ("kilos") is not accepted
    for u in units.values():
        if u.abbrev is None:
            continue
        for p in prefix_list:
            if len(text) - len(p[1]) <= 0:
                continue
            if text[:len(p[1])] == p[1] and text[len(p[1]):] == u.abbrev:
                ue = UExpr()
                ue.dim(u.dim())
                ue.exp(u.exp() + p[2])
                ue.base_factor(u.base_factor())
                ue.unit = u
                ue.prefix = p
                return ue

    # 5. Any synonym ("sec")
    for u in units.values():
        if len(u.syn) == 0:
            continue
        if text in u.syn:
            ue = UExpr()
            ue.dim(u.dim())
            ue.exp(u.exp())
            ue.base_factor(u.base_factor())
            ue.unit = u
            return ue

    # 6. Any synonym with any prefix ("kilosec", "ksec")
    for u in units.values():
        if len(u.syn) == 0:
            continue
        for syn in u.syn:
            for p in prefix_list:
                for i in range(1):
                    if len(text) - len(p[i]) <= 0:
                        continue
                    if text[:len(p[i])] == p[i] and text[len(p[i]):] == syn:
                        ue = UExpr()
                        ue.dim(u.dim())
                        ue.exp(u.exp() + p[2])
                        ue.base_factor(u.base_factor())
                        ue.unit = u
                        ue.prefix = p
                        return ue

    # Nothing matched :-(
    return None


# * takes precedence over / (unlike normal algebra).  For example,
# defining Voltage units as "kg*m^2/A*s^3" will be parsed as
# (kg*m^2) / (A*s^3).
def p_uquotient(p):
    '''uquotient : uquotient SLASH uproduct
                 | uproduct'''
    if len(p) == 4:
        p[0] = UQuot(p[1], p[3])
    else:
        p[0] = p[1]

def p_product(p):
    '''uproduct : uproduct ASTERISK uterm
                | uterm'''
    if len(p) == 4:
        p[0] = UProd(p[1], p[3])
    else:
        p[0] = p[1]

def p_uterm(p):
    '''uterm : uterm CARET NUMBER
             | uterm NUMBER
             | ufactor'''
    if len(p) == 4:
        p[0] = UPow(p[1], p[3])
    elif len(p) == 3:
        p[0] = UPow(p[1], p[2])
    elif len(p) == 2:
        p[0] = p[1]

def p_ufactor(p):
    '''ufactor : UNIT
               | LPAREN uquotient RPAREN'''
    if len(p) == 4:
        p[0] = UParen(p[2])
    elif len(p) == 2:
        ue = unit_lookup(p[1])
        if ue is None:
            throw(X_INVALID_UNIT, "", p[1])
        p[0] = ue


#uparser = yacc.yacc(start='uquotient') # , errorlog=yacc.NullLogger())
uparser = yacc.yacc(start='uquotient', errorlog=yacc.NullLogger())

def try_parsing(text):
    '''Returns an UExpr object, or None if error'''
    me = whoami()
    try:
        result = uparser.parse(text, lexer=ulexer)
    except RuntimeErr as e:
        if e.code == X_INVALID_UNIT:
            result = None
        else:
            raise
    dbg("unit#parse", 1, "{}: result={}".format(me, result))
    return result




#############################################################################
#
#       P R E F I X   L I S T
#
#############################################################################
prefix_list = [
    ("yotta", "Y", +24),
    ("zetta", "Z", +21),
    ("exa"  , "E", +18),
    ("peta" , "P", +15),
    ("tera" , "T", +12),
    ("giga" , "G",  +9),
    ("mega" , "M",  +6),
    ("kilo" , "k",  +3), # offset 7
    ("hecto", "h",  +2),
    ("deka" , "da", +1), # Some use non-standard "D"
    ("deci" , "d",  -1),
    ("centi", "c",  -2),
    ("milli", "m",  -3),
    ("micro", "u",  -6), # "u" non-standard
    ("nano" , "n",  -9),
    ("pico" , "p", -12),
    ("femto", "f", -15),
    ("atto" , "a", -18),
    ("zepto", "z", -21),
    ("yocto", "y", -24),
]




#############################################################################
#
#       U N I T
#
#############################################################################
units = dict()

class Unit:
    # name : Required

    # abbrev : (optional)
    # base_p
    # deriv
    # dim
    # exp : (optional) Exponent, defaults to 0 (10^0 being 1)
    # factor : NB This is the factor to the deriv unit!  If you want the factor
    #          to the base unit, you must follow the chain
    # hidden : (optional, default False) Show in shunit?
    # syn : (optional) list of synonyms
    def __init__(self, name, **kwargs):
        self.abbrev = None
        self.base_p = False
        self.deriv = None
        self._dim = None
        self.orig_exp = None
        self._exp = None
        self._factor = 1
        self.hidden = False
        self.name = name
        self.syn = []

        if "abbrev" in kwargs:
            self.abbrev = kwargs["abbrev"]
            del kwargs["abbrev"]

        if "category" in kwargs:
            c = kwargs["category"]
            if not c in category:
                raise FatalErr("Could not construct unit '{}'; category '{}' not valid".format(name, c))
            self._dim = category[c].dim()
            self.base_p = True
            category[c].base_unit = self
            del kwargs["category"]

        if "exp" in kwargs:
            self.orig_exp = kwargs["exp"]
            self._exp = kwargs["exp"]
            del kwargs["exp"]

        if "factor" in kwargs:
            self._factor = kwargs["factor"]
            del kwargs["factor"]

        if "hidden" in kwargs:
            self.hidden = kwargs["hidden"]
            del kwargs["hidden"]

        if "syn" in kwargs:
            self.syn = kwargs["syn"]
            del kwargs["syn"]

        if "units" in kwargs:
            u = kwargs["units"]
            unit = try_parsing(u)
            if unit is None:
                raise FatalErr("Could not construct unit '{}'; units '{}' not valid".format(name, u))
            self.deriv = unit
            del kwargs["units"]

        # Validate --
        # If there are any keywords left over, they must be ones we
        # don't know about and we want to flag them as errors.
        if len(kwargs) > 0:
            for (key, val) in kwargs.items():
                print("Unrecognized keyword '{}'={}".format(key, val)) # OK
                raise FatalErr("Could not construct unit '{}'".format(name))

        if self._dim is None:
            if self.deriv is not None:
                self._dim = self.deriv.dim()
            else:
                raise FatalErr("Unit '{}' missing dim".format(name))

        if not self.base_p and self.deriv is None:
            raise FatalErr("Unit '{}' is not base and not derived".format(name))

        if self._exp is None:
            if self.base_p:
                self._exp = 0
            else:
                self._exp = self.deriv.exp()
        else:
            if self.deriv is not None:
                self._exp += self.deriv.exp()

        # Store in the unit dictionary
        units[name] = self

    def factor(self):
        return self._factor

    def base_factor(self):
        if self.base_p:
            return self.factor()
        return self.factor() * self.deriv.base_factor()

    def dim(self):
        return self._dim

    def exp(self):
        return self._exp

    def __repr__(self):
        return "Unit[{},base_factor={},factor={},exp={},dim={}]" \
            .format(self.name, self.base_factor(), self.factor(), self.exp(), self.dim())

    def __str__(self):
        return self.abbrev if self.abbrev is not None else self.name




def define_units():
    define_categories()

    #############################################################################
    #
    #       B A S E   U N I T S
    #
    #############################################################################

    # null_unit is implemented as a hack to allow constructs resulting from
    # '50 10_m /  =>  5_1/m'.  This also allows the user to enter a unit object
    # like '50_1' which has a UExpr of no dimensions.  Not sure if that's useful
    # or if it should be disallowed....
    null_unit = Unit("1", category="Null", hidden=True) # pylint: disable=unused-variable

    base_units = [              # pylint: disable=unused-variable
        Unit("ampere",    category="Current",           abbrev="A",   syn=["amperes", "amp", "amps"]),
        Unit("candela",   category="LuminousIntensity", abbrev="cd",  syn=["candelas"]), # Light produced by a standard candle
        Unit("dollar",    category="Money",             abbrev="$",   syn=["USD"]),
        Unit("gram",      category="Mass",              abbrev="g",   syn=["grams", "gramme", "grammes"]),
        Unit("kelvin",    category="Temperature",       abbrev="K",   syn=["degK"]),
        Unit("meter",     category="Length",            abbrev="m",   syn=["meters", "metre", "metres"]),
        Unit("mole",      category="Amount",            abbrev="mol", syn=["moles", "mols"]),
        Unit("radian",    category="Angle",             abbrev="r",   syn=["radians"]), # NOT "rad", that's a radition unit
        Unit("second",    category="Time",              abbrev="s",   syn=["seconds", "sec", "secs"]),
        Unit("steradian", category="SolidAngle",        abbrev="sr",  syn=["steradians"]),
    ]


    #############################################################################
    #
    #       D E R I V E D   U N I T S
    #
    #############################################################################
    derived_units = [           # pylint: disable=unused-variable
        # Length
        Unit("inch",    factor=   2.54, units="cm",      abbrev="in", syn=["inches", "ins"]),
        Unit("point",   factor= 1/72,   units="inch",                syn=["points"], hidden=True), # abbrev "pt" means "pints"
        Unit("mil",     exp=-3,         units="inch",                syn=["mils"]),
        Unit("foot",    factor=  12,    units="inch",   abbrev="ft", syn=["feet"]),
        Unit("yard",    factor=   3,    units="foot",   abbrev="yd", syn=["yards"]),
        Unit("chain",   factor=  66,    units="foot",                syn=["chains"]),
        Unit("mile",    factor=  80,    units="chains", abbrev="mi", syn=["miles"]),
        Unit("rod",     factor= 1/4,    units="chain",               syn=["rods"]),
        Unit("furlong", exp=1,          units="chains",              syn=["furlongs"]),
        Unit("link",    exp=-2,         units="chain",               syn=["links"]),
        Unit("nauticalmile", factor=1852, units="meter", abbrev="nmi"),
        Unit("fathom",  factor=6,       units="feet",   abbrev="fath", syn=["fathoms"]),
        Unit("micron",  exp=-6,         units="m",      abbrev="mu", syn=["microns"]), # micrometer
        Unit("angstrom", exp=-10,       units="m",      abbrev="Å", syn=["ang", "angstroms"]),
        Unit("fermi",   exp=-15,        units="m"), # Nuclear radii is 1--10 fermis
        Unit("surveyfoot", factor=0.304800609601, units="meter", hidden=True),
        Unit("astronomicalunit", factor=1.49597870700, exp=11, units="meter", abbrev="au"), # exact value defined in 2012
        Unit("lightyear", factor=9.4607304725800, exp=15, units="meter", abbrev="ly"),
        Unit("parsec",  factor=648000/rpn.globl.PI, units="au", abbrev="pc", syn=["parsecs"]),

        # Time
        Unit("minute",    factor=  60,      units="second", abbrev="min", syn=["minutes"]), # Not "m", that's meters
        Unit("hour",      factor=  60,      units="minute", abbrev="h",   syn=["hours", "hr", "hrs"]),
        Unit("day",       factor=  24,      units="hour",   abbrev="d",   syn=["days"]),
        Unit("week",      factor=   7,      units="day",    abbrev="wk",  syn=["weeks"]),
        Unit("fortnight", factor=   2,      units="week",                 syn=["fortnights"], hidden=True),
        Unit("year",      factor=31556925.9747, units="seconds", abbrev="yr", syn=["years"]), # Tropical year = 365.242198781 day
        Unit("month",     factor=1/12,      units="year",                 syn=["months"], hidden=True),

        # Speed
        Unit('speed of light', factor=299792458, units="m/s", abbrev="c"),
        Unit('mph',                              units="miles/hour"),
        Unit("kph",                              units="km/hour"),
        Unit("knot",                             units="nauticalmile/hour", syn=["knots"]),
        Unit("mach",               factor=761.2, units="mph"), # approx

        # Acceleration
        # Earth gravity
        Unit("gravity",   factor=9.80665, units="m/s^2", abbrev="ga"),
        # To help convert Mass/Weight/Force:
        Unit("force",     units="gravity", hidden=True),

        # Area
        Unit("acre",                    units="chain*furlong",    syn=["acres"]),
        Unit("are",       exp=2,        units="m^2", abbrev="a"),
        Unit("hectare",   exp=4,        units="m^2", abbrev="ha", syn=["hectares"]),
        Unit("barn",      exp=2,        units="fm^2", abbrev="b", syn=["barns"]),

        # Volume
        Unit("stere",                    units="m^3",    abbrev="st",   syn=["steres"]),
        Unit("liter",             exp=3, units="cm^3",   abbrev="l",    syn=["liters"]),
        Unit("cc",                       units="cm^3", hidden=True),
        Unit("gallon",     factor=231,   units="in^3",   abbrev="gal",  syn=["gallons", "gals"]),
        Unit("barrel",     factor=42,    units="gallon", abbrev="bbl",  syn=["barrels"]), # Oil
        Unit("fifth",      factor=1/5,   units="gallon",                syn=["fifths"]),
        Unit("fluidounce", factor=1/128, units="gallon", abbrev="ozfl", syn=["floz"]),
        Unit("cup",        factor=8,     units="floz",   abbrev="cu",   syn=["cups"]), # 1/2 pint
        Unit("pint",       factor=2,     units="cups",   abbrev="pt",   syn=["pints"]),
        Unit("quart",      factor=2 ,    units="pint",   abbrev="qt",   syn=["quarts"]), # quart == 1/4 gallan
        Unit("gill",       factor=4,     units="floz",                  syn=["gills"]),
        Unit("teaspoon",   factor=1/6,   units="floz",   abbrev="tsp"),
        Unit("tablespoon", factor=3,     units="tsp",    abbrev="tbsp"), # 1/2 floz
        Unit("minim",      factor=59.1938802083, units="microliter",    syn=["minims"]),
        Unit("fluidram",   factor=60,    units="minim",  abbrev="fldr", syn=["fluidrams"]),

        # Dry volume
        Unit("drypint",   factor=33.6,  units="in^3",                   syn=["drypints"]),
        Unit("dryquart",  factor=2,     units="drypints",               syn=["dryquarts"]),
        Unit("drygallon", factor=4,     units="dryquarts",              syn=["drygallons"]),
        Unit("peck",      factor=2,     units="drygallon", abbrev="pk", syn=["pecks"]),
        Unit("bushel",    factor=4,     units="peck"),
        Unit("drybarrel", factor=26.25, units="drygallons",             syn=["drybarrels"]),
        Unit("boardfoot",               units="ft*ft*in", abbrev="fbm"),

        # Mass & Weights
        Unit("pound",     factor=0.45359237, units="kg",    abbrev="lb", syn=["pounds"]),
        Unit("ounce",     factor=1/16,       units="pound", abbrev="oz", syn=["ounces"]),
        Unit("dram",      factor=1/16,       units="ounce", abbrev="dr", syn=["drams"]),
        Unit("grain",     factor=1/7000,     units="lb",    abbrev="gr", syn=["grains"]),
        Unit("scruple",   factor=20,         units="grain",              syn=["scruples"]),
        Unit("carat",     factor=2, exp=-1,  units="g",     abbrev="ct", syn=["carats", "karat", "karats"]),
        Unit("ton",       factor=2, exp=3,   units="lb",                 syn=["tons", "shortton", "shorttons"]),
        Unit("tonne",     exp=3,             units="kg",    abbrev="t",  syn=["tonnes", "metricton", "metrictons"]),

        Unit("dalton", factor=1.660539066605, exp=-27, units="kg", abbrev="Da", syn=["U"]), # Unified atomic mass, = 1/12 mass of Carbon 12

        ## Troy
        Unit("pennyweight", factor=24, units="grain", hidden=True),
        Unit("troyounce",   factor=20, units="pennyweight", abbrev="ozt"),
        Unit("troypound",   factor=12, units="troyounce",   abbrev="lbt"),

        # Grammage
        Unit("gsm", units="g/m^2"),  # Non-standard

        # Force
        Unit('newton',        units="kg*m/s^2",    abbrev="N", syn=["newtons"]),
        Unit('dyne',          units="g*cm/s^2",                syn=["dynes"]),
        Unit('gramforce',     units="g*force",     abbrev="gf"),
        Unit('kilogramforce', units="kg*force",    abbrev="kgf"),
        Unit("poundforce",    units="pound*force", abbrev="lbf"),
        Unit("poundal",       units="lb*foot/s^2", abbrev="pdl", syn=["poundals"]),
        Unit("kilopoundforce", units="poundforce", exp=3, abbrev="kip"),

        ## Other British weight
        Unit("stone",     factor=14, units="pound"),
        Unit("slug",      units="lbf*s^2/ft", syn=["slugs"]),

        # Energy
        Unit("joule",                                units="N*m",      abbrev="J",    syn=["joules"]),
        Unit("erg",                                  units="dyne*cm",                 syn=["ergs"]),
        Unit("footpound",                            units="foot*lbf", abbrev="ftlb", syn=["footpounds"]),
        Unit("electronvolt", factor=1.602176634e-19, units="J",        abbrev="eV",   syn=["electronvolts"]),
        Unit("btu",          factor=1055.05585262,   units="J",                       syn=["btus"]), # british thermal unit
        Unit("calorie",      factor=4.1868,          units="J",        abbrev="cal",  syn=["cals"]),
        Unit("therm",        exp=5,                  units="btu",                     syn=["therms"]),
        Unit("gallongasoline", factor=114100,        units="btu",                     syn=["galgas"], hidden=True),

        # Power
        Unit('watt',      units="J/s", abbrev="W", syn=["watts"]),
        ## "Mechanical" horsepower ::= 33,000 foot-pounds of work per minute = 745.69987 W
        Unit("horsepower", factor=33, exp=3, units="footpound/minute", abbrev="hp"),
        ## "Metric" horsepower ::= 75 m kgf/s = 735.49875 W
        Unit("metrichorsepower", factor=75, units="m*kgf/s", abbrev="mhp"),

        # Energy (part 2)
        Unit("watthour",                             units="W*h",      abbrev="Wh",   syn=["watthours"]), # More commonly seen as "kilowatt-hour" on electricity bills

        # Pressure
        Unit("pascal",   abbrev="Pa",  units="N/m^2", syn=["pascals"]),
        Unit("psi",                    units="lbf/in^2"),
        Unit("torr",     factor=101325/760,    units="pascals", syn=["mmHg"]), # Millimeters of Mercury
        Unit("inH2O",    factor=248.84,        units="pascals"), # Inches of water at 60_degF
        Unit("inHg",     factor=3386.38815789, units="pascals"), # Inces of Mercury at 0_degC
        Unit("bar",      exp=5,        units="pascals"),
        Unit("atmosphere", abbrev="atm", factor=101325, units="pascals"),

        # Frequency
        Unit("hertz",    abbrev="Hz",  units="s^-1"),
        Unit("becquerel",abbrev="Bq",  units="s^-1"),
        Unit("rpm",                    units="min^-1"),
        Unit("curie",    abbrev="Ci",  factor=3.7, exp=10, units="becquerel", syn=["curies"]),

        # Luminous flux
        # Light power, the total amount of light produced by a light
        # source.  Luminous flux as a measurement is different than
        # radiant flux because luminous flux measures only the
        # electromagnetic waves that the human eye can see while radiant
        # flux measures all electromagnetic waves emitted by a source.
        Unit("lumen",    abbrev="lm",  units="cd*sr", syn=["lumens"]),

        # Illuminance
        # Light incident on a surface area
        Unit("lux",        abbrev="lx", units="lumen/m^2"),
        Unit("footcandle", abbrev="fc", units="lumen/ft^2"),
        Unit("phot",       abbrev="ph", units="lumen/cm^2"),

        # Luminance
        # Light per unit area emitted in a specific direction (visible to eye)
        Unit("nit",                                                 units="cd/m^2", syn=["nits"]), # from Latin "nitere" = to shine
        Unit("lambert",     abbrev="lam",  factor=rpn.globl.INV_PI, units="cd/cm^2", syn=["lamberts"]),
        Unit("footlabmert", abbrev="flam", factor=rpn.globl.INV_PI, units="cd/ft^2", syn=["footlamberts"]),
        Unit("stilb",       abbrev="sb",                            units="cd/cm^2"),

        # Charge
        # see also Faraday constant "Fdy" defined in science.rpn
        Unit("coulomb",  abbrev="C",                 units="A*s",     syn=["coulombs"]),
        Unit("amperehour",             factor=3600,  units="coulomb", syn=["amperehours", "amphour", "amphours"]),

        # Radiation, loosely
        Unit("sievert",  abbrev="Sv",  units="J/kg",        syn=["sieverts"]), # Equivalent dose
        Unit("gray",     abbrev="Gy",  units="J/kg",        syn=["grays"]),    # Equivalent dose
        Unit("rad",      exp=2,        units="erg/g",       syn=["rads"]),
        Unit("roentgen", abbrev="R",   factor=2.58, exp=-4, units="C/kg", syn=["roentgens"]), # Exposure
        Unit("rem",      exp=-2,       units="sievert"),    # rem == Roentgen equivalent man

        # Angle
        Unit("degree",    abbrev="deg",    factor=rpn.globl.RAD_PER_DEG,  units="radians", syn=["degrees"]),
        Unit("arcminute", abbrev="arcmin", factor=1/60,                   units="degree",  syn=["arcminutes"]),
        Unit("arcsecond", abbrev="arcsec", factor=1/60,                   units="arcmin",  syn=["arcseconds"]),
        Unit("gradian",   abbrev="grad",   factor=rpn.globl.RAD_PER_GRAD, units="radians", syn=["gradians"]),

        # Electric potential
        Unit("volt",     abbrev="V",   units="W/A", syn=["volts"]),

        # Magnetic flux
        Unit("weber",    abbrev="Wb",         units="V*s",   syn=["webers"]),
        Unit("maxwell",  abbrev="Mx", exp=-8, units="weber", syn=["maxwells"]),

        # Magnetic induction (field)
        Unit("tesla",    abbrev="T",   units="Wb/m^2"),
        Unit("gauss",    exp=-4,       units="tesla"), # G?

        # Conductance
        Unit("siemens",  abbrev="S",   units="A/V", syn=["mho"]),

        # Inductance
        Unit("henry",    abbrev="H",   units="Wb/A", syn=["henries"]),

        # Capacitance
        Unit("farad",    abbrev="F",   units="C/V", syn=["farads"]),

        # Resistance
        Unit("ohm",                    units="V/A", abbrev="Ω", syn=["ohms"]),

        # Dynamic viscosity
        Unit("poise",    abbrev="P",   exp=-1, units="Pa*s"),

        # Kinematic viscosity
        Unit("stokes",   abbrev="St",  exp=-4, units="m^2/s"),

        # Spectral flux density
        Unit("Jansky", abbrev="Jy", exp=-26, units="W/m^2*Hz"),

        # Temperature
'''
degC (Degree Celsius)		274.15 K
degF (Degrees Fahrenheit)	5 / 9 F or 46067 / 180 K
degR (Degrees Rankine)		0.555555555556 K
'''
    ]

    rpn.globl.uexpr["d"]     = try_parsing("degree")
    rpn.globl.uexpr["deg/r"] = try_parsing("degree/radian")
    rpn.globl.uexpr["g"]     = try_parsing("gradian")
    rpn.globl.uexpr["r"]     = try_parsing("radian")




#############################################################################
#
#       U T I L I T Y   F U N C T I O N S
#
#############################################################################
def units_conform(a, b):
    return a.dim() == b.dim()
