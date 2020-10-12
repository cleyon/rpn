'''
#############################################################################
#
#       E X E C U T A B L E   C L A S S E S
#
#############################################################################
'''

import sys


try:
    import ply.lex  as lex
except ModuleNotFoundError:
    print("RPN requires the 'ply' library; please consult the README") # OK
    sys.exit(1)

from   rpn.debug import dbg, whoami, typename
import rpn.exception
import rpn.globl


class Executable:
    def __call__(self, name):
        raise rpn.exception.FatalErr("Executable#__call__: Subclass responsibility")

    def patch_recurse(self, _):
        pass

    def immediate(self):                # pylint: disable=no-self-use
        return False


#############################################################################
#
#       A B O R T   Q U O T E
#
#############################################################################
class AbortQuote(Executable):
    def __init__(self, val):
        self.name = 'abort"'
        if len(val) < 7 or val[0:6] != 'abort"' or val[-1] != '"':
            raise rpn.exception.FatalErr("{}: Malformed string: '{}'".format(whoami(), val))
        self._str = val[6:-1]

    def stringval(self):
        return self._str

    def __call__(self, name):
        dbg("trace", 1, "trace({})".format(repr(self)))
        if rpn.globl.param_stack.empty():
            raise rpn.exception.RuntimeErr(rpn.exception.X_INSUFF_PARAMS, 'abort"', "(1 required)")
        flag = rpn.globl.param_stack.pop()
        if type(flag) is not rpn.type.Integer:
            rpn.globl.param_stack.push(flag)
            raise rpn.exception.RuntimeErr(rpn.exception.X_ARG_TYPE_MISMATCH, 'abort"', "({})".format(typename(flag)))
        if flag.value != 0:
            rpn.globl.lnwriteln("{}".format(self.stringval()))
            raise rpn.exception.Abort()

    def __str__(self):
        return 'abort"{}"'.format(self.stringval())

    def __repr__(self):
        return 'AbortQuote["{}"]'.format(self.stringval())


#############################################################################
#
#       A S C I I
#
#############################################################################
class Ascii(Executable):
    def __init__(self):
        self.name = 'ascii'

    def __call__(self, name):
        dbg("trace", 2, "trace({})".format(repr(self)))
        new_tok = None

        rpn.globl.parse_stack.push("ASCII")
        try:
            tok = next(rpn.util.TokenMgr.next_token())
            dbg("ascii", 1, "ascii: tok={}".format(tok))
            c = tok.value[0]
            new_tok = lex.LexToken()
            new_tok.type = 'INTEGER'
            new_tok.value = "{}".format(ord(c))
            new_tok.lineno = 0
            new_tok.lexpos = 0
        except StopIteration:
            dbg("ascii", 2, "ascii: received StopIteration, returning -1")
            new_tok = lex.LexToken()
            new_tok.type = 'INTEGER'
            new_tok.value = "-1"
            new_tok.lineno = 0
            new_tok.lexpos = 0
        finally:
            rpn.globl.parse_stack.pop()
            if new_tok is not None:
                dbg("ascii", 1, "ascii: Pushing new token {}".format(new_tok))
                rpn.util.TokenMgr.push_token(new_tok)

    def __str__(self):
        return "ascii"

    def __repr__(self):
        return "Ascii[]"


#############################################################################
#
#       B E G I N   A G A I N
#
#############################################################################
class BeginAgain(Executable):
    def __init__(self, begin_seq):
        self.name = 'begin'
        self._begin_seq = begin_seq

    def __call__(self, name):
        dbg("trace", 2, "trace({})".format(repr(self)))
        try:
            while True:
                self._begin_seq.__call__("begin_seq")
        except rpn.exception.RuntimeErr as err_begin_again:
            if err_begin_again.code != rpn.exception.X_LEAVE:
                raise

    def patch_recurse(self, new_word):
        self._begin_seq.patch_recurse(new_word)

    def __str__(self):
        return "begin {} again".format(self._begin_seq)

    def __repr__(self):
        return "BeginAgain[{}]".format(repr(self._begin_seq))


