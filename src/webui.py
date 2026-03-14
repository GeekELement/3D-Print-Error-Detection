from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import threading
import os
import queue
import time
import bambulabs_api as bl
from config import config

app = Flask(__name__, template_folder=os.path.dirname(__file__))
app.config['SECRET_KEY'] = 'bambu_secret'
socketio = SocketIO(app, cors_allowed_origins="*")

printer = None
status_thread = None
camera_thread = None
running = False
camera_running = False
frame_queue = queue.Queue(maxsize=5)
led_state = False

def get_shared_printer():
    global printer
    return printer

def status_loop():
    global running
    while running:
        if printer and printer.mqtt_client_connected():
            try:
                status = printer.mqtt_dump()
                if "print" in status:
                    ps = status["print"]
                    state = ps.get("gcode_state", "unknown")
                    state_map = {
                        "IDLE": "Idle",
                        "PRINTING": "Printing",
                        "PAUSED": "Paused",
                        "FINISHED": "Finished",
                        "FAILED": "Failed",
                        "RUNNING": "Printing"
                    }
                    try:
                        gcode_file = printer.gcode_file()
                    except:
                        gcode_file = ps.get("gcode_file", "No file")
                    
                    socketio.emit('status', {
                        'state': state_map.get(state.upper(), state),
                        'progress': ps.get("mc_percent", 0),
                        'layer': ps.get("layer_num", 0),
                        'total_layer': ps.get("total_layer_num", 0),
                        'file': gcode_file,
                        'nozzle': ps.get("nozzle_temper", 0),
                        'nozzle_target': ps.get("nozzle_target_temper", 0),
                        'bed': ps.get("bed_temper", 0),
                        'bed_target': ps.get("bed_target_temper", 0),
                        'connected': True
                    })
            except Exception as e:
                socketio.emit('log', {'message': f'Status error: {e}'})
        socketio.sleep(1)

def camera_loop():
    global camera_running
    while camera_running:
        if printer and printer.camera_client_alive():
            try:
                frame = printer.get_camera_frame()
                if frame:
                    socketio.emit('camera', {'image': frame})
                    try:
                        if frame_queue.full():
                            try:
                                frame_queue.get_nowait()
                            except:
                                pass
                        frame_queue.put(frame)
                    except:
                        pass
            except Exception as e:
                socketio.emit('log', {'message': f'Camera error: {e}'})
        socketio.sleep(2)

@app.route('/')
def index():
    return render_template('webui.html')

@socketio.on('connect')
def handle_connect():
    emit('log', {'message': 'Web client connected'})
    if printer and printer.mqtt_client_connected():
        emit('connected', {'status': True})
    emit('led_status', {'on': led_state})

def wait_for_mqtt():
    for _ in range(10):
        socketio.sleep(1)
        if printer and printer.mqtt_client_connected():
            return True
    return False

@socketio.on('connect_printer')
def handle_connect_printer():
    global printer, running, status_thread, camera_thread, camera_running
    try:
        host = config.get_str('printer.host', '')
        access_code = config.get_str('printer.access_code', '')
        serial_number = config.get_str('printer.serial_number', '')
        
        emit('log', {'message': f'Connecting to {host}...'})
        printer = bl.Printer(host, access_code, serial_number)
        printer.connect()
        emit('log', {'message': 'TCP Connected, starting MQTT...'})
        printer.mqtt_start()
        emit('log', {'message': 'MQTT started, waiting for data...'})
        
        if wait_for_mqtt():
            emit('log', {'message': 'Connected to printer'})
            running = True
            status_thread = socketio.start_background_task(status_loop)
            
            emit('log', {'message': 'Starting camera...'})
            try:
                printer.camera_start()
                camera_running = True
                camera_thread = socketio.start_background_task(camera_loop)
                emit('log', {'message': 'Camera started'})
            except Exception as e:
                emit('log', {'message': f'Camera not available: {e}'})
            
            emit('connected', {'status': True})
        else:
            emit('log', {'message': 'MQTT connection timeout'})
            emit('connected', {'status': False})
    except Exception as e:
        emit('log', {'message': f'Connection failed: {e}'})
        emit('connected', {'status': False})

@socketio.on('disconnect_printer')
def handle_disconnect_printer():
    global printer, running, camera_running
    running = False
    camera_running = False
    if printer:
        try:
            printer.mqtt_stop()
            printer.disconnect()
        except:
            pass
        printer = None
    emit('log', {'message': 'Disconnected'})
    emit('connected', {'status': False})

@socketio.on('pause')
def handle_pause():
    try:
        printer.pause_print()
        emit('log', {'message': 'Pause command sent'})
    except Exception as e:
        emit('log', {'message': f'Error: {e}'})

@socketio.on('resume')
def handle_resume():
    try:
        printer.resume_print()
        emit('log', {'message': 'Resume command sent'})
    except Exception as e:
        emit('log', {'message': f'Error: {e}'})

@socketio.on('stop')
def handle_stop():
    try:
        printer.stop_print()
        emit('log', {'message': 'Stop command sent'})
    except Exception as e:
        emit('log', {'message': f'Error: {e}'})

@socketio.on('led')
def handle_led(data):
    global led_state
    try:
        led_state = data.get('state', False)
        if led_state:
            printer.turn_light_on()
            emit('log', {'message': 'LED turned on'})
        else:
            printer.turn_light_off()
            emit('log', {'message': 'LED turned off'})
        emit('led_status', {'on': led_state})
    except Exception as e:
        emit('log', {'message': f'LED control error: {e}'})

def get_latest_frame(timeout=5):
    try:
        return frame_queue.get(timeout=timeout)
    except queue.Empty:
        return None

def is_camera_ready():
    return printer and printer.camera_client_alive()

def is_printer_connected():
    return printer and printer.mqtt_client_connected()

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)
