'''
#############################################################################
#
#       E X E C U T A B L E   C L A S S E S
#
#############################################################################
'''

from   rpn.debug import dbg, whoami
import rpn.exception
import rpn.globl


class Executable:
    def __call__(self):
        raise rpn.exception.FatalErr("Executable#__call__: Subclass responsibility")

    def patch_recurse(self, _):
        pass

    def immediate(self):
        return False


class AbortQuote(Executable):
    def __init__(self, val):
        if len(val) < 7 or val[0:6] != 'abort"' or val[-1] != '"':
            raise rpn.exception.FatalErr("{}: Malformed string: '{}'".format(whoami(), val))
        self._str = val[6:-1]

    def stringval(self):
        return self._str

    def __call__(self):
        dbg("trace", 1, "trace({})".format(repr(self)))
        if rpn.globl.param_stack.empty():
            raise rpn.exception.RuntimeErr("abort\": Insufficient parameters (1 required)")
        flag = rpn.globl.param_stack.pop()
        if type(flag) is not rpn.type.Integer:
            rpn.globl.param_stack.push(flag)
            raise rpn.exception.TypeErr("abort\": Flag must be an integer")
        if flag.value != 0:
            rpn.globl.lnwriteln("{}".format(self.stringval()))
            raise rpn.exception.Abort()

    def __str__(self):
        return 'abort"{}"'.format(self.stringval())

    def __repr__(self):
        return 'AbortQuote["{}"]'.format(self.stringval())


class BeginAgain(Executable):
    def __init__(self, begin_seq):
        self._begin_seq = begin_seq

    def __call__(self):
        dbg("trace", 2, "trace({})".format(repr(self)))
        try:
            while True:
                self._begin_seq.__call__()
        except rpn.exception.Leave:
            pass

    def patch_recurse(self, new_word):
        self._begin_seq.patch_recurse(new_word)

    def __str__(self):
        return "begin {} again".format(self._begin_seq)

    def __repr__(self):
        return "BeginAgain[{}]".format(repr(self._begin_seq))


class BeginUntil(Executable):
    def __init__(self, begin_seq):
        self._begin_seq = begin_seq

    def __call__(self):
        dbg("trace", 2, "trace({})".format(repr(self)))
        try:
            while True:
                self._begin_seq.__call__()
                if rpn.globl.param_stack.empty():
                    raise rpn.exception.RuntimeErr("until: Insufficient parameters (1 required)")
                flag = rpn.globl.param_stack.pop()
                if type(flag) is not rpn.type.Integer:
                    rpn.globl.param_stack.push(flag)
                    raise rpn.exception.TypeErr("until: Flag must be an integer")
                if flag.value != 0:
                    break
        except rpn.exception.Leave:
            pass

    def patch_recurse(self, new_word):
        self._begin_seq.patch_recurse(new_word)

    def __str__(self):
        return "begin {} until".format(self._begin_seq)

    def __repr__(self):
        return "BeginUntil[{}]".format(repr(self._begin_seq))


class BeginWhile(Executable):
    def __init__(self, begin_seq, while_seq):
        self._begin_seq = begin_seq
        self._while_seq = while_seq

    def __call__(self):
        dbg("trace", 2, "trace({})".format(repr(self)))
        try:
            while True:
                self._begin_seq.__call__()
                if rpn.globl.param_stack.empty():
                    raise rpn.exception.RuntimeErr("while: Insufficient parameters (1 required)")
                flag = rpn.globl.param_stack.pop()
                if type(flag) is not rpn.type.Integer:
                    rpn.globl.param_stack.push(flag)
                    raise rpn.exception.TypeErr("while: Flag must be an integer")
                if flag.value == 0:
                    break
                self._while_seq.__call__()
        except rpn.exception.Leave:
            pass

    def patch_recurse(self, new_word):
        self._begin_seq.patch_recurse(new_word)
        self._while_seq.patch_recurse(new_word)

    def __str__(self):
        return "begin {} while {} repeat".format(self._begin_seq, self._while_seq)

    def __repr__(self):
        return "BeginWhile[{}, {}]".format(repr(self._begin_seq), repr(self._while_seq))


