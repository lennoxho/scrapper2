#----------Import-Modules-START-----------------------------
import sys
import urllib.parse
#----------Import-Modules-END-------------------------------


#----------Global-Variables-START---------------------------
__standard_msg_types = ("info", "warning", "error", "fatal error", "success", "failure")
__standard_msg_colour = { "black" : '30',  "red"    : '31',
                          "green" : '32',  "yellow" : '33',
                          "blue"  : '34',  "purple" : '35',
                          "cyan"  : '36',  "white"  : '37'  }
#----------Global-Variables-END-----------------------------


#----------General-Utilities-START--------------------------
def valid_root_urls(root_jobs):
    """
    >>> valid_root_urls([])
    True
    >>> valid_root_urls([("http://rand", 0, 0), ("http://rand.com", 0, 0), ("http://rand.com/random", 0, 0)])
    True
    >>> valid_root_urls([("//rand.com", 0, 0)])
    False
    >>> valid_root_urls([("/rand.com", 0, 0)])
    False
    >>> valid_root_urls([("/rand.com", 0, 0)])
    False
    >>> valid_root_urls([("rand", 0, 0)])
    False
    >>> valid_root_urls([("http:rand", 0, 0)])
    False
    >>> valid_root_urls([("rand/random", 0, 0)])
    False
    """
    for url, _, _ in root_jobs:
        info = urllib.parse.urlsplit(url)
        if info.scheme == '' or info.netloc == '':
            return False
    return True
#----------General-Utilities-END----------------------------


#----------Message-Utilities-START--------------------------
def post_msg(msg, type="info", end='\n', file=sys.stdout, colour="white", en_colour=True):
    '''
    General message printing function.

    valid types: "info", "warning", "error", "fatal error", "success", "failure"
                 defaults to "generic"

    valid colours: "black", "red", "green", "yellow", "blue", "purple"
                   "cyan", "white"
    '''
    type = "generic" if type not in __standard_msg_types else type
    if en_colour:
        colour = "white" if colour not in __standard_msg_colour else colour

        colour_format = "\033[1;" + __standard_msg_colour[colour] + ";40m"
        reset_format = "\033[0m"
    else:
        colour_format = ""
        reset_format = ""

    begin_format = colour_format + "scrapper2 " + type.ljust(12) + ": "

    print(begin_format + msg + reset_format, end=end, file=file, flush=True)

def post_info(info_msg, file=sys.stdout, en_colour=True):
    '''
    Print info to stdout.
    '''
    post_msg(info_msg, type="info", file=file, colour="cyan", en_colour=en_colour)

def post_warning(warning_msg, file=sys.stderr, en_colour=True):
    '''
    Print warning to stderr.
    '''
    post_msg(warning_msg, type="warning", file=file, colour="yellow", en_colour=en_colour)

def post_success(success_msg, file=sys.stdout, en_colour=True):
    '''
    Print success message to stdout.
    '''
    post_msg(success_msg, type="success", file=file, colour="green", en_colour=en_colour)

def post_failure(failure_msg, file=sys.stdout, en_colour=True):
    '''
    Print failure message to stdout.
    '''
    post_msg(failure_msg, type="failure", file=file, colour="red", en_colour=en_colour)

def post_error(err_msg, file=sys.stderr, en_colour=True):
    '''
    Print error message to stderr.
    '''
    post_msg(err_msg, type="error", file=file, colour="red", en_colour=en_colour)

def error_out(err_msg, code=1, file=sys.stderr, en_colour=True):
    '''
    Print error message to stderr and exit.
    '''
    post_msg(err_msg, type="fatal error", file=file, colour="red", en_colour=en_colour)
    sys.exit(code)
#----------Message-Utilities-END----------------------------


#----------Main-START---------------------------------------
if __name__ == "__main__":
    import colorama.initialise; colorama.initialise.init()

    post_info("Running doctests...")
    import doctest
    if doctest.testmod()[0] == 0:
        post_success("All tests passed")
#----------Main-END-----------------------------------------