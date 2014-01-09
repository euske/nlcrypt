#!/usr/bin/env python
##
##  Whabapp - A Web application microframework
##
##  usage: $ python app.py -s localhost 8080
##
import sys
import re
import cgi

STATUS_CODE = {
    100: 'Continue',
    101: 'Switching Protocols',
    200: 'OK',
    201: 'Created',
    202: 'Accepted',
    203: 'Non-Authoritative Information',
    204: 'No Content',
    205: 'Reset Content',
    206: 'Partial Content',
    300: 'Multiple Choices',
    301: 'Moved Permanently',
    302: 'Found',
    303: 'See Other',
    304: 'Not Modified',
    305: 'Use Proxy',
    306: 'Reserved',
    307: 'Temporary Redirect',
    400: 'Bad Request',
    401: 'Unauthorized',
    402: 'Payment Required',
    403: 'Forbidden',
    404: 'Not Found',
    405: 'Method Not Allowed',
    406: 'Not Acceptable',
    407: 'Proxy Authentication Required',
    408: 'Request Timeout',
    409: 'Conflict',
    410: 'Gone',
    411: 'Length Required',
    412: 'Precondition Failed',
    413: 'Request Entity Too Large',
    414: 'Request-URI Too Long',
    415: 'Unsupported Media Type',
    416: 'Requested Range Not Satisfiable',
    417: 'Expectation Failed',
    500: 'Internal Server Error',
    501: 'Not Implemented',
    502: 'Bad Gateway',
    503: 'Service Unavailable',
    504: 'Gateway Timeout',
    505: 'HTTP Version Not Supported',
    }

# quote HTML metacharacters.
def q(s):
    assert isinstance(s, basestring), s
    return (s.
            replace('&','&amp;').
            replace('>','&gt;').
            replace('<','&lt;').
            replace('"','&#34;').
            replace("'",'&#39;'))

# encode as a URL.
URLENC = re.compile(r'[^a-zA-Z0-9_.-=]')
def urlenc(url, codec='utf-8'):
    def f(m):
        return '%%%02X' % ord(m.group(0))
    return URLENC.sub(f, url.encode(codec))

# remove redundant spaces.
RMSP = re.compile(r'\s+', re.U)
def rmsp(s):
    return RMSP.sub(' ', s.strip())

# merge two dictionaries.
def mergedict(d1, d2):
    d1 = d1.copy()
    d1.update(d2)
    return d1

# iterable
def iterable(obj):
    return hasattr(obj, '__iter__')

# closable
def closable(obj):
    return hasattr(obj, 'close')


##  Template
##
class Template(object):

    debug = 0

    def __init__(self, *args, **kwargs):
        if '_copyfrom' in kwargs:
            _copyfrom = kwargs['_copyfrom']
            objs = _copyfrom.objs
            kwargs = mergedict(_copyfrom.kwargs, kwargs)
        else:
            objs = []
            for line in args:
                i0 = 0
                for m in self._VARIABLE.finditer(line):
                    objs.append(line[i0:m.start(0)])
                    x = m.group(1)
                    if x == '$':
                        objs.append(x)
                    else:
                        objs.append(self.Variable(x[0], x[1:-1]))
                    i0 = m.end(0)
                objs.append(line[i0:])
        self.objs = objs
        self.kwargs = kwargs
        return

    def __call__(self, **kwargs):
        return self.__class__(_copyfrom=self, **kwargs)

    def __iter__(self):
        return self.render()

    def __repr__(self):
        return '<Template %r>' % self.objs

    def __str__(self):
        return ''.join(self)

    @classmethod
    def load(klass, lines, **kwargs):
        template = klass(*lines, **kwargs)
        if closable(lines):
            lines.close()
        return template
    
    def render(self, codec='utf-8', **kwargs):
        kwargs = mergedict(self.kwargs, kwargs)
        def render1(value, quote=False):
            if value is None:
                pass
            elif isinstance(value, Template):
                if quote:
                    if 2 <= self.debug:
                        raise ValueError
                    elif self.debug:
                        yield '[ERROR: Template in a quoted context]'
                else:
                    for x in value.render(codec=codec, **kwargs):
                        yield x
            elif isinstance(value, dict):
                if 2 <= self.debug:
                    raise ValueError
                elif self.debug:
                    yield '[ERROR: Dictionary included]'
            elif isinstance(value, basestring):
                if quote:
                    yield q(value)
                else:
                    yield value
            elif callable(value):
                for x in render1(value(**kwargs), quote=quote):
                    yield x
            elif iterable(value):
                for obj1 in value:
                    for x in render1(obj1, quote=quote):
                        yield x
            else:
                if quote:
                    yield q(unicode(value))
                else:
                    if 2 <= self.debug:
                        raise ValueError
                    elif self.debug:
                        yield '[ERROR: Non-string object in a non-quoted context]'
            return
        for obj in self.objs:
            if isinstance(obj, self.Variable):
                k = obj.name
                if k in kwargs:
                    value = kwargs[k]
                elif k in self.kwargs:
                    value = self.kwargs[k]
                else:
                    yield '[notfound:%s]' % k
                    continue
                if obj.type == '(':
                    for x in render1(value, quote=True):
                        yield x
                    continue
                elif obj.type == '[':
                    yield urlenc(value)
                    continue
            else:
                value = obj
            for x in render1(value):
                yield x
        return

    _VARIABLE = re.compile(r'\$(\(\w+\)|\[\w+\]|<\w+>)')
    
    class Variable(object):
        
        def __init__(self, type, name):
            self.type = type
            self.name = name
            return
        
        def __repr__(self):
            if self.type == '(':
                return '$(%s)' % self.name
            elif self.type == '[':
                return '$[%s]' % self.name
            else:
                return '$<%s>' % self.name
    

