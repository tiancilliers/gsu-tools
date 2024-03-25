from dataclasses import dataclass
import RPi.GPIO as gpio
import time
from functools import reduce
from rich.console import Console
console = Console()
tohex = lambda list: '[' + ' '.join([f'{i:02X}' for i in list]) + ']'

@dataclass
class Microcontroller:
    nrst: int
    boot: int
    nss: int

EPSMicro = Microcontroller(nrst=38, boot=40, nss=35)
OBCMicro = Microcontroller(nrst=11, boot=12, nss=36)
MISC1Micro = Microcontroller(nrst=16, boot=18, nss=15)
MISC2Micro = Microcontroller(nrst=37, boot=13, nss=22)

class GSUMicro:
    def __init__(self, bus, micro):
        self.micro = micro
        self.bus = bus

        gpio.setwarnings(False)
        gpio.setmode(gpio.BOARD)
        gpio.setup(self.micro.nrst, gpio.OUT, initial=gpio.HIGH)
        gpio.setup(self.micro.boot, gpio.OUT, initial=gpio.LOW)
        gpio.setup(self.micro.nss, gpio.OUT, initial=gpio.HIGH)
    
    def bus_xfer(self, data, log=True):
        orig = [b for b in data]
        ret = []
        for b in data:
            time.sleep(0.00005)
            ret.append(self.bus.xfer([b])[0])
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

    def send_bootldr_cmd(self, cmd, checksum=True, sof=False, verbose=True):
        time.sleep(0.01)
        self.gpio_output(self.micro.nss, 0)
        time.sleep(0.01)
        if verbose:
            console.log(f"Sending bootloader command: {tohex(cmd)}")
        else:
            console.log(f"Sending f{len(cmd)} bytes to bootloader")
        data = ([0x5a] if sof else []) + cmd + ([reduce(lambda x, y: x ^ y, cmd + ([0xFF] if len(cmd) == 1 else []))] if checksum else [])
        self.bus_xfer(data, log=verbose)
        self.gpio_output(self.micro.nss, 1)
    
    def get_bootldr_ack(self):
        time.sleep(0.01)
        self.gpio_output(self.micro.nss, 0)
        time.sleep(0.01)
        self.bus_xfer([0x00, 0xFF])
        while (res := self.bus_xfer([0x00], log=False)[0]) not in [0x79, 0x1F]:
            time.sleep(0.1)
        self.bus_xfer([0x79])
        self.gpio_output(self.micro.nss, 1)
        return res == 0x79

    def update_firmware(self, binary, base_address=0x08000000):
        console.log("Updating firmware...")
        self.reset_bootldr()
        
        self.send_bootldr_cmd([], checksum=False, sof=True)
        
        if not self.get_bootldr_ack():
            raise Exception("Bootloader returned NACK")

        blocks = [binary[i:i+256] for i in range(0, len(binary), 256)]
        blocks[-1] += b'\xFF' * (256 - len(blocks[-1]))
        addresses = [base_address + i * 256 for i in range(len(blocks))]

        for block, address in zip(blocks, addresses):
            self.send_bootldr_cmd([0x31], sof=True)
            if not self.get_bootldr_ack():
                raise Exception("Bootloader returned NACK")
            
            self.send_bootldr_cmd([address >> (24-i*8) & 0xFF for i in range(4)])
            if not self.get_bootldr_ack():
                raise Exception("Bootloader returned NACK")
            
            self.send_bootldr_cmd([0xFF] + list(block), verbose=False)
            if not self.get_bootldr_ack():
                raise Exception("Bootloader returned NACK")
    
        self.send_bootldr_cmd([0x21], sof=True)
        if not self.get_bootldr_ack():
            raise Exception("Bootloader returned NACK")
        
        self.send_bootldr_cmd([base_address >> (24-i*8) & 0xFF for i in range(4)])
        if not self.get_bootldr_ack():
            raise Exception("Bootloader returned NACK")


        

