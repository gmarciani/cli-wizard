Configuration
=============

Settings live in named profiles in ``${HOME}/.my-cli/profiles.yaml``. ``my-cli config init``
creates the file with an empty ``default`` profile, and any command creates it on
first run if it is missing. ``my-cli config show`` lists a profile with the
defaults filled in, ``my-cli config set --param <setting> --value <value>``
changes one setting and ``--profile <name>`` on any command selects a profile other
than ``default``. An API command given a profile the file does not hold fails
without sending the request; ``config set --profile <name>`` creates it.

Settings
--------

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Setting
     - Default
     - Effect
   * - ``baseUrl``
     - ``http://localhost:3000``
     - Base URL of the API every command sends its requests to.
   * - ``accessToken``
     - unset
     - Bearer token sent in the ``Authorization`` header of every request.
   * - ``timeout``
     - ``30``
     - Seconds to wait for a response before a request fails.
   * - ``outputFormat``
     - ``json``
     - How a command prints the response: ``json``, ``yaml`` or ``table``. ``--output`` overrides it for one invocation.
   * - ``jsonIndent``
     - ``2``
     - Indentation of the JSON a command prints.
   * - ``tableStyle``
     - ``rounded``
     - Borders of a ``table`` output: ``rounded``, ``ascii``, ``minimal`` or ``markdown``.
   * - ``logLevel``
     - ``INFO``
     - Lowest level of log message shown: DEBUG, INFO, WARNING or ERROR.
   * - ``outputColors``
     - ``true``
     - Whether log messages and errors are coloured.
   * - ``retryMaxAttempts``
     - ``3``
     - Retries of a request that could not connect or got a 429 or 5xx response, after the first attempt. ``0`` sends every request once.
   * - ``retryBackoffFactor``
     - ``0.5``
     - Seconds waited before retry *n*: the factor times 2^(n-1), or what a ``Retry-After`` header asks.

Precedence
----------

Each setting is resolved through four layers, highest precedence first:

#. The command-line flag, for the settings that have one (``--base-url``,
   ``--timeout``, ``--output``).
#. The environment variable ``MY_CLI_<SETTING>``, the setting
   name in upper snake case: ``baseUrl`` reads ``MY_CLI_BASE_URL``.
#. The value stored in the profile selected with ``--profile``, or ``default``.
#. The built-in default.
