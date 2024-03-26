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

eps_uc = gsumicro.GSUMicro(spi_bus, gsumicro.EPSPins)
time.sleep(0.1)
with open(sys.argv[1], "rb") as f:
    eps_uc.update_firmware(f.read())