

from collections import defaultdict
import json
from typing import Dict, List
from .unifi import LLDPCliMixin, UnifiBaseDriver as _Base

from napalm.base import models

class UnifiSecurityGatewayDriver(LLDPCliMixin, _Base):
    def open(self):
        super().open()
        print("Disable Paging")
        self.send_command("terminal length 0")

    def get_config(self, retrieve: str = "all", full: bool = False, sanitized: bool = False) -> models.ConfigDict:
        if retrieve == "all" or retrieve == "running":
            self._config["running"] = self.send_command("show configuration")

        if retrieve == "all" or retrieve == "startup":
            self._config["startup"] = self.send_command("show configuration saved")

        return self._config

    def get_primary_ipv4(self):
        for interface_name, interface in self.get_interfaces().items():
            if interface["alias"] == "LAN":
                return self.get_interface_ipv4(interface_name)
        return (None, None)

    def get_lldp_neighbors_detail(self, interface: str = "") -> Dict[str, List[models.LLDPNeighborDetailDict]]:
        neighbors: Dict[str, List[models.LLDPNeighborDetailDict]] = defaultdict(list)

        # The lldpctl command on the USG doesn't add a newline at the
        # end of the json output, therefore we simply append one ourselves.
        # This ensures the json output can be fully captured by netmiko and
        # property parsed here
        output = json.loads(self.send_command("lldpctl -f json && echo"))
        # try:
        #     output = json.loads(output)
        # except json.JSONDecodeError:
        #     # sometimes the output is missing the closing brace...
        #     output = json.loads(output + "}")
        for details in output.get("lldp", {}).get("interface", []):
            neighbors[details["name"]].append({
                "parent_interface": "",
                "remote_chassis_id": details["chassis"]["id"][0]["id"],
                "remote_port": details["port"]["id"][0]["id"],
                "remote_port_description": details["port"]["descr"]["descr"],
                "remote_system_capab": [cap["type"] for cap in details["chassis"]["capability"]],
                "remote_system_description": details["chassis"]["descr"]["descr"],
                "remote_system_enable_capab": [cap["type"] for cap in details["chassis"]["capability"] if cap["enabled"] == "on"],
                "remote_system_name": details["chassis"]["name"]["name"],
            })
        if interface == "":
            return neighbors
        return {interface: neighbors.get(interface, None)}