class Case(Executable):
    def __init__(self, case_clauses, otherwise_seq):
        self._case_clauses  = case_clauses
        self._otherwise_seq = otherwise_seq

    def __call__(self):
        dbg("trace", 2, "trace({})".format(repr(self)))
        if rpn.globl.param_stack.empty():
            raise rpn.exception.RuntimeErr("case: Insufficient parameters (1 required)")
        n = rpn.globl.param_stack.pop()
        if type(n) is not rpn.type.Integer:
            rpn.globl.param_stack.push(n)
            raise rpn.exception.TypeErr("case: Case control parameter must be an integer")
        nval = n.value

        # Determine the correct sequence to call
        seq = self._otherwise_seq
        for clause in self._case_clauses.items():
            if clause.x() == nval:
                seq = clause
                break

        # Call it with a new scope
        case_scope = rpn.util.Scope("Call_Case")
        case_scope.set_variable('caseval', rpn.util.Variable("caseval", n))
        try:
            rpn.globl.push_scope(case_scope, "Starting Case")
            seq.__call__()
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


class CaseClause(Executable):
    def __init__(self, x, of_seq):
        self._x = int(x)      # x is a plain integer, not an rpn.type.Integer
        self._of_seq = of_seq

    def x(self):
        return self._x

    def __call__(self):
        self._of_seq.__call__()

    def patch_recurse(self, new_word):
        self._of_seq.patch_recurse(new_word)

    def __str__(self):
        return "{} of {} endof ".format(self._x, self._of_seq)

    def __repr__(self):
        return "Of[{}={}]".format(self._x, repr(self._of_seq))


class Catch(Executable):
    def __init__(self, word, scope):
        if type(word) is not rpn.util.Word:
            raise rpn.exception.FatalErr("{}: Word {} is not an rpn.util.Word".format(whoami(), repr(word)))
        if type(scope) is not rpn.util.Scope:
            raise rpn.exception.FatalErr("{}: Scope {} is not an rpn.util.Scope".format(whoami(), repr(scope)))
        dbg("catch", 1, "{}: Catch({})".format(whoami(), word))
        self._word = word
        self._scope = scope

    def __call__(self):
        dbg("trace", 1, "trace({})".format(repr(self)))
        dbg("catch", 1, "Calling {}: word={}, scope={}".format(whoami(), repr(self._word), repr(self._scope)))
        try:
            rpn.globl.execute(self._word)
        except rpn.exception.Throw as e:
            dbg("catch", 1, "{}: Caught a throw, e={}".format(whoami(), e))
            rpn.globl.param_stack.push(rpn.type.Integer(int(e.args[0])))
        else:
            dbg("catch", 1, "{}: Nothing caught, finishing normally".format(whoami()))
            rpn.globl.param_stack.push(rpn.type.Integer(0))

    def __str__(self):
        return "catch {}".format(self._word.name())

    def __repr__(self):
        return "Catch[{}]".format(repr(self._word.name()))


class Constant(Executable):
    def __init__(self, var):
        self._variable = var

    def __call__(self):
        dbg("trace", 1, "trace({})".format(repr(self)))
        if rpn.globl.param_stack.empty():
            raise rpn.exception.RuntimeErr("constant: Insufficient parameters (1 required)")
        self._variable.set_obj(rpn.globl.param_stack.pop())

    def __str__(self):
        return "constant {}".format(self._variable.name())

    def __repr__(self):
        return "Constant[{}]".format(repr(self._variable))


