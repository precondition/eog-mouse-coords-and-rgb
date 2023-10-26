#!/usr/bin/env python

# mousecoords.py
# copyleft sdaau 2013

# Mouse coordinates Python plugin for Eye of GNOME
# On mouse motion, shows in statusbar: scaled image size, window coords, and image pixel coords of pointer.
# copy mousecoords.eog-plugin  mousecoords.py in ~/.gnome2/eog/plugins/ ; and enable plugin in eog Edit/Preferences/Plugins tab

# 2013-01-21 (c)
# added code to run a `display` crop of (valid: zoomed) viewport upon a "Copy Mouse Coords" command (but it's commented here)

# 2013-01-21 (b)
# added viewport string in ImageMagick geometry format (valid if image is zoomed in)
# added menu item "Copy Mouse Coords" (under /Tools) and shortcut key 'M' - to copy statusbar string to clipboard
# added dump of test ImageMagick `display -crop` command string [with the viewport geometry and current file] to stdout

# 2013-01-21
# initial relase; dev on:
# Eye of GNOME Image Viewer 2.32.1; Python 2.7.1+; Ubuntu 11.04


# see:
# http://git.gnome.org/browse/eog/tree/bindings/python/eog.defs?h=gnome-2-32

# if the plugin locks (after enabling) - restart `eog`; and do mousewheel zoom to refresh

# http://developer.gnome.org/eog/stable/api-index.html


# https://live.gnome.org/EyeOfGnome/Plugins#Writing_plugins
# no work anymore
# ImportError: cannot import name Eog/eog
#~ from gi.repository import GObject, Eog
#~ class MouseCoordsPlugin(GObject.Object, Eog.WindowActivatable):
  #~ # Override EogWindowActivatable's window property
  #~ # This is the EogWindow this plugin instance has been activated for
  #~ window = GObject.property(type=Eog.Window)

  #~ def __init__(self):
    #~ GObject.Object.__init__(self)

  #~ def do_activate(self):
    #~ print 'The answer landed on my rooftop, whoa'

  #~ def do_deactivate(self):
    #~ print 'The answer fell off my rooftop, woot'

# [http://orangepalantir.org/topicspace/index.php?idnum=59 TopicSpace: Eye of Gnome lanch Gimp plugin.]
import gtk
import subprocess

import math
#~ import gobject
#~ import os

ui_str = """
	<ui>
	  <menubar name="MainMenu">
	    <menu name="ToolsMenu" action="Tools">
	      <separator/>
	      <menuitem name="MouseCoords" action="MouseCoords"/>
	      <separator/>
	    </menu>
	  </menubar>
	</ui>
	"""

#~ eb = gtk.EventBox()
#~ window = gtk.Window()
eog_context_id = 1
global initdel
initdel = False
global lastsbartext

from gi.repository import Eog, Gtk, Gdk
from gi.repository import GObject


