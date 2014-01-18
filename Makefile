# Makefile

PYTHON=python
CMP=cmp
RSYNC=rsync -av

WORDNET_DIR=./WordNet-3.0
MKDICT=$(PYTHON) mkdict.py
NLCRYPT=$(PYTHON) nlcrypt.py
WEBAPP=$(PYTHON) app.py

DICTS=g2w.cdb w2g.cdb
PUBLIC_URL=tabesugi:public/cgi/root/host/nlcrypt.tabesugi.net/

all: $(DICTS)

clean:
	-$(RM) *.cdb *.pyc
	-$(RM) *.crypt *.out

$(DICTS): $(WORDNET_DIR) index.skip
	$(MKDICT) -s index.skip $(WORDNET_DIR)/dict

test: $(DICTS)
	$(NLCRYPT) abc sample.txt > sample.txt.crypt
	$(NLCRYPT) -R abc sample.txt.crypt > sample.txt.out
	$(CMP) sample.txt sample.txt.out
	$(NLCRYPT) -C abc sample.txt > sample.txt.crypt
	$(NLCRYPT) -C -R abc sample.txt.crypt > sample.txt.out
	$(CMP) sample.txt sample.txt.out

runapp: $(DICTS)
	$(WEBAPP) -s

update: $(DICTS)
	$(RSYNC) app.py nlcrypt.py arcfour.py pycdb.py quotes.txt $(DICTS) $(PUBLIC_URL)
