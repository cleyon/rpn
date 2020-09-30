'''
#############################################################################
#
#       S U P P O R T   C L A S S E S
#
#############################################################################
'''

import math
import queue
import readline                         # pylint: disable=unused-import

from   rpn.debug import dbg, typename, whoami
import rpn.flag
import rpn.globl
import rpn.type


got_interrupt = False


# | Mode | 40 | 41 |
# |------+----+----|
# | sci  |  0 |  0 |
# | eng  |  0 |  1 |
# | fix  |  1 |  0 |
# | std  |  1 |  1 |
# |------+----+----|
#
# | # digits | 36 | 37 | 38 | 39 |
# |----------+----+----+----+----|
# |        0 |  0 |  0 |  0 |  0 |
# |        1 |  0 |  0 |  0 |  1 |
# |        2 |  0 |  0 |  1 |  0 |
# |        3 |  0 |  0 |  1 |  1 |
# |        4 |  0 |  1 |  0 |  0 |
# |        5 |  0 |  1 |  0 |  1 |
# |        6 |  0 |  1 |  1 |  0 |
# |        7 |  0 |  1 |  1 |  1 |
# |        8 |  1 |  0 |  0 |  0 |
# |        9 |  1 |  0 |  0 |  1 |
# |       10 |  1 |  0 |  1 |  0 |
# |       11 |  1 |  0 |  1 |  1 |
# |       12 |  1 |  1 |  0 |  0 |
# |       13 |  1 |  1 |  0 |  1 |
# |       14 |  1 |  1 |  1 |  0 |
# |       15 |  1 |  1 |  1 |  1 |
# |----------+----+----+----+----|
class DisplayConfig:
    def __init__(self):
        self._style = None
        self._prec  = None

    def style(self):
        return self._style

    def set_style(self, style):
        if style not in ["std", "fix", "sci", "eng"]:
            raise rpn.exception.FatalErr("{}: Invalid display style '{}'".format(whoami(), style))
        self._style = style

    def prec(self):
        return self._prec

    def set_prec(self, prec):
        if prec < 0 or prec >= rpn.globl.PRECISION_MAX:
            raise rpn.exception.FatalErr("{}: Invalid display precision '{}' (0..{} expected)".format(whoami(), prec, rpn.globl.PRECISION_MAX - 1))
        self._prec = prec
        for bit in range(4):
            if prec & 1<<bit != 0:
                rpn.flag.set_flag(39 - bit)
            else:
                rpn.flag.clear_flag(39 - bit)

    def eng_notate(self, x):
        """
        Convert a float to a string in engineering units, with specified
        significant figures
        :param x: float to convert
        :param sf: number of significant figures
        :return: string conversion of x in scientific notation
        """

        sf = self.prec()
        if x == 0:
            return "0." + "0"*(sf-1) + "e+00"
        mant_sign = ""
        if x < 0.0:
            mant_sign = "-"
            x = -x
        # Normalize the number and round to get sf significant figures
        mant, exp = frexp10(x)
        r = round(mant, sf-1)
        # Convert back to original scale
        x = r * math.pow(10.0, exp)
        # Get integer exponent to group by factors of 1000
        p = int(math.floor(math.log10(x)))
        p3 = p // 3
        # Get root value string
        value = x / math.pow(10.0, 3*p3)
        num_str = "{:f}".format(value)
        # Slice to length, avoid trailing "."
        if num_str[sf] != ".":
            num_str = num_str[0:sf+1]
        else:
            num_str = num_str[0:sf]
        exp_sign = "-" if p3 < 0 else "+"
        exp_str = "{:02d}".format(abs(3*p3))
        return mant_sign + num_str + "e" + exp_sign + exp_str

    def fmt(self, x, show_label=True):
        if type(x) is float:
            if self.style() == "fix":
                return "{:.{prec}{style}}".format(x, style="f", prec=self.prec())
            if self.style() == "sci":
                return "{:.{prec}{style}}".format(x, style="e", prec=self.prec())
            if self.style() == "eng":
                return self.eng_notate(x)
            if self.style() == "std":
                return str(x)
            raise rpn.exception.FatalErr("{}: Invalid style '{}'".format(whoami(), self.style()))
        if type(x) is rpn.type.Float:
            s = self.fmt(x.value())
            l = ""
            if show_label and x.label is not None:
                l = r"  \ " + "{}".format(x.label)
            return s + l
        if type(x) is rpn.type.String:
            return x.value()
        return str(x)


