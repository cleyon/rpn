import re

from rpn.debug import dbg, whoami
import rpn.exception

prefixes = {}
units = {}

'''
| Prefix | Name  | Exp |
|--------+-------+-----|
| Y      | yotta | +24 |
| Z      | zetta | +21 |
| E      | exa   | +18 |
| P      | peta  | +15 |
| T      | tera  | +12 |
| G      | giga  |  +9 |
| M      | mega  |  +6 |
| k, K   | kilo  |  +3 |
| h, H   | hecto |  +2 |
| D      | deka  |  +1 |   Non-standard
| d      | deci  |  -1 |
| c      | centi |  -2 |
| m      | milli |  -3 |
| i      | micro |  -6 |   Non-standard
| n      | nano  |  -9 |
| p      | pico  | -12 |
| f      | femto | -15 |
| a      | atto  | -18 |
| z      | zepto | -21 |
| y      | yocto | -24 |
'''

for (prefix, exp) in [("Y", +24),
                      ("Z", +21),
                      ("E", +18),
                      ("P", +15),
                      ("T", +12),
                      ("G",  +9),
                      ("M",  +6),
                      ("k",  +3), ("K",  +3),
                      ("h",  +2), ("H",  +2),
                      ("D",  +1),
                      ("d",  -1),
                      ("c",  -2),
                      ("m",  -3),
                      ("i",  -6),
                      ("n",  -9),
                      ("p", -12),
                      ("f", -15),
                      ("a", -18),
                      ("z", -21),
                      ("y", -24)]:
    prefixes[prefix] = exp


class Unit:
    def __init__(self, name, abbrev, **kwargs):
        self.name         = name
        self.abbrev       = abbrev

        self.base_unit_p  = False
        self.category     = None
        self.defn         = None        # Valunit
        self.derived_from = None
        self.factor       = 1
        self.primary_p    = False
        self.ucat         = []

        if "base" in kwargs:
            self.base_unit_p = bool(kwargs["base"])
            del kwargs["base"]
        if "category" in kwargs:
            self.category = kwargs["category"]
            del kwargs["category"]
        if "defn" in kwargs:
            self.defn = kwargs["defn"]
            del kwargs["defn"]
        if "derived_from" in kwargs:
            self.derived_from = kwargs["derived_from"]
            del kwargs["derived_from"]
        if "factor" in kwargs:
            self.factor = kwargs["factor"]
            del kwargs["factor"]
        if "primary" in kwargs:
            self.primary_p = bool(kwargs["primary"])
            del kwargs["primary"]
        if "ucat" in kwargs:
            self.ucat = list(kwargs["ucat"])
            del kwargs["ucat"]

        if len(kwargs) > 0:
            for (key, val) in kwargs.items():
                print("Unrecognized keyword '{}'={}".format(key, val)) # OK
                raise rpn.exception.FatalErr("Could not construct unit '{}'".format(name))
        if self.ucat is None and self.derived_from is None:
            raise rpn.exception.FatalErr("Unit '{}' has neither ucategory nor derived_from".format(name))

    def definition(self):
        if self.derived_from is None:
            if self.base_unit_p or self.primary_p:
                s = "{}".format(self.name)
            else:
                s = "{} {}".format(self.factor, "?UNITS?")
        elif type(self.derived_from) is str:
            s = "{} '{}'".format(self.factor, self.derived_from)
        else:
            s = "{} {}".format(self.factor, self.derived_from.abbrev)
        if self.category is not None or self.base_unit_p or self.primary_p:
            s += " ["
            if self.category is not None:
                s += "{}".format(self.category.measure)
            if self.base_unit_p or self.primary_p:
                s += ","
            if self.base_unit_p:
                s += "Base"
            if self.primary_p:
                s += "Prim"
            s += "]"
        return s

    def __str__(self):
        return "{}".format(self.abbrev)

    def __repr__(self):
        return "Unit['{}'={},{}]".format(self.abbrev, self.factor, self.ucat)


categories = {}
class Category:
    def __init__(self, measure, unit_name, unit_abbrev, bu_expr, ucat):
        self.measure = measure
        self.base_unit = None
        self.ucat = ucat
        # check if bu_expr == base_units.......
        if unit_name is not None and unit_abbrev is not None:
            basep = ucat.count(1) == 1 and ucat.count(0) == 9
            primaryp = not basep # Hack at some point to exclude Hz
            # u = Unit(unit_name, unit_abbrev, 1, ucat, None, basep, primaryp, self)
            u = Unit(unit_name, unit_abbrev, ucat=ucat, base=basep, primary=primaryp, category=self)
            units[unit_name] = self.base_unit = u

    def __repr__(self):
        if self.base_unit is not None:
            return "Category[{},{},{}]".format(self.measure, self.base_unit, self.ucat)
        else:
            return "Category[{},{}]".format(self.measure, self.ucat)

    @classmethod
    def lookup_by_ucat(cls, my_ucat):
        if type(my_ucat) is not list:
            raise rpn.exception.FatalErr("{}: my_ucat is not a List".format(whoami()))
        my_cats = list(filter(lambda c: list(c.ucat) == my_ucat, categories.values()))
        if len(my_cats) != 1:
            return None
        return my_cats[ 0 ]

