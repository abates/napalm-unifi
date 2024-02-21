

from .unifi import UnifiBaseDriver as _Base

class UnifiSecurityGatewayDriver(_Base):
    def open(self):
        super().open()
        self._netmiko_device.enable(cmd="sudo su -")

    def close(self):
        self._netmiko_device.exit_enable_mode()
        super().close()

    def get_primary_ipv4(self):
        for interface_name, interface in self.get_interfaces().items():
            if interface["alias"] == "LAN":
                return self.get_interface_ipv4(interface_name)
        return (None, None)
