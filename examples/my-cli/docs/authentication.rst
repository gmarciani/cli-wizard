Authentication
==============

Requests are authenticated with a bearer token: when ``accessToken`` is set, every
request carries an ``Authorization: Bearer <token>`` header. Without it, requests
are sent anonymously. Obtaining the token is up to the API; once you have it,
store it in the profile:

.. code-block:: bash

   my-cli config set --param accessToken --value <token>

or hand it to a single invocation through the environment:

.. code-block:: bash

   MY_CLI_ACCESS_TOKEN=<token> my-cli config show

The profile file is created readable by its owner only, and ``--debug`` output
redacts the token.
