from setuptools import setup
import safe_writer

_classifiers = [
    'Development Status :: 4 - Beta',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Topic :: Software Development :: Libraries',
    'Topic :: Utilities',
]

if __name__ == '__main__':
    setup(
        name='safe_writer',
        version=safe_writer.__version__,
        author='Tom Ritchford',
        author_email='tom@swirly.com',
        url='https://github.com/rec/safe_writer',
        tests_require=['pytest'],
        py_modules=['safe_writer'],
        description='Try to import all modules below a given root',
        long_description=open('README.rst').read(),
        license='MIT',
        classifiers=_classifiers,
        keywords=['testing', 'modules'],
        scripts=['safe_writer.py'],
    )
