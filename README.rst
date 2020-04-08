✏️safer ✏️
----------------------

Safely write or print to a file, leaving it unchanged if something goes wrong.

Example:

.. code-block:: python

   import safer

   with safer.writer(filename) as fp:
       for line in source():
          fp.write('this and that')

   with safer.printer(filename) as print:
       print('this', 'and', 'that')
       print('two', 'lines', sep='\n')
       # ...

Writes occur on a temporary file, which is only copied over the original file
when the block completes successfully, so ``safer`` will temporarily use
as much disk space as the old file and the new file put together.

This is great for writing any files which you don't want to get partially
overwritten if something goes wrong in the writing process.
