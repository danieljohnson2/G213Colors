#!/usr/bin/env python3
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
from sys import argv
import usb.core
import usb.util
import binascii
import argparse


supportedProducts = ["G213", "G203"] # The products this module supports

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

confFile       = "/etc/{}Colors.conf" # Product

class DeviceNotFoundError(Exception):
    """An exception raised when connection to the device fails."""
    def __init__(self, product):
        Exception.__init__(self, "USB Device not found: " + product)

def sendCommand(product, command):
    """
    This sends commands to a G-device; you specify the device
    (one of G213 and G203, for the keyboard or mouse) and a command
    block to send. This may contain multiple commands, separated by
    newlines. Each command is a byte sequence encoded as binhex;
    the format functions of this module provide suitable commands
    to use here.
    
    This function takes care of detaching any kernel driver and reattaching
    it afterwards.
    
    This can raise DeviceNotFoundError if you don't have a suitable device.
    """
    
    def connectG():
        """
        Returns device object and a flag indicating if a kernel driver
        should be reconnected; pass all this to disconnectG() to restore
        normal function.
        """
        print("Connecting to " + product)
        device = usb.core.find(idVendor=idVendor, idProduct=idProduct[product])
        
        if device is None:
            raise DeviceNotFoundError(product)
            
        # if a kernel driver is attached to the interface detach it,
        # otherwise no data can be sent
        shouldReattach = device.is_kernel_driver_active(wIndex)
        if shouldReattach:
            print("Detaching kernel driver")
            device.detach_kernel_driver(wIndex)
        return device, shouldReattach

    def transmit(device):
        """
        Transmits commands to the device that is connected; it sends a line
        at a time, and reads after each command so the device is ready for
        the next command.
        """
        print("Sending bmRequestType, bmRequest, wValue[product], wIndex, command")
        
        for cmd in command.splitlines():
            wv = wValue[product]
            unhexed = binascii.unhexlify(cmd)
            print(bmRequestType, bmRequest, wv, wIndex, unhexed)
            device.ctrl_transfer(bmRequestType, bmRequest, wv, wIndex, unhexed)
            
            sleep(0.01) # not sure why we need this; looks like fake synchronization

            # a second command is not accepted unless we read between commands
            if product == "G213":
                device.read(0x82, 64)

    def disconnectG(device, shouldReattach):
        print("Disconnecting")
        # free device resource to be able to reattach kernel driver
        usb.util.dispose_resources(device)
        # reattach kernel driver, otherwise special key will not work
        if shouldReattach:
            print("Reattaching kernel driver");
            device.attach_kernel_driver(wIndex)
    
    device, shouldReattach = connectG()
    try: transmit(device)
    finally: disconnectG(device, shouldReattach)

def formatColorCommand(product, colorHex, field=0):
    """
    Generates a command to set a device color for a field. field 0 is
    the whole keyboard, 1-6 are zones in it from left to right.
    """
    return colorCommand[product].format(str(format(field, '02x')), colorHex)

def formatBreatheCommand(product, colorHex, speed):
    """
    Generates a command set the device to 'breathe' mode, with
    a specific color and breathing speed (in milliseconds).
    """
    return breatheCommand[product].format(colorHex, str(format(speed, '04x')))

def formatCycleCommand(product, speed):
    """
    Generates a command to set the device to 'cycle' mode, with
    a cycle speed (in milliseconds).
    """
    return cycleCommand[product].format(str(format(speed, '04x')))

def formatSegmentsCommand(product, colorHexes):
    """
    Generates a command to set the device to the device color for
    each zone; you can have up to 6.
    """
    buffer = ""
    for i, colorHex in enumerate(colorHexes):
        if i > 5: raise ValueError("Too many colors- only 6 are allowed.")
        if i > 0: buffer += "\n"
        buffer += formatColorCommand(product, colorHex, int(i+1))
    return buffer
    
def sendColorCommand(product, colorHex):
    """Sets the device color in one step."""
    sendCommand(product, formatColorCommand(product, colorHex))

def sendBreatheCommand(product, colorHex, speed):
    """Sets the device to 'breathe' in one step."""
    sendCommand(product, formatBreatheCommand(product, colorHex, speed))

def sendCycleCommand(product, speed):
    """Sets the device to 'cycle' in one step."""
    sendCommand(product, formatCycleCommand(product, speed))

def sendSegmentsCommand(product, colorHexes):
    """Sets the device colors by zone in one step."""
    sendCommand(product, formatSegmentsCommand(product, colorHexes))

def saveConfiguration(product, command):
    """Saves a command for the product in a file for later restoration."""
    with open(confFile.format(product), "w") as file:
        file.write(command)

def restoreConfiguration(product=None):
    """
    Reads the saved command for the product and re-sends it; if
    the configuration file is missing this does nothing. By default
    this will restore all products whose config files can be found.
    """
    targets = [product] if product else supportedProducts
    
    for target in targets:
        try:
            with open(confFile.format(target), "r") as file:
                command = file.read()

            print("Restoring configuration for " + target)

            if "," in command:
                raise ValueError("\",\" is not supported in the config file. If you apply a color scheme with segments, please re-apply it or replace all \",\" with new lines in \"/etc/G213Colors.conf\".")

            sendCommand(target, command)
        except FileNotFoundError:
            pass # treat missing conf file as if empty
        except DeviceNotFoundError:
            pass # just skip missing devices


# Support use as command line!
if len(argv)>1:
    parser = argparse.ArgumentParser()
    parser.add_argument("product", choices=supportedProducts)
    parser.add_argument("mode", choices=["static", "cycle", "breathe", "segments"])
    parser.add_argument("-c", "--color", default=[standardColor], nargs="+")
    parser.add_argument("-s", "--speed", default=3000, type=int)
    
    args = parser.parse_args()
    if args.mode == "static":
        sendColorCommand(args.product, args.color[0])
    elif args.mode == "cycle":
        sendCycleCommand(args.product, args.speed)
    elif args.mode == "breathe":
        sendBreatheCommand(args.product, args.color[0], args.speed)
    elif args.mode == "segments":
        sendSegmentsCommand(args.product, args.color)
