from dotenv import dotenv_values

from config.models import Config


def load_config() -> Config:
    env_values = dotenv_values()

    return Config(
        **{key.lower(): value for key, value in env_values.items()}
    )