<<<<<<<< HEAD:electrum_grs/plugins/cosigner_pool/__init__.py
from electrum_grs.i18n import _
fullname = _('Cosigner Pool')
========
from electrum.i18n import _
fullname = _('PSBT over Nostr')
>>>>>>>> upstream/master:electrum/plugins/psbt_nostr/__init__.py
description = ' '.join([
    _("This plugin facilitates the use of multi-signatures wallets."),
    _("It sends and receives partially signed transactions from/to your cosigner wallet."),
    _("PSBTs are sent and retrieved from Nostr relays.")
])
author = 'The Electrum Developers'
#requires_wallet_type = ['2of2', '2of3']
available_for = ['qt']
version = '0.0.1'
