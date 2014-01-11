#!/usr/bin/env python
##
##  convdict.py - WordNet Dictionary converter
##

import sys
import re
import os.path
import math
try:
  import cdb
except ImportError:
  import pycdb as cdb

C = 1.0/math.log(2)
def convfreq(n):
  return C*math.log(n)+0.5

pat_ys = re.compile(r'.*[^auieo]y$')
def get_s(s):
  if s.endswith('s'):
    return s[:-1]+'ses'
  elif s.endswith('x'):
    return s[:-1]+'xes'
  elif s.endswith('z'):
    return s[:-1]+'zes'
  elif pat_ys.match(s):
    return s[:-1]+'ies'
  elif s.endswith('ch'):
    return s[:-2]+'ches'
  elif s.endswith('sh'):
    return s[:-2]+'shes'
  elif s.endswith('man'):
    return s[:-3]+'men'
  else:
    return s+'s'

def get_plural(s, exc):
  x = exc.get(s)
  if x: return x
  return get_s(s)

def get_mw(w, f, exc):
  return f(w[0], exc)+'_'+'_'.join(w[1:])

def get_pres3rd(s, exc):
  x = exc.get(s)
  if x: return x
  w = s.split('_')
  if 1 < len(w):
    return get_mw(w, get_pres3rd, exc)
  return get_s(s)

def get_past(s, exc):
  x = exc.get(s)
  if x: return x
  w = s.split('_')
  if 1 < len(w):
    return get_mw(w, get_past, exc)
  if s.endswith('e'):
    return s+'d'
  else:
    return s+'ed'

def get_pastpart(s, exc):
  x = exc.get(s)
  if x: return x
  w = s.split('_')
  if 1 < len(w):
    return get_mw(w, get_pastpart, exc)
  return get_past(s, exc)

def get_gerund(s, exc):
  x = exc.get(s)
  if x: return x
  if s == 'see':
    return 'seeing'
  elif s.endswith('e'):
    return s[:-1]+'ing'
  else:
    return s+'ing'

def get_comparative(s, exc):
  x = exc.get(s)
  if x: return x
  if s.endswith('e'):
    return s+'r'
  elif s.endswith('y'):
    return s+'ier'
  else:
    return s+'er'

def get_superlative(s, exc):
  x = exc.get(s)
  if x: return x
  if s.endswith('e'):
    return s+'st'
  elif s.endswith('y'):
    return s+'iest'
  else:
    return s+'est'


