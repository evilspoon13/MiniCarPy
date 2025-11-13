import serial
import time
import msvcrt

SERIAL_PORT = 'COM7'
SERIAL_BAUD = 2000000

CANID_MOTOR_CMD = 0x100
CANID_RX_HEARTBEAT = 0x103
CANID_TX_HEARTBEAT = 0x104

CMD_STOP = 0
CMD_FORWARD = 1
CMD_BACKWARD = 2
CMD_TURN_LEFT = 3
CMD_TURN_RIGHT = 4

last_rx_heartbeat = 0
current_speed = 50  # default speed (0-99 PWM)

ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=0.1)
print(f"Listening on {SERIAL_PORT}")
print("Controls: WASD=movement, SPACE=stop, 1-9=speed (1=11%, 9=99%)")

def receive_can(ser):
    """
        # id: low byte is frame[5], high byte is frame[3]
        data length code: frame[9]
        payload: frame[10:19] (10:10 + length)
    """
    global last_rx_heartbeat
    
    frame = ser.read(20)
    can_id = (frame[3] << 8) | frame[5]
    dlc = frame[9]
    data = frame[10:10+dlc]
    data_hex = ' '.join([f'{b:02x}' for b in data])
    print(f"RX: ID=0x{can_id:03X} Data=[{data_hex}]")

    if can_id == CANID_TX_HEARTBEAT:
        last_rx_heartbeat = time.time()

    #print(frame)

def send_can_frame(ser, can_id, data):
    """
        Send a CAN frame via Waveshare adapter in binary format
        Frame structure: [0xAA, 0x55, ?, id_h, ?, id_l, ?, ?, ?, dlc, data[0-7], ?, checksum]
    """
    dlc = len(data)
    
    frame = bytearray(20)
    frame[0] = 0xAA  # Header
    frame[1] = 0x55  # Header
    frame[2] = 0x01  # Unknown
    frame[3] = (can_id >> 8) & 0xFF  # CAN ID high byte
    frame[4] = 0x01  # Unknown
    frame[5] = can_id & 0xFF  # CAN ID low byte
    frame[6] = 0x01  # Unknown
    frame[7] = 0x00  # Unknown
    frame[8] = 0x00  # Unknown
    frame[9] = dlc   # Data length
    
    for i in range(dlc):
        frame[10 + i] = data[i]
    
    # Calculate checksum: SUM(bytes 0-18) + 1
    checksum = (sum(frame[0:19]) + 1) & 0xFF
    frame[19] = checksum
    
    ser.write(bytes(frame))
    data_hex = ' '.join([f'{b:02x}' for b in data[:dlc]])
    print(f"TX: ID=0x{can_id:03X} Data=[{data_hex}]")

def main():
    global current_speed
    
    try:
        while True:
            # log all RX 
            if ser.in_waiting >= 20:
                receive_can(ser)
            
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
                    send_can_frame(ser, CANID_MOTOR_CMD, [CMD_FORWARD, current_speed, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
                elif key == b'a':   # left
                    send_can_frame(ser, CANID_MOTOR_CMD, [CMD_TURN_LEFT, current_speed, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
                elif key == b's':   # backward
                    send_can_frame(ser, CANID_MOTOR_CMD, [CMD_BACKWARD, current_speed, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
                elif key == b'd':   # right
                    send_can_frame(ser, CANID_MOTOR_CMD, [CMD_TURN_RIGHT, current_speed, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
                elif key == b' ':   # stop
                    send_can_frame(ser, CANID_MOTOR_CMD, [CMD_STOP, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
            
            if time.time() - last_rx_heartbeat > 1:
                print("Heartbeat timeout")
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        ser.close()

if __name__ == "__main__":
    main()