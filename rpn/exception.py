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
X_DIVISION_ZERO       = -10
X_RESULT_OO_RANGE     = -11
X_ARG_TYPE_MISMATCH   = -12
X_UNDEFINED_WORD      = -13
X_COMPILE_ONLY        = -14
X_INVALID_FORGET      = -15
X_ZERO_LEN_STR        = -16
X_PIC_STRING_OVERFLOW = -17
X_STRING_OVERFLOW     = -18
X_NAME_TOO_LONG       = -19
X_READONLY            = -20
X_UNSUPPORTED_OP      = -21
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
X_FP_DIVISION_ZERO    = -42
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

throw_code = {
    X_ABORT              : 'ABORT',
    X_ABORT_QUOTE        : 'ABORT"',
    X_STACK_OVERFLOW     : 'Stack overflow',
    X_STACK_UNDERFLOW    : 'Stack underflow',
    X_RSTACK_OVERFLOW    : 'Return stack overflow',
    X_RSTACK_UNDERFLOW   : 'Return stack underflow',
    X_DO_NESTING         : 'DO-loops nested too deeply during execution',
    X_DICT_OVERFLOW      : 'Dictionary overflow',
    X_INVALID_MEMORY     : 'Invalid memory address',
    X_DIVISION_ZERO      : 'Division by zero',
    X_RESULT_OO_RANGE    : 'Result out of range',
    X_ARG_TYPE_MISMATCH  : 'Argument type mismatch',
    X_UNDEFINED_WORD     : 'Undefined word',
    X_COMPILE_ONLY       : 'Interpreting a compile-only word',
    X_INVALID_FORGET     : 'Invalid FORGET',
    X_ZERO_LEN_STR       : 'Attempt to use zero-length string as a name',
    X_PIC_STRING_OVERFLOW: 'Pictured numeric output string overflow',
    X_STRING_OVERFLOW    : 'Parsed string overflow',
    X_NAME_TOO_LONG      : 'Definition name too long',
    X_READONLY           : 'Write to a read-only location',
    X_UNSUPPORTED_OP     : 'Unsupported operation',       # e.g., AT-XY on a too-dumb terminal
    X_CTL_STRUCTURE      : 'Control structure mismatch',
    X_ALIGNMENT          : 'Address alignment exception',
    X_INVALID_ARG        : 'Invalid numeric argument',
    X_RSTACK_IMBALANCE   : 'Return stack imbalance',
    X_LOOP_PARAMS        : 'Loop parameters unavailable',
    X_INVALID_RECURSION  : 'Invalid recursion',
    X_INTERRUPT          : 'User interrupt',
    X_NESTING            : 'Compiler nesting',
    X_OBSOLETE           : 'Obsolescent feature',
    X_BODY               : '>BODY used on non-CREATEd definition',
    X_INVALID_NAME       : 'Invalid name argument',       # e.g., TO xxx
    X_BLK_READ           : 'Block read exception',
    X_BLK_WRITE          : 'Block write exception',
    X_INVALID_BLK_NUM    : 'Invalid block number',
    X_INVALID_FILE_POS   : 'Invalid file position',
    X_FILE_IO            : 'File I/O exception',
    X_NON_EXISTENT_FILE  : 'Non-existent file',
    X_EOF                : 'Unexpected end of file',
    X_INVALID_BASE       : 'Invalid BASE for floating point conversion',
    X_PRECISION_LOSS     : 'Loss of precision',
    X_FP_DIVISION_ZERO   : 'Floating-point divide by zero',
    X_FP_RESULT_OO_RANGE : 'Floating-point result out of range',
    X_FP_STACK_OVERFLOW  : 'Floating-point stack overflow',
    X_FP_STACK_UNDERFLOW : 'Floating-point stack underflow',
    X_FP_INVALID_ARG     : 'Floating-point invalid argument',
    X_COMP_WORD_DEL      : 'Compilation word list deleted',
    X_INVALID_POSTPONE   : 'Invalid POSTPONE',
    X_SO_OVERFLOW        : 'Search-order overflow',
    X_SO_UNDERFLOW       : 'Search-order underflow',
    X_COMP_WORD_CHG      : 'Compilation word list changed',
    X_CTL_STACK_OVERFLOW : 'Control-flow stack overflow',
    X_XSTACK_OVERFLOW    : 'Exception stack overflow',
    X_FP_UNDERFLOW       : 'Floating-point underflow',
    X_FP_FAULT           : 'Floating-point unidentified fault',
    X_QUIT               : 'QUIT',
    X_CHAR_IO            : 'Exception in sending or receiving a character',
    X_IF_THEN            : '[IF], [ELSE], or [THEN] exception',
}


class XThrow(Exception):
    def __init__(self, code=0, word="", message=""):
        self.code = code
        self.word = word
        self.message = message


class RpnException(Exception):
    def __init__(self, msg=""):
        super().__init__()
        self._message = msg

    def __str__(self):
        return str(self._message)


class Abort(RpnException):
    """Abort is raised by the ABORT and ABORT" words.
It clears the parameter, return, and string stacks.  Caught in p_execute."""


class EndProgram(RpnException):
    """EndProgram is raised when there is no more input to parse, or
the interrupt key is signaled.  It is caught in __main__, where processing
is halted, the exit routine prints the stack, and the program exits."""


class Exit(RpnException):
    """Exit is raised by the word EXIT and terminates execution
of the current word."""


class FatalErr(RpnException):
    """FatalErr is raised whenever an internal error is detected that
forces the program to abend.  It is caught in __main__ and causes an
immediate program termination."""


class Leave(RpnException):
    """Leave is raised by the LEAVE word.  This is caught by
BEGIN or DO loops, and causes an immediate exit from the enclosing loop.
If a loop is not currently executing, it is caught in p_execute() and
an error message is printed."""


class ParseErr(RpnException):
    """ParseError is raised by p_error and is caught in eval_string()."""


class RuntimeErr(RpnException):
    """Runtime error."""


class StackOverflow(RpnException):
    """Stack overflow."""


class StackUnderflow(RpnException):
    """Stack underflow."""


class Throw(RpnException):
    """Exception raised by THROW and caught by CATCH."""


class TopLevel(RpnException):
    """TopLevel causes an immediate return to the top level prompt.
It is caught in main_loop."""


class TypeErr(RpnException):
    """Type error."""


class ValueErr(RpnException):
    """Value error."""
