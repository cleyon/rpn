'''
#############################################################################
#
#       P L Y   L E X  &  P A R S E
#
#############################################################################
'''

import re
import sys

from   rpn.debug import dbg, whoami
from   rpn.exception import *   # pylint: disable=wildcard-import
import rpn.exe
import rpn.globl
import rpn.util


#############################################################################
#
#       L E X E R
#
#       - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#
#       When building the master regular expression, rules are added in
#       the following order:
#
#        1. All tokens defined by functions are added in the same order
#           as they appear in the lexer file.
#        2. Tokens defined by strings are added next by sorting them in
#           order of decreasing regular expression length (longer
#           expressions are added first).
#
#############################################################################
try:
    import ply.lex  as lex
except ModuleNotFoundError:
    print("RPN requires the 'ply' library; please consult the README") # OK
    sys.exit(1)


reserved_words = {
    '+loop'     : 'PLUS_LOOP',
    'again'     : 'AGAIN',
    'ascii'     : 'ASCII',
    'begin'     : 'BEGIN',
    'case'      : 'CASE',
    'catch'     : 'CATCH',
    'constant'  : 'CONSTANT',
    'do'        : 'DO',
    'else'      : 'ELSE',
    'endcase'   : 'ENDCASE',
    'endof'     : 'ENDOF',
    'forget'    : 'FORGET',
    'help'      : 'HELP',
    'hide'      : 'HIDE',
    'if'        : 'IF',
    'loop'      : 'LOOP',
    'of'        : 'OF',
    'otherwise' : 'OTHERWISE',
    'recurse'   : 'RECURSE',
    'repeat'    : 'REPEAT',
    'show'      : 'SHOW',
    'then'      : 'THEN',
    'undef'     : 'UNDEF',
    'until'     : 'UNTIL',
    'variable'  : 'VARIABLE',
    'while'     : 'WHILE',
}

tokens = [
    'ABORT_QUOTE',
    'AT_SIGN',
    'CLOSE_BRACKET',
    'CLOSE_PAREN',
    'COLON',
    'COMMA',
    'DOC_STR',
    'DOT_QUOTE',
    'EXCLAM',
    'FLOAT',
    'IDENTIFIER',
    'INTEGER',
    'OPEN_BRACKET',
    'OPEN_PAREN',
    'RATIONAL',
    'SEMICOLON',
    'STRING',
    'SYMBOL',
    'VBAR',
    'WS',
] + list(reserved_words.values())

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

def t_STRING(t):
    r'"([^"]|\n)*"'
    #r'"([^"\\]*(\\.[^"\\]*)*)"' # Nice, but doesn't work with multi-line strings
    #r'"(?:[^"\\]++|\\.)*+"'     # This causes a stack overflow
    t.type = 'STRING'
    return t

def t_SYMBOL(t):
    r"'([^']|\n)*'"
    t.type = 'SYMBOL'
    return t

def t_RATIONAL(t):
    r'\d+::\d+(_[^ \t\n]+)?'
    t.type = 'RATIONAL'
    return t

# def t_CMPLX(t):
#     r'\([-+]?(\d+(\.\d*[eE][-+]?\d+|[eE][-+]?\d+|\.\d*))|(\d*(\.\d+[eE][-+]?\d+|[eE][-+]?\d+|\.\d+)),[-+]?(\d+(\.\d*[eE][-+]?\d+|[eE][-+]?\d+|\.\d*))|(\d*(\.\d+[eE][-+]?\d+|[eE][-+]?\d+|\.\d+))\)'
#     t.type = 'CMPLX'
#     return t

def t_FLOAT(t):
    r'[-+]?((\d+(\.\d*[eE][-+]?\d+|[eE][-+]?\d+|\.\d*))|(\d*(\.\d+[eE][-+]?\d+|[eE][-+]?\d+|\.\d+)))(_[^ \t\n]+)?'
    t.type = 'FLOAT'
    return t

ASCII_RE = re.compile(r'ascii[ 	]+([^ 	]+)')
def t_ASCII(t):
    r'ascii[ 	]+([^ 	]+)'
    t.type = 'INTEGER'
    match = ASCII_RE.match(t.value)
    if match is None:
        t.value = '-1'
        return t
    m = match.group(1)
    t.value = str(ord(m[0])) if len(m) > 0 else '-1'
    return t

