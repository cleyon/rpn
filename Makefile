#PYLINT_IGNORE=C0301,C0326
#PYLINT_IGNORE=C0301,C0326,W0603,C0116,C0103,W0601,C0115
PYLINT_IGNORE=C0301,C0326,W0603,C0116,C0103,W0601,C0115,C0123

all:
	@echo "make: Please specify a target: clean, lint"

clean:
	rm -f lextab.py parsetab.py
	rm -rf __pycache__

lint:
	pylint -d $(PYLINT_IGNORE) rpn

lintall:
	pylint rpn
