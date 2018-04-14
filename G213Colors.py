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
import json
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
colorCommand   = {"G213": "11ff0c3a{field:02x}01{color}0200000000000000000000",
                  "G203": "11ff0e3c{field:02x}01{color}0200000000000000000000"}
breatheCommand = {"G213": "11ff0c3a0002{color}{speed:04x}006400000000000000",
                  "G203": "11ff0e3c0003{color}{speed:04x}006400000000000000"}
cycleCommand   = {"G213": "11ff0c3a0003ffffff0000{speed:04x}64000000000000",
                  "G203": "11ff0e3c00020000000000{speed:04x}64000000000000"}

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
    return colorCommand[product].format(color=colorHex, field=field)

def formatBreatheCommand(product, colorHex, speed):
    """
    Generates a command set the device to 'breathe' mode, with
    a specific color and breathing speed (in milliseconds).
    """
    return breatheCommand[product].format(color=colorHex, speed=speed)

def formatCycleCommand(product, speed):
    """
    Generates a command to set the device to 'cycle' mode, with
    a cycle speed (in milliseconds).
    """
    return cycleCommand[product].format(speed=speed)

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

class Configuration:

    """
    This class contains the configuration for a keyboard or mouse; it does
    not know which, and we can apply the same configuration to either or
    both.
    
    Attributes:
        mode (string): static, cycle, breathe or segments
        speed (int): cycle or breath time in milliseconds
        colors (string array): 6 segment colors, or 1 color only,
                               depending on mode. Each color is in hex
                               for, RRGGBB.
    """
    
    def __init__(self):
        self.mode = "static"
        self.speed = 3000
        self.colors = []
        
    def save(self, product):
        """
        Saves the configuration into a file as JSON; there is a file
        for each product.
        """
        rep = { "mode": self.mode }
        
        if self.mode in ["cycle", "breathe"]:
            rep["speed"] = self.speed
        if self.mode != "cycle":
            rep["colors"] = self.colors
        
        destinationFile = Configuration.confFileFor(product)
        with open(destinationFile, "w") as file:
            json.dump(rep, file)

    def restore(product):
        """
        Reads the JSON form of the configuration from its file (which
        depends on which product it is); this returns a new Configuration
        and may raise exceptions if the file is not readable or parsable.
        """
        
        sourceFile = Configuration.confFileFor(product)        
        with open(sourceFile, "r") as file:
            rep = json.load(file)
        
        conf = Configuration()
        conf.mode = rep.get("mode", "static")
        conf.speed = rep.get("speed", 3000)
        conf.colors = rep.get("colors", [])
        
        if conf.mode not in ("static", "cycle", "breathe", "segments"):
            raise ValueError("'{mode}' is not a valid mode.".format(mode=conf.mode))

        return conf
                        
    def restoreAny():
        """
        Restores any product file; it tries each product in 'supportedProducts'
        and returns the first it can read. Returns None if no usable file
        is found.
        """
        for product in supportedProducts:
            try: return Configuration.restore(product)
            except FileNotFoundError: pass
            except ValueError: pass
        return None
        
    def confFileFor(product):
        """
        Returns the path to the configuration file for a product.
        """
        return "/etc/{product}Colors.conf".format(product=product)
        
    def apply(self, product):
        """
        Applies the configuration's settings to the hardware.
        """        
        if self.mode == "static":
            command = formatColorCommand(product, self.colors[0])
        elif self.mode == "cycle":
            command = formatCycleCommand(product, self.speed)
        elif self.mode == "breathe":
            command = formatBreatheCommand(product, self.colors[0], self.speed)
        elif self.mode == "segments":
            command = formatSegmentsCommand(product, self.colors)
        
        sendCommand(product, command)

# Support use as command line!
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("product", choices=supportedProducts + ["all"],
        help="The product name whose colors are to be configured.")
    parser.add_argument("mode", choices=["static", "cycle", "breathe", "segments", "restore"],
        help="The mode to put the device it, or restore to reload the most recent configuration.")
    parser.add_argument("-c", "--color", default=[standardColor], nargs="+",
        help="The color (in hex RRGGBB) to display on the device. Up to 6 colors may be used for segments mode.")
    parser.add_argument("-s", "--speed", default=3000, type=int,
        help="The speed (in milliseconds) to cycle or breathe at.")
    parser.add_argument("--save-configuration", action="store_true",
        help="Save the new configuration back to the configuration file, for use by the restore mode.")

    args = parser.parse_args()
    products = [args.product] if args.product != "all" else supportedProducts
    
    if args.mode == "restore":
        for product in products:
            try:
                Configuration.restore(product).apply(product)
            except FileNotFoundError: pass # missing file treated as no-op
            except DeviceNotFoundError: pass # missing device also                
    else:
        config = Configuration()
        config.mode = args.mode
        config.speed = args.speed
        config.colors = args.color or []
        
        for product in products:
            try: config.apply(product)
            except DeviceNotFoundError as ex: print(str(ex))

            if args.save_configuration: config.save(product)