# Beware bad input - e.g., "0b177" is parsed as two token, "0b1" and "77".
# Note a little Python magic: int(xxx, 0) will guess base and parse "0x", etc.
# On the whole, the benefits outweigh the drawbacks.
def t_INTEGER(t):
    r'[-+]?((0[xX][0-9a-fA-F]+)|(0[oO][0-7]+)|(0[bB][0-1]+)|(\d+))(_[^ \t\n]+)?'
    t.type = 'INTEGER'
    return t

def t_ABORT_QUOTE(t):
    r'abort"([^"]|\n)*"'
    return t

# def t_ASTERISK(t):
#     r'\*'
#     t.type = 'ASTERISK'
#     return t

def t_AT_SIGN(t):
    r'@'
    t.type = 'AT_SIGN'
    return t

def t_BACKSLASH(t):                     # pylint: disable=unused-argument
    r'\\.*'

    # \ consumes the remainder of the line.
    # Instead of setting type and returning t, doing nothing will ignore
    # the token.  We want this behaviour, because otherwise the
    # BACKSLASH token is returned and the parser attempts to execute it.
    # This is problematic in places where an executable is not expected.
    # For example, consider:
    #     \ This comment is valid.
    #     case
    #        1 of ."Found one" endof
    #        \ This comment is NOT valid because a case-clause is expected.
    #        otherwise ."Found other value"
    #     endcase

def t_CLOSE_PAREN(t):
    r'\)'
    t.type = 'CLOSE_PAREN'
    return t

def t_CLOSE_BRACKET(t):
    r'\]'
    t.type = 'CLOSE_BRACKET'
    return t

def t_COMMA(t):
    r','
    t.type = 'COMMA'
    return t

def t_DOC_STR(t):
    r'doc:"([^"]|\n)*"'
    return t

def t_DOT_QUOTE(t):
    r'\."([^"]|\n)*"'
    return t

def t_EXCLAM(t):
    r'!'
    t.type = 'EXCLAM'
    return t

def t_OPEN_BRACKET(t):
    r'\['
    t.type = 'OPEN_BRACKET'
    return t

def t_OPEN_PAREN(t):
    r'\('
    t.type = 'OPEN_PAREN'
    return t

# def t_SLASH(t):
#     r'/'
#     t.type = 'SLASH'
#     return t

# def t_UNDERSCORE(t):
#     r'_'
#     t.type = 'UNDERSCORE'
#     return t

def t_VBAR(t):
    r'\|'
    t.type = 'VBAR'
    return t

def t_WS(t):                            # pylint: disable=unused-argument
    r'[ \t\n]+'

def t_IDENTIFIER(t):
    r'[-#$%&\*+,./:;<=>?A-Z^_a-z~][-!"#$%&\'*+,./0-9:;<=>?@A-Z^_a-z~]*'

    single_chars = {
        ':': 'COLON',
        ';': 'SEMICOLON',
    }
    if len(t.value) == 1:
        if t.value in single_chars:
            t.type = single_chars[t.value]
    else:
        #print("ID:'{}'".format(t.value))
        t.type = reserved_words.get(t.value, 'IDENTIFIER')
    return t

def t_error(t):
    #print("Illegal character '%s'" % t.value[0])
    t.value = t.value[0]
    t.type = 'ERROR'
    t.lexer.skip(1)
    return t


def initialize_lexer():
    rpn.globl.lexer = lex.lex(optimize=True)




#############################################################################
#
#       P A R S E R
#
#       - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#
#       These functions appear in alphabetical order, except p_XXX_push()
#       is listed before p_XXX_pop()
#
#############################################################################
try:
    import ply.yacc as yacc
except ModuleNotFoundError:
    print("RPN requires the 'ply' library; please consult the README") # OK
    sys.exit(1)


def p_abort_quote(p):
    '''abort_quote : ABORT_QUOTE'''
    p[0] = rpn.exe.AbortQuote(p[1])

