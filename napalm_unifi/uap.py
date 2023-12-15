from typing import Dict

from napalm.base import models

from .unifi import UnifiBaseDriver as _Base, UnifiConfigMixin


class UnifiAccessPointDriver(_Base, UnifiConfigMixin):
    pass
