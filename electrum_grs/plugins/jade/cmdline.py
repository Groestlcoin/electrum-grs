from electrum_grs.plugin import hook
from .jade import JadePlugin
from electrum_grs.hw_wallet import CmdLineHandler

class Plugin(JadePlugin):
    handler = CmdLineHandler()
    @hook
    def init_keystore(self, keystore):
        if not isinstance(keystore, self.keystore_class):
            return
        keystore.handler = self.handler

    def create_handler(self, window):
        return self.handler
