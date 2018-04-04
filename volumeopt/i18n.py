"""oslo.i18n integration module.

See http://docs.openstack.org/developer/oslo.i18n/usage.html .

"""

import oslo_i18n as i18n

DOMAIN = 'vmware_sdk'

_translators = i18n.TranslatorFactory(domain=DOMAIN)

# The primary translation function using the well-known name "_"
_ = _translators.primary

# Translators for log levels.
#
# The abbreviated names are meant to reflect the usual use of a short
# name like '_'. The "L" is for "log" and the other letter comes from
# the level.
_LI = _translators.log_info
_LW = _translators.log_warning
_LE = _translators.log_error
_LC = _translators.log_critical
