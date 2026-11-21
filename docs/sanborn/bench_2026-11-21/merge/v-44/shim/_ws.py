"""v-44 shim for tools/sanborn/_ws.py (21 Nov 2026). Same DATA and CODE as the repo's _ws.py, but no _mirror(), so
importing it never makes folders under data/sanborn. Used only to run the STAGED merge code from the bench folder."""
DATA = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
CODE = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/'


def data_dir(p):
    raise RuntimeError('v-44 shim: data_dir() is not available here')


def code_dir(p):
    raise RuntimeError('v-44 shim: code_dir() is not available here')
