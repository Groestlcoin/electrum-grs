#!/usr/bin/env python
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2025 The Electrum Developers
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import asyncio
import concurrent
from typing import TYPE_CHECKING, List, Tuple, Optional

from PyQt6.QtCore import QObject, pyqtSignal, pyqtProperty, pyqtSlot

from electrum_grs import util
from electrum_grs.plugin import hook
from electrum_grs.transaction import PartialTransaction, tx_from_any
from electrum_grs.wallet import Multisig_Wallet
from electrum_grs.util import EventListener, event_listener

from electrum_grs.gui.qml.qewallet import QEWallet

from .psbt_nostr import PsbtNostrPlugin, CosignerWallet, now

if TYPE_CHECKING:
    from electrum_grs.wallet import Abstract_Wallet
    from electrum_grs.gui.qml import ElectrumQmlApplication

USER_PROMPT_COOLDOWN = 10


class QReceiveSignalObject(QObject):
    def __init__(self, plugin: 'Plugin'):
        QObject.__init__(self)
        self._plugin = plugin

    cosignerReceivedPsbt = pyqtSignal(str, str, str)
    sendPsbtFailed = pyqtSignal(str, arguments=['reason'])
    sendPsbtSuccess = pyqtSignal()

    @pyqtProperty(str)
    def loader(self):
        return 'main.qml'

    @pyqtSlot(QEWallet, str, result=bool)
    def canSendPsbt(self, wallet: 'QEWallet', tx: str) -> bool:
        cosigner_wallet = self._plugin.cosigner_wallets.get(wallet.wallet)
        if not cosigner_wallet:
            return False
        return cosigner_wallet.can_send_psbt(tx_from_any(tx, deserialize=True))

    @pyqtSlot(QEWallet, str)
    def sendPsbt(self, wallet: 'QEWallet', tx: str):
        cosigner_wallet = self._plugin.cosigner_wallets.get(wallet.wallet)
        if not cosigner_wallet:
            return
        cosigner_wallet.send_psbt(tx_from_any(tx, deserialize=True))

    @pyqtSlot(QEWallet, str)
    def acceptPsbt(self, wallet: 'QEWallet', event_id: str):
        cosigner_wallet = self._plugin.cosigner_wallets.get(wallet.wallet)
        if not cosigner_wallet:
            return
        cosigner_wallet.accept_psbt(event_id)

    @pyqtSlot(QEWallet, str)
    def rejectPsbt(self, wallet: 'QEWallet', event_id: str):
        cosigner_wallet = self._plugin.cosigner_wallets.get(wallet.wallet)
        if not cosigner_wallet:
            return
        cosigner_wallet.reject_psbt(event_id)


class Plugin(PsbtNostrPlugin):
    def __init__(self, parent, config, name):
        super().__init__(parent, config, name)
        self.so = QReceiveSignalObject(self)
        self._app = None

    @hook
    def init_qml(self, app: 'ElectrumQmlApplication'):
        self._app = app
        self.so.setParent(app)  # parent in QObject tree
        # plugin enable for already open wallet
        wallet = app.daemon.currentWallet.wallet if app.daemon.currentWallet else None
        if wallet:
            self.load_wallet(wallet)

    @hook
    def load_wallet(self, wallet: 'Abstract_Wallet'):
        # remove existing, only foreground wallet active
        for wallet in self.cosigner_wallets.copy().keys():
            self.remove_cosigner_wallet(wallet)
        if not isinstance(wallet, Multisig_Wallet):
            return
        if wallet.wallet_type == '2fa':
            return
        self.add_cosigner_wallet(wallet, QmlCosignerWallet(wallet, self))


class QmlCosignerWallet(EventListener, CosignerWallet):

    def __init__(self, wallet: 'Multisig_Wallet', plugin: 'Plugin'):
        db_storage = plugin.get_storage(wallet)
        CosignerWallet.__init__(self, wallet, db_storage)
        self.plugin = plugin
        self.register_callbacks()

        self.tx = None
        self.user_prompt_cooldown = None

    @event_listener
    def on_event_psbt_nostr_received(self, wallet, pubkey, event_id, tx: 'PartialTransaction'):
        if self.wallet == wallet:
            self.tx = tx
            if not (self.user_prompt_cooldown and self.user_prompt_cooldown > now()):
                self.plugin.so.cosignerReceivedPsbt.emit(pubkey, event_id, tx.serialize())
            else:
                self.mark_pending_event_rcvd(event_id)
                self.add_transaction_to_wallet(self.tx, on_failure=self.on_add_fail)

    def close(self):
        super().close()
        self.unregister_callbacks()

    def do_send(self, messages: List[Tuple[str, str]], txid: Optional[str] = None):
        if not messages:
            return
        coro = self.send_direct_messages(messages)

        loop = util.get_asyncio_loop()
        assert util.get_running_loop() != loop, 'must not be called from asyncio thread'
        self._result = None
        self._future = asyncio.run_coroutine_threadsafe(coro, loop)

        try:
            self._result = self._future.result()
            self.plugin.so.sendPsbtSuccess.emit()
        except concurrent.futures.CancelledError:
            pass
        except Exception as e:
            self.plugin.so.sendPsbtFailed.emit(str(e))

    def accept_psbt(self, event_id):
        self.mark_pending_event_rcvd(event_id)

    def reject_psbt(self, event_id):
        self.user_prompt_cooldown = now() + USER_PROMPT_COOLDOWN
        self.mark_pending_event_rcvd(event_id)
        self.add_transaction_to_wallet(self.tx, on_failure=self.on_add_fail)

    def on_add_fail(self):
        self.logger.error('failed to add tx to wallet')
