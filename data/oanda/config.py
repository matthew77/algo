import yaml
import os
import v20
import importlib.resources as pkg_resources


class ConfigPathError(Exception):
    """
    Exception that indicates that the path specifed for a v20 config file
    location doesn't exist
    """

    def __init__(self, path):
        self.path = path

    def __str__(self):
        return "Config file '{}' could not be loaded.".format(self.path)


class ConfigValueError(Exception):
    """
    Exception that indicates that the v20 configuration file is missing
    a required value
    """

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return "Config is missing value for '{}'.".format(self.value)


class Config:
    """
    The Config object encapsulates all of the configuration required to create
    a v20 API context and configure it to work with a specific Account. 

    Using the Config object enables the scripts to exist without many command
    line arguments (host, token, accountID, etc)
    """
    def __init__(self):
        """
        Initialize an empty Config object
        """
        self.hostname = None
        self.streaming_hostname = None
        self.port = 443
        self.ssl = True
        self.token = None
        self.username = None
        self.accounts = []
        self.active_account = None
        self.path = None
        self.datetime_format = "RFC3339"

    def __str__(self):
        """
        Create the string (YAML) representation of the Config instance
        """

        s = ""
        s += "hostname: {}\n".format(self.hostname)
        s += "streaming_hostname: {}\n".format(self.streaming_hostname)
        s += "port: {}\n".format(self.port)
        s += "ssl: {}\n".format(str(self.ssl).lower())
        s += "token: {}\n".format(self.token)
        s += "username: {}\n".format(self.username)
        s += "datetime_format: {}\n".format(self.datetime_format)
        s += "accounts:\n"
        for a in self.accounts:
            s += "- {}\n".format(a)
        s += "active_account: {}".format(self.active_account)

        return s

    def load(self, path):
        """
        Load the YAML config representation from a file into the Config instance

        Args:
            path: The location to read the config YAML from
        """

        self.path = path

        try:
            with open(os.path.expanduser(path)) as f:
                y = yaml.load(f)
                self.hostname = y.get("hostname", self.hostname)
                self.streaming_hostname = y.get(
                    "streaming_hostname", self.streaming_hostname
                )
                self.port = y.get("port", self.port)
                self.ssl = y.get("ssl", self.ssl)
                self.username = y.get("username", self.username)
                self.token = y.get("token", self.token)
                self.accounts = y.get("accounts", self.accounts)
                self.active_account = y.get(
                    "active_account", self.active_account
                )
                self.datetime_format = y.get("datetime_format", self.datetime_format)
        except:
            raise ConfigPathError(path)

    def validate(self):
        """
        Ensure that the Config instance is valid
        """

        if self.hostname is None:
            raise ConfigValueError("hostname")
        if self.streaming_hostname is None:
            raise ConfigValueError("hostname")
        if self.port is None:
            raise ConfigValueError("port")
        if self.ssl is None:
            raise ConfigValueError("ssl")
        if self.username is None:
            raise ConfigValueError("username")
        if self.token is None:
            raise ConfigValueError("token")
        if self.accounts is None:
            raise ConfigValueError("account")
        if self.active_account is None:
            raise ConfigValueError("account")
        if self.datetime_format is None:
            raise ConfigValueError("datetime_format")

    def create_context(self):
        """
        Initialize an API context based on the Config instance
        """
        ctx = v20.Context(
            self.hostname,
            self.port,
            self.ssl,
            application="algo_app",
            token=self.token,
            datetime_format=self.datetime_format
        )

        return ctx

    def create_streaming_context(self):
        """
        Initialize a streaming API context based on the Config instance
        """
        ctx = v20.Context(
            self.streaming_hostname,
            self.port,
            self.ssl,
            application="sample_code",
            token=self.token,
            datetime_format=self.datetime_format
        )

        return ctx

    def load_default_config(self):
        from data import oanda
        yaml_file = pkg_resources.open_text(oanda, 'account_info.yml')
        y = yaml.load(yaml_file, Loader=yaml.FullLoader)
        self.hostname = y.get("hostname", self.hostname)
        self.streaming_hostname = y.get(
            "streaming_hostname", self.streaming_hostname
        )
        self.port = y.get("port", self.port)
        self.ssl = y.get("ssl", self.ssl)
        self.username = y.get("username", self.username)
        self.token = y.get("token", self.token)
        self.accounts = y.get("accounts", self.accounts)
        self.active_account = y.get(
            "active_account", self.active_account
        )
        self.datetime_format = y.get("datetime_format", self.datetime_format)


def make_config_instance(path=''):
    """
    Create a Config instance, load its state from the provided path and 
    ensure that it is valid.

    Args:
        path: The location of the configuration file
    """
    config = Config()
    if path:
        config.load(path)
    else:
        # load from python package
        config.load_default_config()
    config.validate()
    return config
