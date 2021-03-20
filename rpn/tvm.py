'''
#############################################################################
#
#       T V M   U T I L I T Y   F U N C T I O N S
#
#       Note:   (1+i)^N  ==  exp(N * log1p(i))
#
#############################################################################
'''

import math
from   rpn.debug import dbg, whoami
import rpn.flag

N   = None
INT = None
PV  = None
PMT = None
FV  = None
CF  = None
PF  = None



def solve_for_interest():
    eps = 1e-6
    i = {}
    i[0] = i_initial_guess()
    dbg("tvm", 3, "i[0] = {}".format(i[0]))

    def f(i):
        X = X_helper()
        A = math.expm1(rpn.tvm.N.obj.value * math.log1p(i))
        B = (1.0 + i*X) / i
        C = rpn.tvm.PMT.obj.value * B
        pv = rpn.tvm.PV.obj.value
        fv = rpn.tvm.FV.obj.value
        # f(i) = A(PV+C) + PV + FV
        res = A*(pv+C) +  pv + fv
        return res

    def df(i):
        X = X_helper()
        A = math.expm1(rpn.tvm.N.obj.value * math.log1p(i))
        B = (1.0 + i*X) / i
        C = rpn.tvm.PMT.obj.value * B
        D = (A+1) / (1+i)
        pv = rpn.tvm.PV.obj.value
        # f'(i) = n*D*(PV+C) - (A*C)/i
        res = rpn.tvm.N.obj.value*D*(pv+C) - ((A*C)/i)
        return res

    k = 0
    while True:
        i[k+1] = i[k] - (f(i[k]) / df(i[k]))
        diff = i[k+1] - i[k]
        dbg("tvm", 3, "i[{}] = {}; diff={}".format(k+1, i[k+1], diff))
        if abs(diff) < eps:
            return i[k+1]
        k += 1
        if k > 100:
            throw(X_NO_SOLUTION, "int")

def i_initial_guess():
    n   = rpn.tvm.N  .obj.value
    pv  = rpn.tvm.PV .obj.value
    pmt = rpn.tvm.PMT.obj.value
    fv  = rpn.tvm.FV .obj.value

    if pmt * fv < 0:
        # FV case
        denom = 3 * ((n-1)**2 * pmt + pv - fv)
        if pv == 0:
            i_0 = abs((fv + n*pmt) / denom)
        else:
            i_0 = abs((fv - n*pmt) / denom)
    else:
        # PV case
        if pv*pmt < 0:
            i_0 = abs((n*pmt + pv + fv) / (n*pv))
        else:
            # Invalid conditions for sophisticated initial guess;
            # fall back to simpler guess
            pv_fv = abs(pv) + abs(fv)
            i_0 = abs(pmt / pv_fv) + abs(pv_fv / (n**3 * pmt))

    return i_0


def int_nom_to_eff(int_nom):
    cf = rpn.tvm.CF.obj.value
    pf = rpn.tvm.PF.obj.value

    if rpn.flag.flag_set_p(rpn.flag.F_TVM_CONTINUOUS):
        # int_eff = e^(i/PF) - 1
        int_eff = math.expm1(int_nom / pf)
    else:
        # int_eff = (1+i/CF)^(CF/PF) - 1
        int_eff = math.expm1((cf/pf) * math.log1p(int_nom/cf))

    dbg("tvm", 3, "int_nom_to_eff ({}): NOM={} -> EFF={}".format(
        "Continuous" if rpn.flag.flag_set_p(rpn.flag.F_TVM_CONTINUOUS) else "Discrete",
        int_nom, int_eff))
    return int_eff


def int_eff_to_nom(int_eff):
    cf = rpn.tvm.CF.obj.value
    pf = rpn.tvm.PF.obj.value

    if rpn.flag.flag_set_p(rpn.flag.F_TVM_CONTINUOUS):
        # int_nom = LN[ (1+int_eff)^PF ]
        int_nom = pf * math.log1p(int_eff)
    else:
        # int_nom = CF * [ (1+int_eff)^(PF/CF) - 1]
        int_nom = cf * (math.expm1((pf/cf) * math.log1p(int_eff)))

    dbg("tvm", 3, "int_eff_to_nom ({}): EFF={} -> NOM={}".format(
        "Continuous" if rpn.flag.flag_set_p(rpn.flag.F_TVM_CONTINUOUS) else "Discrete",
        int_eff, int_nom))
    return int_nom


def i_helper():
    if not rpn.tvm.INT.defined():
        return None
    i_e = int_nom_to_eff(rpn.tvm.INT.obj.value)
    dbg("tvm", 3, "{}: i_e={}".format(whoami(), i_e))
    return i_e / 100.0


def X_helper():
    # X = Begin/End flag
    return rpn.flag.flag_int_value(rpn.flag.F_TVM_BEGIN_MODE) # 0 or 1


def A_helper():
    # A = (1+i)^n - 1
    if not rpn.tvm.N.defined():
        return None
    n = rpn.tvm.N.obj.value
    i = i_helper()
    if i is None:
        return None
    A = math.expm1(n * math.log1p(i))
    dbg("tvm", 3, "{}: A={}".format(whoami(), A))
    return A


def B_helper():
    # B = (1+iX)/i
    i = i_helper()
    if i is None:
        return None
    X = X_helper()
    B = (1.0 + i*X) / i
    dbg("tvm", 3, "{}: B={}".format(whoami(), B))
    return B


def C_helper():
    # C = PMT * B
    if not rpn.tvm.PMT.defined():
        return None
    pmt = rpn.tvm.PMT.obj.value
    B = B_helper()
    if B is None:
        return None
    C = pmt * B
    dbg("tvm", 3, "{}: C={}".format(whoami(), C))
    return C
