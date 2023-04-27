#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""Simple HTTP Server With Upload.
This module builds on BaseHTTPServer by implementing the standard GET
and HEAD requests in a fairly straightforward manner.
"""

__version__ = "0.3.1"
__author__ = "freelamb@126.com"
__all__ = ["SimpleHTTPRequestHandler"]

import os
import sys
import argparse
import posixpath
try:
    from html import escape
except ImportError:
    from cgi import escape
import shutil
import mimetypes
import re
import signal
from io import StringIO, BytesIO

if sys.version_info.major == 3:
    # Python3
    from urllib.parse import quote
    from urllib.parse import unquote
    from http.server import HTTPServer
    from http.server import BaseHTTPRequestHandler
else:
    # Python2
    reload(sys)
    sys.setdefaultencoding('utf-8')
    from urllib import quote
    from urllib import unquote
    from BaseHTTPServer import HTTPServer
    from BaseHTTPServer import BaseHTTPRequestHandler


import datetime

def format_size(size):
    """Formats the file size in a human-readable format."""
    for unit in ['', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB']:
        if abs(size) < 1024.0:
            return "%3.1f %s" % (size, unit)
        size /= 1024.0
    return "%.1f %s" % (size, 'YiB')

def format_date(timestamp):
    """Formats the modification time in a human-readable format."""
    return datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    """Simple HTTP request handler with GET/HEAD/POST commands.
    This serves files from the current directory and any of its
    subdirectories.  The MIME type for files is determined by
    calling the .guess_type() method. And can receive file uploaded
    by client.
    The GET/HEAD/POST requests are identical except that the HEAD
    request omits the actual contents of the file.
    """

    server_version = "simple_http_server/" + __version__

    def do_GET(self):
        """Serve a GET request."""
        fd = self.send_head()
        if fd:
            shutil.copyfileobj(fd, self.wfile)
            fd.close()

    def do_HEAD(self):
        """Serve a HEAD request."""
        fd = self.send_head()
        if fd:
            fd.close()

    def do_POST(self):
        """Serve a POST request."""
        r, info = self.deal_post_data()
        print(r, info, "by: ", self.client_address)
        f = BytesIO()
        f.write(b'<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
        f.write(b"<html>\n<title>Upload Result Page</title>\n")
        f.write(b"<body>\n<h2>Upload Result Page</h2>\n")
        f.write(b"<hr>\n")
        if r:
            f.write(b"<strong>Success:</strong>")
        else:
            f.write(b"<strong>Failed:</strong>")
        f.write(info.encode('utf-8'))
        f.write(b"<br><a href=\".\">back</a>")
        f.write(b"<hr><small>Powered By: freelamb, check new version at ")
        f.write(b"<a href=\"https://github.com/freelamb/simple_http_server\">")
        f.write(b"here</a>.</small></body>\n</html>\n")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "text/html;charset=utf-8")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        if f:
            shutil.copyfileobj(f, self.wfile)
            f.close()

    def deal_post_data(self):
        boundary = self.headers["Content-Type"].split("=")[1].encode('utf-8')
        remain_bytes = int(self.headers['content-length'])
        line = self.rfile.readline()
        remain_bytes -= len(line)
        if boundary not in line:
            return False, "Content NOT begin with boundary"
        line = self.rfile.readline()
        remain_bytes -= len(line)
        fn = re.findall(r'Content-Disposition.*name="file"; filename="(.*)"', line.decode('utf-8'))
        if not fn:
            return False, "Can't find out file name..."
        path = translate_path(self.path)
        fn = os.path.join(path, fn[0])
        while os.path.exists(fn):
            fn += "_"
        line = self.rfile.readline()
        remain_bytes -= len(line)
        line = self.rfile.readline()
        remain_bytes -= len(line)
        try:
            out = open(fn, 'wb')
        except IOError:
            return False, "Can't create file to write, do you have permission to write?"

        pre_line = self.rfile.readline()
        remain_bytes -= len(pre_line)
        while remain_bytes > 0:
            line = self.rfile.readline()
            remain_bytes -= len(line)
            if boundary in line:
                pre_line = pre_line[0:-1]
                if pre_line.endswith(b'\r'):
                    pre_line = pre_line[0:-1]
                out.write(pre_line)
                out.close()
                return True, "File '%s' upload success!" % fn
            else:
                out.write(pre_line)
                pre_line = line
        return False, "Unexpect Ends of data."

    def send_head(self):
        """Common code for GET and HEAD commands.
        This sends the response code and MIME headers.
        Return value is either a file object (which has to be copied
        to the output file by the caller unless the command was HEAD,
        and must be closed by the caller under all circumstances), or
        None, in which case the caller has nothing further to do.
        """
        path = translate_path(self.path)
        if os.path.isdir(path):
            if not self.path.endswith('/'):
                # redirect browser - doing basically what apache does
                self.send_response(301)
                self.send_header("Location", self.path + "/")
                self.end_headers()
                return None
            for index in "index.html", "index.htm":
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                return self.list_directory(path)
        content_type = self.guess_type(path)
        try:
            # Always read in binary mode. Opening files in text mode may cause
            # newline translations, making the actual size of the content
            # transmitted *less* than the content-length!
            f = open(path, 'rb')
        except IOError:
            self.send_error(404, "File not found")
            return None
        self.send_response(200)
        self.send_header("Content-type", content_type)
        fs = os.fstat(f.fileno())
        self.send_header("Content-Length", str(fs[6]))
        self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
        self.end_headers()
        return f

    def list_directory(self, path):
        """Helper to produce a directory listing (absent index.html).
        Return value is either a file object, or None (indicating an
        error).  In either case, the headers are sent, making the
        interface the same as for send_head().
        """
        try:
            list_dir = os.listdir(path)
        except os.error:
            self.send_error(404, "No permission to list directory")
            return None
        # list_dir.sort(key=lambda a: a.lower())
        f = BytesIO()
        display_path = escape(unquote(self.path))
        f.write(b'<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
        f.write(b'<html>\n<head>\n')
        f.write(b'<title>Directory listing for %s</title>\n' % display_path.encode('utf-8'))
        f.write(b'<style>\n')
        f.write(b'body { font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #F2F2F2; }\n')
        f.write(b'.container { max-width: 800px; margin: 0 auto; padding: 20px; background-color: #FFF; box-shadow: 0 0 10px rgba(0, 0, 0, 0.3); }\n')
        f.write(b'h1 { text-align: center; margin-bottom: 20px; }\n')
        f.write(b'form { display: flex; flex-direction: column; align-items: center; margin-bottom: 20px; }\n')
        f.write(b'input[type="file"] { margin-bottom: 10px; }\n')
        f.write(b'input[type="submit"] { background-color: #4CAF50; color: #FFF; padding: 10px; border: none; border-radius: 5px; cursor: pointer; transition: background-color 0.2s ease-in-out; }\n')
        f.write(b'input[type="submit"]:hover { background-color: #3E8E41; }\n')
        f.write(b'table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }\n')
        f.write(b'th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }\n')
        f.write(b'th { background-color: #4CAF50; color: #FFF; }\n')
        f.write(b'a { color: #000; text-decoration: none; }\n')
        f.write(b'a:hover { text-decoration: underline; }\n')
        f.write(b'</style>\n')
        f.write(b'</head>\n')
        f.write(b"<hr>\n")
        f.write(b"<h1>Upload File</h1>\n")
        f.write(b"<form ENCTYPE=\"multipart/form-data\" method=\"post\" style=\"margin-bottom: 1em;\">\n")
        f.write(b"<input name=\"file\" type=\"file\" style=\"margin-right: 0.5em;\" />\n")
        f.write(b"<input type=\"submit\" value=\"Upload File\" class=\"btn btn-primary\" />\n")
        f.write(b"</form>\n")
        # f.write(b"<html>\n<title>Directory listing for %s</title>\n" % display_path.encode('utf-8'))
        # f.write(b"<body>\n<h2>Directory listing for %s</h2>\n" % display_path.encode('utf-8'))
        # f.write(b"<hr>\n")
        # f.write(b"<form ENCTYPE=\"multipart/form-data\" method=\"post\">")
        # f.write(b"<input name=\"file\" type=\"file\"/>")
        # f.write(b"<input type=\"submit\" value=\"upload\"/></form>\n")
        f.write(b"<hr>\n<ul>\n")
        new_list = []
        new_list_1 = []
        # f.write(b"<h1>Directories</h1>\n")
        for name in list_dir:
            fullname = os.path.join(path, name)
            display_name = linkname = name
            # Append / for directories or @ for symbolic links
            wat = False
            if os.path.isdir(fullname):
                display_name = name + "/"
                linkname = name + "/"
                wat = True
            if os.path.islink(fullname):
                display_name = name + "@"
                wat = True
                # Note: a link to a directory displays with @ and links with /
            if wat:
                # f.write(b'<li><a href="%s">%s</a>\n' % (quote(linkname).encode('utf-8'), escape(display_name).encode('utf-8')))
                new_list_1.append((linkname, display_name))
            else:
                new_list.append((linkname, display_name))
        # f.write(b"<h1>Files</h1>\n")
        # for linkname, display_name in new_list:
        #     f.write(b'<li><a href="%s">%s</a>\n' % (quote(linkname).encode('utf-8'), escape(display_name).encode('utf-8')))
        f.write(b'<hr>\n<h2>Directories:</h2>\n')
        f.write(b'<table style="width:100%">\n')
        f.write(b'<tr>\n<th>Name</th>\n<th>Size</th>\n<th>Last Modified</th>\n</tr>\n')
        for linkname, display_name in new_list_1:
            f.write(b'<tr>\n')
            f.write(b'<td><a href="%s">%s</a></td>\n' % (quote(linkname).encode('utf-8'), escape(display_name).encode('utf-8')))
            # f.write(b'<td>%s</td>\n' % format_size(file_size).encode('utf-8'))
            # f.write(b'<td>%s</td>\n' % format_date(mod_time).encode('utf-8'))
            f.write(b'</tr>\n')
        f.write(b'</table>\n')
        f.write(b'<hr>\n<h2>Files:</h2>\n')
        f.write(b'<table style="width:100%">\n')
        f.write(b'<tr>\n<th>Name</th>\n<th>Size</th>\n<th>Last Modified</th>\n</tr>\n')
        for linkname, display_name in new_list:
            f.write(b'<tr>\n')
            f.write(b'<td><a href="%s">%s</a></td>\n' % (quote(linkname).encode('utf-8'), escape(display_name).encode('utf-8')))
            # f.write(b'<td>%s</td>\n' % format_size(file_size).encode('utf-8'))
            # f.write(b'<td>%s</td>\n' % format_date(mod_time).encode('utf-8'))
            f.write(b'</tr>\n')
        f.write(b'</table>\n')

        f.write(b"</ul>\n<hr>\n</body>\n</html>\n")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "text/html;charset=utf-8")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        return f

    def guess_type(self, path):
        """Guess the type of a file.
        Argument is a PATH (a filename).
        Return value is a string of the form type/subtype,
        usable for a MIME Content-type header.
        The default implementation looks the file's extension
        up in the table self.extensions_map, using application/octet-stream
        as a default; however it would be permissible (if
        slow) to look inside the data to make a better guess.
        """

        base, ext = posixpath.splitext(path)
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        ext = ext.lower()
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        else:
            return self.extensions_map['']

    if not mimetypes.inited:
        mimetypes.init()  # try to read system mime.types
    extensions_map = mimetypes.types_map.copy()
    extensions_map.update({
        '': 'application/octet-stream',  # Default
        '.py': 'text/plain',
        '.c': 'text/plain',
        '.h': 'text/plain',
    })


def translate_path(path):
    """Translate a /-separated PATH to the local filename syntax.
    Components that mean special things to the local file system
    (e.g. drive or directory names) are ignored.  (XXX They should
    probably be diagnosed.)
    """
    # abandon query parameters
    path = path.split('?', 1)[0]
    path = path.split('#', 1)[0]
    path = posixpath.normpath(unquote(path))
    words = path.split('/')
    words = filter(None, words)
    path = os.getcwd()
    for word in words:
        drive, word = os.path.splitdrive(word)
        head, word = os.path.split(word)
        if word in (os.curdir, os.pardir):
            continue
        path = os.path.join(path, word)
    return path


def signal_handler(signal, frame):
    print("You choose to stop me.")
    exit()

def _argparse():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bind', '-b', metavar='ADDRESS', default='0.0.0.0', help='Specify alternate bind address [default: all interfaces]')
    parser.add_argument('--version', '-v', action='version', version=__version__)
    parser.add_argument('port', action='store', default=8000, type=int, nargs='?', help='Specify alternate port [default: 8000]')
    return parser.parse_args()

def main():
    args = _argparse()
    # print(args)
    server_address = (args.bind, args.port)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    server = httpd.socket.getsockname()
    print("server_version: " + SimpleHTTPRequestHandler.server_version + ", python_version: " + SimpleHTTPRequestHandler.sys_version)
    print("sys encoding: " + sys.getdefaultencoding())
    print("Serving http on: " + str(server[0]) + ", port: " + str(server[1]) + " ... (http://" + server[0] + ":" + str(server[1]) + "/)")
    httpd.serve_forever()

if __name__ == '__main__':
    main()
