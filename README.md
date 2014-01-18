NLCrypt: Semantic Cryptography
==============================

NLCrypt is an attempt to create a cryptography system
that doesn't look like a cryptography.

It disguises a secret message as a grammatical (but nonsensical) text
by changing its meanings.

Demo
----

http://nlcrypt.tabesugi.net/

Installation
------------

Prerequisites:

* Python 2.6 or above (Python 3 is not supported).
* WordNet-3.0. http://wordnet.princeton.edu/

How to build:

Unpack the WordNet tarball as `WordNet-3.0` then type this.

    $ make

After this you should see `w2g.cdb` and `g2w.cdb` files.


Command Line Usage
------------------

Syntax:

    $ nlcrypt.py [options] key [file ...]

Options:

 * -c codec ... Specifies a Python codec (default: `utf-8`)
 * -b basedir ... Directory for dictionary files (`w2g.cdb` and `g2w.cdb`)
 * -R ... Reverse the direction (decryption).
 * -C ... Enables CBC mode. It makes the encrypted text even more nonsensical
   (but probably harder to guess the meaning).


Acknowledgements
----------------

 * WordNet is used as a dictionary.
 * Sample texts and quotes are by Bruce Schneier.