class MouseCoords(GObject.Object, Eog.WindowActivatable):
 
  def on_drawing_area_motion(self,widget, event):
    x = event.x
    y = event.y
    state = event.state
    #print("Pointer position: x={}, y={}".format(x, y))

  window = GObject.property(type=Eog.Window)

  def __init__(self):
    super(MouseCoords, self).__init__()
    self.console_window = None
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
    #~ print "eog_context_id", eog_context_id
    self.handlerId3 = self.window.get_statusbar().connect('text-popped', self.status_text_popped)
    #~ self.handlerId4 = window.get_image().connect('size-prepared', self.image_size_prepared) # no image here yet
    # pop last, maybe? nothing happens here.. all c 0
    #~ self.window.get_statusbar().pop(1)
    initdel = False
    lastsbartext = ""
    # prints to stdout if eog called from console (eog -n .)
    print('MouseCoords plugin activated')



  def do_deactivate(self):
    window = self.window
    window.disconnect(self.handlerId2)
    self.window.get_statusbar().disconnect(self.handlerId3)
    # window.get_image().disconnect(self.handlerId4)
    self.window.get_statusbar().hide()
    print('MouseCoords plugin deactivated')

  #~ def it_moved(self, event, window):
  def it_moved(self, window, event):
    #~ print "it_moved"
    #~ self.mousecoords = window.get_display().get_window_at_pointer() # window and coords
    # but this just returns a pair of coords:
    #~ print window.get_image().get_size() # here is EogImage (not in activate); but 'eog.Image' object has no attribute 'get_size'
    #~ print " w ", window.get_image().get_pixbuf().get_width(), "h", window.get_image().get_pixbuf().get_height()
    self.mousecoords = window.get_view().get_pointer()
    self.imwidth = window.get_image().get_pixbuf().get_width(); # cannot with self.image? (could crash due NoneType) LEAKS!
    self.imheight = window.get_image().get_pixbuf().get_height();
    self.zoom = window.get_view().get_zoom();
    self.scrollviewalloc = window.get_view().get_allocation() # gtk.gdk.Rectangle(0, 38, 768, 523), independent of scrollbars/zoom
    drawing_area = tuple(filter(lambda child: isinstance(child, Gtk.DrawingArea), window.get_view().get_children()))[0]
    (drawing_area).connect("motion-notify-event", self.on_drawing_area_motion)
    self.vslide = window.get_view().get_children()[0] # gtk.VScrollbar
    self.hslide = window.get_view().get_children()[1] # gtk.HScrollbar
    self.image = window.get_image()

    eog_context_id = self.window.get_statusbar().get_context_id("")
    if ( not(initdel) ):
      # self.handlerId4 = window.get_image().connect('size-prepared', self.image_size_prepared) # works here - but doesn't do much
      self.window.get_statusbar().pop(eog_context_id) # returns string, doesn't delete
    else:
      self.window.get_statusbar().pop(2) # our own we have to delete with a different context it (sort of?)

    #~ print r[1], r[2]
    # should do self.window.get_statusbar().get_context_id(""); but returns wrong
    # actually, that works with callback - but doesn't remove ?!
    # by bruteforce in Python Console, can see context_id is 1; (for remove)
    # saved that above as eog_context_id
    # gtk.Statusbar has a stack of messages - cannot change them directly as strings
    # have to pop, then get the popped string in listener, then re-push change
    #self.window.get_statusbar().pop(eog_context_id)
    return True

  def status_text_popped(self, statusbar, context_id, text):
    #print("status_text_popped!", statusbar, context_id, text)
    global initdel
    global lastsbartext
    #~ print "status_text_popped: s ", statusbar, " c ", context_id, " text ", text
    # from python console:
    # self.window.get_statusbar().pop(3) -> here lists c 1, gives text, no delete
    # self.window.get_statusbar().pop(1) -> here lists c 0, no text, deletes
    # if push(3, "AAA") -> get text on pop (2,1,0), reported c 3; but pop(3)shows c 0, no text and deletes
    #~ print dir(text)
    # note 'window' is not defined here
    eog_context_id = statusbar.get_context_id("")
    window = statusbar.get_window()
    if (context_id == 0):
      pass # do nothing here; noop
      #~ print "ZERO"
      # statusbar.push(eog_context_id, lastsbartext + " AAA") # causes loop
    else:
      if (context_id == 1):
        if ( not(initdel) ):
          statusbar.pop(1) # force delete
          #~ self.handlerId4 = window.get_image().connect('size-prepared', self.image_size_prepared) # 'window' is not defined
          initdel = True
        lastsbartext = text
        # parse and retrieve image size here - bloody pixbuf access in python plugin causes memleak!
        if "pixels" in lastsbartext:
          ta = lastsbartext.split(' ')
          self.imwidth = int(ta[0])
          self.imheight = int(ta[2])

      if (self.mousecoords is not None):
        #~ print " w ", window.get_image().get_pixbuf().get_width(), "h", window.get_image().get_pixbuf().get_height() # TypeError: Required argument 'x' (pos 1) not found
        self.compute_scaled_size(window)
        self.compute_zoom_offsets()

        self.laststatustext = "(x=%d, y=%d)" % (self.mouse_imgcoord_x, self.mouse_imgcoord_y)

        pixbuf = self.window.get_image().get_pixbuf()
        if 0 <= self.mouse_imgcoord_x <= pixbuf.get_width() and 0 <= self.mouse_imgcoord_y <= pixbuf.get_height():
          # Get the pixel color at the cursor position
          pixels = pixbuf.get_pixels()
          print("pixel = pixels[(self.mouse_imgcoord_y * pixbuf.get_rowstride()) + (self.mouse_imgcoord_x * pixbuf.get_n_channels()):]")
          print("pixel = pixels[(", self.mouse_imgcoord_y, " * ", pixbuf.get_rowstride(), ") + (", self.mouse_imgcoord_x, "*", pixbuf.get_n_channels(), "):]")
          pixel = pixels[(round(self.mouse_imgcoord_y) * pixbuf.get_rowstride()) + (round(self.mouse_imgcoord_x) * pixbuf.get_n_channels()):]
          red, green, blue = pixel[:3]
          self.laststatustext += f" ~ R:{red}, G:{green}, B:{blue}"
        else:
          self.laststatustext += " ~ R:--, G:--, B:--"

        statusbar.push(eog_context_id, self.laststatustext)

  # as in
  # http://git.gnome.org/browse/eog/tree/src/eog-scroll-view.c?h=gnome-2-32
  def compute_scaled_size(self, window):
    #~ print " w ", window,
    # cannot access window.get_image().get_pixbuf().get_width() here;
    # so save in self.imwidth when possible
    #assert(self.imwidth > 0)
    #assert(self.imheight > 0)
    self.imscw = math.floor(self.window.get_image().get_pixbuf().get_width()*self.zoom + 0.5);
    self.imsch = math.floor(self.window.get_image().get_pixbuf().get_height()*self.zoom + 0.5);

  def compute_zoom_offsets(self):
    # must retrieve offset data from scrollbars
    halloc = self.hslide.get_allocation() # Rectangle
    valloc = self.vslide.get_allocation()
    hajd = self.window.get_view().get_hadjustment()
    vajd = self.window.get_view().get_vadjustment()
    #print("alloc: Scrollview: ", self.scrollviewalloc, " h: ", halloc , " v: ", valloc)
    #print("H",
    #   " low ", hajd.get_lower(),
    #   " val ", hajd.get_value(),
    #   " psz ", hajd.get_page_size(),
    #   " upp ", hajd.get_upper(),
    #   " s_i ", hajd.get_step_increment(),
    #   " p_i ", hajd.get_page_increment()
    #   )
    #~ print("V",
      #~ " low ", vajd.get_lower(),
      #~ " val ", vajd.get_value(),
      #~ " psz ", vajd.get_page_size(),
      #~ " upp ", vajd.get_upper(),
      #~ " s_i ", vajd.get_step_increment(),
      #~ " p_i ", vajd.get_page_increment()
      #~ )

    #if (halloc.x == -1): # not good condition, -1 only at start
    if (self.imscw <= self.scrollviewalloc.width):
      # if the hor. scrollbar is not shown, then image is smaller
      # than displayed scrollview - and it will be centered
      offsx = math.floor((self.scrollviewalloc.width-self.imscw)/2)
      # if mouse pointer x (scrollview coords) is below (left of) offsx,
      # (or corresponding right) - it is not over an image pixel,
      # so set it to -1
      if (self.mousecoords[0] < offsx):
        print("self.mousecoords[0] < offsx: ", self.mousecoords[0], "<", offsx)
        self.mouse_imgcoord_x = -2
      if (self.mousecoords[0] > self.scrollviewalloc.width-offsx):
        print("self.mousecoords[0] > self.scrollviewalloc.width-offsx: ", self.mousecoords[0], ">", self.scrollviewalloc.width-offsx)
        self.mouse_imgcoord_x = -3
      if True:
        # mouse pointer x over image - find equivalent image pixel
        within_image_x = self.mousecoords[0] - offsx;
        print("self.mouse_imgcoord_x = math.floor((within_image_x/self.imscw)*self.imwidth)")
        print(self.mouse_imgcoord_x, "= math.floor((", within_image_x, "/", self.imscw, ")*", self.imwidth, ")")
        self.mouse_imgcoord_x = math.floor((within_image_x/self.imscw)*self.imwidth)
    else:
      # here the hor. scrollbar is shown, handle coords
      self.scrollfact_offx = hajd.get_value()/(hajd.get_upper()-hajd.get_lower())
      self.viewport_offset_imgx = self.scrollfact_offx*self.imwidth
      self.scrollfact_szx = hajd.get_page_size()/(hajd.get_upper()-hajd.get_lower())
      self.mouse_imgcoord_x = self.viewport_offset_imgx+self.mousecoords[0]/self.zoom
      if (self.mouse_imgcoord_x > self.imwidth):
        self.mouse_imgcoord_x = -10


    #if (valloc.x == -1): # not good condition, -1 only at start
    if (self.imsch <= self.scrollviewalloc.height):
      # if the ver. scrollbar is not shown, then image is smaller ...
      offsy = math.floor((self.scrollviewalloc.height-self.imsch)/2)
      if (self.mousecoords[1] < offsy) or (self.mousecoords[1] > self.scrollviewalloc.height-offsy):
        self.mouse_imgcoord_y = -1
      if True:
        within_image_y = self.mousecoords[1] - offsy;
        self.mouse_imgcoord_y = math.floor((within_image_y/self.imsch)*self.imheight)
    else:
      # here the ver. scrollbar is shown, handle coords
      self.scrollfact_offy = vajd.get_value()/(vajd.get_upper()-vajd.get_lower())
      self.viewport_offset_imgy = self.scrollfact_offy*self.imheight
      self.scrollfact_szy = vajd.get_page_size()/(vajd.get_upper()-vajd.get_lower())
      self.mouse_imgcoord_y = self.viewport_offset_imgy+self.mousecoords[1]/self.zoom
      if (self.mouse_imgcoord_y > self.imheight):
        self.mouse_imgcoord_y = -10

  # when image is zoomed, the scrollview state can be
  # described as a viewport; output that viewport in
  # image pixel coordinates, string formatted
  # as ImageMagick geometry argument WxH+X+Y:
  # http://www.imagemagick.org/Usage/basics/#arg_geometry
  # http://www.imagemagick.org/script/command-line-processing.php#geometry
  def get_scviewport_IMstring(self):
    retIMstr = ""
    xs = ys = ws = hs = -1

    if (self.imscw >= self.scrollviewalloc.width):
      # note here zoom > 1; scrollfact < 1
      # left edge is self.viewport_offset_imgx (img pixels)
      xs = self.viewport_offset_imgx
      # width
      ws = self.imwidth*self.scrollfact_szx;
    if (self.imsch >= self.scrollviewalloc.height):
      # note here zoom > 1; scrollfact < 1
      # top edge is self.viewport_offset_imgy (img pixels)
      ys = self.viewport_offset_imgy
      # height
      hs = self.imheight*self.scrollfact_szy;

    retIMstr = "%dx%d+%d+%d" % (ws, hs, xs, ys)

    return retIMstr

  def get_test_IMstring(self):
    # test ImageMagick `display` command (print to stdout only)
    vpstr = self.get_scviewport_IMstring()
    fnstr = self.image.get_file().get_path()
    testIMstr = 'display -crop %s "%s"' % (vpstr, fnstr)
    return testIMstr


  def image_size_prepared(self, eogImage, width, height):
    # runs only once per image load; gets only unscaled/unzoomed width/height
    # (same as window.get_image().get_pixbuf().get_width() / get_height())
    #~ print "image_size_prepared: o1 ", o1 , " o2 ", o2 # takes exactly 3 arguments (4 given)
    #~ print "image_size_prepared: o1 ", o1 #, " o2 ", o2 # takes exactly 2 arguments (4 given)
    print("image_size_prepared: eogImage ", eogImage , " width ", width, " height ", height)


