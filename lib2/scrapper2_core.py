#----------Import-Modules-START-----------------------------
from lib2.scrapper2_utils import *
import lib2.scrapper2_templates as templates

import requests
from requests.packages.urllib3.util.retry import Retry as request_retry
from requests.adapters import HTTPAdapter

import threading
import collections
import time
import signal
import inspect
import sys
#----------Import-Modules-END-------------------------------


#----------Global-Variables-START---------------------------
_valid_traversal_modes = ("DFS", "BFS")
_valid_tasks = ("visit", "download", "both")
_http_OK = 200
#----------Global-Variables-END-----------------------------


#----------Exception-Definitions-START----------------------
class ScrapperException(Exception):
    pass
#----------Exception-Definitions-START----------------------


#----------Scrapper-Class-Definition-START------------------
class Scrapper:

    #--------Scrapper-Class-Utilities-START-----------
    def post(self, msg_func, *args):
        '''
        Synchronized wrapper for the message printing functions.

        Do not use error_out with this function!
        '''
        assert msg_func != error_out

        self.__post_lock.acquire()
        if not self.__silent:
            msg_func(*args, en_colour=self.__colour)
        if self.__log:
            msg_func(*args, file=self.__log_file, en_colour=False)
        self.__post_lock.release()

    def sigint_handler(self, signal, frame):
        self.post(post_warning, "SIGINT received")
        self.signal_exit()
    #--------Scrapper-Class-Utilities-END-------------

    def __init__(self, root_jobs, preprocess_func=templates.std_preprocess, traversal="DFS", num_threads=1,
                 silent=False, log=True, colour=True, tenacious=True, initial_header=None):

        if not isinstance(root_jobs, list) or \
           any(not (isinstance(entry, tuple) and len(entry) == 3) for entry in root_jobs) or \
           not valid_root_urls(root_jobs):
            error_out("Invalid root jobs")

        if isinstance(traversal, str):
            if traversal not in _valid_traversal_modes:
                error_out("Invalid traversal mode")
            self.__scrapper_jobs = ScrapperJobs(root_jobs, traversal)
            post_info("Job list created")
        else:
            error_out("Traversal mode must be a string")

        preprocess_func(root_jobs)

        if num_threads < 1 or not isinstance(num_threads, int):
            raise ScrapperException("num_threads must be a positive integer")

        self.__num_threads = num_threads
        self.__silent = silent
        self.__log = log
        self.__colour = colour
        self.__tenacious = tenacious

        self.__visit_func = templates.std_visit
        self.__download_func = templates.std_download
        self.__modify_header_func = templates.std_modify_header
        self.__report_header_func = templates.std_report_header
        self.__nok_func = templates.std_nok
        self.__retries = request_retry(total=2, backoff_factor=0.1)
        self.__timeout = 7

        self.__gen_lock = threading.Lock()
        self.__post_lock = threading.Lock()
        if self.__log:
            try:
                self.__log_file = open("scrapper2_" + time.strftime("%Y%m%d_%H%M%S") + ".log", "w")
            except Exception as e:
                error_out(str(e))

        self.__threads_started = False
        self.__signal_exit = False
        self.__thread_pool = []
        try:
            for i in range(self.__num_threads):
                self.__thread_pool.append(threading.Thread(target=self.scrape, args=(i, initial_header)))
                post_info("Spawning thread " + str(i))
        except Exception as e:
            error_out(str(e))

    def start(self):
        for t in self.__thread_pool:
            t.start()

        self.__threads_started = True

        signal.signal(signal.SIGINT, self.sigint_handler)
        while not self.exit_posted() and not self.__scrapper_jobs.is_done:
            try:
                time.sleep(1)
            except InterruptedError:
                pass

        for t in self.__thread_pool:
            t.join()

        remaining_jobs = self.__scrapper_jobs.curr_jobs()
        if len(remaining_jobs) > 0:
            post_warning("Uncompleted jobs: ")
            for job in remaining_jobs:
                post_warning("      " + str(job[0]) + " - " + str(job[1]))

    def scrape(self, i, initial_header):
        self.post(post_info, "thread " + str(i) + " starting")

        curr_session = ScrapperSession(initial_header, self.__retries)
        url, task, id = None, None, None
        curr_header = None

        while not self.exit_posted():
            try:
                if (url, task, id) == (None, None, None):
                    job = self.__scrapper_jobs.get_job()
                    if job is None:
                        break

                    url, task, id = job

                self.post(post_info, "thread " + str(i) + " performing " + str(id) + " - " + task + " " + url)

                curr_header = curr_session.get_header()
                self.__modify_header_func(curr_header, url, task, id)

                r = curr_session.get(url, self.__timeout)

                success = r.status_code == _http_OK
                if success:
                    if task == "visit" or task == "both":
                        jobs = []
                        success = success and self.__visit_func(r, url, id, jobs)
                        if jobs != []:
                            self.__scrapper_jobs.add_job(jobs)
                    if task == "download" or task == "both":
                        success = success and self.__download_func(r, url, id)

                curr_header = curr_session.get_header()
                self.__report_header_func(curr_header, success, url, task, id)

                redo = False
                if not success:
                    self.post(post_failure, "thread " + str(i) + " failed to perform " + str(id) + " - " + task + " on " + url + ' (' + str(r.status_code) + ')')
                    redo = self.__nok_func(r.status_code, url, task, id)

                if not redo:
                    if not success:
                        self.post(post_warning, "job skipped " + str(id) + " - " + task + " on " + url)
                    self.__scrapper_jobs.done_job((url, task, id))
                    url, task, id = None, None, None
                else:
                    self.post(post_info, "thread " + str(i) + " will redo " + str(id) + " - " + task + " on " + url)

            except Exception as e:
                if isinstance(e, AssertionError):
                    _, _, exc_tb = sys.exc_info()
                    err_msg = "AssertionError at line " + str(exc_tb.tb_lineno)
                else:
                    err_msg = str(e)

                job_info = ''
                if (url, task, id) != (None, None, None):
                    job_info = ' (' + str(id) + " - " + task + " on " + url + ')'

                self.post(post_error, "thread " + str(i) + " encountered error " + err_msg + job_info)
                if self.__tenacious:
                    curr_session = ScrapperSession(curr_header, self.__retries)
                    self.post(post_warning, "thread " + str(i) + " is creating a new Session")
                else:
                    self.signal_exit()

        self.post(post_info, "thread " + str(i) + " exiting")

    def signal_exit(self):
        self.__gen_lock.acquire()
        self.__signal_exit = True
        self.__scrapper_jobs.signal_exit()
        self.post(post_info, "Signalling all threads to exit...")
        self.__gen_lock.release()

    def exit_posted(self):
        self.__gen_lock.acquire()
        ret = self.__signal_exit
        self.__gen_lock.release()
        return ret

    def set_visit_func(self, func):
        assert not self.__threads_started
        if len(inspect.getargspec(func)[0]) != 4:
            error_out("Visit callback function is not well formed")
        self.__visit_func = func

    def set_download_func(self, func):
        assert not self.__threads_started
        if len(inspect.getargspec(func)[0]) != 3:
            error_out("Download callback function is not well formed")
        self.__download_func = func

    def set_modify_header_func(self, func):
        assert not self.__threads_started
        if len(inspect.getargspec(func)[0]) != 4:
            error_out("Modify header callback function is not well formed")
        self.__modify_header_func = func

    def set_report_header_func(self, func):
        assert not self.__threads_started
        if len(inspect.getargspec(func)[0]) != 5:
            error_out("Report header callback function is not well formed")
        self.__report_header_func = func

    def set_nok_func(self, func):
        assert not self.__threads_started
        if len(inspect.getargspec(func)[0]) != 4:
            error_out("not OK callback function is not well formed")
        self.__nok_func = func

    def set_retries_and_timeout(self, retry_num, backoff_factor, timeout):
        assert not self.__threads_started
        if not isinstance(retry_num, int) or retry_num < 0 or backoff_factor <=0:
            error_out("Retries is not well formed")
        if not isinstance(timeout, tuple) or len(timeout) != 2:
            error_out("Timeout is not well formed")

        self.__retries = request_retry(total=retry_num, backoff_factor=backoff_factor)
        self.__timeout = timeout