def defcategory(measure, unit_name, unit_abbrev, bu_expr, ucat):
    cat = Category(measure, unit_name, unit_abbrev, bu_expr, ucat)
    categories[measure] = cat
    return cat

#           Measure          Unit        Abbr  Unit_expr           kg   m   s   A  cd  sr mol  r  K  $
defcategory("Conductance",   "Siemens",  "S",  "s^3*A^2/kg*m^2",  (-1, -2,  3,  2,  0,  0,  0, 0, 0, 0 ))
defcategory("Capacitance",   "Farad",    "F",  "s^4*A^2/kg*m^2",  (-1, -2,  4,  2,  0,  0,  0, 0, 0, 0 ))
defcategory("Exposure",      "Roentgen", "R",  "A*s/kg",          (-1,  0,  1,  1,  0,  0,  0, 0, 0, 0 ))
defcategory("Luminance",     "Lambert",  "lam","cd/m^2",          ( 0, -2,  0,  0,  1,  0,  0, 0, 0, 0 ))
defcategory("Illuminance",   "Lux",      "lx", "cd*sr/m^2",       ( 0, -2,  0,  0,  1,  1,  0, 0, 0, 0 ))
defcategory("Frequency",     None,       None, "s^-1",            ( 0,  0, -1,  0,  0,  0,  0, 0, 0, 0 ))
defcategory("Money",         "Dollar",   "$",  "$",               ( 0,  0,  0,  0,  0,  0,  0, 0, 0, 1 ))
defcategory("Temperature",   "Kelvin",   "K",  "K",               ( 0,  0,  0,  0,  0,  0,  0, 0, 1, 0 ))
defcategory("Angle",         "Radian",   "r",  "r",               ( 0,  0,  0,  0,  0,  0,  0, 1, 0, 0 ))
defcategory("Amount",        "Mole",     "mol","mol",             ( 0,  0,  0,  0,  0,  0,  1, 0, 0, 0 ))
defcategory("Solic angle",   "Steradian","sr", "sr",              ( 0,  0,  0,  0,  0,  1,  0, 0, 0, 0 ))
defcategory("Lum intensity", "Candela",  "cd", "cd",              ( 0,  0,  0,  0,  1,  0,  0, 0, 0, 0 ))
defcategory("Lum flux",      "Lumen",    "lm", "cd*sr",           ( 0,  0,  0,  0,  1,  1,  0, 0, 0, 0 ))
defcategory("Elec current",  "Ampere",   "A",  "A",               ( 0,  0,  0,  1,  0,  0,  0, 0, 0, 0 ))
defcategory("Time",          "Second",   "s",  "s",               ( 0,  0,  1,  0,  0,  0,  0, 0, 0, 0 ))
defcategory("Charge",        "Coulomb",  "C",  "A*s",             ( 0,  0,  1,  1,  0,  0,  0, 0, 0, 0 ))
defcategory("Acceleration",  None,       None, "m/s^2",           ( 0,  1, -2,  0,  0,  0,  0, 0, 0, 0 ))
defcategory("Velocity",      None,       None, "m/s",             ( 0,  1, -1,  0,  0,  0,  0, 0, 0, 0 ))
defcategory("Length",        "Meter",    "m",  "m",               ( 0,  1,  0,  0,  0,  0,  0, 0, 0, 0 ))
defcategory("Equiv Dose",    "Sievert",  "Sv", "m^2/s^2",         ( 0,  2, -2,  0,  0,  0,  0, 0, 0, 0 ))
defcategory("Kin viscosity", "Stokes",   "St", "m^2/s",           ( 0,  2, -1,  0,  0,  0,  0, 0, 0, 0 ))
defcategory("Area",          None,       None, "m^2",             ( 0,  2,  0,  0,  0,  0,  0, 0, 0, 0 ))
defcategory("Volume",        "Liter",    "l",  "m^3",             ( 0,  3,  0,  0,  0,  0,  0, 0, 0, 0 ))
defcategory("Pressure",      "Pascal",   "Pa", "kg/m*s^2",        ( 1, -1, -2,  0,  0,  0,  0, 0, 0, 0 ))
defcategory("Dyn viscosity", "Poise",    "P",  "kg/m*s",          ( 1, -1, -1,  0,  0,  0,  0, 0, 0, 0 ))
defcategory("Mag induction", "Tesla",    "T",  "kg/A*s^2",        ( 1,  0, -2, -1,  0,  0,  0, 0, 0, 0 ))
defcategory("Mass",          "Kilogram", "kg", "kg",              ( 1,  0,  0,  0,  0,  0,  0, 0, 0, 0 ))
defcategory("Force",         "Newton",   "N",  "kg*m/s^2",        ( 1,  1, -2,  0,  0,  0,  0, 0, 0, 0 ))
defcategory("Resistance",    "Ohm",      "Ohm","kg*m^2/A^2*s^3",  ( 1,  2, -3, -2,  0,  0,  0, 0, 0, 0 ))
defcategory("Voltage",       "Volt",     "V",  "kg*m^2/A*s^3",    ( 1,  2, -3, -1,  0,  0,  0, 0, 0, 0 ))
defcategory("Power",         "Watt",     "W",  "kg*m^2/s^3",      ( 1,  2, -3,  0,  0,  0,  0, 0, 0, 0 ))
defcategory("Inductance",    "Henry",    "H",  "kg*m^2/A^2*s^2",  ( 1,  2, -2, -2,  0,  0,  0, 0, 0, 0 ))
defcategory("Energy",        "Joule",    "J",  "kg*m^2/s^2",      ( 1,  2, -2,  0,  0,  0,  0, 0, 0, 0 ))
defcategory("Magnetic flux", "Weber",    "Wb", "kg*m^2/A*s^2",    ( 1,  2, -2,  1,  0,  0,  0, 0, 0, 0 ))


