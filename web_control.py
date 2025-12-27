from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import can
import time
import threading

app = Flask(__name__)
CORS(app)

# CAN IDs
CANID_MOTOR_CMD = 0x100
CANID_RX_HEARTBEAT = 0x103
CANID_TX_HEARTBEAT = 0x104

# Commands
CMD_STOP = 0
CMD_FORWARD = 3
CMD_BACKWARD = 4
CMD_TURN_LEFT = 1
CMD_TURN_RIGHT = 2

# Global state
bus = None
last_rx_heartbeat = 0
last_tx_heartbeat = 0
telemetry_data = {
    'connected': False,
    'last_command': 'STOP',
    'heartbeat_ok': False,
    'messages_received': 0
}

def setup_can_bus():
    """Initialize CAN bus connection"""
    try:
        bus = can.interface.Bus(
            channel='can0',
            interface='socketcan',
            bitrate=500000
        )
        print(f"✓ Connected to CAN bus on can0 at 500 kbps")
        telemetry_data['connected'] = True
        return bus
    except Exception as e:
        print(f"✗ Failed to connect to CAN bus: {e}")
        telemetry_data['connected'] = False
        return None

def send_can_frame(can_id, data):
    """Send a CAN frame"""
    if bus is None:
        return False
    
    message = can.Message(
        arbitration_id=can_id,
        data=data,
        is_extended_id=False
    )
    
    try:
        bus.send(message)
        data_hex = ' '.join([f'{b:02x}' for b in data])
        print(f"TX: ID=0x{can_id:03X} Data=[{data_hex}]")
        return True
    except Exception as e:
        print(f"✗ Error sending message: {e}")
        return False

def heartbeat_thread():
    """Background thread to send heartbeat and receive messages"""
    global last_tx_heartbeat, last_rx_heartbeat
    
    while True:
        # Send heartbeat every 1 second
        if time.time() - last_tx_heartbeat > 1:
            send_can_frame(CANID_RX_HEARTBEAT, [0x00] * 8)
            last_tx_heartbeat = time.time()
        
        # Receive CAN messages
        if bus:
            message = bus.recv(timeout=0.01)
            if message:
                can_id = message.arbitration_id
                data = message.data
                data_hex = ' '.join([f'{b:02x}' for b in data])
                print(f"RX: ID=0x{can_id:03X} Data=[{data_hex}]")
                
                telemetry_data['messages_received'] += 1
                
                if can_id == CANID_TX_HEARTBEAT:
                    last_rx_heartbeat = time.time()
                    telemetry_data['heartbeat_ok'] = True
        
        # Check heartbeat timeout
        if last_rx_heartbeat > 0 and time.time() - last_rx_heartbeat > 5:
            telemetry_data['heartbeat_ok'] = False
        
        time.sleep(0.01)

@app.route('/')
def index():
    return render_template('control.html')

@app.route('/command', methods=['POST'])
def send_command():
    """Handle motor command from web interface"""
    data = request.json
    command = data.get('command')
    speed = data.get('speed', 50)
    
    # Map commands to CAN values
    cmd_map = {
        'forward': CMD_FORWARD,
        'backward': CMD_BACKWARD,
        'left': CMD_TURN_LEFT,
        'right': CMD_TURN_RIGHT,
        'stop': CMD_STOP
    }
    
    if command not in cmd_map:
        return jsonify({'status': 'error', 'message': 'Invalid command'}), 400
    
    cmd_value = cmd_map[command]
    speed_value = 0 if command == 'stop' else int(speed)
    
    # Send CAN message
    can_data = [cmd_value, speed_value, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
    success = send_can_frame(CANID_MOTOR_CMD, can_data)
    
    if success:
        telemetry_data['last_command'] = command.upper()
        return jsonify({
            'status': 'success',
            'command': command,
            'speed': speed_value
        })
    else:
        return jsonify({'status': 'error', 'message': 'CAN send failed'}), 500

@app.route('/status', methods=['GET'])
def get_status():
    """Return current system status"""
    return jsonify({
        'connected': telemetry_data['connected'],
        'last_command': telemetry_data['last_command'],
        'heartbeat_ok': telemetry_data['heartbeat_ok'],
        'messages_received': telemetry_data['messages_received'],
        'timestamp': time.time()
    })

if __name__ == '__main__':
    # Initialize CAN bus
    bus = setup_can_bus()
    
    if bus is None:
        print("\n⚠ Warning: CAN bus not available. Running in demo mode.")
        print("Commands will be logged but not sent.\n")
    
    # Start heartbeat thread
    thread = threading.Thread(target=heartbeat_thread, daemon=True)
    thread.start()
    
    print("\n" + "="*50)
    print("🚗 Mini Car Web Control Server Starting")
    print("="*50)
    
    app.run(host='0.0.0.0', port=5000, debug=False)
