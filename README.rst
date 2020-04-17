✏️safer: a safer file writer ✏️
-------------------------------

No more partial writes and corruption - ``safer`` writes an entire file
successfully, or leaves it untouched.

``safer.writer()`` and ``safer.printer()`` open a file for writing or
printing as a context manager, but actually write to the file only once
the context exits successfully: if an Exception is raised, then the
original file is left untouched.

Tests run on Python 2.7, and 3.4 through 3.8.

Install ``safer`` from the command line using
`pip <https://pypi.org/project/pip/>`_:

.. code-block:: bash

    pip install safer

Note that ``safer`` uses a temporary file which is moved over the target
file after the context manager exits successfully: at its peak it
requires as much disk space as the old and new files put together.

EXAMPLES
---------

``safer.writer``
======================

.. code-block:: python

   # dangerous
   with open(file, 'w') as fp:
       json.dump(data, fp)    # If this fails, the file is corrupted
   
   # safer
   with safer.writer(file) as fp:
       json.dump(data, fp)    # If this fails, the file is untouched

``safer.printer``
======================

.. code-block:: python

   # dangerous
   with open(file, 'w') as fp:
       for item in items:
           print(item, file=fp)
   
   # Prints a partial file if ``items`` raises an exception while iterating
   # or ``item.__str__()`` raises an exception
   
   # safer
   with safer.printer(file) as print:
       for item in items:
           print(item)
   # Either the whole file is written, or nothing.

API call documentation
-----------------------

``safer.writer(file, mode='w', create_parent=False, delete_failures=True, **kwargs)``

    A context that yields the writable stream returned from open(), but undoes any
    changes to the file if there's an exception.

    Arguments:
      file:
        Path to the file to be opened

      mode:
        Mode string passed to ``open()``

      create_parent:
        If true, create the parent directory of the file if it doesn't exist

      delete_failures:
        If true, the temporary file is deleted if there is an exception

      kwargs:
         Keywords passed to built-in ``open``

``safer.printer(file, mode='w', create_parent=False, delete_failures=True, **kwargs)``

    A context that yields a function that prints to the opened file, but undoes any
    changes to the file if there's an exception.

    Arguments:
      file:
        Path to the file to be opened

      mode:
        Mode string passed to ``open()``

      create_parent:
        If true, create the parent directory of the file if it doesn't exist

      delete_failures:
        If true, the temporary file is deleted if there is an exception

      kwargs:
         Keywords passed to built-in ``open``
