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
import usb.core
import usb.util
import binascii
import json
import argparse

standardColor = 'ffb4aa' # Standard color, i found this color to produce a white color on my G213

class DeviceNotFoundError(Exception):
    """An exception raised when connection to the G-device fails."""
    def __init__(self, product):
        Exception.__init__(self, "USB Device not found: " + product.name)

class Product:

    """
    This represents a G-device, either a keyboard or mouse. It has the logic
    to transmit a configuration to the device. Tha attributes it has provide
    the information needed to do this:
    
    name (str): A human readable name for the device
    idProduct (int): The product ID identifying the device
    wValue (int): Heaven only knows. USB voodoo.
    modeCommands: A dictionary keyed on a mode (static, cycle, etc) and
                  which contains strings with the binary commands to send;
                  these are in hex form, but with {insertions} for use with
                  the format method to provide hte field, color and speed.
    """
    
    def __init__(self, name, long_name, max_segments, idProduct, wValue, modeCommands):
        self.name = name
        self.long_name = long_name
        self.max_segments = max_segments
        self.idProduct = idProduct
        self.wValue = wValue
        self.modeCommands = modeCommands
        
    def apply(self, configuration):
        """
        Applies the configuration's settings to the hardware.
        """
        
        cmd = self._make_command(configuration)
        self._send_command(cmd)
        
    def _make_command(self, configuration):
        """
        Constructs the (hex format) commands block to send to
        implement a configuration. This maps thje "Segments" mode
        into multiple "static" operations.
        """
        
        if configuration.mode == "segments":
            fmt = self.modeCommands["static"]
            startField = 1
            colors = configuration.colors
        else:
            fmt = self.modeCommands[configuration.mode]
            startField = 0
            colors = configuration.colors[:1]
            if len(colors) < 1: colors = [standardColor]
            
        buffer = ""
        
        for i, color in enumerate(colors):
            if i >= self.max_segments:
                raise ValueError(f"Too many colors- only {self.max_segments} are allowed.")

            if i > 0: buffer += "\n"

            buffer += fmt.format(
                field=int(startField+i),
                color=color,
                speed=configuration.speed)

        return buffer

    def _send_command(self, command):
        """
        This sends commands to a G-device. The command parameter is a
        command  block to send. This may contain multiple commands,
        separated by newlines.
        
        Each command is a byte sequence encoded as binhex;
        the makeCommand() method of this class provides suitable commands
        to use here.
        
        This function takes care of detaching any kernel driver and reattaching
        it afterwards.
        
        This can raise DeviceNotFoundError if you don't have a suitable device.
        """
        #  The USB control transfer parameters
        bmRequestType  = 0x21
        bmRequest      = 0x09
        wIndex         = 0x0001
        idVendor       = 0x046d # The id of the Logitech company
  
        def connect():
            """
            Returns device object and a flag indicating if a kernel driver
            should be reconnected; pass all this to disconnect() to restore
            normal function.
            """
            print("Connecting to " + self.name)
            device = usb.core.find(idVendor=idVendor, idProduct=self.idProduct)
            
            if device is None:
                raise DeviceNotFoundError(self)
                
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
            print("Sending bmRequestType, bmRequest, wValue, wIndex, command")

            for cmd in command.splitlines():
                unhexed = binascii.unhexlify(cmd)
                print(bmRequestType, bmRequest, self.wValue, wIndex, unhexed)
                device.ctrl_transfer(bmRequestType, bmRequest, self.wValue, wIndex, unhexed)
                
                # a second command is not accepted unless we read between commands
                if self.name == "G213":
                    device.read(0x82, 64)

        def disconnect(device, shouldReattach):
            print("Disconnecting")
            # free device resource to be able to reattach kernel driver
            usb.util.dispose_resources(device)
            # reattach kernel driver, otherwise special key will not work
            if shouldReattach:
                print("Reattaching kernel driver");
                device.attach_kernel_driver(wIndex)
        
        device, shouldReattach = connect()
        try: transmit(device)
        finally: disconnect(device, shouldReattach)

g213_product = Product("G213", "G213 Keyboard", 5, 0xc336, 0x0211,
    { "static":  "11ff0c3a{field:02x}01{color}0200000000000000000000",
      "breathe": "11ff0c3a0002{color}{speed:04x}006400000000000000",
      "cycle":   "11ff0c3a0003ffffff0000{speed:04x}64000000000000" })
      
g203_product = Product("G203", "G203 Mouse", 1, 0xc084, 0x0210,
    { "static":  "11ff0e3c{field:02x}01{color}0200000000000000000000",
      "breathe": "11ff0e3c0003{color}{speed:04x}006400000000000000",
      "cycle":   "11ff0e3c00020000000000{speed:04x}64000000000000" })

products_by_name = { "G213": [g213_product],
                   "G203": [g203_product],
                   "all": [g213_product, g203_product] }
supported_products = [g213_product, g203_product]

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
        
        destinationFile = Configuration.get_configuration_file(product)
        with open(destinationFile, "w") as file:
            json.dump(rep, file)

    def restore(product):
        """
        Reads the JSON form of the configuration from its file (which
        depends on which product it is); this returns a new Configuration
        and may raise exceptions if the file is not readable or parsable.
        """
        
        sourceFile = Configuration.get_configuration_file(product)        
        with open(sourceFile, "r") as file:
            rep = json.load(file)
        
        conf = Configuration()
        conf.mode = rep.get("mode", "static")
        conf.speed = rep.get("speed", 3000)
        conf.colors = rep.get("colors", [])
        
        if conf.mode not in ("static", "cycle", "breathe", "segments"):
            raise ValueError("'{mode}' is not a valid mode.".format(mode=conf.mode))

        return conf
                        
    def restore_any():
        """
        Restores any product file; it tries each product in 'supported_products'
        and returns the first it can read. Returns None if no usable file
        is found.
        """
        for product in supported_products:
            try: return Configuration.restore(product)
            except FileNotFoundError: pass
            except ValueError: pass
        return None
        
    def get_configuration_file(product):
        """
        Returns the path to the configuration file for a product.
        """
        return "/etc/{product}Colors.conf".format(product=product.name)
        
# Support use as command line!
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("product", choices=list(products_by_name) + ["all"],
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
    products = products_by_name[args.product]
    
    if args.mode == "restore":
        for product in products:
            try:
                config = Configuration.restore(product)
                product.apply(config)
            except FileNotFoundError: pass # missing file treated as no-op
            except DeviceNotFoundError: pass # missing device also                
    else:
        config = Configuration()
        config.mode = args.mode
        config.speed = args.speed
        config.colors = args.color or []
        
        for product in products:
            try: product.apply(config)
            except DeviceNotFoundError as ex: print(str(ex))

            if args.save_configuration: config.save(product)
