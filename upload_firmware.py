import gsuconfig
import gsumicro
import smbus
import spidev
import time
import sys

cfg_bus = smbus.SMBus(1)
spi_bus = spidev.SpiDev()
spi_bus.open(0, 0)
spi_bus.max_speed_hz = 100000

eps_cfg = gsuconfig.GSUConfig(cfg_bus, gsuconfig.EPSConfig)
eps_cfg.set_pin(gsuconfig.EPSConfig.VSYS, 1)
time.sleep(0.1)

eps_uc = gsumicro.GSUMicro(spi_bus, gsumicro.EPSMicro)
time.sleep(0.1)
with open(sys.argv[1], "rb") as f:
    eps_uc.update_firmware(f.read())