#############################################################################
#
#       B E G I N   U N T I L
#
#############################################################################
class BeginUntil(Executable):
    def __init__(self, begin_seq):
        self.name = 'begin'
        self._begin_seq = begin_seq

    def __call__(self, name):
        dbg("trace", 2, "trace({})".format(repr(self)))
        try:
            while True:
                self._begin_seq.__call__("begin_seq")
                if rpn.globl.param_stack.empty():
                    raise rpn.exception.RuntimeErr(rpn.exception.X_INSUFF_PARAMS, "until", "(1 required)")
                flag = rpn.globl.param_stack.pop()
                if type(flag) is not rpn.type.Integer:
                    rpn.globl.param_stack.push(flag)
                    raise rpn.exception.RuntimeErr(rpn.exception.X_ARG_TYPE_MISMATCH, 'until', "({})".format(typename(flag)))
                if flag.value != 0:
                    break
        except rpn.exception.RuntimeErr as err_begin_until:
            if err_begin_until.code != rpn.exception.X_LEAVE:
                raise

    def patch_recurse(self, new_word):
        self._begin_seq.patch_recurse(new_word)

    def __str__(self):
        return "begin {} until".format(self._begin_seq)

    def __repr__(self):
        return "BeginUntil[{}]".format(repr(self._begin_seq))


#############################################################################
#
#       B E G I N   W H I L E
#
#############################################################################
class BeginWhile(Executable):
    def __init__(self, begin_seq, while_seq):
        self.name = 'begin'
        self._begin_seq = begin_seq
        self._while_seq = while_seq

    def __call__(self, name):
        dbg("trace", 2, "trace({})".format(repr(self)))
        try:
            while True:
                self._begin_seq.__call__("begin_seq")
                if rpn.globl.param_stack.empty():
                    raise rpn.exception.RuntimeErr(rpn.exception.X_INSUFF_PARAMS, "while", "(1 required)")
                flag = rpn.globl.param_stack.pop()
                if type(flag) is not rpn.type.Integer:
                    rpn.globl.param_stack.push(flag)
                    raise rpn.exception.RuntimeErr(rpn.exception.X_ARG_TYPE_MISMATCH, 'while', "({})".format(typename(flag)))
                if flag.value == 0:
                    break
                self._while_seq.__call__("while_seq")
        except rpn.exception.RuntimeErr as err_begin_while:
            if err_begin_while.code != rpn.exception.X_LEAVE:
                raise

    def patch_recurse(self, new_word):
        self._begin_seq.patch_recurse(new_word)
        self._while_seq.patch_recurse(new_word)

    def __str__(self):
        return "begin {} while {} repeat".format(self._begin_seq, self._while_seq)

    def __repr__(self):
        return "BeginWhile[{}, {}]".format(repr(self._begin_seq), repr(self._while_seq))


#############################################################################
#
#       C A S E
#
#############################################################################
class Case(Executable):
    def __init__(self, case_clauses, otherwise_seq):
        self.name = 'case'
        self._case_clauses  = case_clauses
        self._otherwise_seq = otherwise_seq

    def __call__(self, name):
        dbg("trace", 2, "trace({})".format(repr(self)))
        if rpn.globl.param_stack.empty():
            raise rpn.exception.RuntimeErr(rpn.exception.X_INSUFF_PARAMS, "case", "(1 required)")
        n = rpn.globl.param_stack.pop()
        if type(n) is not rpn.type.Integer:
            rpn.globl.param_stack.push(n)
            raise rpn.exception.RuntimeErr(rpn.exception.X_ARG_TYPE_MISMATCH, 'case', "({})".format(typename(n)))
        nval = n.value

        # Determine the correct sequence to call
        seq = self._otherwise_seq
        for clause in self._case_clauses.items():
            if clause.x() == nval:
                seq = clause
                break

        # Call it with a new scope
        case_scope = rpn.util.Scope("Case")
        case_scope.define_variable('caseval', rpn.util.Variable("caseval", n))
        try:
            rpn.globl.push_scope(case_scope, "Starting Case")
            seq.__call__("seq")
        finally:
            rpn.globl.pop_scope("Case complete")

    def patch_recurse(self, new_word):
        self._case_clauses.patch_recurse(new_word)
        self._otherwise_seq.patch_recurse(new_word)

    def __str__(self):
        s = "case "
        for cc in self._case_clauses.items():
            s += str(cc)
        if self._otherwise_seq is not None:
            s += "otherwise {} ".format(self._otherwise_seq)
        s += "endcase"
        return s

    def __repr__(self):
        s = "Case["
        s += ", ".join([repr(cc) for cc in self._case_clauses.items()])
        if self._otherwise_seq is not None:
            s += ", Otherwise[{}]".format(repr(self._otherwise_seq))
        return s + "]"


