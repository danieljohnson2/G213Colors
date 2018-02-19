'''
  *  The MIT License (MIT)
  *
  *  G213Colors v0.1 Copyright (c) 2016 SebiTimeWaster
  *
  *  Permission is hereby granted, free of charge, to any person obtaining a copy
  *  of this software and associated documentation files (the "Software"), to deal
  *  in the Software without restriction, including without limitation the rights
  *  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
  *  copies of the Software, and to permit persons to whom the Software is
  *  furnished to do so, subject to the following conditions:
  *
  *  The above copyright notice and this permission notice shall be included in all
  *  copies or substantial portions of the Software.
  *
  *  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
  *  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
  *  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
  *  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
  *  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
  *  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
  *  SOFTWARE.
'''


from __future__ import print_function
from time import sleep
import usb.core
import usb.util
import binascii


standardColor  = 'ffb4aa'         # Standard color, i found this color to produce a white color on my G213
idVendor       = 0x046d           # The id of the Logitech company
idProduct      = {"G213": 0xc336, # The id of the G213
                  "G203": 0xc084} # The id of the G203

#  The USB controll transfer parameters
bmRequestType  = 0x21
bmRequest      = 0x09
wValue         = {"G213": 0x0211,
                  "G203": 0x0210}
wIndex         = 0x0001

# binary commands in hex format
colorCommand   = {"G213": "11ff0c3a{}01{}0200000000000000000000",
                  "G203": "11ff0e3c{}01{}0200000000000000000000"} # field; color
breatheCommand = {"G213": "11ff0c3a0002{}{}006400000000000000",
                  "G203": "11ff0e3c0003{}{}006400000000000000"}     # color; speed
cycleCommand   = {"G213": "11ff0c3a0003ffffff0000{}64000000000000",
                  "G203": "11ff0e3c00020000000000{}64000000000000"}  # speed; brightness

device         = ""               # device resource
productName    = ""               # e.g. G213, G203
isDetached     = {"G213": False,  # If kernel driver needs to be reattached
                  "G203": False}
confFile       = "/etc/G213Colors.conf"

class DeviceNotFoundError(Exception):
    """An exception raised when connection to the device fails."""
    def __init__(self, product):
        Exception.__init__(self, "USB Device not found: " + product)

def sendCommand(product, data):
    global device, isDetached, productName
    
    def connectG():
        global device, isDetached, productName
        productName = product
        print(productName)
        # find G product
        device = usb.core.find(idVendor=idVendor, idProduct=idProduct[productName])
        # if not found exit
        #print(device.manufacturer)
        if device is None:
            raise DeviceNotFoundError(product)
        # if a kernel driver is attached to the interface detach it, otherwise no data can be send
        if device.is_kernel_driver_active(wIndex):
            device.detach_kernel_driver(wIndex)
            isDetached[productName] = True
            print("Connected " + productName)

    def transmit():
        global device, isDetached, productName
        """
        Transmits commands to the device that is connected; you can send multiple commands
        in sequence by passing new-line separated commands in 'data'.
        """
        print("Send data to " + productName)
        print("bmRequestType, bmRequest, wValue[productName], wIndex, binascii.unhexlify(data)")
        
        for i, cmd in enumerate(data.splitlines()):
            print(bmRequestType, bmRequest, wValue[productName], wIndex, binascii.unhexlify(cmd))
            # free device resource to uest, wValue[productName], wIndex, binascii.unhexlify(cmd))
            # decode data to binary and send it
            device.ctrl_transfer(bmRequestType, bmRequest, wValue[productName], wIndex, binascii.unhexlify(cmd))
            sleep(0.01) # not sure why we need this; looks like fake synchronization

            # a second command is not accepted unless we read between commands
            if productName == "G213":
                device.read(0x82, 64)

    def disconnectG():
        global device, isDetached, productName
        # free device resource to be able to reattach kernel driver
        usb.util.dispose_resources(device)
        # reattach kernel driver, otherwise special key will not work
        if isDetached[productName]:
            device.attach_kernel_driver(wIndex)
            print("Disconnected " + productName)
    
    connectG()
    try: transmit()
    finally: disconnectG()

def formatColorCommand(product, colorHex, field=0):
    return colorCommand[product].format(str(format(field, '02x')), colorHex)

def formatBreatheCommand(product, colorHex, speed):
    return breatheCommand[product].format(colorHex, str(format(speed, '04x')))

def formatCycleCommand(product, speed):
    return cycleCommand[product].format(str(format(speed, '04x')))

def formatSegmentsCommand(product, colorHexes):
    buffer = ""
    for i, colorHex in enumerate(colorHexes):
        if i > 0: buffer += "\n"
        buffer += formatColorCommand(product, colorHex, int(i+1))
    return buffer
    
def sendColorCommand(product, colorHex):
    sendCommand(formatColorCommand(product, colorHex))

def sendBreatheCommand(product, colorHex, speed):
    sendCommand(formatBreatheCommand(product, colorHex, speed))

def sendCycleCommand(product, speed):
    sendCommand(formatCycleCommand(product, speed))

def sendSegmentsCommand(product, colorHexes):
    sendCommand(formatSegmentsCommand(product, colorHexes))

def saveData(data):
    file = open(confFile, "w")
    file.write(data)
    file.close()
