import serial
import time 

ser = serial.Serial('/dev/ttyACM0',115200)

ser.write(b'Msuck44444')
time.sleep(2)
ser.write(b'Mstop00000')