#############################################################################
#
#       C A S E   C L A U S E
#
#############################################################################
class CaseClause(Executable):
    def __init__(self, x, of_seq):
        self.name = 'of'
        self._x = int(x.value if type(x) is rpn.type.Integer else x)
        self._of_seq = of_seq

    def x(self):
        return self._x

    def __call__(self, name):
        self._of_seq.__call__("of_seq")

    def patch_recurse(self, new_word):
        self._of_seq.patch_recurse(new_word)

    def __str__(self):
        return "{} of {} endof ".format(self._x, self._of_seq)

    def __repr__(self):
        return "Of[{}={}]".format(self._x, repr(self._of_seq))


#############################################################################
#
#       C A T C H
#
#############################################################################
class Catch(Executable):
    def __init__(self, word, scope):
        self.name = 'catch'
        if type(word) is not rpn.util.Word:
            raise rpn.exception.FatalErr("{}: Word {} is not an rpn.util.Word".format(whoami(), repr(word)))
        if type(scope) is not rpn.util.Scope:
            raise rpn.exception.FatalErr("{}: Scope {} is not an rpn.util.Scope".format(whoami(), repr(scope)))
        dbg("catch", 1, "{}: Catch({})".format(whoami(), word))
        self._word = word
        self._scope = scope

    def __call__(self, name):
        dbg("trace", 1, "trace({})".format(repr(self)))
        dbg("catch", 1, "Calling {}: word={}, scope={}".format(whoami(), repr(self._word), repr(self._scope)))
        try:
            rpn.globl.execute(self._word)
        except rpn.exception.RuntimeErr as err_catch:
            dbg("catch", 1, "{}: Caught a throw, e={}".format(whoami(), str(err_catch)))
            rpn.globl.param_stack.push(rpn.type.Integer(int(err_catch.code)))
        else:
            dbg("catch", 1, "{}: Nothing caught, finishing normally".format(whoami()))
            rpn.globl.param_stack.push(rpn.type.Integer(0))

    def __str__(self):
        return "catch {}".format(self._word.name)

    def __repr__(self):
        return "Catch[{}]".format(repr(self._word.name))


#############################################################################
#
#       C O N S T A N T
#
#############################################################################
class Constant(Executable):
    def __init__(self, var):
        self.name = 'constant'
        self._variable = var

    def __call__(self, name):
        dbg("trace", 1, "trace({})".format(repr(self)))
        if rpn.globl.param_stack.empty():
            raise rpn.exception.RuntimeErr(rpn.exception.X_INSUFF_PARAMS, "constant", "(1 required)")
        self._variable.obj = rpn.globl.param_stack.pop()

    def __str__(self):
        return "constant {}".format(self._variable.name)

    def __repr__(self):
        return "Constant[{}]".format(repr(self._variable))


