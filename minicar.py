import serial
import time
import msvcrt

SERIAL_PORT = 'COM7'
SERIAL_BAUD = 2000000

ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=0.1)
print(f"Listening on {SERIAL_PORT}")

def receive_can(ser):
    """
        # id: low byte is frame[5], high byte is frame[3]
        data length code: frame[9]
        payload: frame[10:19] (10:10 + length)
    """
    frame = ser.read(20)
    can_id = (frame[3] << 8) | frame[5]
    dlc = frame[9]
    data = frame[10:10+dlc]
    data_hex = ' '.join([f'{b:02x}' for b in data])
    print(f"RX: ID=0x{can_id:03X} Data=[{data_hex}]")
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
    try:
        while True:
            # log all RX 
            if ser.in_waiting >= 20:
                receive_can(ser)
            
            # TX
            if msvcrt.kbhit():
                key = msvcrt.getch()
                if key == b' ':  # Spacebar
                    send_can_frame(ser, 0x103, [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
            
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        ser.close()

if __name__ == "__main__":
    main()