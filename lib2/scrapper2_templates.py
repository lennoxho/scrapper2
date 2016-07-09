#----------Import-Modules-START-----------------------------
import os
import posixpath
import urllib.parse
from bs4 import BeautifulSoup
#----------Import-Modules-END-------------------------------


#----------Global-Variables-START---------------------------
__std_links_to_visit = [".html"]
__std_links_to_download = [".jpg", ".png", ".jpeg", ".mp4", ".wmv", ".avi"]
__std_chunk_size = 1024
__visited_links = set()
#----------Global-Variables-END-----------------------------


#----------Template-functions-START-------------------------
def std_preprocess(root_jobs):
    for url, _, _ in root_jobs:
        __visited_links.add(url)

def std_visit(request, base_url, id, jobs):
    std_visit_template(request, base_url, id, jobs, __std_links_to_visit, __std_links_to_download)

def std_visit_template(request, base_url, id, jobs, links_to_visit, links_to_download):
    soup = BeautifulSoup(request.text.replace('\n', '').replace('\r', ''), "html.parser")
    new_urls = []

    #--------std_process-Utilities-START-------------
    def format_url(url, base_url):
        '''
        Assumes url and base_url are well formed.
        '''
        info = urllib.parse.urlsplit(url)
        if info.netloc == '':
            path = info.path
            if path.startswith('/'):
                base_info = urllib.parse.urlsplit(base_url)
                base_loc = base_info.scheme + "://" + base_info.netloc

                return posixpath.join(base_loc, path[1:])

            rel_path = path
            if rel_path.startswith("./"):
                rel_path = rel_path[2:]
            return posixpath.join(base_url, rel_path)

        elif info.scheme == '':
            return "http:" + url

        else:
            return url

    def find_and_add_url(tag, attr):
        for div in soup.find_all(tag):
            new_url = format_url(div.get(attr), base_url)
            if new_url not in __visited_links:
                new_urls.append(new_url)
    #--------std_process-Utilities-START-------------

    find_and_add_url("a", "href")
    find_and_add_url("img", "src")
    find_and_add_url("source", "src")
    find_and_add_url("video", "src")

    jobs.clear()
    for new_url in new_urls:
        _, ext = os.path.splitext(new_url)
        # "both" is not used here
        if ext in links_to_visit:
            # id is not used here
            jobs.append((new_url, "visit", 0))
        elif ext in links_to_download:
            jobs.append((new_url, "download", 0))

def std_download(request, url, id):
    path = urllib.parse.urlsplit(url).path
    if path == '' or path == '/':
        filename = urllib.parse.urlsplit(url).netloc
    elif path.startswith('/'):
        filename = path[1:]
    else:
        filename = path

    dirname = os.path.dirname(filename)
    if dirname != "" and not os.path.isdir(dirname):
        os.makedirs(dirname)

    if os.path.isfile(filename):
        return

    hfile = open(filename, 'wb')
    for chunk in request.iter_content(chunk_size=__std_chunk_size):
        if chunk:
            hfile.write(chunk)

    hfile.close()

def std_modify_header(header, url, task, id):
    pass

def std_report_header(header, success, url, task, id):
    pass

def std_nok(status_code, url, task, id):
    return True
#----------Template-functions-END---------------------------