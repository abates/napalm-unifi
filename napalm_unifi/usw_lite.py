from typing import Dict, List

from napalm.base import models


from .unifi import UnifiSwitchBase as _SwitchBase


class UnifiSwitchLiteDriver(_SwitchBase):
    def get_lldp_neighbors_detail(self, interface: str = "") -> Dict[str, List[models.LLDPNeighborDetailDict]]:
        return super().get_lldp_neighbors_detail(interface, interface_name_prefix="gi")

    def _get_lldp_neighbors_detail(self, interface):
        command = f"show lldp interfaces {interface} neighbor"
        return self.cli([command], use_texfsm=True)[command]

    def get_lldp_neighbors(self) -> Dict[str, List[models.LLDPNeighborDict]]:
        return super().get_lldp_neighbors(interface_name_prefix="gi")

    def _get_lldp_neighbors(self) -> Dict[str, List[models.LLDPNeighborDict]]:
        command = "show lldp neighbor"
        return self.cli([command], use_texfsm=True)[command]
