#!/usr/bin/env python

# mousecoords.py
# copyleft sdaau 2013

# Mouse coordinates Python plugin for Eye of GNOME
# On mouse motion, shows in statusbar: scaled image size, window coords, and image pixel coords of pointer.
# copy mousecoords.eog-plugin  mousecoords.py in ~/.gnome2/eog/plugins/ ; and enable plugin in eog Edit/Preferences/Plugins tab

import math

eog_context_id = 1
global initdel
initdel = False
global lastsbartext

from gi.repository import Eog, Gtk, Gdk
from gi.repository import GObject


class MouseCoords(GObject.Object, Eog.WindowActivatable):
    window = GObject.property(type=Eog.Window)

    def __init__(self):
        super(MouseCoords, self).__init__()
        self.mousecoords = None
        self.handlerId2 = None
        self.handlerId3 = None
        self.handlerId4 = None
        self.imwidth = 0
        self.imheight = 0
        self.zoom = 0
        self.scrollviewalloc = None
        # scrollbar value/offset
        self.hslide = None
        self.vslide = None
        self.imscw = 0
        self.imsch = 0
        self.mouse_imgcoord_x = 0
        self.mouse_imgcoord_y = 0
        self.laststatustext = ""
        self.clipboard = None
        self.scrollfact_offx = 0
        self.viewport_offset_imgx = 0
        self.scrollfact_offy = 0
        self.viewport_offset_imgy = 0
        self.scrollfact_szx = 0
        self.scrollfact_szy = 0
        self.image = None
        self.statusbar = Gtk.Statusbar()

    @property
    def app(self):
        return self.window.get_application()

    def do_activate(self):
        global initdel
        global lastsbartext
        window = self.window
        # start reacting as soon as plugin loaded ; was window.connect
        self.handlerId2 = window.connect('motion_notify_event', self.it_moved)
        # hmm, both text_popped and text-popped trigger here?
        self.window.get_statusbar().show()
        eog_context_id = self.window.get_statusbar().get_context_id("")
        # ~ print "eog_context_id", eog_context_id
        self.handlerId3 = self.window.get_statusbar().connect('text-popped', self.status_text_popped)
        # pop last, maybe? nothing happens here.. all c 0
        # ~ self.window.get_statusbar().pop(1)
        initdel = False
        lastsbartext = ""
        # prints to stdout if eog called from console (eog -n .)
        # print('MouseCoords plugin activated')

    def do_deactivate(self):
        window = self.window
        window.disconnect(self.handlerId2)
        self.window.get_statusbar().disconnect(self.handlerId3)
        # window.get_image().disconnect(self.handlerId4)
        self.window.get_statusbar().hide()
        # print('MouseCoords plugin deactivated')

    # ~ def it_moved(self, event, window):
    def it_moved(self, window, event):
        if window.get_image() is None:
            return # eog has been loaded without any image so there is no point in doing anything
        self.mousecoords = window.get_view().get_pointer()
        # Sdaau says that `get_pixbuf()` has a memory leak but I haven't noticed it so it might have been fixed?
        self.imwidth = window.get_image().get_pixbuf().get_width()
        self.imheight = window.get_image().get_pixbuf().get_height()
        self.zoom = window.get_view().get_zoom()
        self.scrollviewalloc = window.get_view().get_allocation()  # gtk.gdk.Rectangle(0, 38, 768, 523), independent of scrollbars/zoom
        self.vslide = window.get_view().get_children()[0]  # gtk.VScrollbar # TODO Update: this no longer refers to VScrollbar object
        self.hslide = window.get_view().get_children()[1]  # gtk.HScrollbar # TODO Update: this no longer refers to HScrollbar object
        self.image = window.get_image()

        eog_context_id = self.window.get_statusbar().get_context_id("")
        if (not (initdel)):
            self.window.get_statusbar().pop(eog_context_id)  # returns string, doesn't delete
        else:
            self.window.get_statusbar().pop(2)  # our own we have to delete with a different context it (sort of?)

        # should do self.window.get_statusbar().get_context_id(""); but returns wrong
        # actually, that works with callback - but doesn't remove ?!
        # by bruteforce in Python Console, can see context_id is 1; (for remove)
        # saved that above as eog_context_id
        # gtk.Statusbar has a stack of messages - cannot change them directly as strings
        # have to pop, then get the popped string in listener, then re-push change
        # self.window.get_statusbar().pop(eog_context_id)
        return True

    def status_text_popped(self, statusbar, context_id, text):
        # print("status_text_popped!", statusbar, context_id, text)
        global initdel
        global lastsbartext
        # ~ print "status_text_popped: s ", statusbar, " c ", context_id, " text ", text
        # from python console:
        # self.window.get_statusbar().pop(3) -> here lists c 1, gives text, no delete
        # self.window.get_statusbar().pop(1) -> here lists c 0, no text, deletes
        # if push(3, "AAA") -> get text on pop (2,1,0), reported c 3; but pop(3)shows c 0, no text and deletes
        # ~ print dir(text)
        # note 'window' is not defined here
        eog_context_id = statusbar.get_context_id("")
        window = statusbar.get_window()
        if (context_id == 0):
            pass  # do nothing here; noop
        else:
            if (context_id == 1):
                if (not (initdel)):
                    statusbar.pop(1)  # force delete
                    initdel = True
                lastsbartext = text
                # parse and retrieve image size here - bloody pixbuf access in python plugin causes memleak!
                if "pixels" in lastsbartext: # This condition is never true on non-English locales !!
                    ta = lastsbartext.split(' ')
                    self.imwidth = int(ta[0])
                    self.imheight = int(ta[2])

            if (self.mousecoords is not None):
                # ~ print " w ", window.get_image().get_pixbuf().get_width(), "h", window.get_image().get_pixbuf().get_height() # TypeError: Required argument 'x' (pos 1) not found
                self.compute_scaled_size(window)
                self.compute_zoom_offsets()

                self.laststatustext = "(x=%d, y=%d)" % (self.mouse_imgcoord_x, self.mouse_imgcoord_y)

                pixbuf = self.window.get_image().get_pixbuf()
                if 0 <= self.mouse_imgcoord_x <= pixbuf.get_width() and 0 <= self.mouse_imgcoord_y <= pixbuf.get_height():
                    # Get the pixel color at the cursor position
                    pixels = pixbuf.get_pixels()
                    pixel = pixels[(round(self.mouse_imgcoord_y) * pixbuf.get_rowstride()) + (
                                round(self.mouse_imgcoord_x) * pixbuf.get_n_channels()):]
                    if len(pixel) == 0:
                        # Comma in parens is to ensure this gets interpreted as a tuple
                        red, green, blue = ("--",) * 3
                    else:
                        red, green, blue = pixel[:3]
                    self.laststatustext += f" ~ R:{red}, G:{green}, B:{blue}"
                else:
                    self.laststatustext += " ~ R:--, G:--, B:--"

                statusbar.push(eog_context_id, self.laststatustext)

    # as in
    # http://git.gnome.org/browse/eog/tree/src/eog-scroll-view.c?h=gnome-2-32
    def compute_scaled_size(self, window):
        # cannot access window.get_image().get_pixbuf().get_width() here;
        # so save in self.imwidth when possible
        # assert(self.imwidth > 0)
        # assert(self.imheight > 0)
        self.imscw = math.floor(self.window.get_image().get_pixbuf().get_width() * self.zoom + 0.5);
        self.imsch = math.floor(self.window.get_image().get_pixbuf().get_height() * self.zoom + 0.5);

    def compute_zoom_offsets(self):
        # must retrieve offset data from scrollbars
        halloc = self.hslide.get_allocation()  # Rectangle
        valloc = self.vslide.get_allocation()
        hajd = self.window.get_view().get_hadjustment()
        vajd = self.window.get_view().get_vadjustment()

        # if (halloc.x == -1): # not good condition, -1 only at start
        if (self.imscw <= self.scrollviewalloc.width):
            # if the hor. scrollbar is not shown, then image is smaller
            # than displayed scrollview - and it will be centered
            offsx = math.floor((self.scrollviewalloc.width - self.imscw) / 2)
            # if mouse pointer x (scrollview coords) is below (left of) offsx,
            # (or corresponding right) - it is not over an image pixel,
            # so set it to -1
            if (self.mousecoords[0] < offsx):
                self.mouse_imgcoord_x = -2
            if (self.mousecoords[0] > self.scrollviewalloc.width - offsx):
                self.mouse_imgcoord_x = -3
            if True:
                # mouse pointer x over image - find equivalent image pixel
                within_image_x = self.mousecoords[0] - offsx;
                self.mouse_imgcoord_x = math.floor((within_image_x / self.imscw) * self.imwidth)
        else:
            # here the hor. scrollbar is shown, handle coords
            self.scrollfact_offx = hajd.get_value() / (hajd.get_upper() - hajd.get_lower())
            self.viewport_offset_imgx = self.scrollfact_offx * self.imwidth
            self.scrollfact_szx = hajd.get_page_size() / (hajd.get_upper() - hajd.get_lower())
            self.mouse_imgcoord_x = self.viewport_offset_imgx + self.mousecoords[0] / self.zoom
            if (self.mouse_imgcoord_x > self.imwidth):
                self.mouse_imgcoord_x = -10

        # if (valloc.x == -1): # not good condition, -1 only at start
        if (self.imsch <= self.scrollviewalloc.height):
            # if the ver. scrollbar is not shown, then image is smaller ...
            offsy = math.floor((self.scrollviewalloc.height - self.imsch) / 2)
            if (self.mousecoords[1] < offsy) or (self.mousecoords[1] > self.scrollviewalloc.height - offsy):
                self.mouse_imgcoord_y = -1
            if True:
                within_image_y = self.mousecoords[1] - offsy;
                self.mouse_imgcoord_y = math.floor((within_image_y / self.imsch) * self.imheight)
        else:
            # here the ver. scrollbar is shown, handle coords
            self.scrollfact_offy = vajd.get_value() / (vajd.get_upper() - vajd.get_lower())
            self.viewport_offset_imgy = self.scrollfact_offy * self.imheight
            self.scrollfact_szy = vajd.get_page_size() / (vajd.get_upper() - vajd.get_lower())
            self.mouse_imgcoord_y = self.viewport_offset_imgy + self.mousecoords[1] / self.zoom
            if (self.mouse_imgcoord_y > self.imheight):
                self.mouse_imgcoord_y = -10
