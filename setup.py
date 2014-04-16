from distutils.core import setup

setup(name='brawl4d',
    version='0.1',
    description='Interactive four-dimensional (space and time) data browsing using the stormdrain data processing pipeline.',
    author='Eric Bruning',
    author_email='eric.bruning@gmail.com',
    url='https://github.com/deeplycloudy/brawl4d/',
    package_dir={'brawl4d': ''}, # wouldn't be necessary if we reorganized to traditional package layout with brawl4d at the same directory level as the setup.py script.
    packages=['brawl4d', 
        'brawl4d.LMA', 
    )