# Return None on error - exceptions will be thrown by callers
def ucat_from_string(str):      # parse_unit_powers(str)
    my_ucat = [0,0,0,0,0,0,0,0,0,0]
    slashes = str.count('/')
    if slashes > 1:
        dbg(whoami(), 2, "ucat_from_string: ('{}') = None; too many slashes".format(str))
        return None
    if slashes == 1:
        (top, bot) = re.split('/', str)
    else:
        top = str
        bot = ""

    for fact in re.split('\*', top):
        # print(fact)
        uf = parse_unit_factors(fact, 1)
        if uf is None:
            dbg(whoami(), 2, "ucat_from_string: ('{}') = None; bad '{}'".format(str, fact))
            return None
        my_ucat = [ a + b for a, b in zip(my_ucat, uf) ]
    if len(bot) > 0:
        for fact in re.split('\*', bot):
            # print(fact)
            uf = parse_unit_factors(fact, -1)
            if uf is None:
                dbg(whoami(), 2, "ucat_from_string: ('{}') = None; bad '{}'".format(str, fact))
                return None
            my_ucat = [ a + b for a, b in zip(my_ucat, uf) ]

    if my_ucat == [0,0,0,0,0,0,0,0,0,0] or my_ucat == []:
        dbg(whoami(), 2, "ucat_from_string: ('{}') = None; no ucat computed".format(str, fact))
        return None
    dbg(whoami(), 2, "ucat_from_string: ('{}') = {}".format(str, my_ucat))
    return my_ucat

def parse_unit_factors(str, sign):
    carets = str.count('^')
    if carets > 1:
        return None
    if carets == 1:
        pos = str.index('^')
        abbrev = str[:pos]
        power = int(str[pos+1:])
    else:
        abbrev = str
        power = 1
    dbg(whoami(), 1, "{}: abbrev_power is {}_{}".format(whoami(), abbrev, power))

    # Lookup abbrev, get its ucat
    (unit, _) = lookup_unit(abbrev)
    dbg(whoami(), 1, "parse_unit_factors: unit={}".format(unit))
    if unit is None:
        return None
    my_ucat = [ sign * x * power for x in unit.ucat]
    dbg(whoami(), 1, "{}: ucat of {} = {}".format(whoami(), abbrev, my_ucat))
    dbg(whoami(), 1, "{}: {}^{} = {}".format(whoami(), abbrev, power, my_ucat))
    return my_ucat

