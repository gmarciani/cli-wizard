Configuration
=============

Configuration uses a YAML file with PascalCase parameter names.
You can reference other parameters with ``#[ParamName]`` syntax
and environment variables with ``${VAR}`` syntax.

See the `examples <https://github.com/gmarciani/cli-wizard/tree/main/examples>`_ for complete configuration examples.

.. autopydantic_model:: cli_wizard.config.schema.Config
