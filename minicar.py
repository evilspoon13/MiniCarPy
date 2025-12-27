import can
import time
import sys
import select
import termios
import tty

CANID_MOTOR_CMD = 0x100
CANID_RX_HEARTBEAT = 0x103
CANID_TX_HEARTBEAT = 0x104

CMD_STOP = 0
CMD_FORWARD = 3 
CMD_BACKWARD = 4
CMD_TURN_LEFT = 1
CMD_TURN_RIGHT = 2

last_rx_heartbeat = 0
last_tx_heartbeat = 0
current_speed = 50  # default speed (0-99 PWM)

def setup_can_bus():
    """Initialize CAN bus connection"""
    try:
        bus = can.interface.Bus(
            channel='can0',
            interface='socketcan',
            bitrate=500000
        )
        print(f"✓ Connected to CAN bus on can0 at 500 kbps")
        return bus
    except Exception as e:
        print(f"✗ Failed to connect to CAN bus: {e}")
        print("\nTroubleshooting:")
        print("1. Bring up CAN interface: sudo ip link set can0 up type can bitrate 500000")
        print("2. Check interface: ip link show can0")
        print("3. Install python-can: pip install python-can")
        sys.exit(1)

def receive_can(bus):
    """Receive and process CAN messages"""
    global last_rx_heartbeat
    
    # Non-blocking receive with timeout
    message = bus.recv(timeout=0.01)
    
    if message:
        can_id = message.arbitration_id
        data = message.data
        data_hex = ' '.join([f'{b:02x}' for b in data])
        print(f"RX: ID=0x{can_id:03X} Data=[{data_hex}]")
        
        if can_id == CANID_TX_HEARTBEAT:
            last_rx_heartbeat = time.time()

def send_can_frame(bus, can_id, data):
    """Send a CAN frame"""
    message = can.Message(
        arbitration_id=can_id,
        data=data,
        is_extended_id=False
    )
    
    try:
        bus.send(message)
        data_hex = ' '.join([f'{b:02x}' for b in data])
        print(f"TX: ID=0x{can_id:03X} Data=[{data_hex}]")
    except Exception as e:
        print(f"✗ Error sending message: {e}")

def get_key():
    """Get keyboard input (non-blocking)"""
    if select.select([sys.stdin], [], [], 0)[0]:
        return sys.stdin.read(1).encode()
    return None

def main():
    global current_speed, last_tx_heartbeat, last_rx_heartbeat
    
    # Initialize CAN bus
    bus = setup_can_bus()
    
    print("\nControls: WASD=movement, SPACE=stop, 1-9=speed (1=11%, 9=99%)")
    print("Press Ctrl+C to exit\n")
    
    # Set up terminal for non-blocking input
    old_settings = termios.tcgetattr(sys.stdin)
    tty.setcbreak(sys.stdin.fileno())
    
    try:
        while True:
            # log all RX 
            if ser.in_waiting >= 20:
                receive_can(ser)
            
            global last_tx_heartbeat

            # send heartbeat to 
            if time.time() - last_tx_heartbeat > 1:
                send_can_frame(ser, CANID_RX_HEARTBEAT, [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
                last_tx_heartbeat = time.time()
            # TX
            if msvcrt.kbhit():
                key = msvcrt.getch()
                
                # Speed control (1-9)
                if key in [b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'8', b'9']:
                    speed_level = int(key.decode())
                    current_speed = int(speed_level * 11)  # Map 1-9 to 11-99 PWM
                    print(f"Speed set to: {current_speed}%")
                
                # Movement commands
                elif key == b'w':   # forward
                    send_can_frame(bus, CANID_MOTOR_CMD, [CMD_FORWARD, current_speed, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
                elif key == b'a':   # left
                    send_can_frame(bus, CANID_MOTOR_CMD, [CMD_TURN_LEFT, current_speed, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
                elif key == b's':   # backward
                    send_can_frame(bus, CANID_MOTOR_CMD, [CMD_BACKWARD, current_speed, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
                elif key == b'd':   # right
                    send_can_frame(bus, CANID_MOTOR_CMD, [CMD_TURN_RIGHT, current_speed, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
                elif key == b' ':   # stop
                    send_can_frame(bus, CANID_MOTOR_CMD, [CMD_STOP, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
            
            # Check heartbeat timeout
            if last_rx_heartbeat > 0 and time.time() - last_rx_heartbeat > 5:
                print("⚠ Heartbeat timeout")
                last_rx_heartbeat = 0  # Reset to avoid spam
            
            time.sleep(0.01)
            
    except KeyboardInterrupt:
        print("\n\nStopped")
    finally:
        # Restore terminal settings
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        bus.shutdown()
        print("CAN bus closed.")

if __name__ == "__main__":
    main()
