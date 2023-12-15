import json
from typing import Dict

from napalm.base import models
from netaddr import IPNetwork

from .unifi import UnifiBaseDriver as _Base

class UnifiSecurityGatewayDriver(_Base):
    def open(self):
        super().open()
        self._netmiko_device.enable(cmd="sudo su -")

    def get_parsed_config(self, retrieve: str = "all", full: bool = False, sanitized: bool = False, use_previous=False):
        config = self._get_config(retrieve, full, sanitized, use_previous)
        for desc, output in config.items():
            config[desc] = json.loads(output)
        return config

    def close(self):
        self._netmiko_device.exit_enable_mode()
        super().close()

    def get_interfaces(self) -> Dict[str, models.InterfaceDict]:
        interfaces: Dict[str, models.InterfaceDict] = {}
        mca = self._get_mca(use_previous=True)
        for interface in mca["network_table"]:
            interfaces[interface["name"]] = {
                "description": None,
                "is_enabled": interface["up"],
                "is_up": interface["l1up"],
                "last_flapped": float(-1),
                "mac_address": interface["mac"],
                "mtu": int(interface["mtu"]),
                "speed": float(interface.get("speed", -1)),
            }
        return interfaces

    def get_interfaces_ip(self) -> Dict[str, models.InterfacesIPDict]:
        ips: Dict[str, models.InterfacesIPDict] = {}
        mca = self._get_mca(True)
        for interface in mca["network_table"]:
            ips[interface["name"]] = {
                "ipv4": {},
                "ipv6": {},
            }
            for ip in interface["addresses"]:
                ip = IPNetwork(ip)
                ips[interface["name"]]["ipv4"][str(ip.ip)] = {
                    "prefix_length": ip.prefixlen,
                }

        return ips
