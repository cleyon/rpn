'''
#############################################################################
#
#       S U P P O R T   C L A S S E S
#
#############################################################################
'''

import collections
import math
import queue
import readline                         # pylint: disable=unused-import

from   rpn.debug     import dbg, typename, whoami
from   rpn.exception import *
import rpn.flag
import rpn.globl
import rpn.type


#############################################################################
#
#       D I S P L A Y   C O N F I G
#
#############################################################################
class DisplayConfig:
    '''
    |----------+----+----+----+----|          |------+----+----|
    | # digits | 36 | 37 | 38 | 39 |          | Mode | 40 | 41 |
    |----------+----+----+----+----|          |------+----+----|
    |        0 |  0 |  0 |  0 |  0 |          | sci  |  0 |  0 |
    |        1 |  0 |  0 |  0 |  1 |          | eng  |  0 |  1 |
    |        2 |  0 |  0 |  1 |  0 |          | fix  |  1 |  0 |
    |        3 |  0 |  0 |  1 |  1 |          | std  |  1 |  1 |
    |        4 |  0 |  1 |  0 |  0 |          |------+----+----|
    |        5 |  0 |  1 |  0 |  1 |
    |        6 |  0 |  1 |  1 |  0 |
    |        7 |  0 |  1 |  1 |  1 |
    |        8 |  1 |  0 |  0 |  0 |
    |        9 |  1 |  0 |  0 |  1 |
    |       10 |  1 |  0 |  1 |  0 |
    |       11 |  1 |  0 |  1 |  1 |
    |       12 |  1 |  1 |  0 |  0 |
    |       13 |  1 |  1 |  0 |  1 |
    |       14 |  1 |  1 |  1 |  0 |
    |       15 |  1 |  1 |  1 |  1 |
    |----------+----+----+----+----|
    '''

    def __init__(self):
        self._style = None
        self._prec  = None

    @property
    def style(self):
        return self._style

    @style.setter
    def style(self, new_style):
        if new_style not in ["std", "fix", "sci", "eng"]:
            raise FatalErr("{}: Invalid display style '{}'".format(whoami(), new_style))
        self._style = new_style

    @property
    def prec(self):
        return self._prec

    @prec.setter
    def prec(self, new_prec):
        if new_prec < 0 or new_prec >= rpn.globl.PRECISION_MAX:
            raise FatalErr("{}: Invalid display precision '{}' (0..{} expected)".format(whoami(), new_prec, rpn.globl.PRECISION_MAX - 1))
        self._prec = new_prec
        for bit in range(4):
            if new_prec & 1<<bit != 0:
                rpn.flag.set_flag(39 - bit)
            else:
                rpn.flag.clear_flag(39 - bit)

    def __str__(self):
        s = ""
        if self.style in ["fix", "sci", "eng"]:
            s += "{} ".format(self.prec)
        s += self.style
        return s


    def eng_notate(self, x):
        """
        Convert a float to a string in engineering units, with specified
        significant figures
        :param x: float to convert
        :param sf: number of significant figures
        :return: string conversion of x in scientific notation
        """

        sf = self.prec
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

    def dcfmt(self, x):
        if type(x) is int:
            return str(x)

        if type(x) is float:
            if self.style == "fix":
                return "{:.{prec}{style}}".format(x, style="f", prec=self.prec)
            if self.style == "sci":
                return "{:.{prec}{style}}".format(x, style="e", prec=self.prec)
            if self.style == "eng":
                return self.eng_notate(x)
            if self.style == "std":
                return str(x)

        if type(x) in [rpn.type.Integer, rpn.type.Float, rpn.type.Rational, rpn.type.Complex]:
            return x.instfmt()

        raise FatalErr("{}: Cannot handle type '{}' for object {}".format(whoami(), typename(x), x))


