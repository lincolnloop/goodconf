Goodconf
========

.. image:: https://img.shields.io/travis/lincolnloop/goodconf.svg
    :target: https://travis-ci.org/lincolnloop/goodconf

.. image:: https://img.shields.io/codecov/c/github/lincolnloop/goodconf.svg
    :target: https://codecov.io/gh/lincolnloop/goodconf

.. image:: https://img.shields.io/pypi/v/goodconf.svg
    :target: https://pypi.python.org/pypi/goodconf

.. image:: https://img.shields.io/pypi/pyversions/goodconf.svg
    :target: https://pypi.python.org/pypi/goodconf

Define configuration variables and load them from environment or JSON/YAML
file. Also generates initial configuration files and documentation for your
defined configuration.


Installation
------------

``pip install goodconf`` or ``pip install goodconf[yaml]`` if
parsing/generating YAML files is required.


Quick Start
-----------

Let's use configurable Django settings as an example.

First, create a ``conf.py`` file in your project's directory, next to
``settings.py``:

.. code:: python

    import base64
    import os

    from goodconf import GoodConf, Value

    class Config(GoodConf):
        "Configuration for My App"
        DEBUG = Value(default=False, help="Toggle debugging.")
        DATABASE_URL = Value(
            default='postgres://localhost:5432/mydb',
            help="Database connection.")
        SECRET_KEY = Value(
            initial=lambda: base64.b64encode(os.urandom(60)).decode(),
            help="Used for cryptographic signing. "
            "https://docs.djangoproject.com/en/2.0/ref/settings/#secret-key")

    config = Config(
        default_files=["/etc/myproject/myproject.yaml", "myproject.yaml"]
    )

Next, use the config in your ``settings.py`` file:

.. code:: python

    import dj_database_url
    from .conf import config

    config.load()

    DEBUG = config.DEBUG
    SECRET_KEY = config.SECRET_KEY
    DATABASES = {"default": dj_database_url.parse(config.DATABASE_URL)}

In your initial developer installation instructions, give some advice such as:

.. code:: shell

    python -c "import myproject; print(myproject.conf.config.generate_yaml(DEBUG=True))" > myproject.yaml

Better yet, make it a function and `entry point <https://setuptools.readthedocs.io/en/latest/setuptools.html#automatic-script-creation>`__ so you can install
your project and run something like ``generate-config > myproject.yaml``.

Usage
-----


``GoodConf``
^^^^^^^^^^^^

Your subclassed ``GoodConf`` object can be initialized with the following
keyword args:

``file_env_var``
  The name of an environment variable which can be used for
  the name of the configuration file to load.
``default_files``
  If no file is passed to the ``load`` method, try to load a
  configuration from these files in order.
``load``
  Trigger the load method during instantiation. Defaults to False.

Use plain-text docstring for use as a header when generating a configuration
file.


``Value``
^^^^^^^^^

Declare configuration values by subclassing ``GoodConf`` and defining class
attributes which are ``Value`` instances. They can be initialized with the
following keyword args:

``default``
  Default value if none is provided. If left unset, loading
  a config that fails to provide this value will raise accept
  ``RequiredValueMissing`` exception.
``initial``
  Initial value to use when generating a config
``cast_as``
  Python type to cast variable as. Defaults to type of default
  (if provided) or str.
``help``
  Plain-text description of the value.


Django Usage
------------

A helper is provided which monkey-patches Django's management commands to
accept a ``--config`` argument. Replace your ``manage.py`` with the following:

.. code:: python

    # Define your GoodConf in `myproject/conf.py`
    from myproject.conf import config

    if __name__ == '__main__':
        config.django_manage()


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