#############################################################################
#
#       D O   L O O P
#
#############################################################################
class DoLoop(Executable):
    def __init__(self, do_seq):
        self.name = 'do'
        self._do_seq = do_seq

    def __call__(self, name):
        dbg("trace", 2, "trace({})".format(repr(self)))
        if rpn.globl.param_stack.size() < 2:
            raise rpn.exception.RuntimeErr(rpn.exception.X_INSUFF_PARAMS, "do", "(2 required)")
        x = rpn.globl.param_stack.pop()
        y = rpn.globl.param_stack.pop()
        if type(y) is not rpn.type.Integer or type(x) is not rpn.type.Integer:
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            raise rpn.exception.RuntimeErr(rpn.exception.X_ARG_TYPE_MISMATCH, 'do', "({} {})".format(typename(y), typename(x)))
        limit = y.value
        i = x.value
        if i == limit:
            #rpn.globl.lnwriteln("do: Not executing because initial == limit")
            return

        # Create a new scope
        _I = rpn.util.Variable("_I", x)
        do_scope = rpn.util.Scope("DoLoop")
        do_scope.define_variable('_I', _I)

        try:
            rpn.globl.push_scope(do_scope, "Starting DoLoop")
            while True:
                self._do_seq.__call__("do_seq")
                i += 1
                _I.obj = rpn.type.Integer(i)
                if i >= limit:
                    break
        except rpn.exception.RuntimeErr as err_do_loop:
            if err_do_loop.code != rpn.exception.X_LEAVE:
                raise
        finally:
            rpn.globl.pop_scope("DoLoop complete")

    def patch_recurse(self, new_word):
        self._do_seq.patch_recurse(new_word)

    def __str__(self):
        return "do {} loop".format(self._do_seq)

    def __repr__(self):
        return "DoLoop[{}]".format(repr(self._do_seq))


#############################################################################
#
#       D O   + L O O P
#
#############################################################################
class DoPlusLoop(Executable):
    def __init__(self, do_seq):
        self.name = 'do'
        self._do_seq = do_seq

    def __call__(self, name):
        dbg("trace", 2, "trace({})".format(repr(self)))
        if rpn.globl.param_stack.size() < 2:
            raise rpn.exception.RuntimeErr(rpn.exception.X_INSUFF_PARAMS, "do", "(2 required)")
        x = rpn.globl.param_stack.pop()
        y = rpn.globl.param_stack.pop()
        if type(y) is not rpn.type.Integer or type(x) is not rpn.type.Integer:
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            raise rpn.exception.RuntimeErr(rpn.exception.X_ARG_TYPE_MISMATCH, 'do', "({} {})".format(typename(y), typename(x)))
        limit = y.value
        i = x.value
        if i == limit:
            #rpn.globl.lnwriteln("do: Not executing because initial == limit")
            return

        # Create a new scope
        _I = rpn.util.Variable("_I", x)
        do_scope = rpn.util.Scope("DoPlusLoop")
        do_scope.define_variable('_I', _I)

        try:
            rpn.globl.push_scope(do_scope, "Starting DoPlusLoop")
            while True:
                self._do_seq.__call__("do_seq")
                if rpn.globl.param_stack.empty():
                    raise rpn.exception.RuntimeErr(rpn.exception.X_INSUFF_PARAMS, "+loop", "(1 required)")
                incr = rpn.globl.param_stack.pop()
                if type(incr) is not rpn.type.Integer:
                    rpn.globl.param_stack.push(incr)
                    raise rpn.exception.RuntimeErr(rpn.exception.X_ARG_TYPE_MISMATCH, '+loop', "({})".format(typename(incr)))
                i += incr.value
                _I.obj = rpn.type.Integer(i)
                if    incr.value > 0 and i >= limit \
                   or incr.value < 0 and i < limit:
                    break
        except rpn.exception.RuntimeErr as err_do_plusloop:
            if err_do_plusloop.code != rpn.exception.X_LEAVE:
                raise
        finally:
            rpn.globl.pop_scope("DoPlusLoop complete")

    def patch_recurse(self, new_word):
        self._do_seq.patch_recurse(new_word)

    def __str__(self):
        return "do {} +loop".format(self._do_seq)

    def __repr__(self):
        return "DoPlusLoop[{}]".format(repr(self._do_seq))


