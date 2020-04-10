✏️safer ✏️
------------

Safely write or print to a file, leaving it unchanged if there's an exception.

Works on Python versions 2.7 through 3.8 and likely beyond.

Writes are performed on a temporary file, which is only copied over the
original file after the context completes successfully.  Note that this
temporarily uses as much disk space as the old file and the new file put
together.

EXAMPLES
-----------

``safer.open``
================

.. code-block:: python

   import safer

   with safer.open(filename, 'w') as fp:
       for line in source():
          fp.write('this and that\n')
          fp.write('two-lines!')

       if CHANGED_MY_MIND:
           raise ValueError
           # Contents of `filename` will be unchanged

``safer.printer``
==================

.. code-block:: python

   with safer.printer(filename) as print:
       print('this', 'and', 'that')
       print('two', 'lines', sep='-', end='!')

       if CHANGED_MY_MIND:
           raise ValueError
           # Contents of ``filename`` will be unchanged

API call documentation
-----------------------

``safer.open(file, mode='r', create_parents=False, delete_failures=True, suffix='.tmp')``

    A context that yields a stream like built-in open() would, and undoes any
    changes to the file if there's an exception.

    Arguments:
      file:
        Path to the file to be opened

      mode:
        Mode string passed to built-in ``open``

      create_parents:
        If True, all parent directories are automatically created

      delete_failures:
        Are partial files deleted if the context terminates with an exception?

      suffix:
        File suffix to use for temporary files

``safer.printer(file, mode='w', create_parents=False, delete_failures=True, suffix='.tmp')``

    A context that yields a print function that prints to the file,
    but which undoes any changes to the file if there's an exception.

    Arguments:
      file:
        Path to the file to be opened

      mode:
        Mode string passed to built-in ``open``

      create_parents:
        If True, all parent directories are automatically created

      delete_failures:
        Are partial files deleted if the context terminates with an exception?

      suffix:
        File suffix to use for temporary files
