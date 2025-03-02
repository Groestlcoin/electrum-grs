from electrum_grs.i18n import _

fullname = _('Watchtower')
description = """
A watchtower is a daemon that watches your channels and prevents the other party from stealing funds by broadcasting an old state.

Example:

daemon setup:

  electrum-grs -o setconfig enable_plugin_watchtower True
  electrum-grs -o setconfig watchtower_user wtuser
  electrum-grs -o setconfig watchtower_password wtpassword
  electrum-grs -o setconfig watchtower_port 12345
  electrum-grs daemon -v

client setup:

  electrum-grs -o setconfig watchtower_url http://wtuser:wtpassword@127.0.0.1:12345

"""

available_for = ['cmdline']
