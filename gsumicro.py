from dataclasses import dataclass
import RPi.GPIO as gpio
import time
from functools import reduce
from rich.console import Console
from rich.progress import track
from enum import Enum

console = Console()
tohex = lambda list: '[' + ' '.join([f'{i:02X}' for i in list]) + ']'
bytes_read_int16_2s = lambda msb, lsb: ((msb << 8) | lsb) if msb < 0x80 else -((msb ^ 0xFF) << 8 | (lsb ^ 0xFF)) - 1

class FakeConsole:
    def __init__(self, displayfn):
        self.displayfn = displayfn
    
    def log(self, msg):
        self.displayfn(msg)    

@dataclass
class Microcontroller:
    nrst: int
    boot: int
    nss: int

EPSPins = Microcontroller(nrst=38, boot=40, nss=35)
OBCPins = Microcontroller(nrst=11, boot=12, nss=36)
MISC1Pins = Microcontroller(nrst=16, boot=18, nss=15)
MISC2Pins = Microcontroller(nrst=37, boot=13, nss=22)

BYTE_TIME = 0.00002

class GSUMicro:
    def __init__(self, bus, micro):
        self.micro = micro
        self.bus = bus

        gpio.setwarnings(False)
        gpio.setmode(gpio.BOARD)
        gpio.setup(self.micro.nrst, gpio.OUT, initial=gpio.HIGH)
        gpio.setup(self.micro.boot, gpio.OUT, initial=gpio.LOW)
        gpio.setup(self.micro.nss, gpio.OUT, initial=gpio.HIGH)
    
    def set_displayfn(self, displayfn):
        global console
        console = FakeConsole(displayfn)
    
    def bus_xfer(self, data, log=False):
        orig = [b for b in data]
        ret = self.bus.xfer(data)
        if log:
            console.log(f"SPI >> {tohex(orig)} << {tohex(ret)}")
        return ret
    
    def gpio_output(self, pin, state, log=True):
        gpio.output(pin, gpio.HIGH if state == 1 else gpio.LOW)
        if log:
            console.log(f"GPIO {pin} = {state}")

    def reset(self):
        console.log("Resetting microcontroller...")
        self.gpio_output(self.micro.nrst, 0)
        time.sleep(0.1)
        self.gpio_output(self.micro.nrst, 1)
        time.sleep(0.1)
    
    def reset_bootldr(self):
        console.log("Entering bootloader...")
        self.gpio_output(self.micro.boot, 1)
        time.sleep(0.1)
        self.reset()
        self.gpio_output(self.micro.boot, 0)

    def send_cmd(self, cmd, checksum=True, sof=False, log=False, slowfirst=False):
        self.gpio_output(self.micro.nss, 0, log=False)
        time.sleep(BYTE_TIME)
        if log:
            console.log(f"Sending command: {tohex(cmd)}")
        data = ([0x5a] if sof else []) + cmd + ([reduce(lambda x, y: x ^ y, cmd + ([0xFF] if len(cmd) == 1 else []))] if checksum else [])
        if slowfirst:
            self.bus_xfer([data[0]], log=log)
            self.gpio_output(self.micro.nss, 1, log=False)
            time.sleep(0.01)
            self.gpio_output(self.micro.nss, 0, log=False)
            time.sleep(0.01)
            if len(data) > 1:
                self.bus_xfer(data[1:], log=log)
        else:
            self.bus_xfer(data, log=log)
        self.gpio_output(self.micro.nss, 1, log=False)
    
    def get_ack(self, log=False, slowfirst=False, timeout=1e6):
        self.gpio_output(self.micro.nss, 0, log=False)
        time.sleep(BYTE_TIME)
        self.bus_xfer([0x00], log=log)
        if slowfirst:
            self.gpio_output(self.micro.nss, 1, log=False)
            time.sleep(0.01)
            self.gpio_output(self.micro.nss, 0, log=False)
            time.sleep(0.01)
        iter = 0
        while (res := self.bus_xfer([0x00], log=log)[0]) not in [0x79, 0x1F]:
            iter += 1
            if iter > timeout:
                raise Exception("SPI iterations exceeded")
        if res != 0x79:
            raise Exception("SPI returned NACK")
        self.bus_xfer([0x79], log=log)
        self.gpio_output(self.micro.nss, 1, log=False)

    def recv_data(self, log=False):
        self.gpio_output(self.micro.nss, 0, log=False)
        time.sleep(BYTE_TIME)
        length = self.bus_xfer([0x00], log=log)[0]+1
        data = self.bus_xfer([0x00] * length, log=log)
        self.gpio_output(self.micro.nss, 1, log=False)
        return data

    def update_firmware(self, binary, base_address=0x08000000):
        console.log("Updating firmware...")
        self.reset_bootldr()
        
        self.send_cmd([], checksum=False, sof=True)
        self.get_ack()

        self.send_cmd([0x44], sof=True)
        self.get_ack()
        self.send_cmd([0x00, 0x00])
        self.get_ack()
        self.send_cmd([0x00, 0x00])
        self.get_ack()

        blocks = [binary[i:i+256] for i in range(0, len(binary), 256)]
        blocks[-1] += b'\xFF' * (256 - len(blocks[-1]))
        addresses = [base_address + i * 256 for i in range(len(blocks))]

        for block, address in track(zip(blocks, addresses), total=len(blocks), description="Uploading..."):
            self.send_cmd([0x31], sof=True)
            self.get_ack()
            self.send_cmd([address >> (24-i*8) & 0xFF for i in range(4)])
            self.get_ack()
            self.send_cmd([0xFF] + list(block), log=False)
            self.get_ack()
    
        self.send_cmd([0x21], sof=True)
        self.get_ack()
        self.send_cmd([base_address >> (24-i*8) & 0xFF for i in range(4)])
        self.get_ack()

