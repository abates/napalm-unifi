"""
Napalm driver for Unifi.

Read https://napalm.readthedocs.io for more information.
"""

from collections import defaultdict
import json
from os import path
from typing import Any, Dict, List, Union

from napalm.base import NetworkDriver, models
from napalm.base.netmiko_helpers import netmiko_args

import ntc_templates
from textfsm import clitable

template_dir = path.abspath(path.join(path.dirname(__file__), "utils", "textfsm_templates"))
local_cli_table = clitable.CliTable("index", template_dir)

template_dir = path.join(path.dirname(ntc_templates.__file__), "templates")
ntc_cli_table = clitable.CliTable("index", template_dir)


def map_textfsm_template(command: str, platform = "ubiquiti_unifi"):
    for table in [local_cli_table, ntc_cli_table]:
        row_idx = table.index.GetRowMatch({
            "Platform": platform,
            "Command": command,
        })
        if row_idx:
            return path.join(table.template_dir, table.index.index[row_idx]['Template'])
    
    return None


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
        self._config: dict = {
            "candidate": None,
            "running": None,
            "startup": None,
        }
        self._mca: dict = None
        self.cli_table = clitable.CliTable()

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
        if use_previous:
            if retrieve == "all" and self._config["candidate"] and self._config["running"] and self._config["startup"]:
                return self._config
            elif self._config[retrieve]:
                return self._config

        if retrieve == "all" or retrieve == "running":
            self._config["running"] = self._read_file("/tmp/running.cfg")

        if retrieve == "all" or retrieve == "startup":
            self._config["startup"] = self._read_file("/tmp/system.cfg")

        return self._config

    def get_config(self, retrieve: str = "all", full: bool = False, sanitized: bool = False) -> models.ConfigDict:
        return self._get_config(retrieve, full, sanitized)

    def get_facts(self) -> models.FactsDict:
       mca = json.loads(self._netmiko_device.send_command("mca-dump"))

       return {
           "fqdn": "",
           "hostname": mca["hostname"],
           "interface_list": list(self.get_interfaces().keys()),
           "model": mca["model"],
           "model_display": mca["model_display"],
           "os_version": mca["version"],
           "uptime": mca["uptime"],
           "serial_number": mca["serial"],
           "vendor": "Ubiquiti Inc.",
       }

    def _read_file(self, file_path):
        return self.send_command(f"cat {file_path}")

    def send_command(self, command: str):
        textfsm_template = map_textfsm_template(command, platform="linux")

        return self._netmiko_device.send_command(
            command,
            use_textfsm=(textfsm_template is not None),
            textfsm_template=textfsm_template,
        )

    def is_physical_interface(self, interface_name) -> bool:
        output = self.send_command(f"readlink -f /sys/class/net/{interface_name}")
        return not output.startswith("/sys/devices/virtual")

    def get_interface_ipv4(self, interface_name):
        interface = self.get_interfaces_ip()[interface_name]
        ip, data = next(iter(interface["ipv4"].items()))
        return (interface_name, f"{ip}/{data['prefix_length']}")

    def get_primary_ipv4(self):
        return self.get_interface_ipv4("eth0")

    def get_interfaces_ip(self) -> Dict[str, models.InterfacesIPDict]:
        interfaces: Dict[str, models.InterfacesIPDict] = {}
        output = self.send_command("ip address show")
        for record in output:
            interface_name = record["interface"]
            interfaces.setdefault(interface_name, {
                "ipv4": {},
                "ipv6": {}
            })
            for i, ip_address in enumerate(record["ip_addresses"]):
                interfaces[interface_name]["ipv4"][ip_address] = {
                    "prefix_length": int(record["ip_masks"][i])
                }
            for i, ip_address in enumerate(record["ipv6_addresses"]):
                interfaces[interface_name]["ipv6"][ip_address] = {
                    "prefix_length": int(record["ipv6_masks"][i])
                }
        return interfaces

    def get_interfaces(self) -> Dict[str, models.InterfaceDict]:
        interfaces: Dict[str, models.InterfaceDict] = {}
        output = self.send_command("ip link show")
        for record in output:
            interface_name = record["interface"]
            if "@" in interface_name:
                interface_name = interface_name[:interface_name.find("@")]
            flags = set(record["flags"].split(","))
            interfaces[interface_name] = {
                "alias": record["alias"],
                "description": interface_name,
                "is_enabled": "UP" in flags,
                "is_up": "UP" in flags,
                "last_flapped": float(-1),
                "mac_address": record["mac_address"],
                "mtu": record["mtu"],
                "speed": float(-1),
                "type": "virtual" if self.is_physical_interface(interface_name) else record["type"],
            }
            if interfaces[interface_name]["type"] != "virtual":
                try:
                    device_path = f"/sys/class/net/{interface_name}"
                    interfaces[interface_name]["speed"] = float(self._read_file(f"{device_path}/speed"))
                except ValueError:
                    """Ignore bad speed parsing."""
        return interfaces