def p_ascii(p):
    '''ascii : ASCII'''
    p[0] = rpn.exe.Ascii()

def p_begin_again(p):
    '''begin_again : BEGIN sequence AGAIN'''
    p[0] = rpn.exe.BeginAgain(p[2])

def p_begin_until(p):
    '''begin_until : BEGIN sequence UNTIL'''
    p[0] = rpn.exe.BeginUntil(p[2])

def p_begin_while(p):
    '''begin_while : BEGIN sequence WHILE sequence REPEAT'''
    p[0] = rpn.exe.BeginWhile(p[2], p[4])

def p_case(p):
    '''case : CASE case_scope_push case_clause_list otherwise_list ENDCASE case_scope_pop'''
    p[0] = rpn.exe.Case(p[3], p[4])

def p_case_clause(p):
    '''case_clause : integer OF sequence ENDOF'''
    p[0] = rpn.exe.CaseClause(p[1], p[3])

def p_case_clause_list(p):
    '''case_clause_list : case_clause
                        | case_clause case_clause_list'''
    if len(p) == 2:
        p[0] = rpn.util.List(p[1])
    else:
        p[0] = rpn.util.List(p[1], p[2])

def p_case_scope_push(p):               # pylint: disable=unused-argument
    '''case_scope_push : empty'''
    scope = rpn.util.Scope("case")
    scope.add_vname(rpn.util.VName("caseval"))
    rpn.globl.push_scope(scope, "Parsing Case")

def p_case_scope_pop(p):                # pylint: disable=unused-argument
    '''case_scope_pop : empty'''
    rpn.globl.pop_scope("Parse Case complete")

def p_catch(p):
    '''catch : CATCH IDENTIFIER'''
    me = whoami()
    name = p[2]
    (word, scope) = rpn.globl.lookup_word(name)
    if word is None:
        rpn.globl.lnwriteln("catch: Word '{}' not found".format(name))
        raise SyntaxError
    dbg("catch", 1, "{}: Creating Catch obj for {}".format(me, word))
    p[0] = rpn.exe.Catch(word, scope)

def p_cmd(p):                           # pylint: disable=unused-argument
    '''cmd :  executable  execute'''

def p_colon(p):
    '''colon : COLON IDENTIFIER docstring sequence SEMICOLON colon_define_word'''
    # This returns None because `colon_define_word' does all the work
    p[0] = None

def p_colon_define_word(p):
    '''colon_define_word : empty'''
    me = whoami()
    identifier = p[-4]
    doc_str    = p[-3]
    sequence   = p[-2]
    dbg("p_colon_define_word", 2, "{}: identifier={}  doc_str={}  sequence={}".format(me, identifier, repr(doc_str), repr(sequence)))
    kwargs = dict()
    if doc_str is not None:
        if len(doc_str) < 6 or doc_str[0:5] != 'doc:"' or doc_str[-1] != '"':
            raise FatalErr("{}: Malformed doc_str: '{}'".format(me, doc_str))
        doc_str = doc_str[5:-1]
        kwargs['doc'] = doc_str

    # Check if word is protected
    (word, _) = rpn.globl.lookup_word(identifier)
    if word is not None and word.protected:
        throw(X_PROTECTED, ": ", "Cannot redefine '{}'".format(identifier))

    # p_sequence() has already popped the scope for this word, so
    # creating it now in rpn.globl.scope_stack.top() will be correct.
    new_word = rpn.util.Word(identifier, "colon", sequence, **kwargs)
    dbg("p_colon_define_word", 1, "{}: Defining word {}={} in scope {}".format(me, identifier, repr(new_word), repr(rpn.globl.scope_stack.top())))
    sequence.patch_recurse(new_word)
    rpn.globl.scope_stack.top().define_word(identifier, new_word)
    p[0] = new_word

def p_colon_error(p):
    '''colon : COLON IDENTIFIER docstring error SEMICOLON '''
    rpn.globl.lnwriteln("{}: Syntax error in definition".format(p[2]))
    raise SyntaxError

def p_complex(p):
    '''complex : OPEN_PAREN real COMMA real CLOSE_PAREN '''
    p[0] = rpn.type.Complex(p[2].value, p[4].value)