##  Router
##
class Router(object):
    
    def __init__(self, method, regex, func):
        self.method = method
        self.regex = regex
        self.func = func
        return

    @staticmethod
    def make_wrapper(method, pat):
        regex = re.compile('^'+pat+'$')
        def wrapper(func):
            return Router(method, regex, func)
        return wrapper

def GET(pat): return Router.make_wrapper('GET', pat)
def POST(pat): return Router.make_wrapper('POST', pat)


##  Response
##
class Response(object):

    def __init__(self, status_code=200, content_type='text/html', **kwargs):
        self.status_code = status_code
        self.headers = [('Content-Type', content_type)]+kwargs.items()
        return

    def add_header(self, k, v):
        self.headers.append((k, v))
        return

class Redirect(Response):

    def __init__(self, location):
        Response.__init__(self, 302, Location=location)
        return

class NotFound(Response):

    def __init__(self):
        Response.__init__(self, 404)
        return

class InternalError(Response):

    def __init__(self):
        Response.__init__(self, 500)
        return


##  WebApp
##
class WebApp(object):

    debug = 0
    codec = 'utf-8'
    
    def run(self, environ, start_response):
        method = environ.get('REQUEST_METHOD', 'GET')
        path = environ.get('PATH_INFO', '/')
        fp = environ.get('wsgi.input')
        fields = cgi.FieldStorage(fp=fp, environ=environ)
        result = None
        for attr in dir(self):
            router = getattr(self, attr)
            if not isinstance(router, Router): continue
            if router.method != method: continue
            m = router.regex.match(path)
            if m is None: continue
            params = m.groupdict().copy()
            params['_path'] = path
            params['_fields'] = fields
            params['_environ'] = environ
            code = router.func.func_code
            args = code.co_varnames[:code.co_argcount]
            kwargs = {}
            for k in args[1:]:
                if k in fields:
                    kwargs[k] = fields.getvalue(k)
                elif k in params:
                    kwargs[k] = params[k]
            try:
                result = router.func(self, **kwargs)
            except TypeError:
                if 2 <= self.debug:
                    raise
                elif self.debug:
                    result = [InternalError()]
            break
        if result is None:
            result = self.get_default(path, fields, environ)
        def f(obj):
            if isinstance(obj, Response):
                status = '%d %s' % (obj.status_code, STATUS_CODE[obj.status_code])
                start_response(status, obj.headers)
            elif isinstance(obj, Template):
                for x in obj.render(codec=self.codec):
                    if isinstance(x, unicode):
                        x = x.encode(self.codec)
                    yield x
            elif iterable(obj):
                for x in obj:
                    for y in f(x):
                        yield y
            else:
                if isinstance(obj, unicode):
                    obj = obj.encode(self.codec)
                yield obj
        return f(result)

    def get_default(self, path, fields, environ):
        return [NotFound(), '<html><body>not found</body></html>']


# run_server
def run_server(host, port, app):
    from wsgiref.simple_server import make_server
    print >>sys.stderr, 'Serving on %r port %d...' % (host, port)
    httpd = make_server(host, port, app.run)
    httpd.serve_forever()

# run_cgi
def run_cgi(app):
    from wsgiref.handlers import CGIHandler
    CGIHandler().run(app.run)

# run_httpcgi: for cgi-httpd
def run_httpcgi(app):
    from wsgiref.handlers import CGIHandler
    class HTTPCGIHandler(CGIHandler):
        def start_response(self, status, headers, exc_info=None):
            protocol = self.environ.get('SERVER_PROTOCOL', 'HTTP/1.0')
            sys.stdout.write('%s %s\r\n' % (protocol, status))
            return CGIHandler.start_response(self, status, headers, exc_info=exc_info)
    HTTPCGIHandler().run(app.run)

