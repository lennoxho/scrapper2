import sys
import lib2.colorama.initialise; lib2.colorama.initialise.init()

if sys.version_info[0] < 3:
    # Use Python 2 compliant printing style
    sys.stderr.write("scrapper2 : The scrapper2 module requires Python 3 or higher\n")
    sys.exit(1)


from lib2.scrapper2_core import *

if __name__ == "__main__":
    error_out("This Python module acts as the common interface for scrapper2. " + \
              "Please import this module into your script to use its functionality.")
    sys.exit(1)