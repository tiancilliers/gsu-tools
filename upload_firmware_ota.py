import time
import sys

import gsuconfig
import smbus
cfg_bus = smbus.SMBus(1)
eps_cfg = gsuconfig.GSUConfig(cfg_bus, gsuconfig.EPSConfig)
eps_cfg.set_pin(gsuconfig.EPSConfig.VSYS, 1)
time.sleep(0.1)

import gsumicro
import spidev
spi_bus = spidev.SpiDev()
spi_bus.open(0, 0)
spi_bus.max_speed_hz = 400000

eps_uc = gsumicro.EPSMicro(spi_bus)
time.sleep(0.1)


eps_cfg.set_pin(gsuconfig.EPSConfig.REG_3V3_EF, True)
time.sleep(0.1)

eps_uc.write_regs(gsumicro.EPSReg.REG_3V3_STATE, [0x01])
time.sleep(0.1)

eps_cfg.set_pin(gsuconfig.EPSConfig.RAW_PIN_BUS, True)
time.sleep(3.0)

# reboot device into uart bootloader
eps_uc.write_regs(0x30, [0x01])
time.sleep(1.0)

with open(sys.argv[1], "rb") as f:
    eps_uc.update_firmware_ota(f.read(), base_address=0x08020000)

eps_cfg.set_pin(gsuconfig.EPSConfig.RAW_PIN_BUS, False)
