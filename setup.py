from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='kNUI',
    version='1.0.0',
    packages=find_packages(),
    install_requires=['kivy>=1.9', 'tinyrpc>=0.6.dev'],
    license='MIT',
    author='Kirill Dudkin',
    author_email='apostol3.mv@yandex.ru',
    description='kivy-based UI for nlab',
    long_description=long_description,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'Intended Audience:: Education',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3 :: Only'
    ],
    entry_points={
        'console_scripts': [
            'kNUI = kNUI:run'
        ]
    },
    package_data={
        '': ['*.py', '*.kv', 'libs/garden/garden.contextmenu/*.py', 'libs/garden/garden.contextmenu/*.kv',
             'libs/garden/garden.graph/*.py', 'libs/garden/garden.graph/*.kv'],
    },
    zip_safe=False
)