class List:
    def __init__(self, item=None, oldlist=None):
        if item is None and oldlist is None:
            self._list = []
        elif item is not None and oldlist is None:
            self._list = [item]
        else:
            val = []
            for x in oldlist.listval():
                val.append(x)
            val.insert(0, item)
            self._list = val

    def listval(self):
        return self._list

    def __getitem__(self, i):
        return self._list[i]

    def __setitem__(self, i, val):
        self._list[i] = val

    def append(self, item):
        self._list.append(item)

    def __call__(self):
        dbg("trace", 2, "trace({})".format(repr(self)))
        for item in self.listval():
            # rpn.globl.lnwriteln("{}: {}.__call__()".format(whoami(), item))
            item.__call__()

    def items(self):
        for item in self.listval():
            yield item

    def patch_recurse(self, new_word):
        for item in self.listval():
            item.patch_recurse(new_word)

    def __len__(self):
        return len(self.listval())

    def __str__(self):
        return " ".join([str(item) for item in self.listval()])

    def __repr__(self):
        return "List[" + ", ".join([repr(item) for item in self.listval()]) + "]"


class Queue:
    def __init__(self):
        self._q = queue.SimpleQueue()

    def empty(self):
        return self._q.empty()

    def get(self):
        return self._q.get_nowait()

    def put(self, item):
        self._q.put(item)


class Scope:
    def __init__(self, name):
        self._name = name
        self._words = {}
        self._variables = {}
        self._all_varnames = List() # Isn't varnames simply the key name for the variables dictionary?
        self._in_varnames  = List()
        self._out_varnames = List()

    def name(self):
        return self._name

    def words(self):
        return self._words

    def variables(self):
        return self._variables

    def set_word(self, identifier, word):
        if type(word) is not rpn.util.Word:
            raise rpn.exception.FatalErr("{}: '{}' is not a Word".format(whoami(), identifier))

        if rpn.globl.default_protected:
            if (word.doc() is None or len(word.doc()) == 0) and not word.hidden():
                print("Warning: Word '{}' has no documentation".format(identifier)) # OK
            # if word.args() is None:
            #     print("Warning: Word '{}' has no args!".format(identifier)) # OK

        self._words[identifier] = word

    def delete_word(self, identifier):
        del self._words[identifier]

    def word(self, identifier):
        return self._words.get(identifier)

    def set_variable(self, identifier, var):
        if type(var) is not Variable:
            raise rpn.exception.FatalErr("{}: '{}' is not a Variable".format(whoami(), identifier))
        dbg(whoami(), 1, "{}: Setting variable '{}' to {} in {}".format(whoami(), identifier, repr(var), repr(self)))
        self._variables[identifier] = var

    def add_varname(self, name):
        self._all_varnames.append(name)

    def all_varnames(self):
        return self._all_varnames

    def set_all_varnames(self, l):
        self._all_varnames = l

    def set_in_varnames(self, l):
        # l is an List of 'str'ings
        self._in_varnames = l

    def in_varnames(self):
        return self._in_varnames

    def set_out_varnames(self, l):
        # l is an List of 'str'ings
        self._out_varnames = l

    def out_varnames(self):
        return self._out_varnames

    def delete_variable(self, identifier):
        del self._variables[identifier]

    def variable(self, identifier):
        return self._variables.get(identifier)

    def visible_variables(self):
        return list(filter(lambda x: not x[1].hidden(), self.variables().items()))

    def unprotected_words(self):
        return list(filter(lambda x: not x[1].protected(), self.words().items()))

    def decorate_varname(self, varname):
        if varname in self.in_varnames() and varname in self.out_varnames():
            return "inout:{}".format(varname)
        if varname in self.in_varnames():
            return "in:{}".format(varname)
        if varname in self.out_varnames():
            return "out:{}".format(varname)
        return varname

    def __str__(self):
        # XXX Fix variable visibility
        s = ""
        #if len(self.visible_variables()) > 0:
        if len(self.all_varnames()) > 0:
            #s += "|" + " ".join([self.decorate_varname(x[0]) for x in self.visible_variables()]) + "|"
            s += "|" + " ".join([self.decorate_varname(x) for x in self.all_varnames()]) + "|"
            if len(self.words()) > 0:
                s += " "
        if len(self.words()) > 0:
            s += " ".join([w.as_definition() for w in self.words().values()])
        return s

    def __repr__(self):
        return "Scope['{}'={}]".format(self.name(), hex(id(self)))


