'''
#############################################################################
#
#       E X C E P T I O N S
#
#       - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#
#       9.3.1  THROW values
#
#       The THROW values {-255...-1} shall be used only as assigned by
#       this Standard.  The values {-4095...-256} shall be used only as
#       assigned by a system.  If the File-Access or Memory-Allocation
#       word sets are implemented, it is recommended that the non-zero
#       values of ior lie within the range of system THROW values, as
#       defined above.  In an operating-system environment, this can
#       sometimes be accomplished by "biasing" the range of operating
#       system exception-codes to fall within the THROW range.  Programs
#       shall not define values for use with THROW in the range {-4095...-1}.
#
#############################################################################
'''

X_ABORT               = -1
X_ABORT_QUOTE         = -2
X_STACK_OVERFLOW      = -3
X_STACK_UNDERFLOW     = -4
X_RSTACK_OVERFLOW     = -5
X_RSTACK_UNDERFLOW    = -6
X_DO_NESTING          = -7
X_DICT_OVERFLOW       = -8
X_INVALID_MEMORY      = -9
X_DIVISION_BY_ZERO    = -10
X_RESULT_OO_RANGE     = -11
X_ARG_TYPE_MISMATCH   = -12
X_UNDEFINED_WORD      = -13
X_COMPILE_ONLY        = -14
X_INVALID_FORGET      = -15     # Do not use, prefer X_PROTECTED
X_ZERO_LEN_STR        = -16
X_PIC_STRING_OVERFLOW = -17
X_STRING_OVERFLOW     = -18
X_NAME_TOO_LONG       = -19
X_READ_ONLY           = -20
X_UNSUPPORTED         = -21
X_CTL_STRUCTURE       = -22
X_ALIGNMENT           = -23
X_INVALID_ARG         = -24
X_RSTACK_IMBALANCE    = -25
X_LOOP_PARAMS         = -26
X_INVALID_RECURSION   = -27
X_INTERRUPT           = -28
X_NESTING             = -29
X_OBSOLETE            = -30
X_BODY                = -31
X_INVALID_NAME        = -32
X_BLK_READ            = -33
X_BLK_WRITE           = -34
X_INVALID_BLK_NUM     = -35
X_INVALID_FILE_POS    = -36
X_FILE_IO             = -37
X_NON_EXISTENT_FILE   = -38
X_EOF                 = -39
X_INVALID_BASE        = -40
X_PRECISION_LOSS      = -41
X_FP_DIVISION_BY_ZERO = -42
X_FP_RESULT_OO_RANGE  = -43
X_FP_STACK_OVERFLOW   = -44
X_FP_STACK_UNDERFLOW  = -45
X_FP_INVALID_ARG      = -46
X_COMP_WORD_DEL       = -47
X_INVALID_POSTPONE    = -48
X_SO_OVERFLOW         = -49
X_SO_UNDERFLOW        = -50
X_COMP_WORD_CHG       = -51
X_CTL_STACK_OVERFLOW  = -52
X_XSTACK_OVERFLOW     = -53
X_FP_UNDERFLOW        = -54
X_FP_FAULT            = -55
X_QUIT                = -56
X_CHAR_IO             = -57
X_IF_THEN             = -58

FIRST_STD_THROW_CODE  = X_ABORT
LAST_STD_THROW_CODE   = X_IF_THEN

X_LEAVE               = -256
X_EXIT                = -257
X_FP_NAN              = -258
X_INSUFF_PARAMS       = -259
X_INSUFF_STR_PARAMS   = -260
X_CONFORMABILITY      = -261
X_BAD_DATA            = -262
X_SYNTAX              = -263
X_NO_SOLUTION         = -264
X_UNDEFINED_VARIABLE  = -265
X_PROTECTED           = -266
X_INVALID_UNIT        = -267

FIRST_SYS_THROW_CODE  = X_LEAVE
LAST_SYS_THROW_CODE   = X_INVALID_UNIT # Keep updated!

