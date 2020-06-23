#!/usr/bin/env python3

import ply.lex as lex

# literals = ['!', ':', '|', '~', ';', ',', '(', ')', '@', '[', ']']
literals = [ '|' ]

reserved_words = {
    '+loop'     : 'PLUS_LOOP',
    '."'        : 'DOT_QUOTE',
    'abort"'    : 'ABORT_QUOTE',
    'again'     : 'AGAIN',
    'begin'     : 'BEGIN',
    'case'      : 'CASE',
    'do'        : 'DO',
    'doc:"'     : 'DOC_STR',
    'else'      : 'ELSE',
    'endcase'   : 'ENDCASE',
    'endof'     : 'ENDOF',
    'help'      : 'HELP',
    'if'        : 'IF',
    'loop'      : 'LOOP',
    'of'        : 'OF',
    'otherwise' : 'OTHERWISE',
    'repeat'    : 'REPEAT',
    'then'      : 'THEN',
    'until'     : 'UNTIL',
    'while'     : 'WHILE',
}

tokens = [
    'AT_SIGN',
    'CLOSE_BRACKET',
    'CLOSE_PAREN',
    'COLON',
    'COMMA',
    'EXCLAM',
    'FLOAT',
    'IDENTIFIER',
    'INTEGER',
    'OPEN_BRACKET',
    'OPEN_PAREN',
    'SEMICOLON',
    'STRING',
    'TILDE',
    'VBAR',
] + list(reserved_words.values())

t_ignore = ' \t'

t_ignore_COMMENT    = r'\\.*'
t_STRING            = r'\"([^\\\n]|(\\.))*?\"'


def t_ABORT_QUOTE(t):
    r'abort\"([^\\\n]|(\\.))*?\"'
    return t

def t_AT_SIGN(t):
    r'@'
    t.type = 'AT_SIGN'
    return t

def t_CLOSE_BRACKET(t):
    r'\]'
    t.type = 'CLOSE_BRACKET'
    return t

def t_CLOSE_PAREN(t):
    r'\)'
    t.type = 'CLOSE_PAREN'
    return t

def t_COLON(t):
    r':'
    t.type = 'COLON'
    return t

def t_COMMA(t):
    r','
    t.type = 'COMMA'
    return t

def t_D_TO_R(t):
    r'd->r'
    t.type = 'IDENTIFIER'
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

def t_R_FETCH(t):
    r'r@'
    t.type = 'IDENTIFIER'
    return t

def t_R_TO_D(t):
    r'r->d'
    t.type = 'IDENTIFIER'
    return t

def t_SEMICOLON(t):
    r';'
    t.type = 'SEMICOLON'
    return t

def t_TILDE(t):
    r'~'
    t.type = 'TILDE'
    return t

def t_VBAR(t):
    r'\|'
    t.type = 'VBAR'
    return t

def t_MINUS_ROT(t):
    r'-rot'
    t.type = 'IDENTIFIER'
    return t

def t_MINUS(t):
    r'-'
    t.type = 'IDENTIFIER'
    return t

def t_ZERO_EQUALS(t):
    r'0='
    t.type = 'IDENTIFIER'
    return t

def t_WORDS_BANG(t):
    r'words!'
    t.type = 'IDENTIFIER'
    return t

def t_DOC_STR(t):
    r'doc:\"([^\\\n]|(\\.))*?\"'
    return t

def t_DOT_QUOTE(t):
    r'.\"([^\\\n]|(\\.))*?\"'
    return t

def t_FLOAT(t):
    # t_CPP_FLOAT = r'((\d+)(\.\d+)(e(\+|-)?(\d+))? | (\d+)e(\+|-)?(\d+))([lL]|[fF])?'
    r'((\d+)(\.\d+)(e(\+|-)?(\d+))?|(\d+)e(\+|-)?(\d+))'
    return t

def t_INTEGER(t):
    # r'(\d)+'
    r'(((((0x)|(0X))[0-9a-fA-F]+)|(\d+)))'
    t.value = int(t.value)
    return t

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

def t_IDENTIFIER(t):
    r'[$%*+./0-9<=>A-Z^a-z][!$%*+./0-9<=>?A-Z^a-z]*'
    t.type = reserved_words.get(t.value, 'IDENTIFIER')
    return t

def t_error(t):
    global parse_error
    print("Illegal character '%s'" % t.value[0])
    parse_error = True
    t.lexer.skip(1)


lexer = lex.lex()
