import rpn.exception

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

prefixes = {}
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

'''
|---------------------+-----------+------+----------------+----+----+----+----+----+----+----+---+---+---|
| Measure             | Unit      | Abbr | Unit expr      | kg |  m |  s |  A | cd | sr |mol | r | K | $ |
|---------------------+-----------+------+----------------+----+----+----+----+----+----+----+---+---+---|
| Conductance         | Siemens   | S    | s^3*A^2/kg*m^2 | -1 | -2 |  3 |  2 |  0 |  0 |  0 | 0 | 0 | 0 |
| Capacitance         | Farad     | F    | s^4*A^2/kg*m^2 | -1 | -2 |  4 |  2 |  0 |  0 |  0 | 0 | 0 | 0 |
| Exposure            | Roentgen  | R    | A*s/kg         | -1 |  0 |  1 |  1 |  0 |  0 |  0 | 0 | 0 | 0 |
| Luminance           | Lambert   | lam  | cd/m^2         |  0 | -2 |  0 |  0 |  1 |  0 |  0 | 0 | 0 | 0 |
| Illuminance         | Lux       | lx   | cd*sr/m^2      |  0 | -2 |  0 |  0 |  1 |  1 |  0 | 0 | 0 | 0 |
| Frequency/Activity  | Hertz     | Hz   | s^-1           |  0 |  0 | -1 |  0 |  0 |  0 |  0 | 0 | 0 | 0 |
| *Money              | Dollar    | $    | $              |  0 |  0 |  0 |  0 |  0 |  0 |  0 | 0 | 0 | 1 |
| *Temperature        | Kelvin    | K    | K              |  0 |  0 |  0 |  0 |  0 |  0 |  0 | 0 | 1 | 0 |
| *                   | Radian    | r    | r              |  0 |  0 |  0 |  0 |  0 |  0 |  0 | 1 | 0 | 0 |
| *Amount             | Mole      | mol  | mol            |  0 |  0 |  0 |  0 |  0 |  0 |  1 | 0 | 0 | 0 |
| *                   | Steradian | sr   | sr             |  0 |  0 |  0 |  0 |  0 |  1 |  0 | 0 | 0 | 0 |
| *Luminous intensity | Candela   | cd   | cd             |  0 |  0 |  0 |  0 |  1 |  0 |  0 | 0 | 0 | 0 |
| Luminous flux       | Lumen     | lm   | cd*sr          |  0 |  0 |  0 |  0 |  1 |  1 |  0 | 0 | 0 | 0 |
| *Electric current   | Ampere    | A    | A              |  0 |  0 |  0 |  1 |  0 |  0 |  0 | 0 | 0 | 0 |
| *Time               | Second    | s    | s              |  0 |  0 |  1 |  0 |  0 |  0 |  0 | 0 | 0 | 0 |
| Charge              | Coulomb   | C    | A*s            |  0 |  0 |  1 |  1 |  0 |  0 |  0 | 0 | 0 | 0 |
| Acceleration        |           | ga   | m/s^2          |  0 |  1 | -2 |  0 |  0 |  0 |  0 | 0 | 0 | 0 |
| Velocity            |           | c    | m/s            |  0 |  1 | -1 |  0 |  0 |  0 |  0 | 0 | 0 | 0 |
| *Length             | Meter     | m    | m              |  0 |  1 |  0 |  0 |  0 |  0 |  0 | 0 | 0 | 0 |
| Absorbed/Equiv Dose | Sievert   | Sv   | m^2/s^2        |  0 |  2 | -2 |  0 |  0 |  0 |  0 | 0 | 0 | 0 |
| Kinematic viscosity | Stokes    | St   | m^2/s          |  0 |  2 | -1 |  0 |  0 |  0 |  0 | 0 | 0 | 0 |
| Area                |           |      | m^2            |  0 |  2 |  0 |  0 |  0 |  0 |  0 | 0 | 0 | 0 |
| Volume              | Liter     | l    | m^3            |  0 |  3 |  0 |  0 |  0 |  0 |  0 | 0 | 0 | 0 |
| Pressure            | Pascal    | Pa   | kg/m*s^2       |  1 | -1 | -2 |  0 |  0 |  0 |  0 | 0 | 0 | 0 |
| Dynamic viscosity   | Poise     | P    | kg/m*s         |  1 | -1 | -1 |  0 |  0 |  0 |  0 | 0 | 0 | 0 |
| Magnetic induction  | Tesla     | T    | kg/A*s^2       |  1 |  0 | -2 | -1 |  0 |  0 |  0 | 0 | 0 | 0 |
| *Mass               | Kilogram  | kg   | kg             |  1 |  0 |  0 |  0 |  0 |  0 |  0 | 0 | 0 | 0 |
| Force               | Newton    | N    | kg*m/s^2       |  1 |  1 | -2 |  0 |  0 |  0 |  0 | 0 | 0 | 0 |
| Resistance          | Ohm       | Ohm  | kg*m^2/A^2*s^3 |  1 |  2 | -3 | -2 |  0 |  0 |  0 | 0 | 0 | 0 |
| Voltage             | Volt      | V    | kg*m^2/A*s^3   |  1 |  2 | -3 | -1 |  0 |  0 |  0 | 0 | 0 | 0 |
| Power               | Watt      | W    | kg*m^2/s^3     |  1 |  2 | -3 |  0 |  0 |  0 |  0 | 0 | 0 | 0 |
| Inductance          | Henry     | H    | kg*m^2/A^2*s^2 |  1 |  2 | -2 | -2 |  0 |  0 |  0 | 0 | 0 | 0 |
| Energy              | Joule     | J    | kg*m^2/s^2     |  1 |  2 | -2 |  0 |  0 |  0 |  0 | 0 | 0 | 0 |
| Magnetic flux       | Weber     | Wb   | kg*m^2/A*s^2   |  1 |  2 | -2 |  1 |  0 |  0 |  0 | 0 | 0 | 0 |
|---------------------+-----------+------+----------------+----+----+----+----+----+----+----+---+---+---|
'''