#############################################################################
#
#       L I S T
#
#############################################################################
class List:
    def __init__(self, item=None, oldlist=None):
        self.name = "List"
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

    def __call__(self, name):
        dbg("trace", 2, "trace({})".format(repr(self)))
        for item in self.listval():
            dbg(whoami(), 3, "{}: {}/{}.__call__()".format(whoami(), type(item), item))
            try:
                if type(item) is Word and item.typ == "colon":
                    dbg(whoami(), 2, ">>>>  {}  <<<<".format(item.name))
                    rpn.globl.colon_stack.push(item)
                item.__call__(item.name)
            finally:
                if type(item) is Word and item.typ == "colon":
                    rpn.globl.colon_stack.pop()

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


#############################################################################
#
#       Q U E U E
#
#############################################################################
class Queue:
    """
    This is actually a double-ended queue (deque).  My conception of the
    deque is similiar to the stack: Items normally come in from the left
    (put/appendleft) and are retrieved from the right (get/pop).  But to
    "push an item back onto the queue", so it is next in line to be
    retrieved, insert it on the right (push/append).
    """

    def __init__(self):
        self._q = collections.deque() # collections.abc.deque() ??

    def empty(self):
        return len(self._q) == 0

    def get(self):
        return self._q.pop()

    def put(self, item):
        self._q.appendleft(item)

    def push(self, item):       # rare
        self._q.append(item)


#############################################################################
#
#       S C O P E
#
#############################################################################
class Scope:
    def __init__(self, name):
        self.name = name
        self._words = {}
        self._variables = {}
        self._vnames = []

    def __str__(self):
        s = ""
        if len(self.vnames()) > 0:
            s += "|" + " ".join([x.decorated() for x in self.vnames()]) + "|"
            if len(self.words()) > 0:
                s += " "
        if len(self.words()) > 0:
            s += " ".join([w.name for w in self.words().values()])
        return s

    def __repr__(self):
        return "Scope['{}'={}]".format(self.name, hex(id(self)))

    ################################################################
    #
    #           Word methods
    #
    ################################################################
    def words(self):
        return self._words

    def word(self, identifier):
        return self._words.get(identifier)

    def define_word(self, identifier, word):
        if type(word) is not rpn.util.Word:
            raise FatalErr("{}: '{}' is not a Word".format(whoami(), identifier))

        if rpn.globl.default_protected:
            if (word.doc() is None or len(word.doc()) == 0) and not word.hidden:
                print("Warning: Word '{}' has no documentation".format(identifier)) # OK
            # if word.args() is None:
            #     print("Warning: Word '{}' has no args!".format(identifier)) # OK

        self._words[identifier] = word

    def delete_word(self, identifier):
        del self._words[identifier]

    def unprotected_words(self):
        return list(filter(lambda x: not x[1].protected, self.words().items()))

    ################################################################
    #
    #           Variable methods
    #
    ################################################################
    def variables(self):
        return self._variables

    def variable(self, identifier):
        return self._variables.get(identifier)

    def define_variable(self, identifier, var):
        if type(var) is not Variable:
            raise FatalErr("{}: '{}' is not a Variable".format(whoami(), identifier))
        dbg(whoami(), 1, "{}: Setting variable '{}' to {} in {}".format(whoami(), identifier, repr(var), repr(self)))
        self._variables[identifier] = var

    def delete_variable(self, identifier):
        del self._variables[identifier]

    def vnames(self):
        return self._vnames

    def vname(self, ident):
        if type(ident) is not str:
            raise FatalErr("Looking for a non-string '{}'".format(ident))
        return next(v for v in self._vnames if v.ident == ident)

    def add_vname(self, vname):
        if type(vname) is not rpn.util.VName:
            raise FatalErr("vname {} is not a VName".format(vname))
        self._vnames.append(vname)

    def has_vname_named(self, ident):
        if type(ident) is not str:
            raise FatalErr("Looking for a non-string '{}'".format(ident))
        return ident in [v.ident for v in self._vnames]


