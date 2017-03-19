from setuptools import setup
import os

datadir = os.path.join('carl','templates')
datafiles = [(d, [os.path.join(d,f) for f in files])
    for d, folders, files in os.walk(datadir)]

setup(name='carl',
      version='0.1.4',
      description='The Headless HAR Crawler',
      long_description='Please see repo for more information:',
      url='XXX',
      author='XXX',
      author_email='XXX',
      license='MIT',
      packages=['carl'],
      setup_requires=[
            'numpy>=1.11.1'],
      install_requires=[
            'argparse==1.2.1',
            'browsermob-proxy==0.7.1',
            'haralyzer==1.4.10',
            'matplotlib==1.5.1',
            'numpy==1.11.1',
            'publicsuffixlist==0.4.1',
            'PyYAML==3.11',
            'requests==2.10.0',
            'selenium==2.53.6',
            'tabulate==0.7.5',
            'tld==0.7.6',
            'wsgiref==0.1.2',
            'Flask==0.12',
            'backports.statistics==0.1.0',
            'xvfbwrapper==0.2.8'],
      entry_points={
          'console_scripts': ['carl=carl.cli:main'],
      },
      data_files = datafiles,
      include_package_data=True,
      zip_safe=False)

