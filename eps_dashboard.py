from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.binding import Binding
from textual.widgets import Label, Button, Header, Footer, Static, RichLog, Footer, Sparkline

import gsuconfig
import smbus
cfg_bus = smbus.SMBus(1)
eps_cfg = gsuconfig.GSUConfig(cfg_bus, gsuconfig.EPSConfig)
eps_cfg.set_pin(gsuconfig.EPSConfig.VSYS, 1)

import gsumicro
import spidev
spi_bus = spidev.SpiDev()
spi_bus.open(0, 0)
spi_bus.max_speed_hz = 400000
eps_uc = gsumicro.EPSMicro(spi_bus)

class MyApp(App):
    CSS_PATH = "style.tcss"	
    TITLE = "EPS Dashboard"
    SUB_TITLE = "ESL GSU Tools"

    BINDINGS = [
        Binding(key="q", action="quit", description="Quit the app")
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Horizontal(RichLog(), id="log")
        yield Horizontal(Button("VSYS", id="cfg_vsys", disabled=True), Button("5V EF", id="cfg_5v"), Button("3V3 EF", id="cfg_3v3"), Button("RAW EF", id="cfg_raw"), id="config")
        #yield Horizontal(Button("RESET", id="cmd_rst"), Button("5V REG ON", id="cmd_5v"), Button("3V3 REG ON", id="cmd_3v3"), Button("LED ON", id="cmd_led"), id="commands")
        yield Horizontal(Button("RESET", id="cmd_rst"), Button("5V REG ON", id="cmd_5v"), Button("3V3 REG ON", id="cmd_3v3"), Button("BOOT", id="cmd_boot"), id="commands")
        yield Horizontal(
            Vertical(
                Label("[underline]3V3 REGULATOR[/underline]"),
                Horizontal(Label("3.300 V ", id="l3v3_v"), Sparkline(data=[0]*300, id="g3v3_v")),
                Horizontal(Label("0.000 A ", id="l3v3_i"), Sparkline(data=[0]*300, id="g3v3_i"))
            ),
            Vertical(
                Label("[underline]5V0 REGULATOR[/underline]"),
                Horizontal(Label("5.000 V ", id="l5v_v"), Sparkline(data=[0]*300, id="g5v_v")),
                Horizontal(Label("0.000 A ", id="l5v_i"), Sparkline(data=[0]*300, id="g5v_i"))
            ),
            id="status")
        yield Footer()
    
    def on_mount(self) -> None:
        self.query_one("#log").border_title = "Log"
        self.query_one("#config").border_title = "Configuration"
        self.query_one("#commands").border_title = "EPS Commands"
        self.query_one("#status").border_title = "Status"
        self.stats = eps_uc.get_stats()
        self.set_interval(1/5, self.update_status)
        self.query_one(RichLog).markup = True
        eps_cfg.set_displayfn(lambda text: self.query_one(RichLog).write(text))
        eps_uc.set_displayfn(lambda text: self.query_one(RichLog).write(text))
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cfg_vsys":
            eps_cfg.toggle_pin(gsuconfig.EPSConfig.VSYS)
        elif event.button.id == "cfg_5v":
            eps_cfg.toggle_pin(gsuconfig.EPSConfig.REG_5V_EF)
        elif event.button.id == "cfg_3v3":
            eps_cfg.toggle_pin(gsuconfig.EPSConfig.REG_3V3_EF)
        elif event.button.id == "cfg_raw":
            eps_cfg.toggle_pin(gsuconfig.EPSConfig.RAW_PIN_BUS)
        elif event.button.id == "cmd_rst":
            #eps_uc.reset()
            eps_uc.write_regs(0x20, [0x01])
        elif event.button.id == "cmd_5v":
            eps_uc.write_regs(gsumicro.EPSReg.REG_5V_STATE, [0x00 if self.stats["5V"]["state"] else 0x01])
        elif event.button.id == "cmd_3v3":
            eps_uc.write_regs(gsumicro.EPSReg.REG_3V3_STATE, [0x00 if self.stats["3V3"]["state"] else 0x01])
        #elif event.button.id == "cmd_led":
        #    eps_uc.write_regs(gsumicro.EPSReg.REG_LED_STATE, [0x01])
        elif event.button.id == "cmd_boot":
            self.query_one("#l3v3_v").renderable = eps_uc.re
    
    
    def update_status(self):
        self.stats = eps_uc.get_stats()
        self.query_one("#l3v3_v").renderable = f'{self.stats["3V3"]["voltage"]:.3f} V'
        self.query_one("#l3v3_i").renderable = f'{self.stats["3V3"]["current"]:.3f} A'
        self.query_one("#l5v_v").renderable = f'{self.stats["5V"]["voltage"]:.3f} V'
        self.query_one("#l5v_i").renderable = f'{self.stats["5V"]["current"]:.3f} A'
        self.query_one("#g3v3_v").data = [5] + self.query_one("#g3v3_v").data[2:] + [self.stats["3V3"]["voltage"]]
        self.query_one("#g3v3_i").data = [2] + self.query_one("#g3v3_i").data[2:] + [self.stats["3V3"]["current"]]
        self.query_one("#g5v_v").data = [5] + self.query_one("#g5v_v").data[2:] + [self.stats["5V"]["voltage"]]
        self.query_one("#g5v_i").data = [2] + self.query_one("#g5v_i").data[2:] + [self.stats["5V"]["current"]]
        self.query_one("#l3v3_v").refresh()
        self.query_one("#l3v3_i").refresh()
        self.query_one("#l5v_v").refresh()
        self.query_one("#l5v_i").refresh()
        self.query_one(RichLog).write(str(self.stats["BOOTL"]))

if __name__ == "__main__":
    app = MyApp()
    app.run()