class EPSReg(Enum):
    REG_3V3_STATE = 0x00
    REG_5V_STATE = 0x01
    REG_CH1_STATE = 0x02
    REG_CH2_STATE = 0x03
    REG_LED_STATE = 0x08
    REG_3V3_V = 0x10
    REG_3V3_I = 0x12
    REG_5V_V = 0x14
    REG_5V_I = 0x16
    REG_CH1_V = 0x18
    REG_CH1_I = 0x1A
    REG_CH2_V = 0x1C
    REG_CH2_I = 0x1E
    REG_RAW_V = 0x20
    REG_RAW_I = 0x22

class EPSMicro(GSUMicro):
    def __init__(self, bus):
        super().__init__(bus, EPSPins)

    def write_regs(self, addr, data, log=True):
        if type(addr) is EPSReg:
            addr = addr.value
        self.send_cmd([0x01], log=log, sof=True, slowfirst=True)
        self.get_ack(slowfirst=True, log=log, timeout=100)
        self.send_cmd([len(data), addr] + data, slowfirst=True, log=log)
        self.get_ack(slowfirst=True, log=log, timeout=100)
    
    def test_bootloader(self):
        self.send_cmd([0x03], log=True, sof=True, slowfirst=True)
        self.get_ack(slowfirst=True, log=True, timeout=100)
    
    def read_all(self, log=False):
        self.send_cmd([0x02], log=log, sof=True, slowfirst=True)
        time.sleep(0.01)
        self.get_ack(slowfirst=True, log=log, timeout=100)
        time.sleep(0.01)
        ret = self.recv_data(log=log)
        time.sleep(0.01)
        self.get_ack(slowfirst=True, log=log, timeout=100)
        return ret

    def get_stats(self):
        data = self.read_all()
        return {
            "3V3": {
                "state": data[EPSReg.REG_3V3_STATE.value],
                "voltage": 0.004*bytes_read_int16_2s(data[EPSReg.REG_3V3_V.value], data[EPSReg.REG_3V3_V.value+1]),
                "current": 0.0005*bytes_read_int16_2s(data[EPSReg.REG_3V3_I.value], data[EPSReg.REG_3V3_I.value+1])
            },
            "5V": {
                "state": data[EPSReg.REG_5V_STATE.value],
                "voltage": 0.004*bytes_read_int16_2s(data[EPSReg.REG_5V_V.value], data[EPSReg.REG_5V_V.value+1]),
                "current": 0.0005*bytes_read_int16_2s(data[EPSReg.REG_5V_I.value], data[EPSReg.REG_5V_I.value+1])
            },
            "RAW": {
                "voltage": 0.004*bytes_read_int16_2s(data[EPSReg.REG_RAW_V.value], data[EPSReg.REG_RAW_V.value+1]),
                "current": 0.0005*bytes_read_int16_2s(data[EPSReg.REG_RAW_I.value], data[EPSReg.REG_RAW_I.value+1])
            }
        }