throw_code_text = {
    X_ABORT               : 'ABORT',
    X_ABORT_QUOTE         : 'ABORT"',
    X_STACK_OVERFLOW      : 'Stack overflow',
    X_STACK_UNDERFLOW     : 'Stack underflow',
    X_RSTACK_OVERFLOW     : 'Return stack overflow',
    X_RSTACK_UNDERFLOW    : 'Return stack underflow',
    X_DO_NESTING          : 'DO-loops nested too deeply during execution',
    X_DICT_OVERFLOW       : 'Dictionary overflow',
    X_INVALID_MEMORY      : 'Invalid memory address',   # Bad non-math arg, like invalid flag, register number, stack idx out of range
    X_DIVISION_BY_ZERO    : 'Division by zero',
    X_RESULT_OO_RANGE     : 'Result out of range',
    X_ARG_TYPE_MISMATCH   : 'Argument type mismatch',   # Used when X or Y types are not legal
    X_UNDEFINED_WORD      : 'Undefined word',
    X_COMPILE_ONLY        : 'Interpreting a compile-only word',
    X_INVALID_FORGET      : 'Invalid FORGET',           # Do not use, prefer X_PROTECTED
    X_ZERO_LEN_STR        : 'Attempt to use zero-length string as a name',
    X_PIC_STRING_OVERFLOW : 'Pictured numeric output string overflow',
    X_STRING_OVERFLOW     : 'Parsed string overflow',
    X_NAME_TOO_LONG       : 'Definition name too long',
    X_READ_ONLY           : 'Write to a read-only location', # Variable cannot be modified
    X_UNSUPPORTED         : 'Unsupported operation',    # Missing library such as e.g., scipy
    X_CTL_STRUCTURE       : 'Control structure mismatch',
    X_ALIGNMENT           : 'Address alignment exception',
    X_INVALID_ARG         : 'Invalid argument',         # Something must be positive, it's out of range, etc.  Not math.  Standard says "Invalid numeric argument"
    X_RSTACK_IMBALANCE    : 'Return stack imbalance',
    X_LOOP_PARAMS         : 'Loop parameters unavailable',
    X_INVALID_RECURSION   : 'Invalid recursion',
    X_INTERRUPT           : 'User interrupt',
    X_NESTING             : 'Compiler nesting',
    X_OBSOLETE            : 'Obsolescent feature',
    X_BODY                : '>BODY used on non-CREATEd definition',
    X_INVALID_NAME        : 'Invalid name argument',    # e.g., TO xxx
    X_BLK_READ            : 'Block read exception',
    X_BLK_WRITE           : 'Block write exception',
    X_INVALID_BLK_NUM     : 'Invalid block number',
    X_INVALID_FILE_POS    : 'Invalid file position',
    X_FILE_IO             : 'File I/O exception',
    X_NON_EXISTENT_FILE   : 'Non-existent file',
    X_EOF                 : 'Unexpected end of file',
    X_INVALID_BASE        : 'Invalid BASE for floating point conversion',
    X_PRECISION_LOSS      : 'Loss of precision',
    X_FP_DIVISION_BY_ZERO : 'Floating-point divide by zero',
    X_FP_RESULT_OO_RANGE  : 'Floating-point result out of range', # Usually when math.XXX() raises OverflowError
    X_FP_STACK_OVERFLOW   : 'Floating-point stack overflow',
    X_FP_STACK_UNDERFLOW  : 'Floating-point stack underflow',
    X_FP_INVALID_ARG      : 'Floating-point invalid argument', # Math funcs bad arguments, or math.ValueError caught
    X_COMP_WORD_DEL       : 'Compilation word list deleted',
    X_INVALID_POSTPONE    : 'Invalid POSTPONE',
    X_SO_OVERFLOW         : 'Search-order overflow',
    X_SO_UNDERFLOW        : 'Search-order underflow',
    X_COMP_WORD_CHG       : 'Compilation word list changed',
    X_CTL_STACK_OVERFLOW  : 'Control-flow stack overflow',
    X_XSTACK_OVERFLOW     : 'Exception stack overflow',
    X_FP_UNDERFLOW        : 'Floating-point underflow',
    X_FP_FAULT            : 'Floating-point unidentified fault',
    X_QUIT                : 'QUIT',
    X_CHAR_IO             : 'Exception in sending or receiving a character',
    X_IF_THEN             : '[IF], [ELSE], or [THEN] exception',

    X_LEAVE               : 'LEAVE',
    X_EXIT                : 'EXIT',
    X_FP_NAN              : 'Floating-point Not a Number', # When math.isnan() detected
    X_INSUFF_PARAMS       : 'Insufficient parameters',
    X_INSUFF_STR_PARAMS   : 'Insufficient string parameters',
    X_CONFORMABILITY      : 'Conformability error',
    X_BAD_DATA            : 'Bad data',
    X_SYNTAX              : 'Syntax error',
    X_NO_SOLUTION         : 'No solution',
    X_UNDEFINED_VARIABLE  : 'Undefined variable',
    X_PROTECTED           : 'Protected',
    X_INVALID_UNIT        : 'Invalid unit',
}


class RuntimeErr(Exception):
    def __init__(self, code=0, from_thrower="", message=""):
        super().__init__()
        self.code = code
        self.from_thrower = from_thrower
        self.message = message

    def __str__(self):
        s = ""
        if self.from_thrower is not None and len(self.from_thrower) > 0:
            s += "{}: ".format(self.from_thrower)
        if    (LAST_STD_THROW_CODE <= self.code <= FIRST_STD_THROW_CODE) \
           or (LAST_SYS_THROW_CODE <= self.code <= FIRST_SYS_THROW_CODE):
            s += throw_code_text[self.code]
        if self.message is not None and len(self.message) > 0:
            s += ": {}".format(self.message)
        if len(s) == 0:
            s = "Unknown error"
        return s


class RpnException(Exception):
    def __init__(self, msg=""):
        super().__init__()
        self._message = msg

    def __str__(self):
        return str(self._message)


class EndProgram(RpnException):
    """EndProgram is raised when there is no more input to parse, or
the interrupt key is signaled.  It is caught in __main__, where processing
is halted, the exit routine prints the stack, and the program exits."""

class FatalErr(RpnException):
    """FatalErr is raised whenever an internal error is detected that
forces the program to abend.  It is caught in __main__ and causes an
immediate program termination."""

class ParseErr(RpnException):
    """ParseError is raised by p_error and is caught in eval_string()."""

class TopLevel(RpnException):
    """TopLevel is raised by typing a sufficient number of interrupt keys.
It causes an immediate return to the top level prompt in app.py::main_loop()."""


def throw(code, from_thrower="", message=""):
    raise RuntimeErr(code, from_thrower, message)
