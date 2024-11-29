import os
import time
import cv2 as cv
import logging
import numpy as np
import math

if os.name == 'nt':
    import msvcrt
    def getch():
        return msvcrt.getch().decode()
else:
    import sys, tty, termios
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    def getch():
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

from dynamixel_sdk import *                    # Uses Dynamixel SDK library

# Control table address
ADDR_MX_TORQUE_ENABLE      = 24               # Control table address is different in Dynamixel model
ADDR_MX_GOAL_POSITION      = 30
ADDR_MX_PRESENT_POSITION   = 36
ADDR_MX_MOVING_SPEED = 32

# Protocol version 
PROTOCOL_VERSION            = 1.0
BAUDRATE                    = 1000000             # Dynamixel default baudrate : 57600
DEVICENAME                  = 'COM14'    # Check which port is being used on your controller
                                                # ex) Windows: "COM1"   Linux: "/dev/ttyUSB0" Mac: "/dev/tty.usbserial-*"

TORQUE_ENABLE               = 1                 # Value for enabling the torque
TORQUE_DISABLE              = 0                 # Value for disabling the torque
DXL_MINIMUM_POSITION_VALUE  = 400           # Dynamixel will rotate between this value
DXL_MAXIMUM_POSITION_VALUE  = 500            # and this value (note that the Dynamixel would not move when the position value is out of movable range. Check e-manual about the range of the Dynamixel you use.)
DXL_MOVING_STATUS_THRESHOLD = 20                # Dynamixel moving status threshold
DXL_IDS = [1,2,3,4]

# For inverse kinematics
d1 = 50
a2 = 93
a3 = 93
a4 = 50


logging.basicConfig(level=logging.INFO)

