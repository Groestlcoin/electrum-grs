from functools import partial
from typing import TYPE_CHECKING

from PyQt6.QtCore import pyqtSignal

from electrum_grs.i18n import _
from electrum_grs.plugin import hook
from electrum_grs.wallet import Standard_Wallet

from electrum_grs.hw_wallet.qt import QtHandlerBase, QtPluginBase
from electrum_grs.hw_wallet import plugin
from electrum_grs.hw_wallet.plugin import only_hook_if_libraries_available
from electrum_grs.gui.qt.wizard.wallet import WCScriptAndDerivation, WCHWUnlock, WCHWXPub, WCHWUninitialized

from .jade import JadePlugin

if TYPE_CHECKING:
    from electrum_grs.gui.qt.wizard.wallet import QENewWalletWizard


class Plugin(JadePlugin, QtPluginBase):
    icon_unpaired = "jade_unpaired.png"
    icon_paired = "jade.png"

    def create_handler(self, window):
        return Jade_Handler(window)

    @only_hook_if_libraries_available
    @hook
    def receive_menu(self, menu, addrs, wallet):
        if len(addrs) != 1:
            return
        if type(wallet) is not Standard_Wallet:
            return
        self._add_menu_action(menu, addrs[0], wallet)

    @only_hook_if_libraries_available
    @hook
    def transaction_dialog_address_menu(self, menu, addr, wallet):
        if type(wallet) is not Standard_Wallet:
            return
        self._add_menu_action(menu, addr, wallet)

    @hook
    def init_wallet_wizard(self, wizard: 'QENewWalletWizard'):
        self.extend_wizard(wizard)

    # insert jade pages in new wallet wizard
    def extend_wizard(self, wizard: 'QENewWalletWizard'):
        super().extend_wizard(wizard)
        views = {
            'jade_start': {'gui': WCScriptAndDerivation},
            'jade_xpub': {'gui': WCHWXPub},
            'jade_not_initialized': {'gui': WCHWUninitialized},
            'jade_unlock': {'gui': WCHWUnlock}
        }
        wizard.navmap_merge(views)


class Jade_Handler(QtHandlerBase):
    setup_signal = pyqtSignal()
    auth_signal = pyqtSignal(object, object)

    MESSAGE_DIALOG_TITLE = _("Jade Status")

    def __init__(self, win):
        super(Jade_Handler, self).__init__(win, 'Jade')