def p_constant(p):
    '''constant : CONSTANT IDENTIFIER'''
    me = whoami()
    ident = p[2]
    #print("p_constant {}".format(ident))
    if not rpn.util.Variable.name_valid_p(ident):
        rpn.globl.lnwriteln("CONSTANT: '{}' is not valid".format(ident))
        raise SyntaxError
    (var, scope) = rpn.globl.lookup_variable(ident)
    if var is not None and var.noshadow():
        rpn.globl.lnwriteln("CONSTANT: '{}' cannot be shadowed".format(ident))
        raise SyntaxError
    if scope is not None and scope == rpn.globl.scope_stack.top():
        rpn.globl.lnwriteln("CONSTANT: '{}' redefined".format(ident))
        raise SyntaxError
    var = rpn.util.Variable(ident, None, constant=True)
    #print("{}: Creating variable {} at address {} in {}".format(me, ident, hex(id(var)), repr(scope)))
    rpn.globl.scope_stack.top().add_vname(rpn.util.VName(ident))
    rpn.globl.scope_stack.top().define_variable(ident, var)
    p[0] = rpn.exe.Constant(var)

def p_do_loop(p):
    '''do_loop : DO sequence LOOP'''
    p[0] = rpn.exe.DoLoop(p[2])

def p_do_plusloop(p):
    '''do_plusloop : DO sequence PLUS_LOOP'''
    p[0] = rpn.exe.DoPlusLoop(p[2])

def p_docstring(p):
    '''docstring : empty
                 | DOC_STR'''
    p[0] = p[1]

def p_dot_quote(p):
    '''dot_quote : DOT_QUOTE'''
    p[0] = rpn.exe.DotQuote(p[1])

def p_empty(p):                         # pylint: disable=unused-argument
    '''empty :'''

def p_error(p):
    raise ParseErr(p if p is not None else 'EOF')

def p_evaluate(p):                      # pylint: disable=unused-argument
    '''evaluate : cmd
                | cmd evaluate'''

def p_executable(p):
    '''executable : abort_quote
                  | ascii
                  | begin_again
                  | begin_until
                  | begin_while
                  | case
                  | catch
                  | colon
                  | constant
                  | do_loop
                  | do_plusloop
                  | dot_quote
                  | fetch_var
                  | forget
                  | help
                  | hide
                  | if_then
                  | if_else_then
                  | matrix
                  | number
                  | recurse
                  | show
                  | store_var
                  | string
                  | symbol
                  | undef
                  | variable
                  | vector
                  | word'''
    p[0] = p[1]
    dbg("p_executable", 1, "p_executable: {}".format(p[0]))

def p_executable_list(p):
    '''executable_list : empty
                       | executable executable_list'''
    me = whoami()
    if len(p) == 2:
        p[0] = rpn.util.List()
    elif len(p) == 3:
        if p[1] is None:
            p[0] = p[2]
        else:
            p[0] = rpn.util.List(p[1], p[2])
    dbg(me, 1, "{}: Returning {}".format(me, p[0]))

def p_execute(p):
    '''execute : empty'''
    executable = p[-1]
    if executable is None:
        return
    dbg("p_execute", 1, "p_execute: {}".format(repr(executable)))
    rpn.globl.execute(executable)

def p_fetch_var(p):
    '''fetch_var : AT_SIGN IDENTIFIER'''
    me = whoami()
    ident = p[2]
    if ident[0] in ['+', '-', '*', '/', '?', '$', '.']:
        modifier = ident[0]
        ident = ident[1:]
    else:
        modifier = None
    if not rpn.util.Variable.name_valid_p(ident):
        rpn.globl.writeln("@: Variable name '{}' not valid".format(ident))
        raise SyntaxError
    dbg(me, 1, "{}: Looking up {}".format(me, ident))
    (vname, _) = rpn.globl.lookup_vname(ident)
    if vname is None:
        rpn.globl.writeln("@: Variable '{}' not found".format(ident))
        raise SyntaxError
    p[0] = rpn.exe.FetchVar(ident, modifier)