# main
def main(app, argv):
    import getopt
    def usage():
        print 'usage: %s [-d] [-s] [host [port]]' % argv[0]
        return 100
    try:
        (opts, args) = getopt.getopt(argv[1:], 'ds')
    except getopt.GetoptError:
        return usage()
    server = False
    debug = 0
    for (k, v) in opts:
        if k == '-d': debug += 1
        elif k == '-s': server = True
    Template.debug = debug
    WebApp.debug = debug
    if server:
        host = ''
        port = 8080
        if args:
            host = args.pop(0)
        if args:
            port = int(args.pop(0))
        run_server(host, port, app)
    else:
        run_httpcgi(app)
    return


##  NLCryptApp
##
from nlcrypt import NLCrypt
class NLCryptHTML(NLCrypt):

    def __init__(self, key, reverse=False, cbc=False, basedir='.', debug=0):
        NLCrypt.__init__(self, key, reverse=reverse, cbc=cbc,
                         basedir=basedir, debug=debug)
        self.logs = []
        return
        
    def _debug_ignore(self, w):
        return
        
    def _debug_word(self, w0,n0, grp, w1,n1):
        if self.debug:
            self.logs.append(
                Template(
                    '<span class=info>Word</span>($(grp)): '
                    '$(w0)($(n0)) &rarr; $(w1)($(n1))<br>\n',
                    grp=grp, w0=w0, n0=n0, w1=w1, n1=n1))
        return
        
    def _debug_unknown(self, w0, w1):
        if self.debug:
            self.logs.append(
                Template(
                    '<span class=info>Letter</span>: '
                    '$(w0) &rarr; $(w1)<br>\n',
                    w0=w0, w1=w1))
        return

class NLCryptApp(WebApp):

    MAXCHARS = 2000
    OPTIONS = (('eb', 'Encryption'),
               ('db', 'Decryption'),
               ('ec', 'Encryption (CBC)'),
               ('dc', 'Decryption (CBC)'))

    @GET('/')
    def index(self):
        yield Response()
        yield self.header()
        yield self.form()
        yield self.footer()
        return
    
    @POST('/crypt')
    def crypt(self, s=u'', k=u'', t=u'', d=u''):
        yield Response()
        yield self.header()
        options = dict(self.OPTIONS)
        decrypt = t.startswith('d')
        cbc = t.endswith('c')
        debug = bool(d)
        crypt = None
        if not k:
            yield Template(
                '<div class=error>Error: Provide an encryption key.</div>\n')
        elif t not in options:
            yield Template(
                '<div class=error>Error: Invalid option.</div>\n')
        elif s:
            key = k.encode('utf-8')
            crypt = NLCryptHTML(key, reverse=decrypt, cbc=cbc, debug=debug)
            if self.MAXCHARS < len(s):
                s = s[:self.MAXCHARS]
                yield Template(
                    '<div class=error>Notice: Text is truncated to 2,000 letters.</div>\n')
            s = crypt.feed(s)
            yield Template(
                '<div class=result>Result ($(opt)):</div>\n'
                '<blockquote>$(s)</blockquote>\n',
                opt=options[t], s=s)
        yield self.form(s=s, k=k, decrypt=(not decrypt), cbc=cbc, debug=debug)
        if crypt is not None and crypt.logs:
            yield Template('<div class=debug>Debug Information:</div>\n')
            yield crypt.logs
        yield self.footer()
        return

    def header(self):
        return Template(
            '<html><head>\n'
            '<title>NLCrypt : Natural Language Cryptography</title>\n'
            '</head><body>\n'
            '<h1>NLCrypt : Natural Language Cryptography</h1>\n'
            )

    def footer(self):
        return Template(
            '<hr>\n'
            '</body></html>\n')

    def form(self,
             s=u'Text to encrypt/decrypt.',
             k=u'',
             decrypt=False, cbc=False, debug=False):
        yield Template(
            '<form method="POST" action="/crypt">\n'
            '<div><textarea name="s" cols="80" rows="8">$(s)</textarea></div>\n'
            '<div><select name="t">',
            s=s)
        for (t,v) in self.OPTIONS:
            selected = ('selected'
                        if (decrypt == t.startswith('d') and cbc == t.endswith('c'))
                        else '')
            yield Template('<option value="$(t)" $(selected)>$(v)</option>',
                           selected=selected, t=t, v=v)
        checked = ('checked' if debug else '')
        yield Template(
            '</select> &nbsp;'
            'with Key <input name="k" size="20" value="$(k)"> &nbsp;'
            '<input type=submit value="Submit"> &nbsp;'
            '<input type=reset> &nbsp;'
            '<label for="debug">'
            '<input id="debug" name="d" type=checkbox $(checked)> Debug mode'
            '</label></div>\n',
            '</form>\n',
            checked=checked, k=k)
        return

if __name__ == '__main__': sys.exit(main(NLCryptApp(), sys.argv))
