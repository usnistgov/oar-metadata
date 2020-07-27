import glob, os, shutil
from distutils.core import setup
from distutils.command.build import build as _build

def set_version():
    try:
        pkgdir = os.environ.get('PACKAGE_DIR', '..')
        setver = os.path.join(pkgdir,'scripts','setversion.sh')
        if os.path.exists(setver):
            if not os.access(setver, os.X_OK):
                setver = "bash "+setver
            excode = os.system(setver)
            if excode != 0:
                raise RuntimeError("setversion.sh encountered an error")
    except Exception as ex:
        print("Unable to set build version: " + str(ex))

def get_version():
    out = "dev"
    pkgdir = os.environ.get('PACKAGE_DIR', '..')
    versfile = os.path.join(pkgdir, 'VERSION')
    if not os.path.exists(versfile):
        set_version()
    if os.path.exists(versfile):
        with open(versfile) as fd:
            parts = fd.readline().split()
        if len(parts) > 0:
            out = parts[-1]
    else:
        out = "(unknown)"
    return out

def write_version_mod(version):
    nistoardir = 'nistoar'
    print("looking in nistoar")
    for pkg in [f for f in os.listdir(nistoardir) \
                  if not f.startswith('_') and not f.startswith('.')
                     and os.path.isdir(os.path.join(nistoardir, f))]:
        print("setting version for nistoar."+pkg)
        versmodf = os.path.join(nistoardir, pkg, "version.py")
        with open(versmodf, 'w') as fd:
            fd.write('"""')
            fd.write("""
An identification of the subsystem version.  Note that this module file gets 
(over-) written by the build process.  
""")
            fd.write('"""\n\n')
            fd.write('__version__ = "')
            fd.write(version)
            fd.write('"\n')

class build(_build):

    def run(self):
        write_version_mod(get_version())
        _build.run(self)

setup(name='nistoar',
      version='0.1',
      description="the NERDm metadata support for nistoar",
      author="Ray Plante",
      author_email="raymond.plante@nist.gov",
      url='https://github.com/usnistgov/oar-metadata',
      packages=['nistoar', 'nistoar.nerdm', 'nistoar.nerdm.convert', 
                'nistoar.id', 'nistoar.doi', 'nistoar.doi.resolving',
                'nistoar.rmm', 'nistoar.rmm.mongo', 'nistoar.rmm.ingest'],
      scripts=[os.path.join("..","scripts",s) for s in 
               ["pdl2resources.py", "ingest-nerdm-res.py",
                "ingest-field-info.py", "ingest-taxonomy.py",
                "ingest-uwsgi.py" ]],
      cmdclass={'build': build}
)

