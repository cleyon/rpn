'''
#############################################################################
#
#       E X C E P T I O N S
#
#############################################################################
'''

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
    """Exception raised by THROW and caught by CATCH.

9.3.1  THROW values

The THROW values {-255...-1} shall be used only as assigned by this
Standard.  The values {-4095...-256} shall be used only as assigned by a
system.  If the File-Access or Memory-Allocation word sets are
implemented, it is recommended that the non-zero values of ior lie
within the range of system THROW values, as defined above.  In an
operating-system environment, this can sometimes be accomplished by
"biasing" the range of operating-system exception-codes to fall within
the THROW range.  Programs shall not define values for use with THROW in
the range {-4095...-1}.

throw_code_name = {
    -1 : 'ABORT',
    -2 : 'ABORT"',
    -3 : 'Stack overflow',
    -4 : 'Stack underflow',
    -5 : 'Return stack overflow',
    -6 : 'Return stack underflow',
    -7 : 'DO-loops nested too deeply during execution',
    -8 : 'Dictionary overflow',
    -9 : 'Invalid memory address',
    -10: 'Division by zero',
    -11: 'Result out of range',
    -12: 'Argument type mismatch',
    -13: 'Undefined word',
    -14: 'Interpreting a compile-only word',
    -15: 'Invalid FORGET',
    -16: 'Attempt to use zero-length string as a name',
    -17: 'Pictured numeric output string overflow',
    -18: 'Parsed string overflow',
    -19: 'Definition name too long',
    -20: 'Write to a read-only location',
    -21: 'Unsupported operation',       # e.g., AT-XY on a too-dumb terminal
    -22: 'Control structure mismatch',
    -23: 'Address alignment exception',
    -24: 'Invalid numeric argument',
    -25: 'Return stack imbalance',
    -26: 'Loop parameters unavailable',
    -27: 'Invalid recursion',
    -28: 'User interrupt',
    -29: 'Compiler nesting',
    -30: 'Obsolescent feature',
    -31: '>BODY used on non-CREATEd definition',
    -32: 'Invalid name argument',       # e.g., TO xxx
    -33: 'Block read exception',
    -34: 'Block write exception',
    -35: 'Invalid block number',
    -36: 'Invalid file position',
    -37: 'File I/O exception',
    -38: 'Non-existent file',
    -39: 'Unexpected end of file',
    -40: 'Invalid BASE for floating point conversion',
    -41: 'Loss of precision',
    -42: 'Floating-point divide by zero',
    -43: 'Floating-point result out of range',
    -44: 'Floating-point stack overflow',
    -45: 'Floating-point stack underflow',
    -46: 'Floating-point invalid argument',
    -47: 'Compilation word list deleted',
    -48: 'Invalid POSTPONE',
    -49: 'Search-order overflow',
    -50: 'Search-order underflow',
    -51: 'Compilation word list changed',
    -52: 'Control-flow stack overflow',
    -53: 'Exception stack overflow',
    -54: 'Floating-point underflow',
    -55: 'Floating-point unidentified fault',
    -56: 'QUIT',
    -57: 'Exception in sending or receiving a character',
    -58: '[IF], [ELSE], or [THEN] exception',
}

    """


class TopLevel(RpnException):
    """TopLevel causes an immediate return to the top level prompt.
It is caught in main_loop."""


class TypeErr(RpnException):
    """Type error."""


class ValueErr(RpnException):
    """Value error."""
