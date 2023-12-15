from typing import Dict

from napalm.base import models

from .unifi import UnifiBaseDriver as _Base, UnifiConfigMixin

class UnifiSwitchDriver(_Base, UnifiConfigMixin):
    def get_interfaces(self) -> Dict[str, models.InterfaceDict]:
        interfaces: Dict[str, models.InterfaceDict] = {}
        config = self.get_parsed_config("running")["running"]
        mca = self._get_mca(use_previous=True)
        mtu = 1500
        if config.switch.jumboframes == "enabled":
            mtu = int(config.switch.mtu)

        for port_id, port in enumerate(config.switch.port):
            interfaces[port.name] = {
                "description": None,
                "is_enabled": True if getattr(port, "status", None) is None else port.status != "disabled",
                "is_up": mca["port_table"][port_id]["up"],
                "last_flapped": float(-1),
                "mac_address": None,
                "mtu": mtu,
                "speed": float(getattr(port, "speed", -1)),
            }
        return interfaces
