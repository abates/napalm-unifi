from netmiko.channel import Channel
from netmiko.linux import LinuxSSH

from napalm_unifi.usg import UnifiSecurityGatewayDriver
from napalm_unifi.usw_flex import UnifiSwitchFlexDriver
from napalm_unifi.usw_lite import UnifiSwitchLiteDriver
from napalm_unifi.usw import UnifiSwitchDriver

DRIVERS = {
    "UnifiSecurityGatewayDriver": UnifiSecurityGatewayDriver,
    "UnifiSwitchFlexDriver": UnifiSwitchFlexDriver,
    "UnifiSwitchLiteDriver": UnifiSwitchLiteDriver,
    "UnifiSwitchDriver": UnifiSwitchDriver,
}

class MockChannel(Channel):
    def __init__(self, prompt: str, command_table: dict[str, str]):
        self.command_table = command_table
        self.prompt = prompt
        self.buffer = prompt

    def read_buffer(self) -> str:
        data = self.buffer
        self.buffer = ""
        # print("Reading", data)
        return data

    def read_channel(self) -> str:
        return self.read_buffer()

    def write_channel(self, out_data: str):
        self.buffer += out_data
        command = out_data.strip()
        # print("Sending", out_data)
        if command in self.command_table:
            self.buffer += self.command_table[command]
            self.buffer += self.prompt
        elif command == "":
            self.buffer += "\n" + self.prompt
        else:
            raise ValueError(f'Cannot find command "{out_data}" in table')
        return None

class MockDevice(LinuxSSH):
    def __init__(self, prompt: str, command_table: dict[str, str]):
        self.mock_prompt = prompt
        self.command_table = command_table
        super().__init__(host="localhost")

    def establish_connection(self, width: int = 511, height: int = 1000) -> None:
        self.channel = MockChannel(self.mock_prompt, self.command_table)
        return None

    def disconnect(self):
        self.channel = None

def get_mocked_driver(driver_cls_name: type, prompt: str, command_table: dict[str, str]):
    driver_cls = DRIVERS[driver_cls_name]

    driver = driver_cls(hostname="", username=None, password=None)
    driver._netmiko_device = MockDevice(prompt, command_table)

    driver.open = lambda : None
    driver.close = lambda : None
    return driver
