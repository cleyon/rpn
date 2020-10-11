'''
#############################################################################
#
#       M A I N
#
#############################################################################
'''

import sys
from rpn import app
from rpn import exception


def main(argv):
    try:
        if app.initialize(argv):
            app.main_loop()
    except exception.EndProgram:
        pass
    except exception.FatalErr as e:
        if len(str(e)) > 0:
            print("Fatal error: {}".format(e)) # OK
        sys.exit(1)
    except exception.RuntimeErr as err_main:
        print("Uncaught exception: {} ({})".format(err_main.code, str(err_main))) # OK
        #sys.exit(1)

    app.end_program()


if __name__ == '__main__':
    main(sys.argv[1:])
