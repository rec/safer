✏️safer: a safer file writer ✏️
-------------------------------

Safely write or print to a file in a context where the original file is
only overwritten if the context completes without throwing an exception.

Tested on Python versions 2.7, and 3.4 through 3.8.

Install ``safer`` from the command line using
`pip <https://pypi.org/project/pip/>`_:

.. code-block:: bash

    pip3 install safer

NOTE: ``safer`` uses a temporary file which is copied over the original
file after the context completes successfully, so it temporarily uses as
much disk space as the old file and the new file put together.

EXAMPLES
---------

``safer.writer``
================

.. code-block:: python

   # dangerous
   with open(config_filename, 'w') as fp:
       json.dump(cfg, fp)    # If this fails, the config file is corrupted
   
   # safer
   with safer.writer(config_filename) as fp:
       json.dump(cfg, fp)    # If this fails, the config file is untouched

``safer.printer``
================

.. code-block:: python

   # dangerous
   with open(configs_filename, 'w') as fp:
       for cfg in configs:
           print(json.dumps(cfg), file=fp)  # Corrupts the file on failure
   
   # safer
   with safer.printer(configs_filename) as print:
       for cfg in configs:
           print(json.dumps(cfg))          # Cannot corrupt the file

API call documentation
-----------------------

``safer.writer(file, mode='w', create_parents=False, delete_failures=True, suffix='.tmp', **kwargs)``

    A context that yields the writable stream returned from open(), but undoes any
    changes to the file if there's an exception.

    Arguments:
      file:
        Path to the file to be opened

      mode:
        Mode string passed to ``open()``

      create_parents:
        If True, all parent directories are automatically created

      delete_failures:
        Are partial files deleted if the context terminates with an exception?

      suffix:
        File suffix to use for temporary files

      kwargs:
         Keywords passed to built-in ``open``

``safer.printer(file, mode='w', create_parents=False, delete_failures=True, suffix='.tmp', **kwargs)``

    A context that yields a function that prints to the opened file, but undoes any
    changes to the file if there's an exception.

    Arguments:
      file:
        Path to the file to be opened

      mode:
        Mode string passed to ``open()``

      create_parents:
        If True, all parent directories are automatically created

      delete_failures:
        Are partial files deleted if the context terminates with an exception?

      suffix:
        File suffix to use for temporary files

      kwargs:
         Keywords passed to built-in ``open``
