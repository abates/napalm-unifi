from collections import defaultdict
import json
from typing import Dict, List

from napalm.base import models


from .unifi import UnifiSwitchBase as _SwitchBase

class UnifiSwitchLiteDriver(_SwitchBase):
    def get_lldp_neighbors_detail(self, interface: str = "") -> Dict[str, List[models.LLDPNeighborDetailDict]]:
        neighbors: Dict[str, List[models.LLDPNeighborDetailDict]] = defaultdict(list)

        output = json.loads(self.send_command("lldpcli -f json0 show neighbors details"))
        for interface in output.get("lldp", {}).get("interface", []):
            for details in interface:
                neighbors[details["name"]].append({
                    "parent_interface": "",
                    "remote_chassis_id": details["chassis"][0]["id"]["value"],
                    "remote_port": details["port"][0]["id"]["value"],
                    "remote_port_description": details["port"][0]["descr"]["value"],
                    "remote_system_capab": [cap["type"] for cap in details["chassis"][0]["capability"]],
                    "remote_system_description": details["chassis"][0]["descr"]["value"],
                    "remote_system_enable_capab": [cap["type"] for cap in details["chassis"][0]["capability"] if cap["enabled"]],
                    "remote_system_name": details["chassis"][0]["name"]["value"],
                })
        if interface == "":
            return neighbors
        return neighbors.get(interface, None)

    def get_lldp_neighbors(self) -> Dict[str, List[models.LLDPNeighborDict]]:
        neighbors: Dict[str, List[models.LLDPNeighborDict]] = defaultdict(list)
        for neighbor in self.get_lldp_neighbors_detail():
            neighbors[neighbor["local_port"]].append(
                {
                    "hostname": neighbor["remote_system_name"],
                    "port": neighbor["remote_port"],
                },
            )
        return neighbors
