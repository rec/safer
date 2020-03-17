✏️safe_writer ✏️
----------------------

A context for writing a file which leaves it unchanged if an exception is
thrown.

Example:

.. code-block:: python

   with safe_writer(filename) as fp:
       for line in source():
           print(line, file=fp)

   # If there's an exception in the block, then `filename` is reverted
   # to its initial state
