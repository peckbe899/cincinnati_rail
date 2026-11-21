"""FAKE _ws for the verify-outline-nesting end-to-end test: DATA points at e2e/data/sanborn/ (copies of the inputs),
so the patched outlines.py and blocks_noguide.py run unmodified and write only inside this folder."""
import os
_HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(_HERE, '..', '..', 'data', 'sanborn')).replace(os.sep, '/') + '/'
CODE = _HERE.replace(os.sep, '/') + '/'