##  DictionaryConverter
##
class DictionaryConverter(object):

  def __init__(self, basedir):
    self.basedir = basedir
    self.read_noun_exc()
    self.read_adj_exc()
    self.read_adv_exc()
    self.read_verb_exc()
    self.read_cntlist()
    self.skip = set()
    self._words = {}
    return

  def _open_file(self, name):
    print >>sys.stderr, 'Reading: %r' % name
    path = os.path.join(self.basedir, name)
    return file(path, 'r')
    
  def _read_exc(self, name):
    fp = self._open_file(name+'.exc')
    for line in fp:
      f = line.strip().split(' ')
      yield (f[1], f[0])
    fp.close()
    return

  def read_noun_exc(self):
    self.nns_exc = {}
    for (s0, s1) in self._read_exc('noun'):
      self.nns_exc[s0] = s1
    return
    
  def read_adj_exc(self):
    self.jjr_exc = {}
    self.jjs_exc = {}
    for (s0, s1) in self._read_exc('adj'):
      if s1.endswith('r'):
        self.jjr_exc[s0] = s1
      elif s1.endswith('t'):
        self.jjs_exc[s0] = s1
    return

  def read_adv_exc(self):
    self.rbr_exc = {}
    self.rbs_exc = {}
    for (s0, s1) in self._read_exc('adv'):
      if s1.endswith('r'):
        self.rbr_exc[s0] = s1
      elif s1.endswith('t'):
        self.rbs_exc[s0] = s1
    return

  pat_past = re.compile(r'[^_]+([deklmtwy]|ang?|on)_')
  pat_pastpart = re.compile(r'[^_]+(ne|ung|en|ain|rn|un|wn)_')
  pat_gerund = re.compile(r'[^_]+ing_')
  def read_verb_exc(self):
    self.vbz_exc = {}
    self.vbd_exc = {}
    self.vbn_exc = {}
    self.vbg_exc = {}
    for (s0, s1) in self._read_exc('verb'):
      if s1.endswith('s'):
        self.vbz_exc[s0] = s1
      elif self.pat_past.match(s1+'_') and not s1.endswith('ne'):
        self.vbd_exc[s0] = s1
      elif self.pat_pastpart.match(s1+'_'):
        self.vbn_exc[s0] = s1
      elif self.pat_gerund.match(s1+'_'):
        self.vbg_exc[s0] = s1
    return

  def read_cntlist(self):
    freq = {}
    fp = self._open_file('cntlist')
    for line in fp:
      f = line.strip().split(' ')
      n = int(f[0])
      f = f[1].split(':')
      (w,_,_) = f[0].partition('%')
      freq[w] = freq.get(w, 0)+n
    fp.close()
    self.weight = {}
    for (w,n) in freq.iteritems():
      self.weight[w] = int(convfreq(n))
    return

  def read_skip(self, fp):
    for line in fp:
      (line,_,_) = line.strip().partition('#')
      if not line: continue
      f = line.split('\t')
      (w, pos) = (f[0], f[1])
      self.skip.add(w.lower())
    return

  pat_word = re.compile(r'^[a-zA-Z]+$')
  def read(self, name):
    fp = self._open_file('index.'+name)
    for line in fp:
      if line.startswith(' '): continue
      f = line.strip().split(' ')
      (w, t) = (f[0], f[1])
      if not self.pat_word.match(w): continue
      if len(w) < 2: continue
      if t == 'a':              # adj
        self._add_pos(w, 'JJ')
        self._add_pos(get_comparative(w, self.jjr_exc), 'JJR')
        self._add_pos(get_superlative(w, self.jjs_exc), 'JJS')
      elif t == 'r':            # adv
        self._add_pos(w, 'RB')
        self._add_pos(get_comparative(w, self.rbr_exc), 'RBR')
        self._add_pos(get_superlative(w, self.rbs_exc), 'RBS')
      elif t == 'n':            # noun
        self._add_pos(w, 'NN')
        self._add_pos(get_plural(w, self.nns_exc), 'NNS')
      elif t == 'v':            # verb
        self._add_pos(w, 'VB')
        self._add_pos(w, 'VBP')
        self._add_pos(get_pres3rd(w, self.vbz_exc), 'VBZ')
        self._add_pos(get_past(w, self.vbd_exc), 'VBD')
        self._add_pos(get_pastpart(w, self.vbn_exc), 'VBN')
        if not '_' in w:
          self._add_pos(get_gerund(w, self.vbg_exc), 'VBG')
      else:
        assert 0, (w, t)
        
    return self

  def _add_pos(self, w, pos):
    w = w.lower()
    if w in self.skip: return
    if w in self._words:
      poss = self._words[w]
    else:
      poss = set()
      self._words[w] = poss
    poss.add(pos)
    return

  def filter_unusual(self, threshold=0.03):
    for (w, poss) in self._words.iteritems():
      t = sum(poss.itervalues())
      if t == 0: continue
      for (pos, f) in poss.items():
        if f and float(f)/t < threshold:
          del poss[pos]
    return

  def write(self, g2wpath, w2gpath):
    print >>sys.stderr, 'Sorting...'
    grp2words = {}
    for (w, poss) in self._words.iteritems():
      n = self.weight.get(w, 0)
      grp = '%s:%d' % ('+'.join(poss), n)
      if grp not in grp2words: grp2words[grp] = []
      grp2words[grp].append(w)
    word2grp = {}
    r = sorted(grp2words.iteritems(), key=lambda (k,v):len(v), reverse=True)
    for (grp, words) in r:
      words.sort()
      for (n,w) in enumerate(words):
        word2grp[w] = (grp, n)
      print >>sys.stderr, ' Group: %r (%d)' % (grp, len(words))
    print >>sys.stderr, 'Writing: %r' % g2wpath
    g2w = cdb.cdbmake(g2wpath, g2wpath+'.tmp')
    for (grp,words) in grp2words.iteritems():
      g2w.add(grp, ' '.join(words))
    g2w.finish()
    print >>sys.stderr, 'Writing: %r' % w2gpath
    w2g = cdb.cdbmake(w2gpath, w2gpath+'.tmp')
    for (word,(grp,n)) in word2grp.iteritems():
      w2g.add(word, '%s,%d' % (grp,n))
    for w in self.skip:
      w2g.add(w, ',0')
    w2g.finish()
    return


# main
def main(argv):
  import getopt
  def usage():
    print 'usage: %s [-O outdir] [-s skip] basedir' % argv[0]
    return 100
  try:
    (opts, args) = getopt.getopt(argv[1:], 'O:s:')
  except getopt.GetoptError:
    return usage()
  outdir = '.'
  skips = []
  for (k, v) in opts:
    if k == '-O': output = v
    elif k == '-s': skips.append(v)

  if not args: return usage()
  basedir = args.pop(0)

  converter = DictionaryConverter(basedir)
  for path in skips:
    fp = file(path, 'r')
    converter.read_skip(fp)
    fp.close()
  converter.read('adj')
  converter.read('adv')
  converter.read('noun')
  converter.read('verb')
  #converter.filter_unusual()
  g2wpath = os.path.join(outdir, 'g2w.cdb')
  w2gpath = os.path.join(outdir, 'w2g.cdb')
  converter.write(g2wpath, w2gpath)
  return
  
if __name__ == '__main__': sys.exit(main(sys.argv))