class Sequence:
    def __init__(self, scope_template, exe_list):
        self._scope_template = scope_template
        self._exe_list       = exe_list
        dbg(whoami(), 1, "{}: scope_template={}, exe_list={}".format(whoami(), repr(scope_template), repr(exe_list)))

    def __call__(self):
        dbg("trace", 2, "trace({})".format(repr(self)))

        # Build a runtime scope populated with actual Variables.
        # We need to create a new empty scope, populate it with new
        # variables which are named clones of the templates in the
        # sequence's scope, and then push that new scope.  This
        # ensure that each frame gets its own set of local
        # variables.

        if self.scope_template().name()[:6] == "Parse_":
            scope_name = "Call_" + self.scope_template().name()[6:]
        else:
            scope_name = "Call_" + self.scope_template().name()
        scope = rpn.util.Scope(scope_name)
        # XXX what about kwargs???
        for varname in self.scope_template().all_varnames():
            var = rpn.util.Variable(varname, None)
            scope.set_variable(varname, var)

        if len(self.scope_template().in_varnames()) > 0:
            if rpn.globl.param_stack.size() < len(self.scope_template().in_varnames()):
                raise rpn.exception.RuntimeErr("{}: Insufficient parameters ({} required)".format(self.scope_template().name(), len(self.scope_template().in_varnames())))
            in_vars = []
            for varname in self.scope_template().in_varnames().items():
                in_vars.append(varname)
            in_vars.reverse()
            for varname in in_vars:
                obj = rpn.globl.param_stack.pop()
                dbg(whoami(), 1, "{}: Setting {} to {}".format(whoami(), varname, obj.value()))
                scope.variable(varname).set_obj(obj)

        dbg(whoami(), 1, "{}: seq={}".format(whoami(), repr(self.seq())))
        pushed_scope = False

        try:
            rpn.globl.push_scope(scope, "Calling {}".format(repr(self)))
            pushed_scope = True
            self.seq().__call__()
        # except rpn.exception.Exit:
        #     raise
        finally:
            if len(self.scope_template().out_varnames()) > 0:
                param_stack_pushes = 0
                for varname in self.scope_template().out_varnames().items():
                    var = scope.variable(varname)
                    if var is None:
                        raise rpn.exception.RuntimeErr("{}: {}: Variable '{}' has vanished!".format(whoami(), self.scope_template().name(), varname))
                    if not var.defined():
                        # Undo any previous param_stack pushes if we come across an out variable that's not defined
                        for _ in range(param_stack_pushes):
                            rpn.globl.param_stack.pop()
                        raise rpn.exception.RuntimeErr("{}: Variable '{}' was never set".format(self.scope_template().name(), varname))
                    dbg(whoami(), 1, "{} is {}".format(varname, repr(var.obj())))
                    rpn.globl.param_stack.push(var.obj())
                    param_stack_pushes += 1
            if pushed_scope:
                rpn.globl.pop_scope("{} complete".format(repr(self)))

    def patch_recurse(self, new_word):
        for idx, _ in enumerate(self.seq().items()):
            self.seq()[idx].patch_recurse(new_word)

    def scope_template(self):
        return self._scope_template

    def seq(self):
        return self._exe_list

    def __str__(self):
        scope_str = str(self.scope_template())
        # print("{}: scope_template={}".format(whoami(), repr(self.scope_template())))
        s = "{}{}{}".format(scope_str,
                            " " if len(scope_str) > 0 and len(self.seq()) > 0 else "",
                            str(self.seq()))
        return s
        # return "Something"


    def __repr__(self):
        return "Sequence[{}, {}]".format(repr(self.scope_template()), repr(self.seq()))


