==========
Change Log
==========

5.0.1 (Unreleased)
========================

- Update Markdown generation, so that output matches v4 output

5.0.0 (13 August 2024)
========================

- **Backwards Incompatible Release**

  - Removed official support for Python 3.8
  - upgraded to pydantic2

  To upgrade from goodconf v4 to goodconf v5:

  - If subclassing ``GoodConf``, replace uses of ``class Config`` with ``model_config``.

    For example goodconf v4 code like this:

    .. code:: python

        from goodconf import GoodConf

        class AppConfig(GoodConf):
            "Configuration for My App"
            DATABASE_URL: PostgresDsn = "postgres://localhost:5432/mydb"

            class Config:
                default_files = ["/etc/myproject/myproject.yaml", "myproject.yaml"]

        config = AppConfig()

    should be replaced in goodconf v5 with:

    .. code:: python

        from goodconf import GoodConf

        class AppConfig(GoodConf):
            "Configuration for My App"
            DATABASE_URL: PostgresDsn = "postgres://localhost:5432/mydb"

            model_config = {"default_files": ["/etc/myproject/myproject.yaml", "myproject.yaml"]}

        config = AppConfig()

4.0.3 (13 August 2024)
========================

- Release from GitHub Actions

4.0.2 (11 February 2024)
========================

- Another markdown output fix
- Fix for markdown generation generation on Python 3.8 & 3.9

4.0.1 (10 February 2024)
========================

- Fix trailing whitespace in markdown output

4.0.0 (10 February 2024)
========================

- Removed errant print statement
- Removed official support for Python 3.7
- Added support for Python 3.12

3.1.0 (10 February 2024)
========================

- Fixed type display in Markdown generation
- Changed markdown output format (trailing spaces were problematic).

3.0.1 (30 June 2023)
====================

- pin to pydantic < 2 due to breaking changes in 2.0

3.0.0 (17 January 2023)
==================

- TOML files are now supported as configuration source
- Python 3.11 and 3.10 are now officially supported
- Python 3.6 is no longer officially supported
- Requires Pydantic 1.7+
- Variables can now be set during class initialization


2.0.1 (15 June 2021)
====================

- Change to newer syntax for safe loading yaml


2.0.0 (13 May 2021)
===================

- **Backwards Incompatible Release**
    Internals replaced with `pydantic <https://pypi.org/project/pydantic/>`_. Users can either pin to ``1.0.0`` or update their code as follows:

    - Replace ``goodconf.Value`` with ``goodconf.Field``.
    - Replace ``help`` keyword argument with ``description`` in ``Field`` (previously ``Value``).
    - Remove ``cast_as`` keyword argument from ``Field`` (previously ``Value``). Standard Python type annotations are now used.
    - Move ``file_env_var`` and ``default_files`` keyword arguments used in class initialization to a sub-class named ``Config``

    Given a version ``1`` class that looks like this:

    .. code:: python

        from goodconf import GoodConf, Value

        class AppConfig(GoodConf):
            "Configuration for My App"
            DEBUG = Value(default=False, help="Toggle debugging.")
            MAX_REQUESTS = Value(cast_as=int)

        config = AppConfig(default_files=["config.yml"])

    A class updated for version `2` would be:

    .. code:: python

        from goodconf import GoodConf, Field

        class AppConfig(GoodConf):
            "Configuration for My App"
            DEBUG: bool = Field(default=False, description="Toggle debugging.")
            MAX_REQUESTS: int

            class Config:
                default_files=["config.yml"]

        config = AppConfig()

2.0b3 (15 April 2021)
=====================

- Environment variables take precedence over configuration files in the event of a conflict

2.0b2 (12 March 2021)
=====================

- Use null value for initial if allowed
- Store the config file parsed as ``GoodConf.Config._config_file``


2.0b1 (11 March 2021)
=====================

- Backwards Incompatible: Migrated backend to ``pydantic``.

  - ``Value`` is replaced by the `Field function <https://pydantic-docs.helpmanual.io/usage/schema/#field-customisation>`__.
  - ``help`` keyword arg is now ``description``
  - ``GoodConf`` is now backed by `BaseSettings <https://pydantic-docs.helpmanual.io/usage/settings/>`__
    Instead of passing keyword args when instantiating the class, they are now defined on a ``Config`` class on the object



1.0.0 (18 July 2018)
====================

- Allow overriding of values in the generate_* methods
- Python 3.7 supported


0.9.1 (10 April 2018)
=====================

- Explicit ``load`` method
- ``django_manage`` method helper on ``GoodConf``
- Fixed a few minor bugs


0.9.0 (8 April 2018)
====================

- Use a declarative class to define GoodConf's values.

- Change description to a docstring of the class.

- Remove the redundant ``required`` argument from ``Values``. To make
  an value optional, give it a default.

- Changed implicit loading to happen during instanciation rather than first
  access. Instanciate with ``load=False`` to avoid loading config initially.

0.8.3 (28 Mar 2018)
===================

- Implicitly load config if not loaded by first access.

0.8.2 (28 Mar 2018)
===================

- ``-c`` is used by Django's ``collectstatic``. Using ``-C`` instead.

0.8.1 (28 Mar 2018)
===================

- Adds ``goodconf.contrib.argparse`` to add a config argument to an existing
  parser.

0.8.0 (27 Mar 2018)
===================

- Major refactor from ``file-or-env`` to ``goodconf``

0.6.1 (16 Mar 2018)
================

- Fixed packaging issue.

0.6.0 (16 Mar 2018)
================

- Fixes bug in stack traversal to find calling file.


0.5.1 (15 March 2018)
==================

- Initial release