class dxlRobot:
    def __init__(self) -> None:
        
        # IMPORTANT VARIABLES AND CONSTANTS
        self.HOME_POSITION = []
        
        
        self.portHandler = PortHandler(DEVICENAME)
        self.packetHandler = PacketHandler(PROTOCOL_VERSION)
        # Open port
        if self.portHandler.openPort():
            logging.info("Succeeded to open the port")
        else:
            logging.error("Failed to open the port")
            getch()
            quit()
        
        # Set port baudrate
        if self.portHandler.setBaudRate(BAUDRATE):
            logging.info("Succeeded to change the baudrate")
        else:
            logging.error("Failed to change the baudrate")
            logging.error("Press any key to terminate...")
            getch()
            quit()    
            
        
        # Enable Dynamixel Torque
        for DXL_ID in DXL_IDS:
            dxl_comm_result, dxl_error = self.packetHandler.write1ByteTxRx(self.portHandler, DXL_ID, ADDR_MX_TORQUE_ENABLE, TORQUE_ENABLE)
            
            if dxl_comm_result != COMM_SUCCESS:
                logging.info("%s" % self.packetHandler.getTxRxResult(dxl_comm_result))
            elif dxl_error != 0:
                logging.error("%s" % self.packetHandler.getRxPacketError(dxl_error))
            else:
                logging.info("Dynamixel has been successfully connected")
                
        # Initializing speed
        for DXL_ID in DXL_IDS:
            self.packetHandler.write2ByteTxRx(self.portHandler, DXL_ID, ADDR_MX_MOVING_SPEED, 20)


    
    def movej(self, joints: list, positions: list) -> None:
        """
        INPUTS

        - joints (list[int]): A list of joint IDs to be moved.
        - positions (list[int]): A list of target positions corresponding to each joint.
        
        """
        # Create a list of length equal to the number of joints we want to move
        joints_that_reached_positions = [False] * len(joints)
        
        # Write a position for each joint
        for joint, position in zip(joints,positions):
            dxl_comm_result, dxl_error = self.packetHandler.write4ByteTxRx(self.portHandler, joint, ADDR_MX_GOAL_POSITION, position)
            if dxl_comm_result != COMM_SUCCESS:
                logging.info("%s" % self.packetHandler.getTxRxResult(dxl_comm_result))
            elif dxl_error != 0:
                logging.info("%s" % self.packetHandler.getRxPacketError(dxl_error))
                
        # Going into a loop that breaks when the robot reaches a position
        while 1:
            for i, (joint, position) in enumerate(zip(joints, positions)):
                #print(self.portHandler)
                dxl_present_position, dxl_comm_result, dxl_error = self.packetHandler.read4ByteTxRx(self.portHandler, joint, ADDR_MX_PRESENT_POSITION)
                #print(joint, dxl_present_position, dxl_comm_result, dxl_error)
                if dxl_comm_result != COMM_SUCCESS:
                    logging.info("%s" % self.packetHandler.getTxRxResult(dxl_comm_result))
                elif dxl_error != 0:
                    logging.info("%s" % self.packetHandler.getRxPacketError(dxl_error))


                if not abs(position - dxl_present_position) > DXL_MOVING_STATUS_THRESHOLD:
                    joints_that_reached_positions[i] = True
                
                # else:
                #     print(position, dxl_present_position, joints_that_reached_positions, joint)
            
            if all(joints_that_reached_positions):
                logging.info("All joints have reached their target positions.")
                break
            else:
                logging.info(joints_that_reached_positions)
                
    def movep(self, x:int, y:int, z:int) -> None:
        """
        Moves robot to a inputed position using inverse kinematics
        """

        
        r = np.sqrt(x**2 + y**2)
        s = z - d1
        c = np.sqrt(r**2 + s**2)
        
        c3 = (r^2 + s^2 - a2^2 - a3^2) / (2*a2*a3);

        s3 = sqrt(1-c3^2);

        theta1 = np.atan2(y,x)
        phi1 = np.acos((a2**2 + c**2 - a3**2)/(2*a2*c))
        phi2 = np.atan2(s,r)
        theta2 = - (np.pi/2 - phi1 - phi2)
        theta3 = -np.acos(c3)


        
        
        
    def calculateXYZ(self, theta1, theta2, theta3, theta4) -> list:
        
        # Convert angles from degrees to radians if needed
        theta1 = np.radians(theta1)
        theta2 = np.radians(theta2)
        theta3 = np.radians(theta3)
        theta4 = np.radians(theta4)
        
        # Compute trigonometric functions
        cos1 = np.cos(theta1)
        sin1 = np.sin(theta1)
        cos2 = np.cos(theta2 + np.pi / 2)
        sin2 = np.sin(theta2 + np.pi / 2)
        cos3 = np.cos(theta3)
        sin3 = np.sin(theta3)
        cos4 = np.cos(theta4)
        sin4 = np.sin(theta4)
        
        # Compute x, y, z
        x = (
            a2 * cos2 * cos1 +
            a3 * cos3 * cos2 * cos1 +
            a4 * cos4 * (cos3 * cos2 * cos1 - sin3 * sin2 * cos1) -
            a3 * sin3 * sin2 * cos1 -
            a4 * sin4 * (cos3 * sin2 * cos1 + sin3 * cos2 * cos1)
        )
        
        y = (
            a2 * cos2 * sin1 +
            a3 * cos3 * cos2 * sin1 +
            a4 * cos4 * (cos3 * cos2 * sin1 + sin3 * sin2 * sin1) +
            a3 * sin3 * sin2 * sin1 +
            a4 * sin4 * (cos3 * sin2 * sin1 - sin3 * cos2 * sin1)
        )
        
        z = (
            d1 +
            a2 * sin2 +
            a3 * cos2 * sin3 +
            a3 * sin2 * cos3 +
            a4 * cos4 * (cos2 * sin3 + sin2 * cos3) +
            a4 * sin4 * (cos2 * cos3 - sin2 * sin3)
        )
        
        return [x, y, z]
        

    def close(self) -> None:
        # Disable Dynamixel Torque
        for DXL_ID in DXL_IDS:
            dxl_comm_result, dxl_error = self.packetHandler.write1ByteTxRx(self.portHandler, DXL_ID, ADDR_MX_TORQUE_ENABLE, TORQUE_DISABLE)
            if dxl_comm_result != COMM_SUCCESS:
                logging.info("%s" % self.packetHandler.getTxRxResult(dxl_comm_result))
            elif dxl_error != 0:
                logging.info("%s" % self.packetHandler.getRxPacketError(dxl_error))

            # Close port
            self.portHandler.closePort()
            sys.exit()
        
        
    