class UnifiConfigMixin:
    def get_config_section(self, prefix: str, trim=False, group=True) -> list[str]:
        if group:
            section = {}
        else:
            section = []
        config = self._get_config("running", use_previous=True)
        for line in config.splitlines():
            if line.startswith(prefix):
                if trim:
                    line = line.removeprefix(prefix)
                
                if group:
                    keys, value = line.split("=")
                    keys = keys.split(".")
                    node = section
                    for key in keys[0:-1]:
                        node.setdefault(key, {})
                        node = node[key]
                    node[keys[-1]] = value
                else:
                    section.append(line)
        return section

    def get_config_value(self, key: str) -> str:
        config = self._get_config("running", use_previous=True)
        for line in config.splitlines():
            line_key, value = line.split("=")
            if line_key == key:
                return value
        raise KeyError(key)


class UnifiSwitchBase(UnifiConfigMixin, UnifiBaseDriver):
    def cli(self, commands: List[str], use_texfsm = False) -> Dict[str, Union[str, Dict[str, Any]]]:
        old_prompt = self._netmiko_device.base_prompt
        self._netmiko_device.set_base_prompt(pattern="(UBNT) ")
        self._netmiko_device.send_command("cli")
        self._netmiko_device.send_command("enable")
        output = {}
        for command in commands:
            self.cli_table.ParseCmd
            textfsm_template = None
            if use_texfsm:
                textfsm_template = map_textfsm_template(command)

            output[command] = self._netmiko_device.send_command(
                command,
                use_textfsm=(textfsm_template is not None),
                textfsm_template=textfsm_template,
            )
        self._netmiko_device.send_command("exit")
        self._netmiko_device.send_command("exit")
        self._netmiko_device.prompt = old_prompt
        return output

    def _get_lldp_neighbors_detail(self, interface) -> Dict:
        raise NotImplementedError("_get_lldp_neighbors_detail may be implemented by sub-classes")

    def get_lldp_neighbors_detail(self, interface: str = "") -> Dict[str, List[models.LLDPNeighborDetailDict]]:
        neighbors: Dict[str, List[models.LLDPNeighborDetailDict]] = defaultdict(list)
        interfaces = []
        if interface == "":
            interfaces = self.get_interfaces().values()
        else:
            interfaces = [interface]

        for interface in interfaces:
            output = self._get_lldp_neighbors_detail(interface)
            for neighbor in output:
                neighbors[interface].append({
                    "parent_interface": "",
                    "remote_chassis_id": neighbor["neighbor_chassis_id"],
                    "remote_port": neighbor["neighbor_portid"],
                    "remote_port_description": neighbor["port_descr"],
                    "remote_system_capab": neighbor["system_capabilities_supported"],
                    "remote_system_description": neighbor["system_descr"],
                    "remote_system_enable_capab": neighbor["system_capabilities_enabled"],
                    "remote_system_name": neighbor["neighbor_sysname"],
                })

    def _get_lldp_neighbors(self) -> Dict:
        raise NotImplementedError("_get_lldp_neighbors may be implemented by sub-classes")

    def get_lldp_neighbors(self) -> Dict[str, List[models.LLDPNeighborDict]]:
        neighbors: Dict[str, List[models.LLDPNeighborDict]] = defaultdict(list)
        output = self._get_lldp_neighbors()
        for neighbor in output:
            neighbors[neighbor["local_port"]].append(
                {
                    "hostname": neighbor["system_name"],
                    "port": neighbor["remote_port"],
                },
            )
        return neighbors

    def get_interfaces(self) -> Dict[str, models.InterfaceDict]:
        interfaces = super().get_interfaces()
        mtu = 1500
        mca = json.loads(self._netmiko_device.send_command("mca-dump"))

        if self.get_config_value("switch.jumboframes") == "enabled":
            mtu = int(self.get_config_value("switch.mtu"))

        for port, details in self.get_config_section("switch.port", group=True, trim=True).items():
            status = mca["port_table"][int(port)-1]
            enabled = True
            if details.get("status") == "disabled":
                enabled = False
            interfaces[port] = {
                "description": details["name"],
                "is_enabled": enabled,
                "is_up": status["up"],
                "last_flapped": float(-1),
                "mac_address": None,
                "mtu": mtu,
                "speed": float(status["speed"]),
                "type": "ether",
                "alias": "",
            }
        return interfaces
