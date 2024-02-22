import json



from .unifi import LLDPCliMixin, UnifiSwitchBase as _SwitchBase

class UnifiSwitchFlexDriver(LLDPCliMixin, _SwitchBase):
    def lldp_show_neighbors(self):
        return json.loads(self.send_command("lldpcli -f json0 show neighbors details"))