#############################################################################
#
#       D O T   Q U O T E
#
#############################################################################
class DotQuote(Executable):
    def __init__(self, val):
        self.name = '."'
        if len(val) < 3 or val[0:2] != '."' or val[-1] != '"':
            raise rpn.exception.FatalErr("{}: Malformed string: '{}'".format(whoami(), val))
        self._str = val[2:-1]

    def stringval(self):
        return self._str

    def __call__(self, name):
        dbg("trace", 1, "trace({})".format(repr(self)))
        rpn.globl.write("{}".format(self.stringval()))

    def __str__(self):
        return '."{}"'.format(self.stringval())

    def __repr__(self):
        return 'DotQuote["{}"]'.format(self.stringval())


#############################################################################
#
#       F E T C H   V A R
#
#############################################################################
class FetchVar(Executable):
    """Fetch variable.

It is normally an error to fetch an undefined variable,
but @?VAR will return 0 if VAR is not defined.

In addition to fetching the value of a variable,
"recall arithmetic" modifies the TOS (X) value in an
additional way: using the variable's value,
        New TOS = Previous TOS +|-|*|/ Variable value
The value stored in Variable is not affected.  Does
the right thing with empty stack (uses zero)."""

    def __init__(self, ident, modifier=None):
        self.name = '@'
        self._identifier = ident
        self._modifier   = modifier

    def identifier(self):
        return self._identifier

    def __call__(self, name):
        dbg("trace", 1, "trace({})".format(repr(self)))
        (var, _) = rpn.globl.lookup_variable(self.identifier())
        if var is None:
            raise rpn.exception.FatalErr("{}: Variable has vanished!".format(str(self)))
        if var.obj is None:
            if self._modifier == '?':
                rpn.globl.param_stack.push(rpn.type.Integer(0))
                # The variable remains undefined
            else:
                raise rpn.exception.RuntimeErr(rpn.exception.X_UNDEFINED_VARIABLE, str(self))
        elif self._modifier == '$' or type(var.obj) is rpn.type.String:
            rpn.globl.string_stack.push(var.obj)
        else:
            if self._modifier is not None and self._modifier == '/' and var.obj.zerop():
                raise rpn.exception.RuntimeErr(rpn.exception.X_DIVISION_BY_ZERO, str(self))
            if self._modifier is not None and self._modifier != '.' and rpn.globl.param_stack.empty():
                # Fake a zero on the stack so recall arithmetic continues to work
                rpn.globl.param_stack.push(rpn.type.Integer(0))
            rpn.globl.param_stack.push(var.obj)

            # Save and restore show X flag
            rpn.flag.copy_flag(rpn.flag.F_SHOW_X, 54)
            if self._modifier == '.':
                rpn.word.w_dot('.')
            elif self._modifier == '+':
                rpn.word.w_plus('+')
            elif self._modifier == '-':
                rpn.word.w_minus('-')
            elif self._modifier == '*':
                rpn.word.w_star('*')
            elif self._modifier == '/':
                rpn.word.w_slash('/')
            rpn.flag.copy_flag(54, rpn.flag.F_SHOW_X)
            rpn.flag.clear_flag(54)

    def __str__(self):
        return "@{}{}".format(self._modifier if self._modifier is not None else "",
                              self.identifier())

    def __repr__(self):
        return "FetchVar{}[{}]".format(self._modifier if self._modifier is not None else "",
                                       self.identifier())


#############################################################################
#
#       F O R G E T
#
#############################################################################
class Forget(Executable):
    def __init__(self, word, scope):
        self.name = 'forget'
        if type(word) is not rpn.util.Word:
            raise rpn.exception.FatalErr("{}: {} is not a Word".format(whoami(), repr(word)))
        if type(scope) is not rpn.util.Scope:
            raise rpn.exception.FatalErr("{}: {} is not a Scope".format(whoami(), repr(scope)))
        self._word = word
        self._scope = scope

    def __call__(self, name):
        dbg("trace", 1, "trace({})".format(repr(self)))
        if self._word.protected:
            raise rpn.exception.RuntimeErr(rpn.exception.X_PROTECTED, 'forget', "Cannot forget '{}'".format(self._word.name))
        self._scope.delete_word(self._word.name)

    def __str__(self):
        return "forget {}".format(self._word.name)

    def __repr__(self):
        return "Forget[{}]".format(repr(self._word.name))


