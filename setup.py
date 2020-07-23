from pathlib import Path
from setuptools import setup

_classifiers = [
    'Development Status :: 5 - Production/Stable',
    'Programming Language :: Python :: 3.4',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Topic :: Software Development :: Libraries',
    'Topic :: Utilities',
]
REQUIREMENTS = Path('requirements.txt').read_text().splitlines()


def _version():
    with open('safer.py') as fp:
        line = next(i for i in fp if i.startswith('__version__'))
        return line.strip().split()[-1].strip("'")


if __name__ == '__main__':
    setup(
        name='safer',
        version=_version(),
        author='Tom Ritchford',
        author_email='tom@swirly.com',
        url='https://github.com/rec/safer',
        tests_require=['pytest'],
        py_modules=['safer'],
        description='Safer streams of every type!',
        long_description=open('README.rst').read(),
        license='MIT',
        classifiers=_classifiers,
        keywords=['streams', 'caches'],
        scripts=['safer.py'],
    )
