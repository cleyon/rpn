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
unit_mass        = ( 1,  0,  0,  0,  0,  0,  0,  0,  0,  0)
unit_length      = ( 0,  1,  0,  0,  0,  0,  0,  0,  0,  0)
unit_time        = ( 0,  0,  1,  0,  0,  0,  0,  0,  0,  0)
unit_current     = ( 0,  0,  0,  1,  0,  0,  0,  0,  0,  0)
unit_lum_inten   = ( 0,  0,  0,  0,  1,  0,  0,  0,  0,  0)
unit_steradians  = ( 0,  0,  0,  0,  0,  1,  0,  0,  0,  0)
unit_amount      = ( 0,  0,  0,  0,  0,  0,  1,  0,  0,  0)
unit_radians     = ( 0,  0,  0,  0,  0,  0,  0,  1,  0,  0)
unit_temperature = ( 0,  0,  0,  0,  0,  0,  0,  0,  1,  0)
unit_money       = ( 0,  0,  0,  0,  0,  0,  0,  0,  0,  1)

unit_conductance  = (-1, -2,  3,  2,  0,  0,  0,  0,  0,  0)
unit_capacitance  = (-1,  0,  1,  1,  0,  0,  0,  0,  0,  0)
unit_frequency    = ( 0,  0, -1,  0,  0,  0,  0,  0,  0,  0)
unit_charge       = ( 0,  0,  1,  1,  0,  0,  0,  0,  0,  0)
unit_acceleration = ( 0,  1, -2,  0,  0,  0,  0,  0,  0,  0)
unit_velocity     = ( 0,  1, -1,  0,  0,  0,  0,  0,  0,  0)
unit_area         = ( 0,  2,  0,  0,  0,  0,  0,  0,  0,  0)
unit_volume       = ( 0,  3,  0,  0,  0,  0,  0,  0,  0,  0)
unit_force        = ( 1,  1, -2,  0,  0,  0,  0,  0,  0,  0)
unit_resistance   = ( 1,  2, -3, -2,  0,  0,  0,  0,  0,  0)
unit_voltage      = ( 1,  2, -3, -1,  0,  0,  0,  0,  0,  0)
unit_power        = ( 1,  2, -3,  0,  0,  0,  0,  0,  0,  0)
unit_energy       = ( 1,  2, -2,  0,  0,  0,  0,  0,  0,  0)

units = {}
def defunit(name, abbrev, factor, si_units):
    units[name] = (abbrev, factor, si_units)


defunit("Acre",            "acre",   4046.87260987,     unit_area)
defunit("Ampere",          "A",         1,              unit_current)
defunit("Coulomb",         "C",         1,              unit_charge)
defunit("Farad",           "F",         1,              unit_capacitance)
defunit("Gallon (US)",     "gal",       0.003785411784, unit_volume)
defunit("Gram",            "g",         0.001,          unit_mass)
defunit("Gravity (Earth)", "ga",        9.80665,        unit_acceleration)
defunit("Hertz",           "Hz",        1,              unit_frequency)
defunit("Horsepower",      "hp",      745.699871582,    unit_power)
defunit("Hour",            "h",      3600,              unit_time)
defunit("Inch",            "in",        0.0254,         unit_length)
defunit("Joule",           "J",         1,              unit_energy)
defunit("Liter",           "l",         0.001,          unit_volume)
defunit("Meter",           "m",         1,              unit_length)
defunit("Minute",          "min",      60,              unit_time)
defunit("Newton",          "N",         1,              unit_force)
defunit("Ohm",             "ohm",       1,              unit_resistance)
defunit("Second",          "s",         1,              unit_time)
defunit("Siemens",         "S",         1,              unit_conductance)
defunit("Speed of light",  "c", 299792458,              unit_velocity)
defunit("Volt",            "V",         1,              unit_voltage)
defunit("Watt",            "W",         1,              unit_power)
