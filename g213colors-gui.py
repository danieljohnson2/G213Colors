#!/usr/bin/env python3

from __future__ import print_function
import g213colors
import subprocess
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GLib

NAME = "G213 Colors"

class Window(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title=NAME)
        self.set_border_width(10)
        self.set_icon_name("g213colors")
        self.set_wmclass(NAME, NAME) # deprecated, but what else works?
        
        vBoxOuter = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.add(vBoxOuter)

        notebook = Gtk.Notebook()
        vBoxOuter.add(notebook)

        self.pages = []
        for p in g213colors.supported_products:
            page = ProductPage(p)
            notebook.append_page(page, Gtk.Label(label=p.long_name))
            self.pages.append(page)
        
        btnAlignBox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        btnSetAll = Gtk.Button.new_with_label("Apply both")
        btnSetAll.connect("clicked", self.on_button_clicked)
        btnSetAll.halign = Gtk.Align.END
        btnSetAll.hexpand = False
        btnAlignBox.pack_end(btnSetAll, False, False, 0)
        vBoxOuter.pack_start(btnAlignBox, False, False, 0)

    def restore_colors(self):
        for page in self.pages:
            page.restore_colors();

    def on_button_clicked(self, button):
        for page in self.pages:
            page.apply()

class ProductPage(Gtk.Box):
    def __init__(self, product):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.set_border_width(10)
        
        self.product = product

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
        self.adjCycle = Gtk.Adjustment(value=5000, lower=500, upper=65535, step_increment=100)
        self.sbCycle = Gtk.SpinButton()
        self.sbCycle.set_adjustment(self.adjCycle)
        vBoxCycle.add(self.sbCycle)
        self.stack.add_titled(vBoxCycle, "cycle", "Cycle")

        ###BREATHE TAB

        vBoxBreathe = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.breatheColorButton = Gtk.ColorButton()
        vBoxBreathe.add(self.breatheColorButton)
        self.adjBCycle = Gtk.Adjustment(value=5000, lower=500, upper=65535, step_increment=100)
        self.sbBCycle = Gtk.SpinButton()
        self.sbBCycle.set_adjustment(self.adjBCycle)
        vBoxBreathe.add(self.sbBCycle)
        self.stack.add_titled(vBoxBreathe, "breathe", "Breathe")

        ###SEGMENTS TAB
        if product.max_segments > 1:
            hBoxSegments = Gtk.Box(spacing=5)
            self.segmentColorBtns = [Gtk.ColorButton() for _ in range(5)]
            for btn in self.segmentColorBtns:
                hBoxSegments.pack_start(btn, True, True, 0)
            self.stack.add_titled(hBoxSegments, "segments", "Segments")
        else:
            self.segmentColorBtns = []

        ###STACK
        self.stack_switcher = Gtk.StackSwitcher()
        self.stack_switcher.set_stack(self.stack)
        self.pack_start(self.stack_switcher, True, True, 0)
        self.pack_start(self.stack, True, True, 0)

        ###SET BUTTON
        btnAlignBox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        btn = Gtk.Button.new_with_label("Apply to " + product.name)
        btn.connect("clicked", lambda btn: self.apply())

        btnAlignBox.pack_end(btn, False, False, 0)
        self.pack_start(btnAlignBox, True, True, 0)

    def restore_colors(self):
        def set_color_button_from_hex(btn, color):
            rgba = Gdk.RGBA()
            rgba.parse("#" + color) # GDK wants HTML Style, leading '#'
            btn.set_rgba(rgba)
        
        try: config = g213colors.Configuration.restore(self.product)
        except FileNotFoundError: return
        except ValueError: return
        
        if len(config.colors) > 0:
            set_color_button_from_hex(self.staticColorButton, config.colors[0])
            set_color_button_from_hex(self.breatheColorButton, config.colors[0])
            
        self.sbCycle.set_value(float(config.speed))
        self.sbBCycle.set_value(float(config.speed))
    
        for b, c in zip(self.segmentColorBtns, config.colors):
            set_color_button_from_hex(b, c)
        
        child = self.stack.get_child_by_name(config.mode)
        if child is not None:
            child.show()
            self.stack.set_visible_child(child)

    def make_command(self):
        """
        Generates the command for whatever the state of the UI is; we
        generate the commmands for the page's product.
        """
        def make_static_args():
            colorHex = get_color_button_hex(self.staticColorButton)
            return ["-c", colorHex]

        def make_breathe_args():
            colorHex = get_color_button_hex(self.breatheColorButton)
            speed = self.sbBCycle.get_value_as_int()
            return ["-c", colorHex, "-s", str(speed)]
            
        def make_cycle_args():
            speed = self.sbCycle.get_value_as_int()
            return ["-s", str(speed)]
        
        def make_segments_args():
            colorHexes = [get_color_button_hex(b) for b in self.segmentColorBtns]
            return ["-c"] + colorHexes
        
        def get_color_button_hex(btn):
            color = btn.get_rgba()
            red = int(color.red * 255)
            green = int(color.green * 255)
            blue = int(color.blue * 255)
            hexColor = "%02x%02x%02x" % (red, green, blue)
            return hexColor

        makers = { "static" : make_static_args,
                   "cycle" : make_cycle_args,
                   "breathe" : make_breathe_args,
                   "segments" : make_segments_args }
        
        mode = self.stack.get_visible_child_name()
        args = makers[mode]()
        return ["pkexec", g213colors.__file__, self.product.name, mode, "--save-configuration"] + args

    def apply(self):
        command = self.make_command()
        subprocess.run(command) # fails if device missing, but we ignore!

win = Window()
win.connect("delete-event", Gtk.main_quit)
win.restore_colors()
win.show_all()
Gtk.main()
