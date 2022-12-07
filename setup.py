from setuptools import setup

import safer

_classifiers = [
    'Development Status :: 5 - Production/Stable',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Programming Language :: Python :: 3.9',
    'Programming Language :: Python :: 3.10',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Topic :: Software Development :: Libraries',
    'Topic :: Utilities',
]

if __name__ == '__main__':
    setup(
        name='safer',
        version=safer.__version__,
        author='Tom Ritchford',
        author_email='tom@swirly.com',
        url='https://github.com/rec/safer',
        tests_require=['pytest'],
        py_modules=['safer'],
        description='A safer file opener',
        long_description=open('README.rst', encoding='utf-8').read(),
        license='MIT',
        classifiers=_classifiers,
        keywords=['testing', 'modules'],
    )
