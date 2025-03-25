from electrum_grs.simple_config import ConfigVar, SimpleConfig

SimpleConfig.WATCHTOWER_SERVER_PORT = ConfigVar('watchtower_server_port', default=None, type_=int, plugin=__name__)
SimpleConfig.WATCHTOWER_SERVER_USER = ConfigVar('watchtower_server_user', default=None, type_=str, plugin=__name__)
SimpleConfig.WATCHTOWER_SERVER_PASSWORD = ConfigVar('watchtower_server_password', default=None, type_=str, plugin=__name__)
