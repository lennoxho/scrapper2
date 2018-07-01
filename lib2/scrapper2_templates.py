#----------Import-Modules-START-----------------------------
import os
import posixpath
import pyexiv2
import urllib.parse
import threading

from bs4 import BeautifulSoup
#----------Import-Modules-END-------------------------------


#----------Global-Variables-START---------------------------
__std_links_to_visit = [".html"]
__std_links_to_download = [".jpg", ".png", ".jpeg", ".mp4", ".wmv", ".avi"]
__std_chunk_size = 1024
__visited_links = set()
__file_lock = threading.Lock()
#----------Global-Variables-END-----------------------------


#----------Utility-functions-START--------------------------
def format_previous_directory(url):
    """
    >>> format_previous_directory('http://www.example.com/foo/bar/../../baz/bux/')
    'http://www.example.com/baz/bux/'
    >>> format_previous_directory('http://www.example.com/some/path/../file.ext')
    'http://www.example.com/some/file.ext'
    >>> format_previous_directory('http://www.example.com/some/../path/../file.ext')
    'http://www.example.com/file.ext'
    """
    parsed = urllib.parse.urlparse(url)
    new_path = posixpath.normpath(parsed.path)
    if parsed.path.endswith('/'):
        new_path += '/'
    cleaned = parsed._replace(path=new_path)
    return cleaned.geturl()

def format_url(url, base_url):
    '''
    Assumes url and base_url are well formed.

    >>> format_url("http://rand.com/random", "http://rand.com")
    'http://rand.com/random'
    >>> format_url("http://rand.com/", "http://rand.com")
    'http://rand.com/'
    >>> format_url("", "http://rand.com") is None
    True
    >>> format_url("//rand.com", "http://rand.com")
    'http://rand.com'
    >>> format_url("//rand.com/random", "http://rand.com")
    'http://rand.com/random'
    >>> format_url("/random", "http://rand.com")
    'http://rand.com/random'
    >>> format_url("/random/ram", "http://rand.com")
    'http://rand.com/random/ram'
    >>> format_url("./random", "http://rand.com/ram")
    'http://rand.com/random'
    >>> format_url("./random", "http://rand.com/ram/")
    'http://rand.com/ram/random'
    >>> format_url("random/rand", "http://rand.com/ram")
    'http://rand.com/random/rand'
    >>> format_url("/random/rand", "http://rand.com/ram")
    'http://rand.com/random/rand'
    '''
    if url == '':
        return None

    info = urllib.parse.urlsplit(url)
    if info.netloc == '':
        path = info.path
        if path.startswith('/'):
            base_info = urllib.parse.urlsplit(base_url)
            base_loc = base_info.scheme + "://" + base_info.netloc

            ret = posixpath.join(base_loc, path[1:])
            if info.query != '':
                ret = ret + '?' + info.query

            return ret

        rel_path = path
        if rel_path.startswith("./"):
            rel_path = rel_path[2:]

        ret = posixpath.join(os.path.dirname(base_url), rel_path)
        if info.query != '':
            ret = ret + '?' + info.query
        return  ret

    elif info.scheme == '':
        return "http:" + url

    else:
        return url

def format_url_with_resolution(url, base_url):
    new_url = format_url(url, base_url)
    if new_url is not None:
        new_url = format_previous_directory(new_url)

    return new_url
#----------Utility-functions-END----------------------------


#----------Template-functions-START-------------------------
def std_preprocess(root_jobs):
    for url, _, _ in root_jobs:
        __visited_links.add(url)

def std_visit(request, base_url, id, jobs):
    return std_visit_template(request, request.url, id, jobs, __std_links_to_visit, __std_links_to_download)

def std_visit_template(request, base_url, id, jobs, links_to_visit, links_to_download):
    new_urls = []

    #--------std_process-Utilities-START-------------
    def find_and_add_url(tag, attr, soup):
        for div in soup.find_all(tag):
            new_url = format_url_with_resolution(div.get(attr), base_url)
            if new_url is not None and new_url not in __visited_links:
                __visited_links.add(new_url)
                new_urls.append(new_url)
    #--------std_process-Utilities-START-------------

    soup = BeautifulSoup(request.text.replace('\n', '').replace('\r', ''), "html.parser")

    find_and_add_url("a", "href", soup)
    find_and_add_url("img", "src", soup)
    find_and_add_url("source", "src", soup)
    find_and_add_url("video", "src", soup)

    jobs.clear()
    for new_url in new_urls:
        _, ext = os.path.splitext(new_url)
        # "both" is not used here
        if ext in links_to_visit:
            # id is not used here
            jobs.append((new_url, "visit", 0))
        elif ext in links_to_download:
            jobs.append((new_url, "download", 0))

    return True

def std_download(request, url, id, iptc_tags):
    url_info = urllib.parse.urlsplit(url)

    path = url_info.path
    if path != '' and path[0] == '/':
        path = path[1:]

    filename = os.path.join(url_info.netloc, path)
    filename = os.path.join("scrapper2_download", filename)

    dirname = os.path.dirname(filename)

    # synchronize file operations
    __file_lock.acquire()
    if dirname != "" and not os.path.exists(dirname):
        os.makedirs(dirname)

    if not os.path.isfile(filename):
        hfile = open(filename, 'wb')
        for chunk in request.iter_content(chunk_size=__std_chunk_size):
            if chunk:
                hfile.write(chunk)
        hfile.close()

    __file_lock.release()

    # Write metadata
    meta = pyexiv2.ImageMetadata(filename)
    meta.read()

    for tag in iptc_tags:
        meta[tag] = pyexiv2.IptcTag(tag, iptc_tags[tag])

    meta.write()

    return True

def std_modify_header(header, url, task, id):
    pass

def std_report_header(header, success, url, task, id):
    pass

def std_nok(status_code, url, task, id):
    return False
#----------Template-functions-END---------------------------


#----------Main-START---------------------------------------
if __name__ == "__main__":
    import colorama.initialise; colorama.initialise.init()
    from scrapper2_utils import *

    post_info("Running doctests...")
    import doctest
    if doctest.testmod()[0] == 0:
        post_success("All tests passed")
#----------Main-END-----------------------------------------