from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import threading
import time
import gsuconfig
import smbus
import gsumicro
import spidev
import os
from datetime import datetime

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
telemetry_log_file = None
global_time_counter = 0

def start_new_telemetry_log():
    global telemetry_log_file, global_time_counter
    # Ensure logs directory exists
    os.makedirs('logs', exist_ok=True)
    # Filename with current time
    fname = datetime.now().strftime('logs/%Y%m%d_%H%M%S.csv')
    telemetry_log_file = open(fname, 'w', encoding='utf-8')
    # Write CSV header
    header = ['time_ms', 'pressure', 'temperature', 'power'] + [f'valve{i}' for i in range(16)]
    telemetry_log_file.write(','.join(header) + '\n')
    telemetry_log_file.flush()
    global_time_counter = 0
    # Reset logging on hardware
    eps_uc.write_regs(0x2F, [0x01])

start_new_telemetry_log()

time.sleep(0.1)

def update_and_emit_status():
    global status, telemetry_log_file, global_time_counter
    with eps_uc_lock:
        status = eps_uc.get_stats()
    # Add EF and REG state info for toggles
    efuse_state = {
        '3v3': bool(eps_cfg.state[1] & (1 << 0)),  # REG_3V3_EF
        '5v': bool(eps_cfg.state[1] & (1 << 1)),   # REG_5V_EF
        'raw': bool(eps_cfg.state[1] & (1 << 4)),  # RAW_PIN_BUS
    }
    reg_state = {
        '3v3': status.get('3V3', {}).get('state', False),
        '5v': status.get('5V', {}).get('state', False),
    }
    status['efuse'] = efuse_state
    status['reg'] = reg_state
    status['telav'] = status.get('TEL_AVAIL', False)
    status['telemetry'] = status.get('TELEMETRY', [])
    # --- Telemetry logging ---
    if telemetry_log_file and status['telemetry']:
        for entry in status['telemetry']:
            # entry: [pressure, temperature, power, [valve0..valve15]]
            row = [str(global_time_counter), str(entry[0]), str(entry[1]), str(entry[2])] + [str(v) for v in entry[3]]
            telemetry_log_file.write(','.join(row) + '\n')
            global_time_counter += 5
        telemetry_log_file.flush()
    socketio.emit('status', status)

def poll_status():
    while True:
        time.sleep(0.2)
        update_and_emit_status()

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
        elif btn == "cmd_reset_logging":
            start_new_telemetry_log()
        elif btn == "dis_pl1":
            eps_uc.write_regs(0x28, [0x01])
        elif btn == "en_pl1":
            eps_uc.write_regs(0x29, [0x01])
        elif btn == "dis_pl2":
            eps_uc.write_regs(0x2A, [0x01])
        elif btn == "en_pl2":
            eps_uc.write_regs(0x2B, [0x01])
        elif btn == "dis_seq":
            eps_uc.write_regs(0x2C, [0x01])
        elif btn == "en_seq":
            eps_uc.write_regs(0x2D, [0x01])

    return jsonify(success=True)

@socketio.on('connect')
def handle_connect():
    update_and_emit_status()

if __name__ == '__main__':
    t = threading.Thread(target=poll_status, daemon=True)
    t.start()
    socketio.run(app, host='0.0.0.0', port=5000)
