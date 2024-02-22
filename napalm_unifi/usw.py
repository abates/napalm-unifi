from typing import Dict, List

from napalm.base import models


from .unifi import UnifiSwitchBase as _UnifiSwitchBase

class UnifiSwitchDriver(_UnifiSwitchBase):
    def get_lldp_neighbors_detail(self, interface: str = "") -> Dict[str, List[models.LLDPNeighborDetailDict]]:
        return super().get_lldp_neighbors_detail(interface, interface_name_prefix="0/")
    
    def _get_lldp_neighbors_detail(self, interface):
        command = f"show lldp remote-device detail {interface}"
        return self.cli([command], use_texfsm=True)[command]

    def get_lldp_neighbors(self) -> Dict[str, List[models.LLDPNeighborDict]]:
        return super().get_lldp_neighbors(interface_name_prefix="0/")

    def _get_lldp_neighbors(self) -> Dict[str, List[models.LLDPNeighborDict]]:
        command = "show lldp remote-device all"
        return self.cli([command], use_texfsm=True)[command]
