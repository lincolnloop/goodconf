from goodconf import GoodConf


class AppConfig(GoodConf):
    """Configuration for the example project"""

    model_config = {
        "default_files": ["project.json"],
        "file_env_var": "PROJECT_CONF",
    }

    APP_NAME: str = "default"


config = AppConfig()
