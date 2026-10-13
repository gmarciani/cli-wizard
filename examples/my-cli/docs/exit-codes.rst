Exit codes
==========

Every command prints one JSON document on stdout: the response on success, or
on failure an error object a script can parse, with the error's type, its
message and the exit code the command exits with:

.. code-block:: json

   {
     "error": {
       "type": "ClientError",
       "message": "404 Not Found\n  Greeting not found",
       "exitCode": 4
     }
   }

Logs go to stderr. The exit code names the class of what went wrong, so a
script can branch on it or retry only what is worth retrying.

.. list-table::
   :header-rows: 1
   :widths: 10 90

   * - Code
     - Meaning
   * - 0
     - The command succeeded.
   * - 1
     - Any other failure.
   * - 2
     - Usage error: an unknown command, a missing option or a bad value.
   * - 3
     - No response: connection refused, unknown host, timeout or TLS failure.
   * - 4
     - The API rejected the request, with a 4xx, or a ``--header`` is not ``Name: value``.
   * - 5
     - The API failed, with a 5xx.
   * - 6
     - The response body is not valid JSON.
   * - 7
     - The profile file cannot be read or written, the selected profile is not in it, or a configured file does not exist.
   * - 8
     - A bug in the CLI; ``--debug`` logs its traceback.
