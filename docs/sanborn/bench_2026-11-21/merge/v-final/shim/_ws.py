"""v-final shim for tools/sanborn/_ws.py (21 Nov 2026): the repo's DATA and CODE, but no _mirror(), so importing it never
makes folders under data/sanborn. Used only to run the applied (staged) merge code from merge/v-final."""
DATA = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
CODE = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/'


def data_dir(p):
    raise RuntimeError('v-final shim: data_dir() is not available here')


def code_dir(p):
    raise RuntimeError('v-final shim: code_dir() is not available here')