#----------Scrapper-Class-Definition-END--------------------


#----------ScrapperSession-Class-Definition-START-----------
class ScrapperSession:

    def __init__(self, initial_header, retries):
        self.__session = requests.Session()
        self.__session.mount("http://", HTTPAdapter(max_retries=retries))
        if initial_header is not None:
            self.__session.headers = initial_header

    def get(self, url, timeout):
        return self.__session.get(url, timeout=timeout)

    def get_header(self):
        return self.__session.headers

    def get_cookies(self):
        return self.__session.cookies

    def clear_headers(self):
        self.__session.headers.clear()

    def clear_cookies(self):
        self.__session.cookies.clear()
#----------ScrapperSession-Class-Definition-END-------------


#----------ScrapperJobs-Class-Definition-START--------------
class ScrapperJobs:

    def __init__(self, root_jobs, traversal):
        self.__traversal = traversal
        self.__container = collections.deque(root_jobs)
        self.__current_jobs = set()
        self.__job_lock = threading.Lock()
        self.__cv = threading.Condition(self.__job_lock)
        self.__signal_done = False

    def add_job(self, jobs):
        assert all((isinstance(job, tuple) and \
                    len(job) == 3 and \
                    job[1] in _valid_tasks) for job in jobs)
        self.__job_lock.acquire()
        self.__container.extend(jobs)
        self.__cv.notify_all()
        self.__job_lock.release()

    def empty(self):
        self.__job_lock.acquire()
        empty = len(self.__container) == 0
        self.__job_lock.release()
        return empty

    def get_job(self):
        self.__job_lock.acquire()

        while len(self.__container) == 0 and not self.__signal_done:
            self.__cv.wait()

        if not self.__signal_done:
            if self.__traversal == "DFS":
                job = self.__container.pop()
            else:
                job = self.__container.popleft()
            self.__current_jobs.add(job)
        else:
            job = None

        self.__job_lock.release()
        return job

    def done_job(self, job):
        '''
        Make sure new job is added before calling done_job.
        '''
        self.__job_lock.acquire()
        self.__current_jobs.remove(job)
        if len(self.__current_jobs) == 0 and len(self.__container) == 0:
            self.__signal_done = True
            self.__cv.notify_all()
        self.__job_lock.release()

    def is_done(self):
        self.__job_lock.acquire()
        ret = self.__signal_done
        self.__job_lock.release()
        return ret

    def signal_exit(self):
        self.__job_lock.acquire()
        self.__cv.notify_all()
        self.__job_lock.release()

    def curr_jobs(self):
        self.__job_lock.acquire()
        jobs = self.__current_jobs
        self.__job_lock.release()
        return jobs
#----------ScrapperJobs-Class-Definition-END----------------