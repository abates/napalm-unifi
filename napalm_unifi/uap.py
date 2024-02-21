from .unifi import UnifiBaseDriver as _Base, UnifiConfigMixin


class UnifiAccessPointDriver(UnifiConfigMixin, _Base):
    def get_primary_ipv4(self):
        return self.get_interface_ipv4("br0")

