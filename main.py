#!/usr/bin/env python3

from __future__ import print_function
import G213Colors
from time import sleep
import subprocess
import gi
import sys
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import Gdk

NAME = "G213 Colors"

class Window(Gtk.Window):
    def restoreColors(self):
        def btnSetHex(btn, color):
            rgba = Gdk.RGBA()
            rgba.parse("#" + color) # GDK wants HTML Style, leading '#'
            btn.set_rgba(rgba)

        config = G213Colors.Configuration.restoreAny()

        if config is not None:
            if len(config.colors) > 0:
                btnSetHex(self.staticColorButton, config.colors[0])
                btnSetHex(self.breatheColorButton, config.colors[0])
                
            self.sbCycle.set_value(float(config.speed))
            self.sbBCycle.set_value(float(config.speed))
        
            for b, c in zip(self.segmentColorBtns, config.colors):
                btnSetHex(b, c)
            
            child = self.stack.get_child_by_name(config.mode)
            if child is not None:
                child.show()
                self.stack.set_visible_child(child)

    def makeCurrentCommand(self, product):
        """
        Generates the command for whatever the state of the UI is; we
        generate the commmands for the indicated product.
        """
        def makeStaticArgs():
            colorHex = btnGetHex(self.staticColorButton)
            return ["-c", colorHex]

        def makeBreatheArgs():
            colorHex = btnGetHex(self.breatheColorButton)
            speed = sbGetValue(self.sbBCycle)
            return ["-c", colorHex, "-s", str(speed)]
            
        def makeCycleArgs():
            speed = sbGetValue(self.sbCycle)
            return ["-s", str(speed)]
        
        def makeSegmentsArgs():
            colorHexes = [btnGetHex(b) for b in self.segmentColorBtns]
            return ["-c"] + colorHexes
        
        def btnGetHex(btn):
            color = btn.get_rgba()
            red = int(color.red * 255)
            green = int(color.green * 255)
            blue = int(color.blue * 255)
            hexColor = "%02x%02x%02x" % (red, green, blue)
            return hexColor

        def sbGetValue(sb):
            return sb.get_value_as_int()

        makers = { "static" : makeStaticArgs,
                   "cycle" : makeCycleArgs,
                   "breathe" : makeBreatheArgs,
                   "segments" : makeSegmentsArgs }
        
        mode = self.stack.get_visible_child_name()
        args = makers[mode]()
        return ["pkexec", G213Colors.__file__, product, mode, "--save-configuration"] + args


    def on_button_clicked(self, button, product):
        command = self.makeCurrentCommand(product)
        subprocess.run(command) # fails if device missing, but we ignore!

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
            btn = Gtk.Button.new_with_label("Set" + p.name)
            hBoxSetButtons.pack_start(btn, True, True, 0)
            btn.connect("clicked", self.on_button_clicked, p)
        vBoxMain.pack_start(hBoxSetButtons, True, True, 0)

        ###SET ALL BUTTON
        btnSetAll = Gtk.Button.new_with_label("Set all")
        btnSetAll.connect("clicked", self.on_button_clicked, "all")
        vBoxMain.pack_start(btnSetAll, True, True, 0)

win = Window()
win.connect("delete-event", Gtk.main_quit)
win.restoreColors()
win.show_all()
Gtk.main()