def p_float(p):
    '''float : FLOAT'''
    p[0] = rpn.type.Float.from_string(p[1])

def p_forget(p):
    '''forget : FORGET IDENTIFIER'''
    name = p[2]
    (word, scope) = rpn.globl.lookup_word(name)
    if word is None:
        rpn.globl.lnwriteln("forget: Word '{}' not found".format(name))
        raise SyntaxError
    p[0] = rpn.exe.Forget(word, scope)

def p_help(p):
    '''help : HELP AGAIN
            | HELP ASCII
            | HELP BEGIN
            | HELP CASE
            | HELP CATCH
            | HELP COLON
            | HELP CONSTANT
            | HELP DO
            | HELP DOT_QUOTE
            | HELP ELSE
            | HELP ENDCASE
            | HELP ENDOF
            | HELP FORGET
            | HELP HELP
            | HELP HIDE
            | HELP IDENTIFIER
            | HELP IF
            | HELP LOOP
            | HELP OF
            | HELP OTHERWISE
            | HELP PLUS_LOOP
            | HELP RECURSE
            | HELP REPEAT
            | HELP SEMICOLON
            | HELP SHOW
            | HELP THEN
            | HELP UNDEF
            | HELP UNTIL
            | HELP VARIABLE
            | HELP WHILE'''
    name = p[2]
    (word, _) = rpn.globl.lookup_word(name)
    if word is None:
        rpn.globl.lnwriteln("help: Word '{}' not found".format(name))
        raise SyntaxError
    p[0] = rpn.exe.Help(name, word.doc() if word.doc() is not None \
                                    and len(word.doc()) > 0 \
                    else "No help available for '{}'".format(name))

def p_hide(p):
    '''hide : HIDE IDENTIFIER'''
    name = p[2]
    (word, _) = rpn.globl.lookup_word(name)
    if word is None:
        rpn.globl.lnwriteln("hide: Word '{}' not found".format(name))
        raise SyntaxError
    p[0] = rpn.exe.Hide(word)

def p_identifier_list(p):
    '''identifier_list : empty
                       | IDENTIFIER identifier_list'''
    if len(p) == 2:
        p[0] = rpn.util.List()
    elif len(p) == 3:
        (_, ident) = rpn.globl.separate_decorations(p[1])
        if not rpn.util.Variable.name_valid_p(ident):
            rpn.globl.lnwriteln("|{}|: Variable name is not valid".format(ident))
            raise SyntaxError
        (var, _) = rpn.globl.lookup_variable(ident)
        if var is not None and var.noshadow():
            rpn.globl.lnwriteln("|{}|: Variable cannot be shadowed".format(ident))
            raise SyntaxError
        p[0] = rpn.util.List(p[1], p[2])

def p_if_else_then(p):
    '''if_else_then : IF sequence ELSE sequence THEN'''
    p[0] = rpn.exe.IfElse(p[2], p[4])

def p_if_then(p):
    '''if_then : IF sequence THEN'''
    p[0] = rpn.exe.IfElse(p[2], None)

def p_integer(p):
    '''integer : INTEGER'''
    p[0] = rpn.type.Integer.from_string(p[1])

def p_locals(p):
    '''locals : empty
              | VBAR identifier_list VBAR'''
    me = whoami()
    scope_name = None
    idx = -1
    while scope_name is None:
        if p[idx] in ['begin', 'do', 'else', 'if', 'otherwise']:
            scope_name = p[idx]
        elif p[idx] == 'of':
            v = p[idx - 1]
            if type(v) is rpn.type.Integer:
                v = str(v.value)
            scope_name = "of_" + v
        elif p[idx] == ':':
            scope_name = p[idx + 1]
        else:
            dbg(me, 3, "p_locals: Not sure about {}".format(p[idx]))
            # scope_name = "locals"
            idx -= 1
    scope = rpn.util.Scope(scope_name)
    dbg(me, 1, "{}: Creating new scope {}".format(me, repr(scope)))

    if len(p) == 4:
        for i in p[2].items():
            vname = None
            # Already tested for name_valid_p and noshadow in p_identifier_list()
            (decoration, ident) = rpn.globl.separate_decorations(i)
            vname = rpn.util.VName(ident)
            if decoration == 'in':
                dbg(me, 3, "{} is an IN variable".format(ident))
                vname.in_p = True
            elif decoration == 'out':
                dbg(me, 3, "{} is an OUT variable".format(ident))
                vname.out_p = True
            elif decoration == 'inout':
                dbg(me, 3, "{} is an INOUT variable".format(ident))
                vname.in_p = True
                vname.out_p = True

            dbg(me, 2, "{}: Adding vname '{}'".format(me, vname))
            scope.add_vname(vname)
    rpn.globl.push_scope(scope, "New sequence (locals={})".format(scope.vnames()))
    p[0] = scope

