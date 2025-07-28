from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import threading
import time
import gsuconfig
import smbus
import gsumicro
import spidev

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

cfg_bus = smbus.SMBus(1)
eps_cfg = gsuconfig.GSUConfig(cfg_bus, gsuconfig.EPSConfig)
eps_cfg.set_pin(gsuconfig.EPSConfig.VSYS, 1)

spi_bus = spidev.SpiDev()
spi_bus.open(0, 0)
spi_bus.max_speed_hz = 400000
eps_uc = gsumicro.EPSMicro(spi_bus)

time.sleep(0.1)

status = {}
eps_uc_lock = threading.Lock()

def poll_status():
    while True:
        stats = eps_uc.get_stats()
        socketio.emit('status', stats)
        time.sleep(0.2)

def emit_log(text):
    socketio.emit('log', text)

eps_cfg.set_displayfn(emit_log)
eps_uc.set_displayfn(emit_log)

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/action', methods=['POST'])
def action():
    # Accept both JSON and form data
    data = request.form.to_dict() if request.form else None
    if not data:
        try:
            data = request.get_json(force=True)
        except Exception:
            data = {}
    btn = data.get('button')
    with eps_uc_lock:
        if btn == "cfg_vsys":
            eps_cfg.toggle_pin(gsuconfig.EPSConfig.VSYS)
        elif btn == "cfg_5v":
            eps_cfg.toggle_pin(gsuconfig.EPSConfig.REG_5V_EF)
        elif btn == "cfg_3v3":
            eps_cfg.toggle_pin(gsuconfig.EPSConfig.REG_3V3_EF)
        elif btn == "cfg_raw":
            eps_cfg.toggle_pin(gsuconfig.EPSConfig.RAW_PIN_BUS)
        elif btn == "cmd_rst":
            eps_uc.reset()
        elif btn == "cmd_5v":
            eps_uc.write_regs(gsumicro.EPSReg.REG_5V_STATE, [0x00 if status.get("5V", {}).get("state") else 0x01])
        elif btn == "cmd_3v3":
            eps_uc.write_regs(gsumicro.EPSReg.REG_3V3_STATE, [0x00 if status.get("3V3", {}).get("state") else 0x01])
        elif btn == "cmd_led":
            eps_uc.write_regs(gsumicro.EPSReg.REG_LED_STATE, [0x01])
    return jsonify(success=True)

@socketio.on('connect')
def handle_connect():
    emit('status', eps_uc.get_stats())

if __name__ == '__main__':
    t = threading.Thread(target=poll_status, daemon=True)
    t.start()
    socketio.run(app, host='0.0.0.0', port=5000)
