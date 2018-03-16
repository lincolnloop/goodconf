File or Env
===========

Transparently load variables from environment or JSON/YAML file.

Installation
------------

``pip install file-or-env`` or ``pip install file-or-env[yaml]`` if parsing
YAML files is required.

Usage
-----

Examples::

    from file_or_env import FileOrEnv
    config = FileOrEnv('config.json')
    config['SOME_VAL']
    config.get('ANOTHER_VAL', 'default value')
    config.get('BOOLEAN_VAL', 'false', cast=bool)

``FileOrEnv`` is a dict-like object which abstracts retrieval of values from a
file or ``os.environ``. Environment variables take precedence over the file.

The file can be provided as an absolute path or a filename. If a filename
is provided, it will walk up the filesystem looking for a filename that
matches, loading the first one that is found.

JSON is assumed as the default format for the file, but files with a ``.yml`` or
``.yaml`` extension will be parsed as YAML (requires installing the ``[yaml]``
variant of the package``.

Environment variables can be cast to common types using the optional ``cast``
keyword argument to ``.get``. Default is a string.

Why?
----

I don't like working with environment variables. First, there are potential
security issues:

1. Accidental leaks via logging or error reporting services.
2. Child process inheritance (see `ImageTragick <https://imagetragick.com/>`__
   for an idea why this could be bad.

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
