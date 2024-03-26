from enum import Enum
from dataclasses import dataclass
from rich.console import Console
console = Console()
tobin = lambda list: '[' + ' '.join([f'{i:08b}' for i in list]) + ']'

class FakeConsole:
    def __init__(self, displayfn):
        self.displayfn = displayfn
    
    def log(self, msg):
        self.displayfn(msg)

@dataclass
class PinConfig:
    location: tuple
    opendrain: bool
    inverted: bool

class EPSConfig(Enum):
    CAN1 = PinConfig((0, 0), False, True)
    RS4851 = PinConfig((0, 1), True, False)
    I2C1 = PinConfig((0, 2), False, False)
    I2C1_PU = PinConfig((0, 3), False, True)
    UART1 = PinConfig((0, 4), False, True)
    UART1_REV = PinConfig((0, 5), False, False)
    SPI1 = PinConfig((0, 6), False, True)
    SPI1_SHIFT = PinConfig((0, 7), False, False)
    REG_3V3_EF = PinConfig((1, 0), True, False)
    REG_5V_EF = PinConfig((1, 1), True, False)
    REG_CH1_EF = PinConfig((1, 2), True, False)
    REG_CH2_EF = PinConfig((1, 3), True, False)
    RAW_PIN_BUS = PinConfig((1, 4), False, False)
    RAW_BAT_BUS = PinConfig((1, 5), False, False)
    VT3V3 = PinConfig((2, 0), False, True)
    VT5V = PinConfig((2, 1), False, True)
    VSYS = PinConfig((2, 2), False, True)
    GPIO = PinConfig((2, 3), False, True)

class OBCConfig(Enum):
    CAN1 = PinConfig((0, 0), False, True)
    # TODO: add other pins

class MISCConfig(Enum):
    CAN1 = PinConfig((0, 0), False, True)
    # TODO: add other pins

PCAL_IOCR = 0x70
PCAL_OUT = 0x04
PCAL_CFG = 0x0C
PCAL_ADDRESS = {
    EPSConfig: 0b00100001,
    OBCConfig: 0b00100000,
    MISCConfig: 0b00100010
}

CY8C_ADDRESSES = {
    # TODO: add CY8C addresses
}

class GSUConfig:
    def __init__(self, bus, device: Enum):
        self.bus = bus

        if not device in [EPSConfig, OBCConfig, MISCConfig]:
            raise Exception("Invalid device enum provided. Must be EPS, OBC, or MISC.")
        self.device = device
        
        self.opendrain = [0 for i in range(3)]
        self.state = [0 for i in range(3)]
        for pin in self.device:
            self.opendrain[pin.value.location[0]] |= (1 << pin.value.location[1]) if pin.value.opendrain else 0
            self.state[pin.value.location[0]] |= (1 << pin.value.location[1]) if pin.value.inverted else 0
        
        self.bus_write(PCAL_ADDRESS[self.device], PCAL_IOCR, self.opendrain)
        self.bus_write(PCAL_ADDRESS[self.device], PCAL_OUT, self.state)
        self.bus_write(PCAL_ADDRESS[self.device], PCAL_CFG, [0 for i in range(3)])
    
    def set_displayfn(self, displayfn):
        self.console = FakeConsole(displayfn)

    def bus_write(self, address, register, data, log=True):
        self.bus.write_i2c_block_data(address, register, data)
        if log:
            console.log(f"I2C {address:08b} >> {register:02X} = {tobin(data)}")

    def toggle_pin(self, pin):
        if type(pin) != self.device:
            raise Exception("Invalid pin enum provided. Must be of the same type as the device.")
        pin = pin.value
        
        self.state[pin.location[0]] ^= (1 << pin.location[1])
        self.bus_write(PCAL_ADDRESS[self.device], PCAL_OUT, self.state)

    def set_pin(self, pin, value):
        if type(pin) != self.device:
            raise Exception("Invalid pin enum provided. Must be of the same type as the device.")
        pin = pin.value
        
        self.state[pin.location[0]] &= ~(1 << pin.location[1])
        self.state[pin.location[0]] |= (1 << pin.location[1]) if value ^ pin.inverted else 0
        self.bus_write(PCAL_ADDRESS[self.device], PCAL_OUT, self.state)