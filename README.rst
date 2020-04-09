✏️safer ✏️
----------------------

Safely write or print to a file, leaving it unchanged if there's an exception

Writes happen on a temporary file, which is only copied over the original file
when the context completes successfully.

This means that ``safer`` will temporarily use as much disk space as the old
file and the new file put together.


Example:

.. code-block:: python

   import safer

   with safer.open(filename, 'w') as fp:
       for line in source():
          fp.write('this and that')

       if CHANGED_MY_MIND:
           # filename will be unchanged
           raise ValueError

   # or

   with safer.printer(filename) as print:
       print('this', 'and', 'that')
       print('two', 'lines', sep='\n', end='\n---\n')

       if CHANGED_MY_MIND:
           # filename will be unchanged
           raise ValueError