def lookup_unit(name):
    # Check if the unit is an exact match
    unit_match_list = list(filter(lambda unit: unit.abbrev == name, units.values()))
    if len(unit_match_list) > 1:
        raise rpn.exception.FatalErr("{}('{}') found {} unit matches: {}".format(whoami(), name, len(unit_match_list), unit_match_list))
    if len(unit_match_list) == 1:
        exact_unit = unit_match_list[0]
        dbg(whoami(), 1, "{}: Exact match: {}".format(whoami(), repr(exact_unit)))
        # convert to SI base unit
        return (exact_unit, 0)

    # Check for a one-letter prefix, then unit
    if len(name) >= 2:
        first_char = name[0]
        unit_remain = name[1:]
        if first_char not in prefixes:
            dbg(whoami(), 1, "{}: '{}' not matched".format(whoami(), name))
            return (None, None)

        unit_match_list = list(filter(lambda unit: unit.abbrev == unit_remain, units.values()))
        if len(unit_match_list) == 1:
            exact_unit = unit_match_list[0]
            dbg(whoami(), 1, "{}: Exact match with prefix({}): {}".format(whoami(), first_char, exact_unit))
            # convert to SI base unit
            return (exact_unit, prefixes[first_char])

    dbg(whoami(), 1, "{}: '{}' not matched".format(whoami(), name))
    return (None, None)


def units_conform(y, x):
    return y.ucat == x.ucat


def base_units_string(ucat):
    usl = []
    for x in range(10):
        power = ucat[x]
        if power != 0:
            l2 = [ [0]*x, [1], [0]*(9-x) ]
            l = [ item for sbl in l2 for item in sbl ]
            unit_match_list = list(filter(lambda unit: unit.ucat == l and unit.base_unit_p, units.values()))
            if len(unit_match_list) == 0 or len(unit_match_list) > 1:
                raise rpn.exception.FatalErr("base_units_str: Found {} unit matches for ucat {}: {}".format(len(unit_match_list), l, unit_match_list))
            unit = unit_match_list[0]
            us = unit.abbrev
            if power != 1:
                us += "^" + str(power)
            usl.append(us)

    return "*".join(usl)


defunit_list = []
defunit_deferred = []

def defunit(name, abbrev, factor, string):
    global defunit_list
    defunit_list.append( (name, abbrev, factor, string) )

#       Unit name (sing.), Abbrev,   Value,             Derived from or other unit(s)
defunit("Acre",            "acre",   4046.87260987,     "m^2")
# defunit("Day",             "day",      24,              "h")
defunit("Foot",            "ft",       12,              "in")
defunit("Gallon (US)",     "gal",       0.003785411784, "m^3")
# defunit("Gram",            "g",         0.001,          "kg")
# defunit("Gravity (Earth)", "ga",        9.80665,        "m*s^-2")
defunit("Horsepower",      "hp",      745.699871582,    "W") # Mechanical horsepower, not metric
defunit("Hour",            "h",        60,              "min")
defunit("Inch",            "in",        0.0254,         "m")
defunit("Liter",           "l",         0.001,          "m^3")
defunit("Mile",            "mi",     5280,              "ft")
defunit("Mile/Hour",       "mph",       0.44704,        "m/s")
defunit("mymph",           "mymph",     1,              "mi/h")
defunit("Minute",          "min",      60,              "s")
defunit("Speed of light",  "c", 299792458,              "m*s^-1")


def validate_unit(ul):
    global defunit_list, defunit_deferred
    (name, abbrev, factor, string) = ul
    dbg(whoami(), -1, "{}({})".format(whoami(), name))
    ucat = None
    s = ""

    (derived_from, prefix_power) = lookup_unit(string)
    if derived_from is not None:
        if dbg(whoami(), 1):
            s += "{}('{}'): derived_from={}, prefix_power={}".format(whoami(), name, repr(derived_from), prefix_power)
        category = derived_from.category
        ucat = derived_from.ucat
    else:
        ucat = ucat_from_string(string)
        if ucat is None:
            #raise rpn.exception.FatalErr("defunit: derived_from and ucat are None")
            defunit_deferred.append(ul)
            return

        derived_from = string
        category = Category.lookup_by_ucat(ucat)
        if dbg(whoami(), 2):
            s + ", ucat={}, category={}".format(whoami(), ucat, category)

    # if len(s) > 0:
    #     print(s)
    #u = Unit(name, abbrev, factor, ucat, derived_from, False, False, category)
    u = Unit(name, abbrev,
             factor=factor, ucat=ucat, derived_from=derived_from, category=category)
    dbg(whoami(), 1, repr(u))
    units[name] = u


# Check all unit resolve properly
def validate_units():
    global defunit_list, defunit_deferred
    while True:
        defs = len(defunit_list)
        for ul in defunit_list:
            validate_unit(ul)
        if len(defunit_deferred) == 0:
            break
        defunit_list = defunit_deferred
        defunit_deferred = []
        if len(defunit_list) == defs:
            print("validate_units: could not finish")
            return
