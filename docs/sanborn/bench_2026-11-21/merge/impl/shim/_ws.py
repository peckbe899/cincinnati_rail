"""merge/impl shim for tools/sanborn/_ws.py, used ONLY to run the staged code from the bench folder (21 Nov 2026).

The staged files live in merge/staged/tools/sanborn/unet/, where no _ws.py sits beside them. Put this folder on
PYTHONPATH and `import _ws` gives the same DATA and CODE as the repo's _ws.py, without its _mirror() (which makes
folders under data/sanborn on import), so a staged run cannot create anything in the repo.
"""
DATA = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
CODE = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/'


def data_dir(p):
    raise RuntimeError('merge/impl shim: data_dir() is not available in bench runs')