#                    +------------------------------------- Mass (kg)
#                    |   +--------------------------------- Length (m)
#                    |   |   +----------------------------- Time (s)
#                    |   |   |   +------------------------- Current (A)
#                    |   |   |   |   +--------------------- Luminous intensity (cd)
#                    |   |   |   |   |   +----------------- Steradians (sr)
#                    |   |   |   |   |   |   +------------- Amount (mol)
#                    |   |   |   |   |   |   |   +--------- Radians (r)
#                    |   |   |   |   |   |   |   |   +----- Temperature (K)
#                    |   |   |   |   |   |   |   |   |   +- Money ($)
#                    v   v   v   v   v   v   v   v   v   v
ucat_mass        = ( 1,  0,  0,  0,  0,  0,  0,  0,  0,  0)
ucat_length      = ( 0,  1,  0,  0,  0,  0,  0,  0,  0,  0)
ucat_time        = ( 0,  0,  1,  0,  0,  0,  0,  0,  0,  0)
ucat_current     = ( 0,  0,  0,  1,  0,  0,  0,  0,  0,  0)
ucat_lum_inten   = ( 0,  0,  0,  0,  1,  0,  0,  0,  0,  0)
ucat_steradians  = ( 0,  0,  0,  0,  0,  1,  0,  0,  0,  0)
ucat_amount      = ( 0,  0,  0,  0,  0,  0,  1,  0,  0,  0)
ucat_radians     = ( 0,  0,  0,  0,  0,  0,  0,  1,  0,  0)
ucat_temperature = ( 0,  0,  0,  0,  0,  0,  0,  0,  1,  0)
ucat_money       = ( 0,  0,  0,  0,  0,  0,  0,  0,  0,  1)