def p_matrix(p):
    '''matrix : OPEN_BRACKET vector_list CLOSE_BRACKET'''
    if not rpn.globl.have_module('numpy'):
        raise ParseErr("Matrices require 'numpy' library")
    p[0] = rpn.type.Matrix.from_rpn_List(p[2])

def p_number(p):
    '''number : real
              | rational
              | complex'''
    p[0] = p[1]

def p_number_list(p):
    '''number_list : empty
                   | number number_list'''
    if len(p) == 2:
        p[0] = rpn.util.List()
    elif len(p) == 3:
        p[0] = rpn.util.List(p[1], p[2])

def p_otherwise_list(p):
    '''otherwise_list : empty
                      | OTHERWISE sequence'''
    if len(p) == 2:
        p[0] = rpn.util.List()
    else:
        p[0] = rpn.util.List(p[2])

def p_rational(p):
    '''rational : RATIONAL'''
    p[0] = rpn.type.Rational.from_string(p[1])

def p_real(p):
    '''real : integer
            | float'''
    p[0] = p[1]

def p_recurse(p):
    '''recurse : RECURSE'''
    p[0] = rpn.exe.Recurse()

def p_sequence(p):
    '''sequence : locals executable_list'''
    # `locals' is an rpn.util.Scope; `executable_list' is an rpn.util.List
    #scope = pop_scope("p_sequence() is finishing")
    rpn.globl.pop_scope("p_sequence() is finishing")
    p[0] = rpn.util.Sequence(p[1], p[2])

def p_show(p):
    '''show : SHOW IDENTIFIER'''
    name = p[2]
    (word, _) = rpn.globl.lookup_word(name)
    if word is None:
        rpn.globl.lnwriteln("show: Word '{}' not found".format(name))
        raise SyntaxError
    p[0] = rpn.exe.Show(word)

def p_store_var(p):
    '''store_var : EXCLAM IDENTIFIER'''
    me = whoami()
    ident = p[2]
    if ident[0] in ['+', '-', '*', '/', '?', '$']:
        modifier = ident[0]
        ident = ident[1:]
    else:
        modifier = None
    if not rpn.util.Variable.name_valid_p(ident):
        rpn.globl.lnwriteln("!: Variable name '{}' not valid".format(ident))
        raise SyntaxError
    dbg(me, 1, "{}: Looking up {}".format(me, ident))
    (vname, _) = rpn.globl.lookup_vname(ident)
    if vname is None:
        if modifier != '?':
            rpn.globl.lnwriteln("!: Variable '{}' not found".format(ident))
            raise SyntaxError
        # Create variable on the fly
        var = rpn.util.Variable(ident)
        dbg(me, 1, "{}: Creating variable {} at address {} in {}".format(me, ident, hex(id(var)), repr(rpn.globl.scope_stack.top())))
        rpn.globl.scope_stack.top().add_vname(rpn.util.VName(ident))
        rpn.globl.scope_stack.top().define_variable(ident, var)
    p[0] = rpn.exe.StoreVar(ident, modifier)

def p_string(p):
    '''string : STRING'''
    me = whoami()
    s = p[1]
    if len(s) < 2 or s[0] != '"' or s[-1] != '"':
        raise FatalErr("{}: Malformed string: '{}'".format(me, s))
    p[0] = rpn.type.String(s[1:-1])

