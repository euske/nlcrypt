#!/usr/bin/env python
##
##  nlcrypt.py - Semantic Cryptography
##
##  Usage:
##    $ nlcrypt.py [options] key [file ...]
##
##  Options:
##    -c codec          Specifies a Python codec (default: utf-8)
##    -b basedir        Directory for dictionary files (w2g.cdb and g2w.cdb)
##    -R                Reverse the direction (decryption).
##    -C                Enables CBC mode.
##
import re
import sys
import hmac
import struct
import os.path
import arcfour
try:
    import cdb
except ImportError:
    import pycdb as cdb

def adjust_caps(w1,w2):
    if w1[0].isupper() and w1[-1].isupper():
        # ALL CAPS.
        return w2.upper()
    w = u''
    for (i,c) in enumerate(w2):
        if i < len(w1) and w1[i].isupper():
            c = c.upper()
        w += c
    return w

def segment_text(pat, s):
    i0 = 0
    for m in pat.finditer(s):
        i1 = m.start(0)
        if i0 < i1:
            yield (False, s[i0:i1])
        yield (True, m.group(0))
        i0 = m.end(0)
    if i0 < len(s):
        yield (False, s[i0:])
    return

def is_voweled(w):
    w = w.lower()
    return (w[0] in 'aeiou')

class NLCrypt(object):
    
    GROUP2CHARS = (
        u'0123456789',
        u'aeiou',
        u'AEIOU',
        u'bcdfghjklmnpqrstvwxyz',
        u'BCDFGHJKLMNPQRSTVWXYZ',
    )
    CHAR2GROUP = {}
    for (grp,chars) in enumerate(GROUP2CHARS):
        for (n,c) in enumerate(chars):
            CHAR2GROUP[c] = (grp,n)

    def __init__(self, key, reverse=False, cbc=False, basedir='.', debug=0):
        self._hmac = hmac.HMAC(key) # Defaults to MD5.
        self.reverse = reverse
        self.cbc = cbc
        self.debug = debug
        self.WORD2GROUP = cdb.init(os.path.join(basedir, 'w2g.cdb'))
        self.GROUP2WORDS = cdb.init(os.path.join(basedir, 'g2w.cdb'))
        self._a0 = None
        self._a1 = None
        return

    def _crypt(self, i0, grp, n):
        assert i0 < n
        k = self._hmac.digest()
        v = struct.pack('=I', n)+grp
        v = arcfour.Arcfour(k).process(v)
        if self.cbc:
            self._hmac.update(v)
        (x,) = struct.unpack('=I', v[:4])
        if self.reverse:
            i1 = (i0-x) % n
        else:
            i1 = (i0+x) % n
        return i1

    def crypt_letter(self, c0):
        if c0 in self.CHAR2GROUP:
            (grp,i0) = self.CHAR2GROUP[c0]
            chars = self.GROUP2CHARS[grp]
            i1 = self._crypt(i0, str(grp), len(chars))
            c1 = chars[i1]
        else:
            c1 = c0
        return c1

    def _word2group(self, w):
        (grp,_,n) = self.WORD2GROUP[w].partition(',')
        return (grp, int(n))
    
    _group2words_cache = {}
    def _group2words(self, grp):
        if grp in self._group2words_cache:
            words = self._group2words_cache
        else:
            words = self.GROUP2WORDS[grp].decode('utf-8').split(' ')
            self._group2words_cache = words
        return words

    IGNORE = re.compile(r'^(\w\W)+$', re.U)
    
    def crypt_word(self, w0, force=False):
        w1 = None
        k = w0.lower().replace(u'\u2019',u",")
        if self.IGNORE.match(k):
            w1 = w0
            self._debug_ignore(w0)
        elif k in self.WORD2GROUP:
            (grp,i0) = self._word2group(k)
            if grp:
                words = self._group2words(grp)
                i1 = self._crypt(i0, grp, len(words))
                w1 = words[i1]
                w1 = adjust_caps(w0, w1)
                self._debug_word(w0,i0, grp, w1,i1)
            else:
                w1 = w0
                self._debug_ignore(w0)
        elif force:
            w1 = u''.join(map(self.crypt_letter, w0))
            self._debug_unknown(w0, w1)
        return w1

    WORD = re.compile(ur'[-\u2019\'\-\.\w]+', re.U)
    PART = re.compile(ur'\d+|\w+|\'\w+', re.U)

    def _handle_a(self, w):
        if self._a0 is None and w.lower() in ('a', 'an'):
            self._a0 = w
            self._a1 = u''
            return True
        return False
        
    def _put_space(self, s):
        if self._a0 is not None:
            self._a1 += s
        else:
            self._output += s
        return
        
    def _put_word(self, w):
        if self._a0 is not None:
            a = 'a'
            if is_voweled(w):
                a = 'an'
            self._output += adjust_caps(self._a0, a)
            self._output += self._a1
            self._a0 = None
        self._output += w
        return

    def feed(self, s):
        self._output = u''
        for (isword,w0) in segment_text(self.WORD, s):
            if not isword:
                self._put_space(w0)
                continue
            if self._handle_a(w0):
                continue
            w1 = self.crypt_word(w0)
            if w1 is not None:
                self._put_word(w1)
                continue
            for (ispart,p0) in segment_text(self.PART, w0):
                if not ispart:
                    self._put_space(p0)
                    continue
                p1 = self.crypt_word(p0, force=True)
                self._put_word(p1 or p0)
        return self._output

    def _debug_ignore(self, w):
        if self.debug:
            print 'ignore: %r' % w
        return
    def _debug_word(self, w0,i0, grp, w1,i1):
        if self.debug:
            print 'word: %s(%s,%s) -> %s(%s,%s)' % (w0,grp,i0,w1,grp,i1)
        return
    def _debug_unknown(self, w0, w1):
        if self.debug:
            print 'unknown: %s -> %s' % (w0,w1)
        return

def main(argv):
    import getopt
    import fileinput
    def usage():
        print 'usage: %s [-d] [-c codec] [-b basedir] [-C] [-R] key [file ...]' % argv[0]
        return 100
    try:
        (opts, args) = getopt.getopt(argv[1:], 'dc:b:CR')
    except getopt.GetoptError:
        return usage()
    debug = 0
    codec = 'utf-8'
    basedir = '.'
    cbc = False
    reverse = False
    for (k, v) in opts:
        if k == '-d': debug += 1
        elif k == '-c': codec = v
        elif k == '-b': basedir = v
        elif k == '-C': cbc = True
        elif k == '-R': reverse = True
    if not args: return usage()
    #
    key = args.pop(0)
    nlcrypt = NLCrypt(key, reverse=reverse, cbc=cbc, basedir=basedir, debug=debug)
    for line in fileinput.input(args):
        text = line.decode(codec, 'ignore')
        text = nlcrypt.feed(text)
        sys.stdout.write(text.encode(codec, 'ignore'))
    return 0

if __name__ == '__main__': sys.exit(main(sys.argv))