"""

<qp l="https://github.com/mormegil-cz/gnubg/blob/master/gtkgame.c" t="gnubg/gtkgame.c at master - mormegil-cz/gnubg - GitHub" d="Sun Jan 20 2013 23:54:31 GMT+0100 (CET)" s="1">
/* The brain-damaged gtk_statusbar_pop interface doesn't return a value,
so we have to use a signal to see if anything was actually popped. */
static int fFinishedPopping;

static void TextPopped( GtkWidget *UNUSED(pw), guint UNUSED(id), gchar *text, void *UNUSED(p) ) {

    if( !text )
fFinishedPopping = TRUE;
}

</qp>

>>> print window.get_view().get_children()
[<gtk.VScrollbar object at 0x980120c (GtkVScrollbar at 0x956f140)>, <gtk.HScrollbar object at 0x9801234 (GtkHScrollbar at 0x956f008)>, <gtk.DrawingArea object at 0x980125c (GtkDrawingArea at 0x941b280)>]

in eog.defs:
(define-method get_size
  (of-object "EogImage")
  (c-name "eog_image_get_size")
but nothing via
print window.get_image().get_size() # here is EogImage (not in activate)
and in eog-image.c
void
eog_image_get_size (EogImage *img, int *width, int *height)
but still: Eye of GNOME Image Viewer 2.32.1: 'eog.Image' object has no attribute 'get_size'




>>> dir(window)
['__class__', '__copy__', '__deepcopy__', '__delattr__', '__dict__', '__doc__', '__eq__', '__format__', '__gdoc__', '__ge__', '__getattribute__', '__gobject_init__', '__grefcount__', '__gt__', '__gtype__', '__hash__', '__init__', '__iter__', '__le__', '__len__', '__lt__', '__module__', '__ne__', '__new__', '__nonzero__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__', 'activate', 'activate_default', 'activate_focus', 'activate_key', 'add', 'add_accel_group', 'add_accelerator', 'add_child', 'add_events', 'add_mnemonic', 'add_mnemonic_label', 'add_with_properties', 'allocation', 'allow_grow', 'allow_shrink', 'begin_move_drag', 'begin_resize_drag', 'border_width', 'can_activate_accel', 'chain', 'check_resize', 'child', 'child_focus', 'child_get', 'child_get_property', 'child_notify', 'child_set', 'child_set_property', 'child_type', 'children', 'class_path', 'configure_notify_received', 'configure_request_count', 'connect', 'connect_after', 'connect_object', 'connect_object_after', 'construct_child', 'create_pango_context', 'create_pango_layout', 'decorated', 'default_widget', 'deiconify', 'destroy', 'destroy_with_parent', 'disconnect', 'disconnect_by_func', 'do_activate_default', 'do_activate_focus', 'do_add', 'do_add_child', 'do_button_press_event', 'do_button_release_event', 'do_can_activate_accel', 'do_check_resize', 'do_child_type', 'do_client_event', 'do_composite_name', 'do_composited_changed', 'do_configure_event', 'do_construct_child', 'do_delete_event', 'do_destroy', 'do_destroy_event', 'do_direction_changed', 'do_drag_begin', 'do_drag_data_delete', 'do_drag_data_get', 'do_drag_data_received', 'do_drag_drop', 'do_drag_end', 'do_drag_leave', 'do_drag_motion', 'do_enter_notify_event', 'do_event', 'do_expose_event', 'do_focus', 'do_focus_in_event', 'do_focus_out_event', 'do_forall', 'do_frame_event', 'do_get_accessible', 'do_get_child_property', 'do_get_internal_child', 'do_grab_broken_event', 'do_grab_focus', 'do_grab_notify', 'do_hide', 'do_hide_all', 'do_hierarchy_changed', 'do_key_press_event', 'do_key_release_event', 'do_keys_changed', 'do_leave_notify_event', 'do_map', 'do_map_event', 'do_mnemonic_activate', 'do_motion_notify_event', 'do_move_focus', 'do_no_expose_event', 'do_parent_set', 'do_parser_finished', 'do_popup_menu', 'do_property_notify_event', 'do_proximity_in_event', 'do_proximity_out_event', 'do_realize', 'do_remove', 'do_screen_changed', 'do_scroll_event', 'do_selection_clear_event', 'do_selection_get', 'do_selection_notify_event', 'do_selection_received', 'do_selection_request_event', 'do_set_child_property', 'do_set_focus', 'do_set_focus_child', 'do_set_name', 'do_show', 'do_show_all', 'do_show_help', 'do_size_allocate', 'do_size_request', 'do_state_changed', 'do_style_set', 'do_unmap', 'do_unmap_event', 'do_unrealize', 'do_visibility_notify_event', 'do_window_state_event', 'drag_begin', 'drag_check_threshold', 'drag_dest_add_image_targets', 'drag_dest_add_text_targets', 'drag_dest_add_uri_targets', 'drag_dest_find_target', 'drag_dest_get_target_list', 'drag_dest_get_track_motion', 'drag_dest_set', 'drag_dest_set_proxy', 'drag_dest_set_target_list', 'drag_dest_set_track_motion', 'drag_dest_unset', 'drag_get_data', 'drag_highlight', 'drag_source_add_image_targets', 'drag_source_add_text_targets', 'drag_source_add_uri_targets', 'drag_source_get_target_list', 'drag_source_set', 'drag_source_set_icon', 'drag_source_set_icon_name', 'drag_source_set_icon_pixbuf', 'drag_source_set_icon_stock', 'drag_source_set_target_list', 'drag_source_unset', 'drag_unhighlight', 'draw', 'emit', 'emit_stop_by_name', 'ensure_style', 'error_bell', 'event', 'flags', 'focus_child', 'focus_widget', 'forall', 'foreach', 'frame', 'frame_bottom', 'frame_left', 'frame_right', 'frame_top', 'freeze_child_notify', 'freeze_notify', 'fullscreen', 'get_accept_focus',
'get_accessible', 'get_action', 'get_activate_signal', 'get_allocation', 'get_ancestor', 'get_app_paintable', 'get_border_width', 'get_can_default', 'get_can_focus', 'get_child', 'get_child_requisition', 'get_child_visible', 'get_children', 'get_clipboard', 'get_colormap', 'get_composite_name', 'get_data', 'get_decorated', 'get_default_size', 'get_default_widget', 'get_deletable', 'get_destroy_with_parent', 'get_direction', 'get_display', 'get_double_buffered', 'get_events', 'get_extension_events', 'get_focus', 'get_focus_chain', 'get_focus_child', 'get_focus_hadjustment', 'get_focus_on_map', 'get_focus_vadjustment', 'get_frame_dimensions', 'get_gravity', 'get_group', 'get_has_frame', 'get_has_tooltip', 'get_has_window', 'get_icon', 'get_icon_list', 'get_icon_name', 'get_image', 'get_internal_child', 'get_mapped', 'get_mnemonic_modifier', 'get_mnemonics_visible', 'get_modal', 'get_mode', 'get_modifier_style', 'get_name', 'get_no_show_all', 'get_opacity', 'get_pango_context', 'get_parent', 'get_parent_window', 'get_pointer', 'get_position', 'get_properties', 'get_property', 'get_realized', 'get_receives_default', 'get_requisition', 'get_resizable', 'get_resize_mode', 'get_role', 'get_root_window', 'get_screen', 'get_sensitive', 'get_settings', 'get_sidebar', 'get_size', 'get_size_request', 'get_skip_pager_hint', 'get_skip_taskbar_hint', 'get_snapshot', 'get_state', 'get_statusbar', 'get_store', 'get_style', 'get_thumb_nav', 'get_thumb_view', 'get_title', 'get_tooltip_markup', 'get_tooltip_text', 'get_tooltip_window', 'get_toplevel', 'get_transient_for', 'get_type_hint', 'get_ui_manager', 'get_urgency_hint', 'get_view', 'get_visible', 'get_visual', 'get_window', 'get_window_type', 'grab_add', 'grab_default', 'grab_focus', 'grab_remove', 'gravity', 'group', 'handler_block', 'handler_block_by_func', 'handler_disconnect', 'handler_is_connected', 'handler_unblock', 'handler_unblock_by_func', 'has_default', 'has_focus', 'has_focus_chain', 'has_frame', 'has_grab', 'has_group', 'has_rc_style', 'has_screen', 'has_toplevel_focus', 'has_user_ref_count', 'hide', 'hide_all', 'hide_on_delete', 'iconify', 'iconify_initially', 'input_shape_combine_mask', 'install_child_property', 'intersect', 'is_active', 'is_ancestor', 'is_composited', 'is_drawable', 'is_empty', 'is_focus', 'is_sensitive', 'is_toplevel', 'keynav_failed', 'keys_changed_handler', 'list_accel_closures', 'list_child_properties', 'list_mnemonic_labels', 'map', 'maximize', 'maximize_initially', 'menu_get_for_attach_widget', 'mnemonic_activate', 'mnemonic_modifier', 'modal', 'modify_base', 'modify_bg', 'modify_cursor', 'modify_fg', 'modify_font', 'modify_style', 'modify_text', 'move', 'name', 'need_default_position', 'need_default_size', 'need_resize', 'notify', 'parent', 'parse_geometry', 'parser_finished', 'path', 'position', 'present', 'present_with_time', 'propagate_expose', 'propagate_key_event', 'props', 'queue_clear', 'queue_clear_area', 'queue_draw', 'queue_draw_area', 'queue_resize', 'queue_resize_no_redraw', 'rc_get_style', 'realize', 'reallocate_redraws', 'ref_accessible', 'region_intersect', 'remove', 'remove_accel_group', 'remove_accelerator', 'remove_data', 'remove_mnemonic', 'remove_mnemonic_label', 'remove_no_notify', 'render_icon', 'reparent', 'requisition', 'reset_rc_styles', 'reset_shapes', 'reshow_with_initial_size', 'resize', 'resize_children', 'resize_mode', 'saved_state', 'selection_add_target', 'selection_add_targets', 'selection_clear_targets', 'selection_convert', 'selection_owner_set', 'selection_remove_all', 'send_expose', 'send_focus_change', 'set_accel_path', 'set_accept_focus', 'set_activate_signal', 'set_allocation', 'set_app_paintable', 'set_border_width', 'set_can_default', 'set_can_focus', 'set_child_visible', 'set_colormap', 'set_composite_name', 'set_data', 'set_decorated', 'set_default', 'set_default_size', 'set_deletable', 'set_destroy_with_parent', 'set_direction', 'set_double_buffered', 'set_events', 'set_extension_events', 'set_flags', 'set_focus', 'set_focus_chain', 'set_focus_child', 'set_focus_hadjustment', 'set_focus_on_map', 'set_focus_vadjustment', 'set_frame_dimensions', 'set_geometry_hints', 'set_gravity', 'set_has_frame', 'set_has_tooltip', 'set_has_window', 'set_icon', 'set_icon_from_file', 'set_icon_list', 'set_icon_name', 'set_keep_above', 'set_keep_below', 'set_mapped', 'set_mnemonic_modifier', 'set_mnemonics_visible', 'set_modal', 'set_mode', 'set_name', 'set_no_show_all', 'set_opacity', 'set_parent', 'set_parent_window', 'set_policy', 'set_position', 'set_properties', 'set_property', 'set_realized', 'set_reallocate_redraws', 'set_receives_default', 'set_redraw_on_allocate', 'set_resizable', 'set_resize_mode', 'set_role', 'set_screen', 'set_scroll_adjustments', 'set_sensitive', 'set_set_scroll_adjustments_signal', 'set_size_request', 'set_skip_pager_hint', 'set_skip_taskbar_hint', 'set_startup_id', 'set_state', 'set_style', 'set_title', 'set_tooltip_markup', 'set_tooltip_text', 'set_tooltip_window', 'set_transient_for', 'set_type_hint', 'set_uposition', 'set_urgency_hint', 'set_usize', 'set_visible', 'set_window', 'set_wmclass', 'shape_combine_mask', 'show', 'show_all', 'show_now', 'size_allocate', 'size_request', 'state', 'stick', 'stick_initially', 'stop_emission', 'style', 'style_attach', 'style_get_property', 'thaw_child_notify', 'thaw_notify', 'title', 'tooltips_get_info_from_tip_window', 'transient_parent', 'translate_coordinates', 'trigger_tooltip_query', 'type', 'type_hint', 'unfullscreen', 'unmap', 'unmaximize', 'unparent', 'unrealize', 'unset_flags', 'unset_focus_chain', 'unstick', 'weak_ref', 'window', 'wm_role', 'wmclass_class', 'wmclass_name']
>>> dir(window.get_view())
['__class__', '__copy__', '__deepcopy__', '__delattr__', '__dict__', '__doc__', '__eq__', '__format__', '__gdoc__', '__ge__', '__getattribute__', '__gobject_init__', '__grefcount__', '__gt__', '__gtype__', '__hash__', '__init__', '__iter__', '__le__', '__len__', '__lt__', '__module__', '__ne__', '__new__', '__nonzero__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__', 'activate', 'add', 'add_accelerator', 'add_child', 'add_events', 'add_mnemonic_label', 'add_with_properties', 'allocation', 'attach', 'attach_defaults', 'border_width', 'can_activate_accel', 'chain', 'check_resize', 'child_focus', 'child_get', 'child_get_property', 'child_notify', 'child_set', 'child_set_property', 'child_type', 'children', 'class_path', 'connect', 'connect_after', 'connect_object', 'connect_object_after', 'construct_child', 'create_pango_context', 'create_pango_layout', 'destroy', 'disconnect', 'disconnect_by_func', 'do_add', 'do_add_child', 'do_button_press_event', 'do_button_release_event', 'do_can_activate_accel', 'do_check_resize', 'do_child_type', 'do_client_event', 'do_composite_name', 'do_composited_changed', 'do_configure_event', 'do_construct_child', 'do_delete_event', 'do_destroy', 'do_destroy_event', 'do_direction_changed', 'do_drag_begin', 'do_drag_data_delete', 'do_drag_data_get', 'do_drag_data_received', 'do_drag_drop', 'do_drag_end', 'do_drag_leave', 'do_drag_motion', 'do_enter_notify_event', 'do_event', 'do_expose_event', 'do_focus', 'do_focus_in_event', 'do_focus_out_event', 'do_forall', 'do_get_accessible', 'do_get_child_property', 'do_get_internal_child', 'do_grab_broken_event', 'do_grab_focus', 'do_grab_notify', 'do_hide', 'do_hide_all', 'do_hierarchy_changed', 'do_key_press_event', 'do_key_release_event', 'do_leave_notify_event', 'do_map', 'do_map_event', 'do_mnemonic_activate', 'do_motion_notify_event', 'do_no_expose_event', 'do_parent_set', 'do_parser_finished', 'do_popup_menu', 'do_property_notify_event', 'do_proximity_in_event', 'do_proximity_out_event', 'do_realize', 'do_remove', 'do_screen_changed', 'do_scroll_event', 'do_selection_clear_event', 'do_selection_get', 'do_selection_notify_event', 'do_selection_received', 'do_selection_request_event', 'do_set_child_property', 'do_set_focus_child', 'do_set_name', 'do_show', 'do_show_all', 'do_show_help', 'do_size_allocate', 'do_size_request', 'do_state_changed', 'do_style_set', 'do_unmap', 'do_unmap_event', 'do_unrealize', 'do_visibility_notify_event', 'do_window_state_event', 'drag_begin', 'drag_check_threshold', 'drag_dest_add_image_targets', 'drag_dest_add_text_targets', 'drag_dest_add_uri_targets', 'drag_dest_find_target', 'drag_dest_get_target_list', 'drag_dest_get_track_motion', 'drag_dest_set', 'drag_dest_set_proxy', 'drag_dest_set_target_list', 'drag_dest_set_track_motion', 'drag_dest_unset', 'drag_get_data', 'drag_highlight', 'drag_source_add_image_targets', 'drag_source_add_text_targets', 'drag_source_add_uri_targets', 'drag_source_get_target_list', 'drag_source_set', 'drag_source_set_icon', 'drag_source_set_icon_name', 'drag_source_set_icon_pixbuf', 'drag_source_set_icon_stock', 'drag_source_set_target_list', 'drag_source_unset', 'drag_unhighlight', 'draw', 'emit', 'emit_stop_by_name', 'ensure_style', 'error_bell', 'event', 'flags', 'focus_child', 'forall', 'foreach', 'freeze_child_notify', 'freeze_notify', 'get_accessible', 'get_action', 'get_activate_signal', 'get_allocation', 'get_ancestor', 'get_app_paintable', 'get_border_width', 'get_can_default', 'get_can_focus', 'get_child_requisition', 'get_child_visible', 'get_children', 'get_clipboard', 'get_col_spacing', 'get_colormap', 'get_composite_name', 'get_data', 'get_default_col_spacing', 'get_default_row_spacing', 'get_direction', 'get_display', 'get_double_buffered', 'get_events', 'get_extension_events', 'get_focus_chain', 'get_focus_child', 'get_focus_hadjustment', 'get_focus_vadjustment', 'get_has_tooltip', 'get_has_window', 'get_homogeneous', 'get_internal_child', 'get_mapped', 'get_modifier_style', 'get_name', 'get_no_show_all', 'get_pango_context', 'get_parent', 'get_parent_window', 'get_pointer', 'get_properties', 'get_property', 'get_realized', 'get_receives_default', 'get_requisition', 'get_resize_mode', 'get_root_window', 'get_row_spacing', 'get_screen', 'get_sensitive', 'get_settings', 'get_size_request', 'get_snapshot', 'get_state', 'get_style', 'get_tooltip_markup', 'get_tooltip_text', 'get_tooltip_window', 'get_toplevel', 'get_visible', 'get_visual', 'get_window', 'get_zoom', 'get_zoom_is_max', 'get_zoom_is_min', 'grab_add', 'grab_default', 'grab_focus', 'grab_remove', 'handler_block', 'handler_block_by_func', 'handler_disconnect', 'handler_is_connected', 'handler_unblock', 'handler_unblock_by_func', 'has_default', 'has_focus', 'has_focus_chain', 'has_grab', 'has_rc_style', 'has_screen', 'hide', 'hide_all', 'hide_cursor', 'hide_on_delete', 'input_shape_combine_mask', 'install_child_property', 'intersect', 'is_ancestor', 'is_composited', 'is_drawable', 'is_focus', 'is_sensitive', 'is_toplevel', 'keynav_failed', 'list_accel_closures', 'list_child_properties', 'list_mnemonic_labels', 'map', 'menu_get_for_attach_widget', 'mnemonic_activate', 'modify_base', 'modify_bg', 'modify_cursor', 'modify_fg', 'modify_font', 'modify_style', 'modify_text', 'name', 'need_resize', 'notify', 'parent', 'parser_finished', 'path', 'propagate_expose', 'props', 'queue_clear', 'queue_clear_area', 'queue_draw', 'queue_draw_area', 'queue_resize', 'queue_resize_no_redraw', 'rc_get_style', 'realize', 'reallocate_redraws', 'ref_accessible', 'region_intersect', 'remove', 'remove_accelerator', 'remove_data', 'remove_mnemonic_label', 'remove_no_notify', 'render_icon', 'reparent', 'requisition', 'reset_rc_styles', 'reset_shapes', 'resize', 'resize_children', 'resize_mode', 'saved_state', 'scrollbars_visible', 'selection_add_target', 'selection_add_targets', 'selection_clear_targets', 'selection_convert', 'selection_owner_set', 'selection_remove_all', 'send_expose', 'send_focus_change', 'set_accel_path', 'set_activate_signal', 'set_allocation', 'set_antialiasing_in', 'set_antialiasing_out', 'set_app_paintable', 'set_border_width', 'set_can_default', 'set_can_focus', 'set_child_visible', 'set_col_spacing', 'set_col_spacings', 'set_colormap', 'set_composite_name', 'set_data', 'set_direction', 'set_double_buffered', 'set_events', 'set_extension_events', 'set_flags', 'set_focus_chain', 'set_focus_child', 'set_focus_hadjustment', 'set_focus_vadjustment', 'set_has_tooltip', 'set_has_window', 'set_homogeneous', 'set_image', 'set_mapped', 'set_name', 'set_no_show_all', 'set_parent', 'set_parent_window', 'set_properties', 'set_property', 'set_realized', 'set_reallocate_redraws', 'set_receives_default', 'set_redraw_on_allocate', 'set_resize_mode', 'set_row_spacing', 'set_row_spacings', 'set_scroll_adjustments', 'set_sensitive', 'set_set_scroll_adjustments_signal', 'set_size_request', 'set_state', 'set_style', 'set_tooltip_markup', 'set_tooltip_text', 'set_tooltip_window', 'set_transparency', 'set_uposition', 'set_usize', 'set_visible', 'set_window', 'set_zoom', 'set_zoom_multiplier', 'set_zoom_upscale', 'shape_combine_mask', 'show', 'show_all', 'show_cursor', 'show_now', 'size_allocate', 'size_request', 'state', 'stop_emission', 'style', 'style_attach', 'style_get_property', 'thaw_child_notify', 'thaw_notify', 'translate_coordinates', 'trigger_tooltip_query', 'unmap', 'unparent', 'unrealize', 'unset_flags', 'unset_focus_chain', 'weak_ref', 'window', 'zoom_fit', 'zoom_in', 'zoom_out']
>>> dir(window.get_image())
['__class__', '__copy__', '__deepcopy__', '__delattr__', '__dict__', '__doc__', '__eq__', '__format__', '__gdoc__', '__ge__', '__getattribute__', '__gobject_init__', '__grefcount__', '__gt__', '__gtype__', '__hash__', '__init__', '__le__', '__lt__', '__module__', '__ne__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__', 'chain', 'connect', 'connect_after', 'connect_object', 'connect_object_after', 'disconnect', 'disconnect_by_func', 'emit', 'emit_stop_by_name', 'freeze_notify', 'get_bytes', 'get_caption', 'get_data', 'get_file', 'get_pixbuf', 'get_properties', 'get_property', 'get_thumbnail', 'get_uri_for_display', 'handler_block', 'handler_block_by_func', 'handler_disconnect', 'handler_is_connected', 'handler_unblock', 'handler_unblock_by_func', 'has_data', 'is_modified', 'load', 'modified', 'notify', 'props', 'set_data', 'set_properties', 'set_property', 'set_thumbnail', 'stop_emission', 'thaw_notify', 'undo', 'weak_ref']
>>> dir(window.get_display())
['__class__', '__copy__', '__deepcopy__', '__delattr__', '__dict__', '__doc__', '__eq__', '__format__', '__gdoc__', '__ge__', '__getattribute__', '__gobject_init__', '__grefcount__', '__gt__', '__gtype__', '__hash__', '__init__', '__le__', '__lt__', '__module__', '__ne__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__', 'beep', 'chain', 'close', 'connect', 'connect_after', 'connect_object', 'connect_object_after', 'disconnect', 'disconnect_by_func', 'do_closed', 'do_get_default_screen', 'do_get_display_name', 'do_get_n_screens', 'do_get_screen', 'emit', 'emit_stop_by_name', 'flush', 'freeze_notify', 'get_core_pointer', 'get_data', 'get_default_cursor_size', 'get_default_group', 'get_default_screen', 'get_event', 'get_maximal_cursor_size', 'get_n_screens', 'get_name', 'get_pointer', 'get_properties', 'get_property', 'get_screen', 'get_user_time', 'get_window_at_pointer', 'grab', 'handler_block', 'handler_block_by_func', 'handler_disconnect', 'handler_is_connected', 'handler_unblock', 'handler_unblock_by_func', 'is_closed', 'keyboard_ungrab', 'list_devices', 'notify', 'peek_event', 'pointer_is_grabbed', 'pointer_ungrab', 'props', 'put_event', 'request_selection_notification', 'set_data', 'set_double_click_distance', 'set_double_click_time', 'set_properties', 'set_property', 'stop_emission', 'store_clipboard', 'supports_clipboard_persistence', 'supports_composite', 'supports_cursor_alpha', 'supports_cursor_color', 'supports_input_shapes', 'supports_selection_notification', 'supports_shapes', 'sync', 'thaw_notify', 'ungrab', 'warp_pointer', 'weak_ref']

>>> print(window.get_view().get_children()[0])
<gtk.VScrollbar object at 0x8c5de64 (GtkVScrollbar at 0x89cb140)>

>>> dir(window.get_view().get_children()[0])
['__class__', '__copy__', '__deepcopy__', '__delattr__', '__dict__', '__doc__', '__eq__', '__format__', '__gdoc__', '__ge__', '__getattribute__', '__gobject_init__', '__grefcount__', '__gt__', '__gtype__', '__hash__', '__init__', '__le__', '__lt__', '__module__', '__ne__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__', 'activate', 'add_accelerator', 'add_child', 'add_events', 'add_mnemonic_label', 'allocation', 'can_activate_accel', 'chain', 'child_focus', 'child_notify', 'class_path', 'connect', 'connect_after', 'connect_object', 'connect_object_after', 'construct_child', 'create_pango_context', 'create_pango_layout', 'destroy', 'disconnect', 'disconnect_by_func', 'do_add_child', 'do_adjust_bounds', 'do_button_press_event', 'do_button_release_event', 'do_can_activate_accel', 'do_change_value', 'do_client_event', 'do_composited_changed', 'do_configure_event', 'do_construct_child', 'do_delete_event', 'do_destroy', 'do_destroy_event', 'do_direction_changed', 'do_drag_begin', 'do_drag_data_delete', 'do_drag_data_get', 'do_drag_data_received', 'do_drag_drop', 'do_drag_end', 'do_drag_leave', 'do_drag_motion', 'do_enter_notify_event', 'do_event', 'do_expose_event', 'do_focus', 'do_focus_in_event', 'do_focus_out_event', 'do_get_accessible', 'do_get_internal_child', 'do_get_range_border', 'do_grab_broken_event', 'do_grab_focus', 'do_grab_notify', 'do_hide', 'do_hide_all', 'do_hierarchy_changed', 'do_key_press_event', 'do_key_release_event', 'do_leave_notify_event', 'do_map', 'do_map_event', 'do_mnemonic_activate', 'do_motion_notify_event', 'do_move_slider', 'do_no_expose_event', 'do_parent_set', 'do_parser_finished', 'do_popup_menu', 'do_property_notify_event', 'do_proximity_in_event', 'do_proximity_out_event', 'do_realize', 'do_screen_changed', 'do_scroll_event', 'do_selection_clear_event', 'do_selection_get', 'do_selection_notify_event', 'do_selection_received', 'do_selection_request_event', 'do_set_name', 'do_show', 'do_show_all', 'do_show_help', 'do_size_allocate', 'do_size_request', 'do_state_changed', 'do_style_set', 'do_unmap', 'do_unmap_event', 'do_unrealize', 'do_value_changed', 'do_visibility_notify_event', 'do_window_state_event', 'drag_begin', 'drag_check_threshold', 'drag_dest_add_image_targets', 'drag_dest_add_text_targets', 'drag_dest_add_uri_targets', 'drag_dest_find_target', 'drag_dest_get_target_list', 'drag_dest_get_track_motion', 'drag_dest_set', 'drag_dest_set_proxy', 'drag_dest_set_target_list', 'drag_dest_set_track_motion', 'drag_dest_unset', 'drag_get_data', 'drag_highlight', 'drag_source_add_image_targets', 'drag_source_add_text_targets', 'drag_source_add_uri_targets', 'drag_source_get_target_list', 'drag_source_set', 'drag_source_set_icon', 'drag_source_set_icon_name', 'drag_source_set_icon_pixbuf', 'drag_source_set_icon_stock', 'drag_source_set_target_list', 'drag_source_unset', 'drag_unhighlight', 'draw', 'emit', 'emit_stop_by_name', 'ensure_style', 'error_bell', 'event', 'flags', 'freeze_child_notify', 'freeze_notify',
'get_accessible', 'get_action', 'get_activate_signal', 'get_adjustment', 'get_allocation', 'get_ancestor', 'get_app_paintable', 'get_can_default', 'get_can_focus', 'get_child_requisition', 'get_child_visible', 'get_clipboard', 'get_colormap', 'get_composite_name', 'get_data', 'get_direction', 'get_display', 'get_double_buffered', 'get_events', 'get_extension_events', 'get_fill_level', 'get_flippable', 'get_has_tooltip', 'get_has_window', 'get_internal_child', 'get_inverted', 'get_lower_stepper_sensitivity', 'get_mapped', 'get_min_slider_size', 'get_modifier_style', 'get_name', 'get_no_show_all', 'get_orientation', 'get_pango_context', 'get_parent', 'get_parent_window', 'get_pointer', 'get_properties', 'get_property', 'get_range_rect', 'get_realized', 'get_receives_default', 'get_requisition', 'get_restrict_to_fill_level', 'get_root_window', 'get_screen', 'get_sensitive', 'get_settings', 'get_show_fill_level', 'get_size_request', 'get_slider_size_fixed', 'get_snapshot', 'get_state', 'get_style', 'get_tooltip_markup', 'get_tooltip_text', 'get_tooltip_window', 'get_toplevel', 'get_update_policy', 'get_upper_stepper_sensitivity', 'get_value', 'get_visible', 'get_visual', 'get_window', 'grab_add', 'grab_default', 'grab_focus', 'grab_remove', 'handler_block', 'handler_block_by_func', 'handler_disconnect', 'handler_is_connected', 'handler_unblock', 'handler_unblock_by_func', 'has_default', 'has_focus', 'has_grab', 'has_rc_style', 'has_screen', 'hide', 'hide_all', 'hide_on_delete', 'input_shape_combine_mask', 'intersect', 'is_ancestor', 'is_composited', 'is_drawable', 'is_focus', 'is_sensitive', 'is_toplevel', 'keynav_failed', 'list_accel_closures', 'list_mnemonic_labels', 'map', 'menu_get_for_attach_widget', 'mnemonic_activate', 'modify_base', 'modify_bg', 'modify_cursor', 'modify_fg', 'modify_font', 'modify_style', 'modify_text', 'name', 'notify', 'parent', 'parser_finished', 'path', 'props', 'queue_clear', 'queue_clear_area', 'queue_draw', 'queue_draw_area', 'queue_resize', 'queue_resize_no_redraw', 'rc_get_style', 'realize', 'ref_accessible', 'region_intersect', 'remove_accelerator', 'remove_data', 'remove_mnemonic_label', 'remove_no_notify', 'render_icon', 'reparent', 'requisition', 'reset_rc_styles', 'reset_shapes', 'saved_state', 'selection_add_target', 'selection_add_targets', 'selection_clear_targets', 'selection_convert', 'selection_owner_set', 'selection_remove_all', 'send_expose', 'send_focus_change', 'set_accel_path', 'set_activate_signal', 'set_adjustment', 'set_allocation', 'set_app_paintable', 'set_can_default', 'set_can_focus', 'set_child_visible', 'set_colormap', 'set_composite_name', 'set_data', 'set_direction', 'set_double_buffered', 'set_events', 'set_extension_events', 'set_fill_level', 'set_flags', 'set_flippable', 'set_has_tooltip', 'set_has_window', 'set_increments', 'set_inverted', 'set_lower_stepper_sensitivity', 'set_mapped', 'set_min_slider_size', 'set_name', 'set_no_show_all', 'set_orientation', 'set_parent', 'set_parent_window', 'set_properties', 'set_property', 'set_range', 'set_realized', 'set_receives_default', 'set_redraw_on_allocate', 'set_restrict_to_fill_level', 'set_scroll_adjustments', 'set_sensitive', 'set_set_scroll_adjustments_signal', 'set_show_fill_level', 'set_size_request', 'set_slider_size_fixed', 'set_state', 'set_style', 'set_tooltip_markup', 'set_tooltip_text', 'set_tooltip_window', 'set_update_policy', 'set_uposition', 'set_upper_stepper_sensitivity', 'set_usize', 'set_value', 'set_visible', 'set_window', 'shape_combine_mask', 'show', 'show_all', 'show_now', 'size_allocate', 'size_request', 'state', 'stop_emission', 'style', 'style_attach', 'style_get_property', 'thaw_child_notify', 'thaw_notify', 'translate_coordinates', 'trigger_tooltip_query', 'unmap', 'unparent', 'unrealize', 'unset_flags', 'weak_ref', 'window']

>>> print window.get_view().get_children()[1].get_adjustment()
<gtk.Adjustment object at 0x8c623c4 (GtkAdjustment at 0x8881180)>
>>> dir(window.get_view().get_children()[1].get_adjustment())
['__class__', '__copy__', '__deepcopy__', '__delattr__', '__dict__', '__doc__', '__eq__', '__format__', '__gdoc__', '__ge__', '__getattribute__', '__gobject_init__', '__grefcount__', '__gt__', '__gtype__', '__hash__', '__init__', '__le__', '__lt__', '__module__', '__ne__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__', 'chain', 'changed', 'clamp_page', 'configure', 'connect', 'connect_after', 'connect_object', 'connect_object_after', 'destroy', 'disconnect', 'disconnect_by_func', 'do_changed', 'do_destroy', 'do_value_changed', 'emit', 'emit_stop_by_name', 'flags', 'freeze_notify', 'get_data', 'get_lower', 'get_page_increment', 'get_page_size', 'get_properties', 'get_property', 'get_step_increment', 'get_upper', 'get_value', 'handler_block', 'handler_block_by_func', 'handler_disconnect', 'handler_is_connected', 'handler_unblock', 'handler_unblock_by_func', 'lower', 'notify', 'page_increment', 'page_size', 'props', 'remove_data', 'remove_no_notify', 'set_all', 'set_data', 'set_flags', 'set_lower', 'set_page_increment', 'set_page_size', 'set_properties', 'set_property', 'set_step_increment', 'set_upper', 'set_value', 'step_increment', 'stop_emission', 'thaw_notify', 'unset_flags', 'upper', 'value', 'value_changed', 'weak_ref']

#The gtk.Scrollbar widget is an abstract base class for gtk.HScrollbar and #gtk.VScrollbar. The position of the thumb in a scrollbar is controlled by the# #scroll adjustments. The gtk.Scrollbar uses the attributes in an adjustment (see #gtk.Adjustment) as follows:

# note - slider and its adjustment have same value:
>>> print window.get_view().get_children()[1].get_adjustment().get_value()
177.0
>>> print window.get_view().get_children()[1].get_value()
177.0


"""