#############################################################################
#
#       S E Q U E N C E
#
#############################################################################
class Sequence:
    def __init__(self, scope_template, exe_list):
        self.name = "Sequence"
        self._scope_template = scope_template
        self._exe_list       = exe_list
        dbg(whoami(), 1, "{}: scope_template={}, exe_list={}".format(whoami(), repr(scope_template), repr(exe_list)))

    def __call__(self, name):
        dbg("trace", 2, "trace({})".format(repr(self)))

        # Build a runtime scope populated with actual Variables.
        # We need to create a new empty scope, populate it with new
        # variables which are named clones of the templates in the
        # sequence's scope, and then push that new scope.  This
        # ensure that each frame gets its own set of local
        # variables.

        in_vnames = list(filter(lambda v: v.in_p, self.scope_template().vnames()))
        if rpn.globl.param_stack.size() < len(in_vnames):
            throw(X_INSUFF_PARAMS, self.scope_template().name, "({} required)".format(len(in_vnames)))

        scope_name = self.scope_template().name
        scope = rpn.util.Scope(scope_name)
        # XXX what about kwargs???
        for vname in self.scope_template().vnames():
            var = rpn.util.Variable(vname.ident, None)
            scope.define_variable(vname.ident, var)

        in_vars = []
        for vname in in_vnames:
            in_vars.append(vname.ident)
        in_vars.reverse()
        for v in in_vars:
            obj = rpn.globl.param_stack.pop()
            dbg(whoami(), 1, "{}: Setting {} to {}".format(whoami(), v, obj.value))
            scope.variable(v).obj = obj

        dbg(whoami(), 1, "{}: seq={}".format(whoami(), repr(self.seq())))
        pushed_scope = False

        try:
            rpn.globl.push_scope(scope, "Calling {}".format(repr(self)))
            pushed_scope = True
            self.seq().__call__("seq")
        finally:
            param_stack_pushes = 0
            out_vnames = list(filter(lambda v: v.out_p, self.scope_template().vnames()))
            for vname in out_vnames:
                var = scope.variable(vname.ident)
                if var is None:
                    raise FatalErr("{}: {}: Variable '{}' has vanished!".format(whoami(), self.scope_template().name, vname.ident))
                if not var.defined():
                    # Undo any previous param_stack pushes if we come across an out variable that's not defined
                    for _ in range(param_stack_pushes):
                        rpn.globl.param_stack.pop()
                    if rpn.globl.sigint_detected:
                        throw(X_INTERRUPT, self.scope_template().name)
                    throw(X_UNDEFINED_VARIABLE, self.scope_template().name, "Variable '{}' was never set".format(vname.ident))
                dbg(whoami(), 3, "{} is {}".format(vname.ident, repr(var.obj)))
                rpn.globl.param_stack.push(var.obj)
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


