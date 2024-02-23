

from collections import defaultdict
import json
from typing import Dict, List
from .unifi import LLDPCliMixin, UnifiBaseDriver as _Base

from napalm.base import models

class UnifiSecurityGatewayDriver(LLDPCliMixin, _Base):
    def get_primary_ipv4(self):
        for interface_name, interface in self.get_interfaces().items():
            if interface["alias"] == "LAN":
                return self.get_interface_ipv4(interface_name)
        return (None, None)

    def get_lldp_neighbors_detail(self, interface: str = "") -> Dict[str, List[models.LLDPNeighborDetailDict]]:
        neighbors: Dict[str, List[models.LLDPNeighborDetailDict]] = defaultdict(list)

        output = self.send_command("lldpctl -f json")
        try:
            output = json.loads(output)
        except json.JSONDecodeError:
            # sometimes the output is missing the closing brace...
            output = json.loads(output + "}")
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