def p_symbol(p):
    '''symbol : SYMBOL'''
    me = whoami()
    s = p[1]
    if len(s) < 2 or s[0] != "'" or s[-1] != "'":
        raise FatalErr("{}: Malformed symbol: '{}'".format(me, s))
    name = s[1:-1]
    (word, _) = rpn.globl.lookup_word(name)
    if word is None:
        rpn.globl.lnwriteln("{}: Word '{}' not found".format(me, name))
        raise SyntaxError
    p[0] = rpn.type.Symbol(name, word)

def p_undef(p):
    '''undef : UNDEF IDENTIFIER'''
    ident = p[2]
    if not rpn.util.Variable.name_valid_p(ident):
        rpn.globl.lnwriteln("UNDEF: '{}' is not valid".format(ident))
        raise SyntaxError
    (var, scope) = rpn.globl.lookup_variable(ident)
    if var is None:
        rpn.globl.lnwriteln("UNDEF: Variable '{}' not found".format(ident))
        raise SyntaxError
    if var.protected:
        rpn.globl.lnwriteln("UNDEF: Variable '{}' protected".format(ident))
        raise SyntaxError
    if scope != rpn.globl.scope_stack.top():
        rpn.globl.lnwriteln("UNDEF: Variable '{}' out of scope".format(ident))
        raise SyntaxError
    cur_obj = var.obj
    new_obj = None
    for pre_hook_func in var.pre_hooks():
        try:
            pre_hook_func(ident, cur_obj, new_obj)
        except RuntimeErr as err_pre_hook_undef:
            rpn.globl.lnwriteln(str(err_pre_hook_undef))
            return
    old_obj = cur_obj
    rpn.globl.scope_stack.top().delete_variable(ident)
    cur_obj = None
    for post_hook_func in var.post_hooks():
        post_hook_func(ident, old_obj, cur_obj)

def p_variable(p):
    '''variable :  VARIABLE IDENTIFIER'''
    me = whoami()
    ident = p[2]
    if not rpn.util.Variable.name_valid_p(ident):
        rpn.globl.lnwriteln("VARIABLE: '{}' is not valid".format(ident))
        raise SyntaxError
    (var, scope) = rpn.globl.lookup_variable(ident)
    if var is not None and var.noshadow():
        rpn.globl.lnwriteln("VARIABLE: '{}' cannot be shadowed".format(ident))
        raise SyntaxError
    if scope is not None and scope == rpn.globl.scope_stack.top():
        rpn.globl.lnwriteln("VARIABLE: '{}' redefined".format(ident))
        raise SyntaxError
    var = rpn.util.Variable(ident)
    dbg(me, 1, "{}: Creating variable {} at address {} in {}".format(me, ident, hex(id(var)), repr(rpn.globl.scope_stack.top())))
    rpn.globl.scope_stack.top().add_vname(rpn.util.VName(ident))
    rpn.globl.scope_stack.top().define_variable(ident, var)

def p_vector(p):
    '''vector : OPEN_BRACKET number_list CLOSE_BRACKET'''
    if not rpn.globl.have_module('numpy'):
        raise ParseErr("Vectors require 'numpy' library")
    p[0] = rpn.type.Vector.from_rpn_List(p[2])

def p_vector_list(p):
    '''vector_list : vector
                   | vector vector_list'''
    me = whoami()
    #rpn.globl.lnwriteln("{}: len={}".format(me, len(p)))
    if len(p) == 2:
        p[0] = rpn.util.List(p[1])
    elif len(p) == 3:
        p[0] = rpn.util.List(p[1], p[2])

def p_word(p):
    '''word : IDENTIFIER'''
    # A "word" is not just an identifier: a word is something that is
    # findable somewhere in the scope stack.  It is a syntax error if
    # the identifier is not found.
    name = p[1]
    (word, _) = rpn.globl.lookup_word(name)
    if word is None:
        rpn.globl.lnwriteln("Word '{}' not found".format(name))
        raise SyntaxError
    p[0] = word


def initialize_parser():
    #rpn.globl.rpn_parser = yacc.yacc(start='evaluate') # , errorlog=yacc.NullLogger())
    rpn.globl.rpn_parser = yacc.yacc(start='evaluate', errorlog=yacc.NullLogger())
