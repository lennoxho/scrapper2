#----------Import-Modules-START-----------------------------
import scrapper2

import argparse
import time
import urllib.parse
import os
#----------Import-Modules-END-------------------------------


#----------Global-Variables-START---------------------------
__test_mode = False
#----------Global-Variables-END-----------------------------


#----------Utilities-START----------------------------------
def jobs(s):
    """
    >>> jobs("http://rand.com/hello,visit")
    ('http://rand.com/hello', 'visit')
    >>> jobs("http://rand.com/hello ,both")
    ('http://rand.com/hello', 'both')
    >>> jobs("http://rand.com/hello, download")
    ('http://rand.com/hello', 'download')
    >>> jobs("http://rand.com/hello")
    Traceback (most recent call last):
    ...
    argparse.ArgumentTypeError: Jobs must be tuples of (URL, task)
    >>> jobs("http://rand.com/hello,random")
    Traceback (most recent call last):
    ...
    argparse.ArgumentTypeError: Jobs must be tuples of (URL, task)
    >>> jobs("//rand.com/hello,visit")
    Traceback (most recent call last):
    ...
    argparse.ArgumentTypeError: Jobs must be tuples of (URL, task)
    >>> jobs("rand.com/hello,visit")
    Traceback (most recent call last):
    ...
    argparse.ArgumentTypeError: Jobs must be tuples of (URL, task)
    """
    try:
        x, y = map(str, s.split(','))
        x, y = x.strip(), y.strip()
        if y not in ["visit", "download", "both"]:
            raise Exception('Task must be one of "visit", "download", or "both"')
        base_info = urllib.parse.urlsplit(x)
        if base_info.scheme == "" or base_info.netloc == "":
            raise Exception("URL must have full form, ie: <scheme>://<locname>[/...]")
        return x, y

    except Exception as e:
        if not __test_mode:
            scrapper2.post_error(str(e) + "\n")
        raise argparse.ArgumentTypeError("Jobs must be tuples of (URL, task)")

def get_jobs_from_ini(filename):
    try:
        hfile = open(filename, "r")
    except Exception as e:
        scrapper2.error_out(str(e) + " while opening " + filename)

    jobs = []
    for line in hfile:
        line = line.strip()
        if line != '':
            val = line.split(',')
            if len(val) != 2:
                scrapper2.error_out("ini file is ill formed .Jobs must be tuples of (URL, task)")
            jobs.append(val)

    return jobs
#----------Utilities-END------------------------------------


#----------Main-START---------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Command line interface for scrapper2.")

    parser.add_argument('root_jobs', metavar='<job>', type=jobs, nargs='*', help='tuples of (URL, task), where task is "visit", "download", or "both"')

    parser.add_argument("-s", "--silent", action="store_true", required=False, help="Silent mode")
    parser.add_argument("-l", "--no_log", action="store_true", required=False, help="Disable logging")
    parser.add_argument("-c", "--no_colour", action="store_true", required=False, help="Disable colour console printing")
    parser.add_argument("-a", "--tenacious", action="store_true", required=False, help="Enable tenacious/aggressive behaviour")
    parser.add_argument("-n", "--num_threads", action="store", metavar="<num>", nargs=1, default=1, type=int, required=False, help="Number of threads to spawn")
    parser.add_argument("-t", "--traversal", action="store", metavar="<method>", nargs=1, default="DFS", choices=["DFS", "BFS"], type=str, required=False, help="Traversal method")

    parser.add_argument("--test", action="store_true", required=False, help="Run doctests")

    args = parser.parse_args()
    if args.test:
        __test_mode = True
        scrapper2.post_info("Running doctests...")
        import doctest
        if doctest.testmod()[0] == 0:
            scrapper2.post_success("All tests passed")
    else:
        has_ini_file = os.path.isfile("scrapper2_jobs.ini")

        if len(args.root_jobs) < 1 and not has_ini_file:
            scrapper2.error_out("No jobs specified. Please specify at least one job")

        ini_jobs = get_jobs_from_ini("scrapper2_jobs.ini")

        scrapper2.post_info("Root jobs:")
        for url, task in args.root_jobs:
            scrapper2.post_info("    " + url + " - " + task)

        for url, task in ini_jobs:
            scrapper2.post_info("    " + url + " - " + task)

        a_threads = args.num_threads[0] if isinstance(args.num_threads, list) else args.num_threads
        a_traversal = args.traversal[0] if isinstance(args.traversal, list) else args.traversal

        scrapper2.post_info("Number of worker threads: " + str(a_threads))
        scrapper2.post_info("Traversal method: " + a_traversal)
        scrapper2.post_info("Silent: " + str(args.silent))
        scrapper2.post_info("logging: " + str(not args.no_log))
        scrapper2.post_info("colour: " + str(not args.no_colour))
        scrapper2.post_info("Tenacious: " + str(args.tenacious) + "\n")

        root_jobs = []
        for url, task in args.root_jobs:
            root_jobs.append((url, task, 0))

        for url, task in ini_jobs:
            root_jobs.append((url, task, 0))

        scrapper2.post_info("Creating Scrapper...")
        scrapper = scrapper2.Scrapper(root_jobs, traversal=a_traversal, num_threads=a_threads, silent=args.silent, log=(not args.no_log), colour=(not args.no_colour), tenacious=args.tenacious)

        scrapper2.post_info("Starting Scrapper...")
        start_time = time.clock()

        scrapper.start()

        scrapper2.post_info("Scrapper exiting...")
        elapsed_time = time.clock() - start_time
        scrapper2.post_info("Time elapsed : " + str(elapsed_time) + " seconds")
#----------Main-END-----------------------------------------