class Stack:
    def __init__(self, min_size=0, max_size=-1):
        self._min_size = min_size
        self._max_size = max_size
        self.clear()

    def clear(self):
        self._stack = []
        self._nitems = 0

    def size(self):
        return self._nitems

    def empty(self):
        return self.size() == 0

    def push(self, item):
        if self.size() == self._max_size:
            raise rpn.exception.StackOverflow("Stack overflow ({}) on {}".format(self._max_size, item))
        self._nitems += 1
        self._stack.append(item)

    def pop(self):
        if self.empty():
            raise rpn.exception.FatalErr("{}: Empty stack".format(whoami()))
        if self.size() == self._min_size:
            raise rpn.exception.StackUnderflow("Stack underflow ({})".format(self._min_size))
        self._nitems -= 1
        return self._stack.pop()

    def pick(self, n):
        if n < 0 or n >= self.size():
            raise rpn.exception.FatalErr("{}: Bad index".format(whoami()))
        return self._stack[self.size() - 1 - n]

    def roll(self, n):
        if n < 0 or n >= self.size():
            raise rpn.exception.FatalErr("{}: Bad index".format(whoami()))
        # Prevent stack underflow in unlucky situations.  Temporarily
        # increase the stack minimum size, because we're just going to
        # push an item back again to restore the situation.
        self._min_size += 1
        item = self._stack.pop(self.size() - 1 - n)
        self._nitems -= 1
        self._min_size -= 1
        self.push(item)

    def top(self):
        if self.empty():
            raise rpn.exception.FatalErr("{}: Empty stack".format(whoami()))
        return self._stack[self.size() - 1]

    def items_bottom_to_top(self):
        """Return stack items from bottom to top."""
        i = self._nitems + 1
        for item in self._stack:
            i -= 1
            yield (i-1, item)

    def items_top_to_bottom(self):
        """Return stack items from top to bottom."""
        return reversed(list(self.items_bottom_to_top()))

    def __str__(self):
        sa = []
        for (i, item) in self.items_bottom_to_top():
            sa.append("{}: {}".format(i, rpn.globl.fmt(item)))
        #print(sa)
        return "\n".join(sa)

    def __repr__(self):
        sa = []
        for (i, item) in self.items_bottom_to_top():
            sa.append("{}: {}".format(i, repr(item)))
        #print(sa)
        return "Stack[{}]".format(", ".join(sa))