class DoLoop(Executable):
    def __init__(self, do_seq):
        self._do_seq = do_seq

    def __call__(self):
        dbg("trace", 2, "trace({})".format(repr(self)))
        if rpn.globl.param_stack.size() < 2:
            raise rpn.exception.RuntimeErr("do: Insufficient parameters (2 required)")
        x = rpn.globl.param_stack.pop()
        y = rpn.globl.param_stack.pop()
        if type(y) is not rpn.type.Integer or type(x) is not rpn.type.Integer:
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            raise rpn.exception.TypeErr("do: Loop control parameters must be integers")
        limit = y.value
        i = x.value
        if i == limit:
            #rpn.globl.lnwriteln("do: Not executing because initial == limit")
            return

        # Create a new scope
        _I = rpn.util.Variable("_I", x)
        do_scope = rpn.util.Scope("Call_Do_Loop")
        do_scope.set_variable('_I', _I)

        try:
            rpn.globl.push_scope(do_scope, "Starting Do_Loop")
            while True:
                self._do_seq.__call__()
                i += 1
                _I.set_obj(rpn.type.Integer(i))
                if i >= limit:
                    break
        except rpn.exception.Leave:
            pass
        finally:
            rpn.globl.pop_scope("Do_Loop complete")

    def patch_recurse(self, new_word):
        self._do_seq.patch_recurse(new_word)

    def __str__(self):
        return "do {} loop".format(self._do_seq)

    def __repr__(self):
        return "DoLoop[{}]".format(repr(self._do_seq))


class DoPlusLoop(Executable):
    def __init__(self, do_seq):
        self._do_seq = do_seq

    def __call__(self):
        dbg("trace", 2, "trace({})".format(repr(self)))
        if rpn.globl.param_stack.size() < 2:
            raise rpn.exception.RuntimeErr("do: Insufficient parameters (2 required)")
        x = rpn.globl.param_stack.pop()
        y = rpn.globl.param_stack.pop()
        if type(y) is not rpn.type.Integer or type(x) is not rpn.type.Integer:
            rpn.globl.param_stack.push(y)
            rpn.globl.param_stack.push(x)
            raise rpn.exception.TypeErr("do: Loop control parameters must be integers")
        limit = y.value
        i = x.value
        if i == limit:
            #rpn.globl.lnwriteln("do: Not executing because initial == limit")
            return

        # Create a new scope
        _I = rpn.util.Variable("_I", x)
        do_scope = rpn.util.Scope("Call_Do_PlusLoop")
        do_scope.set_variable('_I', _I)

        try:
            rpn.globl.push_scope(do_scope, "Starting Do_PlusLoop")
            while True:
                self._do_seq.__call__()
                if rpn.globl.param_stack.empty():
                    raise rpn.exception.RuntimeErr("+loop: Insufficient parameters (1 required)")
                incr = rpn.globl.param_stack.pop()
                if type(incr) is not rpn.type.Integer:
                    rpn.globl.param_stack.push(incr)
                    raise rpn.exception.TypeErr("+loop: Increment must be integer")
                i += incr.value
                _I.set_obj(rpn.type.Integer(i))
                if    incr.value > 0 and i >= limit \
                   or incr.value < 0 and i < limit:
                    break
        except rpn.exception.Leave:
            pass
        finally:
            rpn.globl.pop_scope("Do_PlusLoop complete")

    def patch_recurse(self, new_word):
        self._do_seq.patch_recurse(new_word)

    def __str__(self):
        return "do {} +loop".format(self._do_seq)

    def __repr__(self):
        return "DoPlusLoop[{}]".format(repr(self._do_seq))


