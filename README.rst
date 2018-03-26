Goodconf
========

Define configuration variables and load them from environment or JSON/YAML file.
Also generates initial configuration files and documentation for your defined
configuration.

Installation
------------

``pip install goodconf`` or ``pip install goodconf[yaml]`` if parsing/generating
YAML files is required.

Usage
-----

Examples:

  .. code:: python

    # define a configuration
    import base64
    import os

    from goodconf import GoodConf, Value

    config = GoodConf(description="Configuration for My App")
    config.define_values([
        Value('DEBUG', default=False, help="Toggle debugging."),
        Value('DATABASE_URL', default='postgres://localhost:5432/mydb',
              help="Database connection."),
        Value('SECRET_KEY',
              initial=lambda: base64.b64encode(os.urandom(60)).decode(),
              help="Used for cryptographic signing. "
                   "https://docs.djangoproject.com/en/2.0/ref/settings/#secret-key")
    ])

    # load a configuration
    config.load('myapp.conf')

    # access values as attributes on the GoodConf instance
    config.DATABASE_URL

    # generate an initial config file from the definition
    print(config.generate_yaml())

    # generate documentation for a configuration
    print(config.generate_markdown())

``GoodConf``
^^^^^^^^^^^^

The ``GoodConf`` object can be initialized with the following keyword args:

* ``description`` A plain-text description used as a header when generating
  a configuration file.
* ``file_env_var`` The name of an environment variable which can be used for
  the name of the configuration file to load.
* ``default_files`` If no file is passed to the ``load`` method, try to load a
  configuration from these files in order.

``Value``
^^^^^^^^^

The ``define_values`` method of ``GoodConf`` takes a list of ``Value``
instances. They can be initialized with the following keyword args:

* ``key`` Name of the value used in file or environment variable.
* ``default`` Default value if none is provided.
* ``required`` Loading a config will fail if a value is not provided.
  Defaults to True if no default is provided otherwise False.
* ``initial`` Initial value to use when generating a config
* ``cast_as``  Python type to cast variable as. Defaults to type of default
  (if provided) or str.
* ``help`` Plain-text description of the value.

Django Usage
------------

A helper is provided which monkey-patches Django's management commands to accept
a ``--config`` argument. Replace your ``manage.py`` with the following:

  .. code:: python

    from goodconf.contrib.django import execute_from_command_line_with_config
    # Define your GoodConf in `myproject/__init__.py`
    from myproject import config

    if __name__ == '__main__':
        execute_from_command_line_with_config(config)




Why?
----

I took inspiration from `logan <https://github.com/dcramer/logan>`__ (used by
Sentry) and `derpconf <https://github.com/globocom/derpconf>`__ (used by
Thumbor). Both, however used Python files for configuration. I wanted a safer
format and one that was easier to serialize data into from a configuration
management system.

Environment Variables
^^^^^^^^^^^^^^^^^^^^^

I don't like working with environment variables. First, there are potential
security issues:

1. Accidental leaks via logging or error reporting services.
2. Child process inheritance (see `ImageTragick <https://imagetragick.com/>`__
   for an idea why this could be bad).

Second, in practice on deployment environments, environment variables end up
getting written to a number of files (cron, bash profile, service definitions,
web server config, etc.). Not only is it cumbersome, but also increases the
possibility of leaks via incorrect file permissions.

I prefer a single structured file which is explicitly read by the application.
I also want it to be easy to run my applications on services like Heroku
where environment variables are the preferred configuration method.

This module let's me do things the way I prefer in environments I control, but
still run them with environment variables on environments I don't control with
minimal fuss.