class TokenMgr:
    qtok = Queue()
    e = 0

    @classmethod
    def get_more_tokens(cls):
        tok_count = 0
        data = ""
        prompt = prompt_string()

        # Read characters from input stream
        while data == "":
            if rpn.flag.flag_set_p(rpn.flag.F_SHOW_X) and not rpn.globl.param_stack.empty():
                rpn.globl.writeln("{}".format(rpn.globl.fmt(rpn.globl.param_stack.top())))
            rpn.flag.clear_flag(rpn.flag.F_SHOW_X)

            rpn.globl.lnwrite()
            rpn.globl.sharpout.set_obj(rpn.type.Integer(len(prompt)))
            data = input(prompt)
            rpn.globl.sharpout.set_obj(rpn.type.Integer(0))

        # Get all the tokens
        rpn.globl.lexer.input(data)
        while True:
            tok = rpn.globl.lexer.token()
            if not tok:
                break
            cls.qtok.put(tok)
            dbg("token", 3, "Lexer returned {}, queueing".format(tok))
            tok_count += 1

        return tok_count

    @classmethod
    def next_token(cls):
        global got_interrupt            # pylint: disable=global-statement
        if cls.qtok.empty():
            if cls.e == 0:
                new_toks = 0
                while new_toks == 0:
                    try:
                        new_toks = TokenMgr.get_more_tokens()
                    except EOFError:
                        # ^D (eof) on input signals end of input tokens
                        rpn.globl.lnwrite()
                        return
                    except KeyboardInterrupt:
                        # ^C can either void the parse_stack, or the end program
                        if rpn.globl.parse_stack.empty():
                            if got_interrupt:
                                raise rpn.exception.EndProgram()
                            rpn.globl.lnwriteln("[Interrupt; once more to quit]")
                            got_interrupt = True
                            continue
                        rpn.globl.lnwriteln("[Interrupt]")
                        raise rpn.exception.TopLevel()
                    else:
                        got_interrupt = False

        try:
            yield cls.qtok.get()
        except queue.Empty:
            return


class Variable:
    def __init__(self, rawname, obj=None, **kwargs):
        if not Variable.name_valid_p(rawname):
            raise rpn.exception.FatalErr("Invalid variable name '{}'".format(rawname))

        self._constant   = False
        self._doc        = None
        self._hidden     = False
        self._rawname    = rawname
        self._noshadow   = False
        self._protected  = rpn.globl.default_protected
        self._readonly   = False
        self._rpnobj     = obj
        self._pre_hooks  = []
        self._post_hooks = []

        # `constant' is created by user word "constant".  Constants are
        # initialized from the paramteter stack and cannot be modified
        # after creation.
        if "constant" in kwargs:
            self._constant = kwargs["constant"]
            del kwargs["constant"]

        # `doc' is the variable's documentation string.  For future use,
        # not currently implemented.
        if "doc" in kwargs:
            self._doc = kwargs["doc"]
            del kwargs["doc"]

        # `hidden' means that the variable does not appear in the VARS
        # command.  In all other respects (lookup, store, fetch) the
        # variable behaves normally.
        if "hidden" in kwargs:
            self._hidden = kwargs["hidden"]
            del kwargs["hidden"]

        # `noshadow' means that no variable of the same name can be
        # created in a lower scope.  This ensures that every operation
        # will find the original variable.
        if "noshadow" in kwargs:
            self._noshadow = kwargs["noshadow"]
            del kwargs["noshadow"]

        # `protected' variables cannot be UNDEFined.  However, they can
        # be modified or shadowed.
        if "protected" in kwargs:
            self._protected = kwargs["protected"]
            del kwargs["protected"]

        # `readonly' means variable may not be modified by the user.
        # Very similar to constant.  Users cannot create readonly variables,
        # only constants.  One previous difference was it was supposed
        # to be a syntax error to attempt to modify a constant, while it
        # was a runtime error to attempt to modify a readonly variable.
        # This distinction is not currently enforced.
        if "readonly" in kwargs:
            self._readonly = kwargs["readonly"]
            del kwargs["readonly"]

        # `pre_hooks' is a list of functions that are called before a
        # user-mode "!VAR" or "undef VAR".  It is called with the
        # following parameters: variable name, old object (be sure to
        # take .value()), and the new proposed value.  For "undef", new
        # value is None.  If system wants to prevent the change, the
        # pre_hook function should raise a rpn.exception.RuntimeErr
        # exception.  Nothing needs to be returned.
        if "pre_hooks" in kwargs:
            self._pre_hooks = kwargs["pre_hooks"]
            del kwargs["pre_hooks"]

        # `post_hooks' is a list of functions that are called after a
        # user-mode "!VAR" or "undef VAR".  It is used to update other
        # things that depend on the variable's new value.  Two
        # parameters are passed: the variable name, and some object:
        # usually the new value object, but if the variable is deleted
        # then None will be passed.  Nothing needs to be returned, and
        # no exceptions should be raised.
        if "post_hooks" in kwargs:
            self._post_hooks = kwargs["post_hooks"]
            del kwargs["post_hooks"]

        # If there are any keywords left over, they must be ones we
        # don't know about and we want to flag them as errors.
        if len(kwargs) > 0:
            for (key, val) in kwargs.items():
                print("Unrecognized keyword '{}'={}".format(key, val)) # OK
                raise rpn.exception.FatalErr("Could not construct variable '{}'".format(rawname))

    @classmethod
    def name_valid_p(cls, name):
        return not (name is None or len(name) == 0 or \
                    name[0] in ['+', '-', '*', '/', '?'])

    def obj(self):
        return self._rpnobj

    def set_obj(self, newobj):
        self._rpnobj = newobj

    def name(self):
        return self._rawname

    def defined(self):
        return self.obj() is not None

    def constant(self):
        return self._constant

    def hidden(self):
        return self._hidden

    def noshadow(self):
        return self._noshadow

    def protected(self):
        return self._protected

    def readonly(self):
        return self._readonly

    def pre_hooks(self):
        return self._pre_hooks

    def post_hooks(self):
        return self._post_hooks

    def __str__(self):
        return str(self._rawname)

    def __repr__(self):
        return "Variable[{},addr={},value={}]".format(self._rawname, hex(id(self)), repr(self.obj()))


