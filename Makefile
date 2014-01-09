# Makefile

PYTHON=python
CMP=cmp
WORDNET_DICT=./WordNet-dict
MKDICT=$(PYTHON) mkdict.py
NLCRYPT=$(PYTHON) nlcrypt.py
WEBAPP=$(PYTHON) app.py

all: dicts

clean:
	-$(RM) *.cdb *.pyc
	-$(RM) *.crypt *.out

dicts: g2w.cdb w2g.cdb

g2w.cdb w2g.cdb: $(WORDNET_DICT) index.skip
	$(MKDICT) -s index.skip $(WORDNET_DICT)

test: dicts
	$(NLCRYPT) abc sample.txt > sample.txt.crypt
	$(NLCRYPT) -R abc sample.txt.crypt > sample.txt.out
	$(CMP) sample.txt sample.txt.out
	$(NLCRYPT) -C abc sample.txt > sample.txt.crypt
	$(NLCRYPT) -C -R abc sample.txt.crypt > sample.txt.out
	$(CMP) sample.txt sample.txt.out

runapp: dicts
	$(WEBAPP) -s
