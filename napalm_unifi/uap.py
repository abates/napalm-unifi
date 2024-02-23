import json
from .unifi import UnifiBaseDriver as _Base, LLDPCliMixin, NoEnableMixin, UnifiConfigMixin


class UnifiAccessPointDriver(NoEnableMixin, LLDPCliMixin, UnifiConfigMixin, _Base):
    def get_primary_ipv4(self):
        return self.get_interface_ipv4("br0")

    def lldp_show_neighbors(self):
        return json.loads(self.send_command("lldpcli -f json0 show neighbors details"))
