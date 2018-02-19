#!/usr/bin/env python3

from __future__ import print_function
import G213Colors
from time import sleep
import gi
import sys
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

NAME = "G213 Colors"

numArguments = len(sys.argv)    # number of arguments given

if numArguments > 1:
    option = str(sys.argv[1]) # option to use
else:
    option = ""

class Window(Gtk.Window):

    def makeCurrentCommand(self, product):
        """
        Generates the command for whatever the state of the UI is; we
        generate the commmands for the indicated product.
        """
        def makeStatic():
            colorHex = btnGetHex(self.staticColorButton)
            return G213Colors.formatColorCommand(product, colorHex)

        def makeBreathe():
            colorHex = btnGetHex(self.breatheColorButton)
            speed = sbGetValue(self.sbBCycle)
            return G213Colors.formatBreatheCommand(product, colorHex, speed)

        def makeCycle():
            speed = sbGetValue(self.sbCycle)
            return G213Colors.formatCycleCommand(product, speed)
        
        def makeSegments():
            colorHexes = (btnGetHex(b) for b in self.segmentColorBtns)
            return G213Colors.formatSegmentsCommand(product, colorHexes)
        
        def btnGetHex(btn):
            color = btn.get_rgba()
            red = int(color.red * 255)
            green = int(color.green * 255)
            blue = int(color.blue * 255)
            hexColor = "%02x%02x%02x" % (red, green, blue)
            return hexColor

        def sbGetValue(sb):
            return sb.get_value_as_int()

        makers = { "static" : makeStatic,
                   "cycle" : makeCycle,
                   "breathe" : makeBreathe,
                   "segments" : makeSegments }
        
        stackName = self.stack.get_visible_child_name()
        return makers[stackName]()


    def on_button_clicked(self, button, product):
        targets = [product] if product else G213Colors.supportedProducts

        for target in targets:
            try:
                command = self.makeCurrentCommand(target)
                G213Colors.sendCommand(target, command)
                G213Colors.saveConfiguration(target, command)
            except G213Colors.DeviceNotFoundError as ex:
                # continue even if one device is not found
                print(str(ex))    

    def __init__(self):

        Gtk.Window.__init__(self, title=NAME)
        self.set_border_width(10)

        vBoxMain = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.add(vBoxMain)

        ###STACK
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_transition_duration(1000)

        ###STATIC TAB
        vBoxStatic = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.staticColorButton = Gtk.ColorButton()
        vBoxStatic.add(self.staticColorButton)

        self.stack.add_titled(vBoxStatic, "static", "Static")

        ###CYCLE TAB
        vBoxCycle = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.adjCycle = Gtk.Adjustment(5000, 500, 65535, 100, 100, 0)
        self.sbCycle = Gtk.SpinButton()
        self.sbCycle.set_adjustment(self.adjCycle)
        vBoxCycle.add(self.sbCycle)
        self.stack.add_titled(vBoxCycle, "cycle", "Cycle")

        ###BREATHE TAB

        vBoxBreathe = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.breatheColorButton = Gtk.ColorButton()
        vBoxBreathe.add(self.breatheColorButton)
        self.adjBCycle = Gtk.Adjustment(5000, 500, 65535, 100, 100, 0)
        self.sbBCycle = Gtk.SpinButton()
        self.sbBCycle.set_adjustment(self.adjBCycle)
        vBoxBreathe.add(self.sbBCycle)
        self.stack.add_titled(vBoxBreathe, "breathe", "Breathe")

        ###SEGMENTS TAB
        hBoxSegments = Gtk.Box(spacing=5)
        self.segmentColorBtns = [Gtk.ColorButton() for _ in range(5)]
        for btn in self.segmentColorBtns:
            hBoxSegments.pack_start(btn, True, True, 0)
        self.stack.add_titled(hBoxSegments, "segments", "Segments")

        ###STACK
        self.stack_switcher = Gtk.StackSwitcher()
        self.stack_switcher.set_stack(self.stack)
        vBoxMain.pack_start(self.stack_switcher, True, True, 0)
        vBoxMain.pack_start(self.stack, True, True, 0)

        ###SET BUTTONS
        hBoxSetButtons = Gtk.Box(spacing=5)
        self.setColorBtns = []
        for p in G213Colors.supportedProducts:
            btn = Gtk.Button.new_with_label("Set" + p)
            hBoxSetButtons.pack_start(btn, True, True, 0)
            btn.connect("clicked", self.on_button_clicked, p)
        vBoxMain.pack_start(hBoxSetButtons, True, True, 0)

        ###SET ALL BUTTON
        btnSetAll = Gtk.Button.new_with_label("Set all")
        btnSetAll.connect("clicked", self.on_button_clicked, None)
        vBoxMain.pack_start(btnSetAll, True, True, 0)


if "-t" in option:
    G213Colors.restoreConfiguration()
else:
    win = Window()
    win.connect("delete-event", Gtk.main_quit)
    win.show_all()
    Gtk.main()
