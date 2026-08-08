Configuration
=============

Configuration uses a YAML file with PascalCase parameter names.
You can reference other parameters with ``#[ParamName]`` syntax
and environment variables with ``${VAR}`` syntax.

References are resolved before generation. A parameter must not reference
itself, directly or through other parameters: a circular reference is
reported as an invalid configuration instead of being expanded. A reference
to a parameter that does not exist is left in the value as written.

See the `examples <https://github.com/gmarciani/cli-wizard/tree/main/examples>`_ for complete configuration examples.

.. autopydantic_model:: cli_wizard.config.schema.Config
