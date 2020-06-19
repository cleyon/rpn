#!/usr/bin/env python3

import ply.lex as lex

literals = "|"

reserved_words = {
    '+loop'  : 'PLUS_LOOP',
    '."'     : 'DOT_QUOTE',
    'again'  : 'AGAIN',
    'begin'  : 'BEGIN',
    'do'     : 'DO',
    'else'   : 'ELSE',
    'help'   : 'HELP',
    'if'     : 'IF',
    'loop'   : 'LOOP',
    'repeat' : 'REPEAT',
    'then'   : 'THEN',
    'until'  : 'UNTIL',
    'while'  : 'WHILE',
}

tokens = [
    'AT_SIGN',
    'CLOSE_BRACKET',
    'CLOSE_PAREN',
    'COLON',
    'COMMA',
    'EXCLAMATION',
    'FLOAT',
    'IDENTIFIER',
    'INTEGER',
    'OPEN_BRACKET',
    'OPEN_PAREN',
    'SEMICOLON',
    'STRING',
    'BAR',
] + list(reserved_words.values())

t_ignore = ' \t'

t_AT_SIGN           = r'@'
t_BAR               = r'\|'
t_CLOSE_BRACKET     = r']'
t_CLOSE_PAREN       = r'\)'
t_COLON             = r':'
t_COMMA             = r','
t_ignore_COMMENT    = r'\\.*'
t_EXCLAMATION       = r'!'
t_OPEN_PAREN        = r'\('
t_OPEN_BRACKET      = r'\['
t_SEMICOLON         = r';'
t_STRING            = r'\"([^\\\n]|(\\.))*?\"'


def t_MINUS_ROT(t):
    r'-rot'
    t.type = "IDENTIFIER"
    return t

def t_MINUS(t):
    r'-'
    t.type = "IDENTIFIER"
    return t

def t_ZERO_EQUALS(t):
    r'0='
    t.type = "IDENTIFIER"
    return t

def t_DOT_QUOTE(t):
    #t_DOT_QUOTE = r'.\"([^\\\n]|(\\.))*?\"'
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

def t_IDENTIFIER(t):
    r'[0-9a-zA-Z_+.$?=][a-zA-Z0-9_+.$!?=]*'
    t.type = reserved_words.get(t.value, 'IDENTIFIER')
    return t

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

def t_error(t):
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)


lexer = lex.lex()
