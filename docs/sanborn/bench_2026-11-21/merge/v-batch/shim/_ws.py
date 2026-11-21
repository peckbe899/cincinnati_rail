"""merge/v-batch shim for tools/sanborn/_ws.py (21 Nov 2026): the repo's DATA and CODE, without _mirror() (which makes
folders under data/sanborn on import). Used only to run the staged code read-only against the repo's data; every
output of those runs is redirected into merge/v-batch."""
DATA = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
CODE = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/'


def data_dir(p):
    raise RuntimeError('merge/v-batch shim: data_dir() is not available')


def code_dir(p):
    raise RuntimeError('merge/v-batch shim: code_dir() is not available')


def ext(p):
    return p
