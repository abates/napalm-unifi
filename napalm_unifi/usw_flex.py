import json
from typing import Any, Dict, List, Union

from napalm.base import models


from .unifi import UnifiBaseDriver as _Base, UnifiConfigMixin, map_textfsm_template

class UnifiSwitchDriver(UnifiConfigMixin, _Base):
    def get_interfaces(self) -> Dict[str, models.InterfaceDict]:
        interfaces = super().get_interfaces()
        mca = json.loads(self._netmiko_device.send_command("mca-dump"))
        
        mtu = 1500
        if self.get_config_value("switch.jumboframes") == "enabled":
            mtu = int(self.get_config_value("switch.mtu"))

        for interface in mca["port_table"]:
            interface_name = f"Port {interface['port_idx']}"
            interfaces[interface_name] = {
                "description": interface_name,
                "is_enabled": interface["enable"],
                "is_up": interface["up"],
                "last_flapped": float(-1),
                "mac_address": None,
                "mtu": mtu,
                "speed": float(interface["speed"]),
                "type": "ether",
                "alias": "",
            }
        return interfaces
    
    def cli(self, commands: List[str], encoding: str = "text", use_texfsm = False) -> Dict[str, Union[str, Dict[str, Any]]]:
        old_prompt = self._netmiko_device.base_prompt
        self._netmiko_device.set_base_prompt(pattern="(UBNT) ")
        self._netmiko_device.send_command("cli")
        self._netmiko_device.send_command("enable")
        output = {}
        for command in commands:
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

    def get_lldp_neighbors_detail(self, interface: str = "") -> Dict[str, List[models.LLDPNeighborDetailDict]]:
        command = f"show lldp remote-device detail {interface}"
        output = self.cli(command, use_texfsm=True)[command]

    def get_lldp_neighbors(self) -> Dict[str, List[models.LLDPNeighborDict]]:
        neighbors: Dict[str, List[models.LLDPNeighborDict]] = {}

        command = "show lldp remote-device all"
        output = self.cli(command, use_texfsm=True)[command]
        for neighbor in output:
            neighbors[neighbor["local_port"]] = [
                {
                    "hostname": neighbor["system_name"],
                    "port": neighbor["remote_port"],
                },
            ]
        return neighbors