ucat_conductance  = (-1, -2,  3,  2,  0,  0,  0,  0,  0,  0)
ucat_capacitance  = (-1,  0,  1,  1,  0,  0,  0,  0,  0,  0)
ucat_frequency    = ( 0,  0, -1,  0,  0,  0,  0,  0,  0,  0)
ucat_charge       = ( 0,  0,  1,  1,  0,  0,  0,  0,  0,  0)
ucat_acceleration = ( 0,  1, -2,  0,  0,  0,  0,  0,  0,  0)
ucat_velocity     = ( 0,  1, -1,  0,  0,  0,  0,  0,  0,  0)
ucat_area         = ( 0,  2,  0,  0,  0,  0,  0,  0,  0,  0)
ucat_volume       = ( 0,  3,  0,  0,  0,  0,  0,  0,  0,  0)
ucat_force        = ( 1,  1, -2,  0,  0,  0,  0,  0,  0,  0)
ucat_resistance   = ( 1,  2, -3, -2,  0,  0,  0,  0,  0,  0)
ucat_voltage      = ( 1,  2, -3, -1,  0,  0,  0,  0,  0,  0)
ucat_power        = ( 1,  2, -3,  0,  0,  0,  0,  0,  0,  0)
ucat_energy       = ( 1,  2, -2,  0,  0,  0,  0,  0,  0,  0)

base_categories = [ucat_mass,
                   ucat_length,
                   ucat_time,
                   ucat_current,
                   ucat_lum_inten,
                   ucat_steradians,
                   ucat_amount,
                   ucat_radians,
                   ucat_temperature,
                   ucat_money]

class Unit:
    def __init__(self, name, abbrev, factor, ucategory, base_unit_p, primary_p):
        self.name = name
        self.abbrev = abbrev
        self.factor = factor
        self.ucat = ucategory
        self.basep = base_unit_p
        self.primaryp = primary_p

    def __str__(self):
        return "{}".format(self.abbrev)

    def __repr__(self):
        return "Unit[{},'{}',{},{}]".format(self.name, self.abbrev, self.factor, self.ucat)


def base_units(ucat):
    usl = []
    for x in range(10):
        power = ucat[x]
        if power != 0:
            l = []
            for r in range(x):
                l.append(0)
            l.append(1)
            for r in range(9-x):
                l.append(0)
            #print(x, l)
            t = tuple(l)
            #print(t)
            unit_match_list = list(filter(lambda unit: unit.ucat == t and unit.basep, units.values()))
            if len(unit_match_list) == 0 or len(unit_match_list) > 1:
                raise rpn.exception.FatalErr("Found {} unit matches: {}".format(len(unit_match_list), unit_match_list))
            unit = unit_match_list[0]
            us = unit.abbrev
            if power != 1:
                us += "^" + str(power)
            usl.append(us)

    return "*".join(usl)


units = {}
def base_unit(name, abbrev, factor, ucategory):
    u = Unit(name, abbrev, factor, ucategory, None, True, True)
    units[name] = u
    return u

def primary_unit(name, abbrev, factor, ucategory):
    u = Unit(name, abbrev, factor, ucategory, None, False, True)
    units[name] = u
    return u

def unit(name, abbrev, factor, string):
    derived_from = rpn.global.lookup_unit(string)
    u = Unit(name, abbrev, factor, ucategory, derived_from, False, False)
    units[name] = u
    return u


base_unit("Kilogram",   "kg",  1, ucat_mass)
base_unit("Meter",      "m",   1, ucat_length)
base_unit("Second",     "s",   1, ucat_time)
base_unit("Ampere",     "A",   1, ucat_current)

primary_unit("Siemens", "S",   1, ucat_conductance)
primary_unit("Farad",   "F",   1, ucat_capacitance)
primary_unit("Hertz",   "Hz",  1, ucat_frequency)
primary_unit("Coulomb", "C",   1, ucat_charge)
primary_unit("Newton",  "N",   1, ucat_force)
primary_unit("Ohm",     "ohm", 1, ucat_resistance)
primary_unit("Volt",    "V",   1, ucat_voltage)
primary_unit("Watt",    "W",   1, ucat_power)
primary_unit("Joule",   "J",   1, ucat_energy)

unit("Gravity (Earth)", "ga",        9.80665,        "m*s^-2")
unit("Liter",           "l",         0.001,          "m^3")
unit("Acre",            "acre",   4046.87260987,     "m^2")
unit("Gallon (US)",     "gal",       0.003785411784, "m^3")
unit("Speed of light",  "c", 299792458,              "m*s^-1")

unit("Horsepower",      "hp",      745.699871582,    "W")
unit("Hour",            "h",      3600,              "s")
unit("Gram",            "g",         0.001,          "kg")
unit("Inch",            "in",        0.0254,         "m")
unit("Minute",          "min",      60,              "s")
