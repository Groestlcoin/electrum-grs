from functools import partial
from typing import TYPE_CHECKING

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QInputDialog, QLineEdit

from electrum_grs.i18n import _
from electrum_grs.plugin import hook
from electrum_grs.wallet import Standard_Wallet

from .ledger import LedgerPlugin, Ledger_Client
from ..hw_wallet.qt import QtHandlerBase, QtPluginBase
from ..hw_wallet.plugin import only_hook_if_libraries_available
from electrum_grs.gui.qt.wizard.wallet import WCScriptAndDerivation, WCHWUninitialized, WCHWUnlock, WCHWXPub

if TYPE_CHECKING:
    from electrum_grs.gui.qt.wizard.wallet import QENewWalletWizard


class Plugin(LedgerPlugin, QtPluginBase):
    icon_unpaired = "ledger_unpaired.png"
    icon_paired = "ledger.png"

    def create_handler(self, window):
        return Ledger_Handler(window)

    @only_hook_if_libraries_available
    @hook
    def receive_menu(self, menu, addrs, wallet):
        if type(wallet) is not Standard_Wallet:
            return
        keystore = wallet.get_keystore()
        if type(keystore) == self.keystore_class and len(addrs) == 1:
            def show_address():
                keystore.thread.add(partial(self.show_address, wallet, addrs[0], keystore=keystore))
            menu.addAction(_("Show on Ledger"), show_address)

    @hook
    def init_wallet_wizard(self, wizard: 'QENewWalletWizard'):
        self.extend_wizard(wizard)

    # insert ledger pages in new wallet wizard
    def extend_wizard(self, wizard: 'QENewWalletWizard'):
        super().extend_wizard(wizard)
        views = {
            'ledger_start': {'gui': WCScriptAndDerivation},
            'ledger_xpub': {'gui': WCHWXPub},
            'ledger_not_initialized': {'gui': WCHWUninitialized},
            'ledger_unlock': {'gui': WCHWUnlock}
        }
        wizard.navmap_merge(views)


class Ledger_Handler(QtHandlerBase):

    MESSAGE_DIALOG_TITLE = _("Ledger Status")

    def __init__(self, win):
        super(Ledger_Handler, self).__init__(win, 'Ledger')

