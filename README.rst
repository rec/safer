✏️safer: safe file writer ✏️
-------------------------------

Safely write or print to a file, so that the original file is only
overwritten if the operation completes successfuly.

Works on Python versions 2.7 through 3.8 and likely beyond.

Writes are performed on a temporary file, which is only copied over the
original file after the context completes successfully.  Note that this
temporarily uses as much disk space as the old file and the new file put
together.

EXAMPLES
-----------

``safer.writer``
================

.. code-block:: python

   # dangerous
   with open(config_filename, 'w') as fp:
       json.dump(cfg, fp)  # If this fails, the config file gets broken

   # safer
   with safer.writer(config_filename) as fp:
       json.dump(cfg, fp)  # If this fails, the config file is untouched


``safer.printer``
==================

.. code-block:: python

   with safer.printer(configs_filename) as print:
       for cfg in configs:
           print(json.dumps(cfg))

API call documentation
-----------------------

``safer.writer(file, mode='w', create_parents=False, delete_failures=True, suffix='.tmp', **kwargs)``

    A context that yields a writable stream, like from open(), but undoes any
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