class DotQuote(Executable):
    def __init__(self, val):
        if len(val) < 3 or val[0:2] != '."' or val[-1] != '"':
            raise rpn.exception.FatalErr("{}: Malformed string: '{}'".format(whoami(), val))
        self._str = val[2:-1]

    def stringval(self):
        return self._str

    def __call__(self):
        dbg("trace", 1, "trace({})".format(repr(self)))
        rpn.globl.write("{}".format(self.stringval()))

    def __str__(self):
        return '."{}"'.format(self.stringval())

    def __repr__(self):
        return 'DotQuote["{}"]'.format(self.stringval())


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
        self._identifier = ident
        self._modifier   = modifier

    def identifier(self):
        return self._identifier

    def __call__(self):
        dbg("trace", 1, "trace({})".format(repr(self)))
        (var, _) = rpn.globl.lookup_variable(self.identifier())
        if var is None:
            raise rpn.exception.FatalErr("{}: Variable has vanished!".format(str(self)))
        if var.obj() is None:
            if self._modifier == '?':
                rpn.globl.param_stack.push(rpn.type.Integer(0))
                # The variable remains undefined
            else:
                raise rpn.exception.RuntimeErr("{}: Variable is not defined".format(str(self)))
        elif self._modifier == '$' or type(var.obj()) is rpn.type.String:
            rpn.globl.string_stack.push(var.obj())
        else:
            if self._modifier is not None and self._modifier == '/' and var.obj().zerop():
                raise rpn.exception.RuntimeErr("{}: Cannot divide by zero".format(str(self)))
            if self._modifier is not None and rpn.globl.param_stack.empty():
                # Fake a zero on the stack so recall arithmetic continues to work
                rpn.globl.param_stack.push(rpn.type.Integer(0))
            rpn.globl.param_stack.push(var.obj())

            # Save and restore show X flag
            rpn.flag.copy_flag(rpn.flag.F_SHOW_X, 54)
            if self._modifier == '+':
                rpn.word.w_plus()
            elif self._modifier == '-':
                rpn.word.w_minus()
            elif self._modifier == '*':
                rpn.word.w_star()
            elif self._modifier == '/':
                rpn.word.w_slash()
            rpn.flag.copy_flag(54, rpn.flag.F_SHOW_X)
            rpn.flag.clear_flag(54)

    def __str__(self):
        return "@{}{}".format(self._modifier if self._modifier is not None else "",
                              self.identifier())

    def __repr__(self):
        return "FetchVar{}[{}]".format(self._modifier if self._modifier is not None else "",
                                       self.identifier())


class Forget(Executable):
    def __init__(self, word, scope):
        if type(word) is not rpn.util.Word:
            raise rpn.exception.FatalErr("{}: {} is not a Word".format(whoami(), repr(word)))
        if type(scope) is not rpn.util.Scope:
            raise rpn.exception.FatalErr("{}: {} is not a Scope".format(whoami(), repr(scope)))
        self._word = word
        self._scope = scope

    def __call__(self):
        dbg("trace", 1, "trace({})".format(repr(self)))
        if self._word.protected():
            raise rpn.exception.RuntimeErr("forget: '{}' is protected".format(self._word.name()))
        self._scope.delete_word(self._word.name())

    def __str__(self):
        return "forget {}".format(self._word.name())

    def __repr__(self):
        return "Forget[{}]".format(repr(self._word.name()))


class Help(Executable):
    def __init__(self, ident, doc):
        self._identifier = ident
        self._doc = doc

    def __call__(self):
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


class IfElse(Executable):
    def __init__(self, if_seq, else_seq):
        self._if_seq   = if_seq
        self._else_seq = else_seq

    def __call__(self):
        dbg("trace", 2, "trace({})".format(repr(self)))
        if rpn.globl.param_stack.empty():
            raise rpn.exception.RuntimeErr("if: Insufficient parameters (1 required)")
        flag = rpn.globl.param_stack.pop()
        if type(flag) is not rpn.type.Integer:
            rpn.globl.param_stack.push(flag)
            raise rpn.exception.TypeErr("if: Flag must be an integer")
        if flag.value != 0:
            self._if_seq.__call__()
        elif self._else_seq is not None:
            self._else_seq.__call__()

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


class Recurse(Executable):
    def __init__(self, target=None):
        if target is not None and type(target) is not rpn.util.Word:
            raise rpn.exception.FatalErr("{}: Target '{}' is not an rpn.util.Word".format(whoami(), repr(target)))
        self._target = target

    def __call__(self):
        dbg("trace", 1, "trace({})".format(repr(self)))
        if self.target() is None:
            raise rpn.exception.RuntimeErr("recurse: Only valid in colon definition")
        self.target().__call__()

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
        return "RWord[{}]".format(repr(self.target().name()))