#############################################################################
#
#       H E L P
#
#############################################################################
class Help(Executable):
    def __init__(self, ident, doc):
        self.name = 'help'
        self._identifier = ident
        self._doc = doc

    def __call__(self, name):
        dbg("trace", 1, "trace({})".format(repr(self)))
        rpn.globl.lnwriteln(self.doc())

    def identifier(self):
        return self._identifier

    def doc(self):
        return self._doc

    def __str__(self):
        return "help {}".format(self.identifier())

    def __repr__(self):
        return "Help[{}]".format(repr(self.identifier()))


#############################################################################
#
#       H I D E
#
#############################################################################
class Hide(Executable):
    def __init__(self, word):
        self.name = 'hide'
        if type(word) is not rpn.util.Word:
            raise rpn.exception.FatalErr("{}: {} is not a Word".format(whoami(), repr(word)))
        self._word = word

    def __call__(self, name):
        dbg("trace", 1, "trace({})".format(repr(self)))
        if self._word.protected:
            raise rpn.exception.RuntimeErr(rpn.exception.X_PROTECTED, 'hide', "Cannot hide '{}'".format(self._word.name))
        self._word.hidden = True

    def __str__(self):
        return "hide {}".format(self._word.name)

    def __repr__(self):
        return "Hide[{}]".format(repr(self._word.name))


#############################################################################
#
#       I F   E L S E
#
#############################################################################
class IfElse(Executable):
    def __init__(self, if_seq, else_seq):
        self.name = 'if'
        self._if_seq   = if_seq
        self._else_seq = else_seq

    def __call__(self, name):
        dbg("trace", 2, "trace({})".format(repr(self)))
        if rpn.globl.param_stack.empty():
            raise rpn.exception.RuntimeErr(rpn.exception.X_INSUFF_PARAMS, "if", "(1 required)")
        flag = rpn.globl.param_stack.pop()
        if type(flag) is not rpn.type.Integer:
            rpn.globl.param_stack.push(flag)
            raise rpn.exception.RuntimeErr(rpn.exception.X_ARG_TYPE_MISMATCH, 'if', "({})".format(typename(flag)))
        if flag.value != 0:
            self._if_seq.__call__("if_seq")
        elif self._else_seq is not None:
            self._else_seq.__call__("else_seq")

    def patch_recurse(self, new_word):
        self._if_seq.patch_recurse(new_word)
        if self._else_seq is not None:
            self._else_seq.patch_recurse(new_word)

    def __str__(self):
        s = "if {} ".format(self._if_seq)
        if self._else_seq is not None:
            s += "else {} ".format(self._else_seq)
        return s + "then"

    def __repr__(self):
        s = "If"
        if self._else_seq is not None:
            s += "Else"
        s += "[{}".format(repr(self._if_seq))
        if self._else_seq is not None:
            s += ", {}".format(repr(self._else_seq))
        return s + "]"


#############################################################################
#
#       R E C U R S E
#
#############################################################################
class Recurse(Executable):
    def __init__(self, target=None):
        self.name = 'recurse'
        if target is not None and type(target) is not rpn.util.Word:
            raise rpn.exception.FatalErr("{}: Target '{}' is not an rpn.util.Word".format(whoami(), repr(target)))
        self._target = target

    def __call__(self, name):
        dbg("trace", 1, "trace({})".format(repr(self)))
        if self.target() is None:
            raise rpn.exception.RuntimeErr(rpn.exception.X_INVALID_RECURSION, "recurse")
        self.target().__call__("target")

    def target(self):
        return self._target

    def patch_recurse(self, new_word):
        if self.target() is None:
            self._target = new_word
        else:
            raise rpn.exception.FatalErr("{}: Invoked on already patched Recurse object".format(whoami()))

    def __str__(self):
        return "recurse"

    def __repr__(self):
        if self.target() is None:
            return "Recurse[]"
        return "RWord[{}]".format(repr(self.target().name))


