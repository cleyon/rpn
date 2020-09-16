invalid_name=C0103
missing_class_docstring=C0115
missing_function_docstring=C0116
unidiomatic_typecheck=C0123
line_too_long=C0301
bad_whitespace=C0326
too_many_instance_attributes=R0902
too_few_public_methods=R0903
too_many_return_statements=R0911
too_many_branches=R0912
too_many_locals=R0914
too_many_statements=R0915
too_many_boolean_expressions=R0916
global_variable_undefined=W0601
global_statement=W0603

#PYLINT_IGNORE=$(line_too_long),$(bad_whitespace)
#PYLINT_IGNORE=$(line_too_long),$(bad_whitespace),$(global_statement),$(missing_function_docstring),$(invalid_name),$(global_variable_undefined),$(missing_class_docstring)
PYLINT_IGNORE=$(line_too_long),$(bad_whitespace),$(global_statement),$(missing_function_docstring),$(invalid_name),$(global_variable_undefined),$(missing_class_docstring),$(unidiomatic_typecheck),$(too_many_boolean_expressions),$(too_many_statements),$(too_many_branches),$(too_many_return_statements),$(too_many_locals),$(too_few_public_methods),$(too_many_instance_attributes)

all:
	@echo "make: Please specify a target: clean, lint"

clean:
	rm -f lextab.py parsetab.py
	rm -rf __pycache__

lint:
	pylint -d $(PYLINT_IGNORE) rpn

lintall:
	pylint rpn
