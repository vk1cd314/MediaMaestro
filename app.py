
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
import urllib.parse

from urllib.parse import quote
from urllib.parse import unquote
from http.server import HTTPServer
from http.server import BaseHTTPRequestHandler


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
    def do_GET(self):
        if self.path.startswith('/search?q='):
            query = self.path.split('=')[1]
            print(f"Search query: {query}")
            path = translate_path(self.path)
            fd = self.filter(path)
            if fd:
                shutil.copyfileobj(fd, self.wfile)
                fd.close()
            
        else:    
            """Serve a GET request."""
            fd = self.send_head()
            if fd:
                shutil.copyfileobj(fd, self.wfile)
                fd.close()

    def filter(self, path):
        print(path)
        query_params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        search_query = query_params.get("q", [""])[0] 

        
        try:
            path = path[:-7]
            print(path)
            list_dir = os.listdir(path)
            list_dir = [f for f in list_dir if search_query.lower() in f.lower()]
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
        f.write(b'img { display: block; width: 60%; margin-left: auto; margin-right: auto;}\n')
        f.write(b'.container { max-width: 800px; margin: 0 auto; padding: 20px; background-color: #FFF; box-shadow: 0 0 10px rgba(0, 0, 0, 0.3); }\n')
        f.write(b'h1 { text-align: center; margin-bottom: 20px; }\n')
        f.write(b'form { display: flex; flex-direction: column; align-items: center; margin-bottom: 20px; }\n')
        f.write(b'input[type="file"] { margin-bottom: 10px; }\n')
        f.write(b'input[type="submit"] { background-color: #13274D; color: #FFF; padding: 10px; border: none; border-radius: 5px; cursor: pointer; transition: background-color 0.2s ease-in-out; }\n')
        f.write(b'input[type="submit"]:hover { background-color: #3E8E41; }\n')
        f.write(b'table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }\n')
        f.write(b'th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }\n')
        f.write(b'th { background-color: #13274D; color: #FFF; }\n')
        f.write(b'a { color: #000; text-decoration: none; }\n')
        f.write(b'a:hover { text-decoration: underline; }\n')
        f.write(b'</style>\n')
        f.write(b'</head>\n')
        #f.write(b'<div style=\"text-align: center;\">\n')
        f.write(b'<img width=\"400\" src=\"https://images2.imgbox.com/46/aa/qG7wrGvc_o.png\">\n')
        f.write(b'<h1>Share files</h1>')
        #f.write(b'<\div>\n')
        f.write(b"<hr>\n")
        f.write(b"<h1>Upload File</h1>\n")
        f.write(b"<form ENCTYPE=\"multipart/form-data\" method=\"post\" style=\"margin-bottom: 1em;\">\n")
        f.write(b"<input name=\"file\" type=\"file\" style=\"margin-right: 0.5em;\" />\n")
        f.write(b"<input type=\"submit\" value=\"Upload File\" class=\"btn btn-primary\" />\n")
        f.write(b"</form>\n")
        f.write(b"<form action=\"/search\" method=\"get\">\n")
        f.write(b"<label for=\"search\">Search:</label>\n")
        f.write(b"<input type=\"search\" id=\"search\" name=\"q\" placeholder=\"Search...\">\n")
        f.write(b"<button type=\"submit\">Go</button>\n")
        f.write(b"</form>\n")
        #f.write(b'<img width=\"400\" src=\"https://www.hubspot.com/hubfs/image-hubspot-centering-css.jpeg\">\n')
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
            size = os.stat(fullname).st_size
            modified_time = os.stat(fullname).st_mtime
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
                new_list_1.append((linkname, display_name, size, modified_time))
            else:
                new_list.append((linkname, display_name, size, modified_time))
        # f.write(b"<h1>Files</h1>\n")
        # for linkname, display_name in new_list:
        #     f.write(b'<li><a href="%s">%s</a>\n' % (quote(linkname).encode('utf-8'), escape(display_name).encode('utf-8')))
        f.write(b'<hr>\n<h2>Directories:</h2>\n')
        f.write(b'<table style="width:100%" align="center">\n')
        f.write(b'<tr>\n<th>Name</th>\n<th>Size</th>\n<th>Last Modified</th>\n</tr>\n')
        for linkname, display_name, size, modified_time in new_list_1:
            print(linkname, display_name, size, modified_time)
            f.write(b'<tr>\n')
            f.write(b'<td><a href="%s">%s</a></td>\n' % (quote(linkname).encode('utf-8'), escape(display_name).encode('utf-8')))
            f.write(b'<td>%s</td>\n' % format_size(size).encode('utf-8'))
            f.write(b'<td>%s</td>\n' % format_date(modified_time).encode('utf-8'))
            f.write(b'</tr>\n')
        f.write(b'</table>\n')
        f.write(b'<hr>\n<h2>Files:</h2>\n')
        f.write(b'<table style="width:100%" align="center">\n')
        f.write(b'<tr>\n<th>Name</th>\n<th>Size</th>\n<th>Last Modified</th>\n</tr>\n')
        for linkname, display_name, size, modified_time in new_list:
            print(linkname, display_name, size, modified_time)
            f.write(b'<tr>\n')
            f.write(b'<td><a href="%s">%s</a></td>\n' % (quote(linkname).encode('utf-8'), escape(display_name).encode('utf-8')))
            f.write(b'<td>%s</td>\n' % format_size(size).encode('utf-8'))
            f.write(b'<td>%s</td>\n' % format_date(modified_time).encode('utf-8'))
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

        

    def do_HEAD(self):

        fd = self.send_head()
        if fd:
            fd.close()

    def do_POST(self):

        r, info = self.deal_post_data()
        print(r, info, "addresss: ", self.client_address)
        f = BytesIO()
        f.write(b'<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
        f.write(b"<html>\n<title>Upload Result Page</title>\n")
        f.write(b"<body>\n")
        f.write(b"<div style=\"text-align: center;\">")
        f.write(b'<img width=\"400\" src=\"https://images2.imgbox.com/46/aa/qG7wrGvc_o.png\">\n')
        f.write(b"</div>\n")
        f.write(b'<h1><center>Share files in your network</h1>\n')
        f.write(b"<h2><center>Upload Result Page</h2>\n")
        f.write(b"<hr>\n")
        if r:
            f.write(b"<strong><center>Success:</strong>")
        else:
            f.write(b"<strong><center>Failed:</strong>")
        f.write(info.encode('utf-8'))
        f.write(b"<br><a href=\".\">back</a>")
        f.write(b"<hr><small><center>Powered By: Tsunderead - 1 ")
        f.write(b"<a href=\"https://www.youtube.com/watch?v=dQw4w9WgXcQ\">")
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
        print(self.headers)
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
            return False, "Can't find file name"
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
            return False, "No write permission"

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
        
        path = translate_path(self.path)
        if os.path.isdir(path):
            if not self.path.endswith('/'):
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
        print(path)
       
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
        f.write(b'img { display: block; width: 60%; margin-left: auto; margin-right: auto;}\n')
        f.write(b'h1 { text-align: center; margin-bottom: 20px; }\n')
        f.write(b'form { display: flex; flex-direction: column; align-items: center; margin-bottom: 20px; }\n')
        f.write(b'input[type="file"] { margin-bottom: 10px; }\n')
        f.write(b'input[type="submit"] { background-color: #13274D; color: #FFF; padding: 10px; border: none; border-radius: 5px; cursor: pointer; transition: background-color 0.2s ease-in-out; }\n')
        f.write(b'input[type="submit"]:hover { background-color: #3E8E41; }\n')
        f.write(b'table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }\n')
        f.write(b'th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }\n')
        f.write(b'th { background-color: #13274D; color: #FFF; }\n')
        f.write(b'a { color: #000; text-decoration: none; }\n')
        f.write(b'a:hover { text-decoration: underline; }\n')
        f.write(b'</style>\n')
        f.write(b'</head>\n')
        f.write(b'<img width=\"400\" src=\"https://images2.imgbox.com/46/aa/qG7wrGvc_o.png\">\n')
        f.write(b'<h1>Share files</h1>\n')
        f.write(b"<hr>\n")
        f.write(b"<h1>Upload File</h1>\n")
        f.write(b"<form ENCTYPE=\"multipart/form-data\" method=\"post\" style=\"margin-bottom: 1em;\">\n")
        f.write(b"<input name=\"file\" type=\"file\" style=\"margin-right: 0.5em;\" />\n")
        f.write(b"<input type=\"submit\" value=\"Upload File\" class=\"btn btn-primary\" />\n")
        f.write(b"</form>\n")
        f.write(b"<form action=\"/search\" method=\"get\">\n")
        f.write(b"<label for=\"search\">Search:</label>\n")
        f.write(b"<input type=\"search\" id=\"search\" name=\"q\" placeholder=\"Search...\">\n")
        f.write(b"<button type=\"submit\">Go</button>\n")
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
            size = os.stat(fullname).st_size
            modified_time = os.stat(fullname).st_mtime
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
                new_list_1.append((linkname, display_name, size, modified_time))
            else:
                new_list.append((linkname, display_name, size, modified_time))
        # f.write(b"<h1>Files</h1>\n")
        # for linkname, display_name in new_list:
        #     f.write(b'<li><a href="%s">%s</a>\n' % (quote(linkname).encode('utf-8'), escape(display_name).encode('utf-8')))
        f.write(b'<hr>\n<h2>Directories:</h2>\n')
        f.write(b'<table style="width:100%" align="center">\n')
        f.write(b'<tr>\n<th>Name</th>\n<th>Size</th>\n<th>Last Modified</th>\n</tr>\n')
        for linkname, display_name, size, modified_time in new_list_1:
            print(linkname, display_name, size, modified_time)
            f.write(b'<tr>\n')
            f.write(b'<td><a href="%s">%s</a></td>\n' % (quote(linkname).encode('utf-8'), escape(display_name).encode('utf-8')))
            f.write(b'<td>%s</td>\n' % format_size(size).encode('utf-8'))
            f.write(b'<td>%s</td>\n' % format_date(modified_time).encode('utf-8'))
            f.write(b'</tr>\n')
        f.write(b'</table>\n')
        f.write(b'<hr>\n<h2>Files:</h2>\n')
        f.write(b'<table style="width:100%" align="center">\n')
        f.write(b'<tr>\n<th>Name</th>\n<th>Size</th>\n<th>Last Modified</th>\n</tr>\n')
        for linkname, display_name, size, modified_time in new_list:
            print(linkname, display_name, size, modified_time)
            f.write(b'<tr>\n')
            f.write(b'<td><a href="%s">%s</a></td>\n' % (quote(linkname).encode('utf-8'), escape(display_name).encode('utf-8')))
            f.write(b'<td>%s</td>\n' % format_size(size).encode('utf-8'))
            f.write(b'<td>%s</td>\n' % format_date(modified_time).encode('utf-8'))
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
    

        base, ext = posixpath.splitext(path)
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        ext = ext.lower()
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        else:
            return self.extensions_map['']

    if not mimetypes.inited:
        mimetypes.init()  
    extensions_map = mimetypes.types_map.copy()
    extensions_map.update({
        '': 'application/octet-stream',  
        '.py': 'text/plain',
        '.c': 'text/plain',
        '.h': 'text/plain',
    })


def translate_path(path):
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
    exit()

def _argparse():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bind', '-b', metavar='ADDRESS', default='0.0.0.0', help='Specify alternate bind address [default: all interfaces]')
    parser.add_argument('port', action='store', default=8000, type=int, nargs='?', help='Specify alternate port [default: 8000]')
    return parser.parse_args()

def main():
    args = _argparse()
    server_address = (args.bind, args.port)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    server = httpd.socket.getsockname()
    print("sys encoding: " + sys.getdefaultencoding())
    print("Serving http on: " + str(server[0]) + ", port: " + str(server[1]) + " ... (http://" + server[0] + ":" + str(server[1]) + "/)")
    httpd.serve_forever()

if __name__ == '__main__':
    main()