class Word:
    def __init__(self, name, defn, **kwargs):
        self._args      = 0
        self._defn      = defn  # rpn.util.Sequence
        self._doc       = None
        self._hidden    = False
        self._immediate = False
        self._name      = name
        self._protected = rpn.globl.default_protected
        self._smudge    = False # True=Hidden, False=Findable
        self._str_args  = 0

        my_print_x = None

        if name is None or len(name) == 0:
            raise rpn.exception.FatalErr("Invalid word name '{}'".format(name))
        if defn is None:
            raise rpn.exception.FatalErr("{}: defn is None".format(name))
        #dbg(whoami(), 3, "defn is {}".format(type(defn)))

        # `args' is the number of numeric arguments that must be present
        # on the parameter stack.
        if "args" in kwargs:
            self._args = kwargs['args']
            del kwargs["args"]

        # `doc' is the docstring for the word.  For a built-in word, it
        # is set directly in the @defword() call.  For a colon
        # definition, use the doc:"DOCSTRING" construct.
        if "doc" in kwargs:
            self._doc = kwargs["doc"]
            del kwargs["doc"]

        # `hidden' means that the word will not appear in the vlist.  It
        # is still findable/executable by name like any other word.
        if "hidden" in kwargs:
            self._hidden = kwargs["hidden"]
            del kwargs["hidden"]

        # `immediate' means that the word will be immediately executed
        # when encountered, even in a colon definition.  Still evolving.
        if "immediate" in kwargs:
            self._immediate = kwargs["immediate"]
            del kwargs["immediate"]

        # `print_x' indicates whether the top of stack should be printed
        # (without popping) before the interactive prompt.  Most
        # computation words set this, most words that do I/O clear this
        # (on the grounds that desired output has already been
        # displayed), most control words do not change the setting.
        if "print_x" in kwargs:
            my_print_x = kwargs["print_x"]
            del kwargs["print_x"]
        # else:
        #     if self._protected:
        #         print("Word {} missing print_x".format(name))

        # `protected' means the word cannot be forgotten.  Built-in
        # words defined in code, and internal colon words defined in
        # define_secondary_words() are protected; user-defined colon
        # words and those created in define_tertiary_words() are not.
        if "protected" in kwargs:
            self._protected = kwargs["protected"]
            del kwargs["protected"]

        # `smudge' means the word cannot be located through normal
        # lookup.  This is used during definition.  The bit is cleared
        # to make the word findable.
        if "smudge" in kwargs:
            self._smudge = kwargs["smudge"]
            del kwargs["smudge"]

        # `str_args' is the number of string arguments that must be
        # present on the string stack.
        if "str_args" in kwargs:
            self._str_args = kwargs["str_args"]
            del kwargs["str_args"]

        if len(kwargs) > 0:
            for (key, val) in kwargs.items():
                print("Unrecognized keyword '{}'={}".format(key, val)) # OK
                raise rpn.exception.FatalErr("Could not construct word '{}'".format(name))

        kwargs["print_x"] = my_print_x

    def __call_immed__(self, arg):
        #print("{}: arg={}".format(whoami(), repr(arg)))
        self._defn.__call__(arg)

    def __call__(self):
        dbg("trace", 1, "trace({})".format(repr(self)))
        if rpn.globl.param_stack.size() < self.args():
            raise rpn.exception.RuntimeErr("{}: Insufficient parameters ({} required)".format(self.name(), self.args()))
        if rpn.globl.string_stack.size() < self.str_args():
            raise rpn.exception.RuntimeErr("{}: Insufficient string parameters ({} required)".format(self.name(), self.str_args()))

        try:
            self._defn.__call__()
        except rpn.exception.Exit:
            if self.name() == "exit":
                raise

    def name(self):
        return self._name

    def args(self):
        return self._args

    def str_args(self):
        return self._str_args

    def set_defn(self, new_defn):
        # defn is rpn.util.Sequence
        self._defn = new_defn

    def doc(self):
        return self._doc

    def set_doc(self, new_doc):
        self._doc = new_doc

    def hidden(self):
        return self._hidden

    def set_hidden(self, val):
        self._hidden = val

    def immediate(self):
        return self._immediate

    def protected(self):
        return self._protected

    def smudge(self):
        return self._smudge

    def set_smudge(self, new_smudge):
        self._smudge = new_smudge

    def as_definition(self):
        if typename(self._defn) == 'function':
            return self.name()
        if type(self._defn) is rpn.util.Sequence:
            return ": {} {}{} ;".format(self.name(),
                                        'doc:"{}"\n'.format(self.doc()) if self.doc() is not None and len(self.doc()) > 0 else "",
                                        str(self._defn))
        raise rpn.exception.FatalErr("{}: Unhandled type {}".format(whoami(), type(self._defn)))

    def __str__(self):
        return self.name()

    def patch_recurse(self, new_word):
        pass

    def __repr__(self):
        return "Word[{}]".format(self.name())
        # if typename(self._defn) == 'function':
        #     return "Word[{}]".format(self.name())
        # else:
        #     return "Word[{}, {}]".format(self.name(), repr(self._defn))



def frexp10(x):
    """
    Return mantissa and exponent (base 10), similar to base-2 frexp()
    :param x: floating point number
    :return: tuple (mantissa, exponent)
    """
    exp = math.floor(math.log10(x))
    return x/10**exp, exp


def prompt_string():
    s = "[{}{}".format(rpn.globl.angle_mode_letter(), rpn.globl.param_stack.size())
    if not rpn.globl.string_stack.empty():
        s += ",{}".format(rpn.globl.string_stack.size())
    s += "] "
    if not rpn.globl.parse_stack.empty():
        qq = " ".join([p[1] for p in rpn.globl.parse_stack.items_bottom_to_top()])
        s += qq + " ... "
    return s
