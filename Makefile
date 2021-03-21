SRCS=rpn/__main__.py rpn/app.py rpn/debug.py rpn/exception.py rpn/exe.py rpn/flag.py rpn/globl.py rpn/parser.py rpn/tvm.py rpn/type.py rpn/util.py rpn/word.py

bad_whitespace=C0326
fixme=W0511
invalid_name=C0103
line_too_long=C0301
missing_class_docstring=C0115
missing_function_docstring=C0116
too_few_public_methods=R0903
too_many_boolean_expressions=R0916
too_many_branches=R0912
too_many_instance_attributes=R0902
too_many_locals=R0914
too_many_return_statements=R0911
too_many_statements=R0915
unidiomatic_typecheck=C0123
unused_import=W0614

#PYLINT_IGNORE=$(line_too_long),$(bad_whitespace),$(unused_import)
#PYLINT_IGNORE=$(line_too_long),$(bad_whitespace),$(missing_function_docstring),$(invalid_name),$(missing_class_docstring),$(unidiomatic_typecheck),$(fixme),$(unused_import)
PYLINT_IGNORE=$(line_too_long),$(bad_whitespace),$(missing_function_docstring),$(invalid_name),$(missing_class_docstring),$(unidiomatic_typecheck),$(too_many_boolean_expressions),$(too_many_statements),$(too_many_branches),$(too_many_return_statements),$(too_many_locals),$(too_few_public_methods),$(too_many_instance_attributes),$(fixme),$(unused_import)

all:
	@echo "make: Please specify a target: clean, lint, lintall, tags"

clean:
	@-find . -type d -name __pycache__ -exec rm -rf {} \;  >/dev/null 2>&1
	@-find . -type f -name lextab.py   -exec rm -f  {} \;  >/dev/null 2>&1
	@-find . -type f -name parsetab.py -exec rm -f  {} \;  >/dev/null 2>&1
	@-find . -type f -name parser.out  -exec rm -f  {} \;  >/dev/null 2>&1

lint:
	pylint -d $(PYLINT_IGNORE) rpn

lintall:
	pylint rpn

tags:
	etags $(SRCS)
