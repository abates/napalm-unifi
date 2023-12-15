"""
Napalm driver for Unifi.

Read https://napalm.readthedocs.io for more information.
"""

from collections import UserList
import json
from typing import Any, Dict

from netaddr import IPNetwork

from napalm.base import NetworkDriver, models
from napalm.base.netmiko_helpers import netmiko_args

class UnifiList(UserList):
    def __setitem__(self, index, value):
        if index >= len(self):
            for _ in range(index - len(self) + 1):
                self.append(UnifiConfig())
        return super().__setitem__(index, value)


class UnifiConfig(UserList):
    def __init__(self, config=None):
        super().__init__()
        if config is not None:
            for line in config.split("\n"):
                line = line.strip()
                if line and not line.startswith("#"):
                    key, value = line.split("=")
                    self.set(key, value)

    def __setitem__(self, index, value):
        if index >= len(self):
            for _ in range(index - len(self) + 1):
                self.append(UnifiConfig())
        return super().__setitem__(index, value)

    def set(self, path, value):
        item = self
        path = path.split(".")
        for key in path[0:-1]:
            try:
                key = int(key)
                try:
                    item = item[key - 1]
                except IndexError:
                    item[key - 1] = UnifiConfig()
                    item = item[key - 1]
            except ValueError:
                try:
                    item = getattr(item, key)
                except AttributeError:
                    newitem = UnifiConfig()
                    setattr(item, key, newitem)
                    item = newitem
        setattr(item, path[-1], value)

    def get(self, path, default_value=None):
        item = self
        try:
            for key in path.split("."):
                try:
                    key = int(key)
                    item = item[key - 1]
                    if item is None:
                        raise KeyError(str(key))
                except ValueError:
                    item = getattr(item, key)
        except AttributeError:
            return default_value
        return item


    def to_json(self, **dumps_options):
        return json.dumps(self, cls=UnifiJSONEncoder, **dumps_options)

class UnifiJSONEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, (UnifiList, UnifiConfig)):
            return o.data
        return super().default(o)


class UnifiBaseDriver(NetworkDriver):
    """Napalm driver for Unifi."""

    def __init__(self, hostname, username, password, timeout=60, optional_args=None):
        """Constructor."""
        self.device = None
        self.hostname = hostname
        self.username = username
        self.password = password
        self.timeout = timeout

        if optional_args is None:
            optional_args = {
                "allow_agent": False,
                "allowed_types": ["password"],
            }
        self.netmiko_optional_args = netmiko_args(optional_args)

        self._config: models.ConfigDict = None
        self._mca: dict = None

    def open(self):
        """Implement the NAPALM method open (mandatory)"""
        self.device = self._netmiko_open(
            device_type="linux",
            netmiko_optional_args=self.netmiko_optional_args
        )

    def close(self):
        """Implement the NAPALM method close (mandatory)"""
        self._netmiko_close()

    def _get_config(self, retrieve: str = "all", full: bool = False, sanitized: bool = False, use_previous: bool = False) -> models.ConfigDict:
        if use_previous and self._config is not None:
            return self._config

        self._config = {
            "candidate": None,
            "running": None,
            "startup": None,
        }

        if retrieve == "all" or retrieve == "running":
            self._config["running"] = self._netmiko_device.send_command("cat /tmp/running.cfg")

        if retrieve == "all" or retrieve == "startup":
            self._config["startup"] = self._netmiko_device.send_command("cat /tmp/system.cfg")

        return self._config

    def get_config(self, retrieve: str = "all", full: bool = False, sanitized: bool = False) -> models.ConfigDict:
        return self._get_config(retrieve, full, sanitized)

    def _get_mca(self, use_previous=False):
        if use_previous and self._mca is not None:
            return self._mca
        self._mca = json.loads(self._netmiko_device.send_command("mca-dump"))
        return self._mca

    def get_mca(self) -> dict:
        return json.loads(self._netmiko_device.send_command("mca-dump"))


    def get_facts(self) -> models.FactsDict:
       mca = self._get_mca(use_previous=True)

       return {
           "fqdn": "",
           "hostname": mca["hostname"],
           "interface_list": sorted(self.get_interfaces().keys()),
           "model": mca["model"],
           "model_display": mca["model_display"],
           "os_version": mca["version"],
           "uptime": mca["uptime"],
           "serial_number": mca["serial"],
           "vendor": "Ubiquiti Inc.",
       }

    def get_interfaces_ip(self) -> Dict[str, models.InterfacesIPDict]:
        ips: Dict[str, models.InterfacesIPDict] = {}
        mca = self._get_mca(True)
        for interface in mca["if_table"]:
            ips[interface["name"]] = {
                "ipv4": {},
                "ipv6": {},
            }
            ip = IPNetwork(f"{interface['ip']}/{interface['netmask']}")
            ips[interface["name"]]["ipv4"][str(ip.ip)] = {
                "prefix_length": ip.prefixlen,
            }

        return ips


class UnifiConfigMixin:
    def get_parsed_config(self, retrieve: str = "all", full: bool = False, sanitized: bool = False, use_previous=False):
        config = self._get_config(retrieve, full, sanitized, use_previous)
        for desc, output in config.items():
            config[desc] = UnifiConfig(output)
        return config