#############################################################################
#
#       S T A C K
#
#############################################################################
class Stack:
    '''Internally, in these methods, stacks are 0-based like the Python
    lists in which they are implemented.  To the outside word, in user-
    space, stacks are 1-based.  Try to make this implementation detail
    invisible to the user.  All instances methods will internally convert
    elements from 1-based to 0-based as needed.  Also, items_top_to_bottom()
    et al return 1-based indices.'''

    def __init__(self, name, min_size=0, max_size=-1):
        self._name = name
        self._min_size = min_size
        self._max_size = max_size
        self.clear()

    def name(self):
        return self._name

    def clear(self):
        self._stack = []
        self._nitems = 0

    def size(self):
        return self._nitems

    def empty(self):
        return self.size() == 0

    def push(self, item):
        if self.size() == self._max_size:
            throw(X_STACK_OVERFLOW, whoami(), "{} exceeded max size={} when attempting to push {}".format(self.name(), self._max_size, item))
        self._nitems += 1
        self._stack.append(item)

    def pop(self):
        if self.empty():
            raise FatalErr("{}: Empty stack".format(whoami()))
        if self.size() == self._min_size:
            throw(X_STACK_UNDERFLOW, whoami(), "{} has min size={}".format(self.name, self._min_size))
        self._nitems -= 1
        return self._stack.pop()

    def pick(self, n):
        '''n will be 1-based, so handle appropriately.'''

        if n < 1 or n > self.size():
            raise FatalErr("{}: Bad index".format(whoami()))
        return self._stack[self.size() - n]

    def roll(self, n):
        '''n will be 1-based, so handle appropriately.'''
        if n < 1 or n > self.size():
            raise FatalErr("{}: Bad index".format(whoami()))
        # Prevent stack underflow in unlucky situations.  Temporarily
        # increase the stack minimum size, because we're just going to
        # push an item back again to restore the situation.
        self._min_size += 1
        item = self._stack.pop(self.size() - n)
        self._nitems -= 1
        self._min_size -= 1
        self.push(item)

    def top(self):
        if self.empty():
            raise FatalErr("{}: Empty stack".format(whoami()))
        return self._stack[self.size() - 1]

    def items_bottom_to_top(self):
        """Return stack items from bottom to top."""
        i = self._nitems + 1
        for item in self._stack:
            i -= 1
            yield (i, item)     # This yields 1-based indices; use i-1 for 0-based

    def items_top_to_bottom(self):
        """Return stack items from top to bottom."""
        return reversed(list(self.items_bottom_to_top()))

    def __str__(self):
        sa = []
        for (i, item) in self.items_bottom_to_top():
            sa.append("{}: {}".format(i, str(item)))
        #print(sa)
        return "\n".join(sa)

    def __repr__(self):
        sa = []
        for (i, item) in self.items_bottom_to_top():
            sa.append("{}: {}".format(i, repr(item)))
        #print(sa)
        return "Stack[{}]".format(", ".join(sa))


#############################################################################
#
#       T O K E N   M G R
#
#############################################################################
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
                rpn.globl.write("{} ".format(str(rpn.globl.param_stack.top())))
            rpn.flag.clear_flag(rpn.flag.F_SHOW_X)

            rpn.globl.lnwrite()
            rpn.globl.sharpout.obj = rpn.type.Integer(len(prompt))
            data = input(prompt)
            rpn.globl.sharpout.obj = rpn.type.Integer(0)

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
                    except RuntimeErr as e:
                        if e.code == X_INTERRUPT:
                            rpn.globl.lnwrite(throw_code_text[X_INTERRUPT])
                            # ^C can either void the parse_stack, or the end program
                            rpn.globl.sigint_detected = False
                            if rpn.globl.parse_stack.empty():
                                if rpn.globl.got_interrupt:
                                    rpn.globl.writeln()
                                    raise EndProgram() from e
                                rpn.globl.writeln("; once more to quit")
                                rpn.globl.got_interrupt = True
                                continue
                            raise TopLevel() from e
                        else:
                            rpn.globl.got_interrupt = False
                    else:
                        rpn.globl.got_interrupt = False

        try:
            yield cls.qtok.get()
        except queue.Empty:
            return

    @classmethod
    def push_token(cls, item):
        cls.qtok.push(item)


#############################################################################
#
#       V A R I A B L E
#
#############################################################################
class Variable:
    def __init__(self, name, obj=None, **kwargs):
        if not Variable.name_valid_p(name):
            raise FatalErr("Invalid variable name '{}'".format(name))

        self.name        = name
        self._constant   = False
        self._doc        = None
        self._hidden     = False
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
        # take .value), and the new proposed value.  For "undef", new
        # value is None.  If system wants to prevent the change, the
        # pre_hook function should raise a RuntimeErr exception (i.e.,
        # throw()).  Nothing needs to be returned.
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
                raise FatalErr("Could not construct variable '{}'".format(name))

    @classmethod
    def name_valid_p(cls, name):
        return not (name is None or len(name) == 0 or \
                    name[0] in ['+', '-', '*', '/', '?'])

    @property
    def obj(self):
        return self._rpnobj

    @obj.setter
    def obj(self, new_obj):
        self._rpnobj = new_obj

    def defined(self):
        return self.obj is not None

    def constant(self):
        return self._constant

    @property
    def hidden(self):
        return self._hidden

    @hidden.setter
    def hidden(self, new_hidden):
        self._hidden = new_hidden

    def noshadow(self):
        return self._noshadow

    @property
    def protected(self):
        return self._protected

    def readonly(self):
        return self._readonly

    def pre_hooks(self):
        return self._pre_hooks

    def post_hooks(self):
        return self._post_hooks

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return "Variable[{},addr={},value={}]".format(self.name, hex(id(self)), repr(self.obj))


