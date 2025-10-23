import can
import keyboard
import time
import sys
from enum import IntEnum


class MotorCommand(IntEnum):
    """Motor command codes matching STM32 firmware"""
    CMD_STOP = 0x00
    CMD_FORWARD = 0x01
    CMD_BACKWARD = 0x02
    CMD_TURN_LEFT = 0x03
    CMD_TURN_RIGHT = 0x04


class CANCarController:
    """Main controller class for CAN car interface"""
    
    # CAN Message IDs
    CAN_ID_MOTOR_CMD = 0x100
    CAN_ID_EMERGENCY_STOP = 0x101
    CAN_ID_CONFIG = 0x102
    
    def __init__(self, interface='socketcan', channel='can0', bitrate=500000):
        try:
            self.bus = can.interface.Bus(
                channel=channel,
                bustype=interface,
                bitrate=bitrate
            )
            print(f"Connected to CAN bus: {channel} at {bitrate} bps")
        except Exception as e:
            print(f"Failed to connect to CAN bus: {e}")
            sys.exit(1)
        
        self.current_speed = 50  # Default speed (0-100)
        self.running = True
        self.last_command = MotorCommand.CMD_STOP
        
    def send_motor_command(self, command, speed=None):
        """
        Send motor command via CAN
        
        Args:
            command: MotorCommand enum value
            speed: Speed value 0-100 (optional, uses current_speed if None)
        """
        if speed is None:
            speed = self.current_speed
        
        # clamp speed
        speed = max(0, min(100, speed))
        
        # Pack CAN message: [command, speed, 0, 0, 0, 0, 0, 0]
        data = [command, speed, 0, 0, 0, 0, 0, 0]
        
        message = can.Message(
            arbitration_id=self.CAN_ID_MOTOR_CMD,
            data=data,
            is_extended_id=False
        )
        
        try:
            self.bus.send(message)
            self.last_command = command
            print(f"→ Sent: {MotorCommand(command).name}, Speed: {speed}%")
        except Exception as e:
            print(f"✗ Error sending message: {e}")
    
    def send_emergency_stop(self):
        message = can.Message(
            arbitration_id=self.CAN_ID_EMERGENCY_STOP,
            data=[0xFF, 0, 0, 0, 0, 0, 0, 0],
            is_extended_id=False
        )
        
        try:
            self.bus.send(message)
            print("emergency stopping")
        except Exception as e:
            print(f"Error sending emergency stop: {e}")
    
    def send_config(self, max_speed=100, timeout_ms=1000):
        """
        Send configuration parameters to car
        
        Args:
            max_speed: Maximum allowed speed (0-100)
            timeout_ms: Heartbeat timeout in milliseconds
        """
        # Pack config: [max_speed, timeout_high_byte, timeout_low_byte, ...]
        timeout_high = (timeout_ms >> 8) & 0xFF
        timeout_low = timeout_ms & 0xFF
        
        data = [max_speed, timeout_high, timeout_low, 0, 0, 0, 0, 0]
        
        message = can.Message(
            arbitration_id=self.CAN_ID_CONFIG,
            data=data,
            is_extended_id=False
        )
        
        try:
            self.bus.send(message)
            print(f"Config sent: Max Speed={max_speed}%, Timeout={timeout_ms}ms")
        except Exception as e:
            print(f"Error sending config: {e}")
    
    def adjust_speed(self, delta):
        self.current_speed = max(0, min(100, self.current_speed + delta))
        print(f"Speed adjusted to {self.current_speed}%")
        # Resend last command with new speed
        if self.last_command != MotorCommand.CMD_STOP:
            self.send_motor_command(self.last_command)
    
    def print_controls(self):
        """Print control instructions"""
        print("\n" + "="*50)
        print("CAN CAR CONTROLLER - KEYBOARD CONTROLS")
        print("="*50)
        print("Movement:")
        print("  W - Forward")
        print("  S - Backward")
        print("  A - Turn Left")
        print("  D - Turn Right")
        print("  SPACE - Stop")
        print("\nSpeed Control:")
        print("  + / = - Increase speed")
        print("  - / _ - Decrease speed")
        print("\nOther:")
        print("  E - Emergency Stop")
        print("  C - Send Config")
        print("  Q - Quit")
        print("="*50)
        print(f"Current Speed: {self.current_speed}%\n")
    
    def run(self):
        self.print_controls()
        
        print("Controller ready. Press keys to control the car...")
        print("Press 'Q' to quit.\n")
        
        try:
            while self.running:
                if keyboard.is_pressed('w'):
                    self.send_motor_command(MotorCommand.CMD_FORWARD)
                    time.sleep(0.1)
                
                elif keyboard.is_pressed('s'):
                    self.send_motor_command(MotorCommand.CMD_BACKWARD)
                    time.sleep(0.1)
                
                elif keyboard.is_pressed('a'):
                    self.send_motor_command(MotorCommand.CMD_TURN_LEFT)
                    time.sleep(0.1)
                
                elif keyboard.is_pressed('d'):
                    self.send_motor_command(MotorCommand.CMD_TURN_RIGHT)
                    time.sleep(0.1)
                
                elif keyboard.is_pressed('space'):
                    self.send_motor_command(MotorCommand.CMD_STOP)
                    time.sleep(0.1)
                
                elif keyboard.is_pressed('e'):
                    self.send_emergency_stop()
                    time.sleep(0.3)
                
                elif keyboard.is_pressed('c'):
                    self.send_config()
                    time.sleep(0.3)
                
                elif keyboard.is_pressed('+') or keyboard.is_pressed('='):
                    self.adjust_speed(10)
                    time.sleep(0.2)
                
                elif keyboard.is_pressed('-') or keyboard.is_pressed('_'):
                    self.adjust_speed(-10)
                    time.sleep(0.2)
                
                elif keyboard.is_pressed('q'):
                    print("\nShutting down...")
                    self.send_motor_command(MotorCommand.CMD_STOP)
                    self.running = False
                
                time.sleep(0.05)
                
        except KeyboardInterrupt:
            print("\n\nInterrupted by user")
        finally:
            self.cleanup()
    
    def cleanup(self):
        print("sending final stop command...")
        self.send_motor_command(MotorCommand.CMD_STOP)
        time.sleep(0.1)
        self.bus.shutdown()
        print("CAN bus connection closed")


def main():
    print("CAN Car Controller - Starting...")
    
    controller = CANCarController(
        interface='socketcan',
        channel='can0',
        bitrate=500000
    )
    
    # Send initial config
    controller.send_config(max_speed=100, timeout_ms=1000)
    
    controller.run()


if __name__ == "__main__":
    main()