#############################################################################
#
#       S H O W
#
#############################################################################
class Show(Executable):
    def __init__(self, word):
        self.name = 'show'
        if type(word) is not rpn.util.Word:
            raise rpn.exception.FatalErr("{}: Word {} is not an rpn.util.Word".format(whoami(), repr(word)))
        self._word = word

    def __call__(self, name):
        dbg("trace", 1, "trace({})".format(repr(self)))
        rpn.globl.writeln(self._word.as_definition())

    def __str__(self):
        return "show {}".format(self._word.name)

    def __repr__(self):
        return "Show[{}]".format(repr(self._word.name))


#############################################################################
#
#       S T O R E   V A R
#
#############################################################################
class StoreVar(Executable):
    """Store variable.

In addition to storing a value directly in a variable,
"storage arithmetic" modifies the variable's value in an
additional way: using the TOS value,
        Variable New value = Previous value +|-|*|/ TOS
The TOS is consumed as normal."""

    def __init__(self, ident, modifier=None):
        self.name = '!'
        self._identifier = ident
        self._modifier   = modifier

    def identifier(self):
        return self._identifier

    def __call__(self, name):
        dbg("trace", 1, "trace({})".format(repr(self)))
        (var, _) = rpn.globl.lookup_variable(self.identifier())
        stringp = bool(self._modifier == '$')
        if var is None:
            raise rpn.exception.FatalErr("{}: Variable has vanished!".format(str(self)))
        if var.readonly():
            raise rpn.exception.RuntimeErr(rpn.exception.X_READ_ONLY, str(self), "Variable cannot be modified")
        if var.constant():
            raise rpn.exception.RuntimeErr(rpn.exception.X_READ_ONLY, str(self), "Constant cannot be modified")
        if stringp and rpn.globl.string_stack.empty():
            raise rpn.exception.RuntimeErr(rpn.exception.X_INSUFF_STR_PARAMS, str(self), "(1 required)")
        if not stringp and rpn.globl.param_stack.empty():
            raise rpn.exception.RuntimeErr(rpn.exception.X_INSUFF_PARAMS, str(self), "(1 required)")
        if self._modifier == '/' and rpn.globl.param_stack.top().zerop():
            raise rpn.exception.RuntimeErr(rpn.exception.X_DIVISION_BY_ZERO, str(self))

        cur_obj = var.obj
        new_obj = rpn.globl.string_stack.top() if stringp else rpn.globl.param_stack.top()
        for pre_hook_func in var.pre_hooks():
            try:
                pre_hook_func(self.identifier(), cur_obj, new_obj)
            except rpn.exception.RuntimeErr as err_pre_hook_store:
                rpn.globl.lnwriteln(str(err_pre_hook_store))
                return

        if not stringp and self._modifier is not None:
            rpn.globl.param_stack.push(cur_obj)
            rpn.flag.copy_flag(rpn.flag.F_SHOW_X, 54)
            rpn.word.w_swap('swap')
            if self._modifier == '+':
                rpn.word.w_plus('+')
            elif self._modifier == '-':
                rpn.word.w_minus('-')
            elif self._modifier == '*':
                rpn.word.w_star('*')
            elif self._modifier == '/':
                rpn.word.w_slash('/')
            rpn.flag.copy_flag(54, rpn.flag.F_SHOW_X)
            rpn.flag.clear_flag(54)

        old_obj = cur_obj
        new_obj = rpn.globl.string_stack.pop() if stringp else rpn.globl.param_stack.pop()
        var.obj = new_obj

        for post_hook_func in var.post_hooks():
            post_hook_func(self.identifier(), old_obj, new_obj)

    def __str__(self):
        return "!{}{}".format(self._modifier if self._modifier is not None else "",
                              self.identifier())

    def __repr__(self):
        return "StoreVar{}[{}]".format(self._modifier if self._modifier is not None else "",
                                       self.identifier())
