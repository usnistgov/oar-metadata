import glob, os, shutil
from distutils.core import setup

setup(name='nistoar',
      version='0.1',
      description="the NERDm metadata support for nistoar",
      author="Ray Plante",
      author_email="raymond.plante@nist.gov",
      url='https://github.com/usnistgov/oar-metadata',
      packages=['nistoar', 'nistoar.nerdm', 'nistoar.id',
                'nistoar.rmm', 'nistoar.rmm.mongo'],
      scripts=[os.path.join("..","scripts",s) for s in 
               ["pdl2resources.py", "ingest-nerdm-res.py",
                "ingest-field-info.py", "ingest-taxonomy.py" ]]
)