#############################################################################
#
#       V N A M E
#
#############################################################################
class VName:
    def __init__(self, ident):
        self.ident = ident
        self.in_p = False
        self.out_p = False

    def decorated(self):
        dec = ""
        if self.in_p or self.out_p:
            if self.in_p:
                dec += "in"
            if self.out_p:
                dec += "out"
            dec += ":"
        return dec + self.ident

    def __str__(self):
        return self.decorated()

    def __repr__(self):
        return "VName[{}]".format(self.decorated())


#############################################################################
#
#       W O R D
#
#############################################################################
class Word:
    def __init__(self, name, typ, defn, **kwargs):
        self.name       = name
        self._args      = 0
        self._defn      = defn  # rpn.util.Sequence
        self._doc       = None
        self._hidden    = False
        self._immediate = False
        self._protected = rpn.globl.default_protected
        self._smudge    = False # True=Hidden, False=Findable
        self._str_args  = 0
        self.typ        = typ   # "python" or "colon"

        my_print_x = None

        if name is None or len(name) == 0:
            raise FatalErr("Invalid word name '{}'".format(name))
        if defn is None:
            raise FatalErr("{}: defn is None".format(name))
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
        #     if self.protected:
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
                raise FatalErr("Could not construct word '{}'".format(name))

        kwargs["print_x"] = my_print_x

    def __call_immed__(self, arg):
        #print("{}: arg={}".format(whoami(), repr(arg)))
        self._defn.__call__(arg)

    def __call__(self, name):
        dbg("trace", 1, "trace({})".format(repr(self)))
        if rpn.globl.param_stack.size() < self.args():
            throw(X_INSUFF_PARAMS, self.name, "({} required)".format(self.args()))
        if rpn.globl.string_stack.size() < self.str_args():
            throw(X_INSUFF_STR_PARAMS, self.name, "({} required)".format(self.str_args()))

        self._defn.__call__(self.name)

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

    @property
    def hidden(self):
        return self._hidden

    @hidden.setter
    def hidden(self, new_hidden):
        self._hidden = new_hidden

    def immediate(self):
        return self._immediate

    @property
    def protected(self):
        return self._protected

    def smudge(self):
        return self._smudge

    def set_smudge(self, new_smudge):
        self._smudge = new_smudge

    def as_definition(self):
        if typename(self._defn) == 'function':
            return repr(self)
        if type(self._defn) is rpn.util.Sequence:
            return ": {} {}{} ;".format(self.name,
                                        'doc:"{}"\n'.format(self.doc()) if self.doc() is not None and len(self.doc()) > 0 else "",
                                        str(self._defn))
        raise FatalErr("{}: Unhandled type {}".format(whoami(), type(self._defn)))

    def __str__(self):
        return self.name

    def patch_recurse(self, new_word):
        pass

    def __repr__(self):
        return "Word[{}]".format(self.name)



def frexp10(x):
    """
    Return mantissa and exponent (base 10), similar to base-2 frexp()
    :param x: floating point number
    :return: tuple (mantissa, exponent)
    """
    exp = math.floor(math.log10(x))
    return x/10**exp, exp


def prompt_string():
    if not rpn.globl.go_interactive:
        return ""

    s = "[{}{}".format(rpn.globl.angle_mode_letter(), rpn.globl.param_stack.size())
    if not rpn.globl.string_stack.empty():
        s += ",{}".format(rpn.globl.string_stack.size())
    s += "] "
    if not rpn.globl.parse_stack.empty():
        qq = " ".join([p[1] for p in rpn.globl.parse_stack.items_bottom_to_top()])
        s += qq + " ... "
    return s