class Show(Executable):
    def __init__(self, word, scope):
        if type(word) is not rpn.util.Word:
            raise rpn.exception.FatalErr("{}: Word {} is not an rpn.util.Word".format(whoami(), repr(word)))
        if type(scope) is not rpn.util.Scope:
            raise rpn.exception.FatalErr("{}: Scope {} is not a Scope".format(whoami(), repr(scope)))
        self._word = word
        self._scope = scope

    def __call__(self):
        dbg("trace", 1, "trace({})".format(repr(self)))
        rpn.globl.writeln(self._word.as_definition())

    def __str__(self):
        return "show {}".format(self._word.name())

    def __repr__(self):
        return "Show[{}]".format(repr(self._word.name()))


class StoreVar(Executable):
    """Store variable.

In addition to storing a value directly in a variable,
"storage arithmetic" modifies the variable's value in an
additional way: using the TOS value,
        Variable New value = Previous value +|-|*|/ TOS
The TOS is consumed as normal."""

    def __init__(self, ident, modifier=None):
        self._identifier = ident
        self._modifier   = modifier

    def identifier(self):
        return self._identifier

    def __call__(self):
        dbg("trace", 1, "trace({})".format(repr(self)))
        (var, _) = rpn.globl.lookup_variable(self.identifier())
        stringp = bool(self._modifier == '$')
        if var is None:
            raise rpn.exception.FatalErr("{}: Variable has vanished!".format(str(self)))
        if var.readonly():
            raise rpn.exception.RuntimeErr("{}: Variable cannot be modified".format(str(self)))
        if var.constant():
            raise rpn.exception.RuntimeErr("{}: Constant cannot be modified".format(str(self)))
        if stringp and rpn.globl.string_stack.empty():
            raise rpn.exception.RuntimeErr("{}: Insufficient string parameters (1 required)".format(str(self)))
        if not stringp and rpn.globl.param_stack.empty():
            raise rpn.exception.RuntimeErr("{}: Insufficient parameters (1 required)".format(str(self)))
        if self._modifier == '/' and rpn.globl.param_stack.top().zerop():
            raise rpn.exception.ValueErr("{}: X cannot be zero".format(str(self)))

        cur_obj = var.obj()
        new_obj = rpn.globl.string_stack.top() if stringp else rpn.globl.param_stack.top()
        for pre_hook_func in var.pre_hooks():
            try:
                pre_hook_func(self.identifier(), cur_obj, new_obj)
            except rpn.exception.RuntimeErr as e:
                rpn.globl.lnwriteln(str(e))
                return

        if not stringp and self._modifier is not None:
            rpn.globl.param_stack.push(cur_obj)
            rpn.flag.copy_flag(rpn.flag.F_SHOW_X, 54)
            rpn.word.w_swap()
            if self._modifier == '+':
                rpn.word.w_plus()
            elif self._modifier == '-':
                rpn.word.w_minus()
            elif self._modifier == '*':
                rpn.word.w_star()
            elif self._modifier == '/':
                rpn.word.w_slash()
            rpn.flag.copy_flag(54, rpn.flag.F_SHOW_X)
            rpn.flag.clear_flag(54)

        old_obj = cur_obj
        new_obj = rpn.globl.string_stack.pop() if stringp else rpn.globl.param_stack.pop()
        var.set_obj(new_obj)

        for post_hook_func in var.post_hooks():
            post_hook_func(self.identifier(), old_obj, new_obj)

    def __str__(self):
        return "!{}{}".format(self._modifier if self._modifier is not None else "",
                              self.identifier())

    def __repr__(self):
        return "StoreVar{}[{}]".format(self._modifier if self._modifier is not None else "",
                                       self.identifier())
