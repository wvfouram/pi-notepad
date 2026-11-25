#!/usr/bin/python3
# Notepad for Raspberry Pi, styled after the Windows 11 Notepad (dark).
import os
import sys
import re
import json
import math
import time
import shutil
import signal
import threading
import subprocess

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf, Pango, Gio, GObject  # noqa: E402,F401
import cairo  # noqa: E402

HOME = os.path.expanduser("~")
C_ACCENT = "#4CC2FF"
def hexc(h, a=1.0):
    h = h.lstrip("#")
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, a)


def _rr(cr, x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    cr.close_path()


def _line(cr, *pts):
    cr.move_to(*pts[0])
    for p in pts[1:]:
        cr.line_to(*p)
    cr.stroke()


def draw_glyph(cr, name, s, col):
    """Monochrome line icons for buttons."""
    cr.save()
    cr.scale(s / 16.0, s / 16.0)
    cr.set_source_rgba(*col)
    cr.set_line_width(1.15)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.set_line_join(cairo.LINE_JOIN_ROUND)
    pi = math.pi
    L = lambda *p: _line(cr, *p)  # noqa: E731
    if name == "back":
        L((13.5, 8), (2.5, 8))
        L((7, 3.5), (2.5, 8), (7, 12.5))
    elif name == "forward":
        L((2.5, 8), (13.5, 8))
        L((9, 3.5), (13.5, 8), (9, 12.5))
    elif name == "up":
        L((8, 13.5), (8, 2.5))
        L((3.5, 7), (8, 2.5), (12.5, 7))
    elif name == "refresh":
        cr.arc(8, 8, 5.5, -pi * 0.35, pi * 1.55)
        cr.stroke()
        L((12.9, 1.8), (12.6, 4.9), (9.6, 4.6))
    elif name == "plus":
        L((8, 2.5), (8, 13.5))
        L((2.5, 8), (13.5, 8))
    elif name == "new":
        cr.set_source_rgba(*hexc(C_ACCENT))
        cr.arc(8, 8, 6.5, 0, 2 * pi)
        cr.stroke()
        L((8, 4.8), (8, 11.2))
        L((4.8, 8), (11.2, 8))
    elif name == "cut":
        cr.arc(4.5, 12, 2, 0, 2 * pi)
        cr.stroke()
        cr.arc(11.5, 12, 2, 0, 2 * pi)
        cr.stroke()
        L((5.8, 10.5), (11, 1.8))
        L((10.2, 10.5), (5, 1.8))
    elif name == "copy":
        _rr(cr, 5, 1.5, 9, 10.5, 1.5)
        cr.stroke()
        cr.move_to(3, 4.5)
        cr.line_to(3, 13)
        cr.arc_negative(4.5, 13, 1.5, pi, pi / 2)
        cr.line_to(11, 14.5)
        cr.stroke()
    elif name == "paste":
        _rr(cr, 2.5, 3, 11, 11.5, 1.5)
        cr.stroke()
        _rr(cr, 5.5, 1.5, 5, 3, 1)
        cr.stroke()
        L((5.5, 8), (10.5, 8))
        L((5.5, 11), (9, 11))
    elif name == "rename":
        _rr(cr, 1.5, 4.5, 13, 7, 1.3)
        cr.stroke()
        L((4, 8), (8, 8))
        L((10.5, 2.5), (10.5, 13.5))
        L((9, 2.5), (12, 2.5))
        L((9, 13.5), (12, 13.5))
    elif name == "delete" or name == "trash":
        L((2.5, 4), (13.5, 4))
        L((6, 4), (6.5, 2), (9.5, 2), (10, 4))
        cr.move_to(4, 4)
        cr.line_to(4.8, 14)
        cr.line_to(11.2, 14)
        cr.line_to(12, 4)
        cr.stroke()
        L((6.8, 6.8), (7, 11.5))
        L((9.2, 6.8), (9, 11.5))
    elif name == "sort":
        L((4.5, 2.5), (4.5, 13.5))
        L((2, 5), (4.5, 2.5), (7, 5))
        L((11.5, 2.5), (11.5, 13.5))
        L((9, 11), (11.5, 13.5), (14, 11))
    elif name == "view":
        for y in (3, 8, 13):
            L((2, y), (14, y))
    elif name == "more":
        for x in (3, 8, 13):
            cr.arc(x, 8, 1.1, 0, 2 * pi)
            cr.fill()
    elif name == "chevdown":
        L((4, 6), (8, 10), (12, 6))
    elif name == "chevright":
        L((6, 4), (10, 8), (6, 12))
    elif name == "close":
        L((3.5, 3.5), (12.5, 12.5))
        L((12.5, 3.5), (3.5, 12.5))
    elif name == "min":
        L((3, 8), (13, 8))
    elif name == "max":
        _rr(cr, 3, 3, 10, 10, 1.2)
        cr.stroke()
    elif name == "restore":
        _rr(cr, 3, 5, 8, 8, 1.2)
        cr.stroke()
        L((5, 3), (12, 3), (13, 4), (13, 11))
    elif name == "search":
        cr.arc(6.6, 6.6, 4.6, 0, 2 * pi)
        cr.stroke()
        L((10, 10), (14, 14))
    elif name == "pane":
        _rr(cr, 1.5, 2.5, 13, 11, 1.5)
        cr.stroke()
        L((10, 2.5), (10, 13.5))
    elif name == "terminal":
        _rr(cr, 1.5, 2.5, 13, 11, 1.5)
        cr.stroke()
        L((4, 6), (6.5, 8), (4, 10))
        L((8, 10.5), (11.5, 10.5))
    elif name == "properties":
        _rr(cr, 2.5, 1.5, 11, 13, 1.5)
        cr.stroke()
        for y in (5, 8, 11):
            cr.arc(5.2, y, 0.8, 0, 2 * pi)
            cr.fill()
            L((7.2, y), (11, y))
    elif name == "pin":
        cr.move_to(6, 2)
        cr.line_to(10, 2)
        cr.line_to(9.5, 6.5)
        cr.line_to(12, 9)
        cr.line_to(4, 9)
        cr.line_to(6.5, 6.5)
        cr.close_path()
        cr.stroke()
        L((8, 9), (8, 14))
    elif name == "pin-fill":
        cr.set_line_width(1.0)
        cr.translate(8, 8)
        cr.rotate(pi / 4)
        cr.translate(-8, -8)
        cr.move_to(6, 2)
        cr.line_to(10, 2)
        cr.line_to(9.5, 6.5)
        cr.line_to(12, 9)
        cr.line_to(4, 9)
        cr.line_to(6.5, 6.5)
        cr.close_path()
        cr.stroke()
        L((8, 9), (8, 14))
    elif name == "folder":
        cr.move_to(1.5, 4)
        cr.line_to(6, 4)
        cr.line_to(7.5, 5.5)
        cr.line_to(14.5, 5.5)
        cr.line_to(14.5, 13)
        cr.line_to(1.5, 13)
        cr.close_path()
        cr.stroke()
    elif name == "file":
        cr.move_to(3.5, 1.5)
        cr.line_to(9.5, 1.5)
        cr.line_to(12.5, 4.5)
        cr.line_to(12.5, 14.5)
        cr.line_to(3.5, 14.5)
        cr.close_path()
        cr.stroke()
        L((9.5, 1.5), (9.5, 4.5), (12.5, 4.5))
    elif name == "zip":
        _rr(cr, 2.5, 1.5, 11, 13, 1.5)
        cr.stroke()
        for y in (3, 5, 7):
            L((7, y), (9, y))
        _rr(cr, 6.5, 9, 3, 3.5, 0.6)
        cr.stroke()
    elif name == "extract":
        _rr(cr, 2.5, 6.5, 11, 8, 1.5)
        cr.stroke()
        L((8, 1.5), (8, 10))
        L((5.5, 7.5), (8, 10), (10.5, 7.5))
    elif name == "restoreitem":
        cr.arc(8.5, 8.5, 5, -pi * 0.9, pi * 0.6)
        cr.stroke()
        L((2, 3.5), (3.6, 6.6), (6.6, 5.4))
    elif name == "open":
        _rr(cr, 1.5, 1.5, 13, 13, 2)
        cr.stroke()
        L((7, 9), (12.5, 3.5))
        L((8.5, 3.5), (12.5, 3.5), (12.5, 7.5))
    elif name == "newtab":
        _rr(cr, 1.5, 3.5, 13, 10, 1.5)
        cr.stroke()
        L((1.5, 6), (8, 6))
        L((8, 3.5), (8, 6))
    elif name == "check":
        L((3, 8.5), (6.5, 12), (13, 4.5))
    elif name == "eject":
        cr.move_to(8, 3)
        cr.line_to(13, 9)
        cr.line_to(3, 9)
        cr.close_path()
        cr.stroke()
        L((3, 12.5), (13, 12.5))
    elif name == "details-view":
        for y in (3.5, 8, 12.5):
            _rr(cr, 1.5, y - 1.2, 2.4, 2.4, 0.5)
            cr.stroke()
            L((6, y), (14.5, y))
    elif name == "icons-view":
        for x in (2, 9):
            for y in (2, 9):
                _rr(cr, x, y, 5, 5, 1.2)
                cr.stroke()
    elif name == "selectall":
        _rr(cr, 2, 2, 12, 12, 1.5)
        cr.stroke()
        L((5, 8), (7.2, 10.2), (11, 6))
    elif name == "info":
        cr.arc(8, 8, 6, 0, 2 * pi)
        cr.stroke()
        L((8, 7), (8, 11.5))
        cr.arc(8, 4.8, 0.9, 0, 2 * pi)
        cr.fill()
    elif name == "share":
        cr.arc(4, 8, 1.8, 0, 2 * pi)
        cr.stroke()
        cr.arc(12, 3.8, 1.8, 0, 2 * pi)
        cr.stroke()
        cr.arc(12, 12.2, 1.8, 0, 2 * pi)
        cr.stroke()
        L((5.6, 7.1), (10.4, 4.7))
        L((5.6, 8.9), (10.4, 11.3))
    elif name == "network":
        _rr(cr, 5, 1.5, 6, 4.5, 1)
        cr.stroke()
        L((8, 6), (8, 9))
        L((3, 9), (13, 9))
        L((3, 9), (3, 11))
        L((13, 9), (13, 11))
        _rr(cr, 1, 11, 4, 3.5, 0.8)
        cr.stroke()
        _rr(cr, 11, 11, 4, 3.5, 0.8)
        cr.stroke()
    elif name == "link":
        cr.arc(5.5, 10.5, 3, pi * 0.25, pi * 1.75)
        cr.stroke()
        cr.arc(10.5, 5.5, 3, pi * 1.25, pi * 0.75)
        cr.stroke()
        L((6.5, 9.5), (9.5, 6.5))
    else:
        draw_glyph_extra(cr, name, L, pi)
    cr.restore()




# ----------------------------------------------------------------------------
# Shared Windows 11 dark style
# ----------------------------------------------------------------------------
BASE_CSS = """
* { font-family: "Segoe UI Variable Text", "Segoe UI", "Selawik", "Open Sans", "Noto Sans", sans-serif; }
window.fx, window.fx-dialog { background-color: #202020; color: #ffffff; font-size: 12px; }
.fx label { color: #ffffff; }
headerbar.fx-title { background: #202020; border: none; box-shadow: none; min-height: 40px; padding: 0; margin: 0; }
headerbar.fx-title:backdrop { background: #202020; }
.app-title { font-size: 12px; color: #ffffff; margin-left: 4px; }
.app-title:backdrop { color: rgba(255,255,255,0.55); }
button.wc { background: transparent; border: none; border-radius: 0; min-width: 46px; min-height: 32px; padding: 0; box-shadow: none; }
button.wc:hover { background-color: rgba(255,255,255,0.06); }
button.wc.close:hover { background-color: #C42B1C; }
.tabstrip { margin-top: 6px; margin-left: 6px; }
button.tab { outline-color: transparent; background: transparent; border: none; border-radius: 8px 8px 0 0; min-height: 34px;
   padding: 0 6px 0 12px; box-shadow: none; margin-right: 1px; }
button.tab:hover { background-color: rgba(255,255,255,0.04); }
button.tab.active { background-color: #2C2C2C; }
button.tab label { font-size: 12px; }
button.tab-x { background: transparent; border: none; border-radius: 4px; min-width: 24px; min-height: 24px; padding: 0; box-shadow: none; }
button.tab-x:hover { background-color: rgba(255,255,255,0.08); }
button.tab-new { background: transparent; border: none; border-radius: 4px; min-width: 32px; min-height: 28px; padding: 0;
   box-shadow: none; margin-top: 4px; margin-left: 2px; }
button.tab-new:hover { background-color: rgba(255,255,255,0.06); }
.bar { background-color: #2C2C2C; padding: 4px 8px; }
.bar-bottom { border-bottom: 1px solid rgba(255,255,255,0.06); }
button.tb, button.nb { background: transparent; border: none; border-radius: 4px; min-height: 32px; padding: 0 9px; box-shadow: none; color: #ffffff; }
button.nb { min-width: 34px; padding: 0; }
button.tb:hover, button.nb:hover { background-color: rgba(255,255,255,0.06); }
button.tb:active, button.nb:active { background-color: rgba(255,255,255,0.04); }
button.tb:disabled label { color: rgba(255,255,255,0.36); }
button.tb label { font-size: 12px; }
button.tb.on, button.nb.on { background-color: rgba(255,255,255,0.09); }
.vsep { background-color: rgba(255,255,255,0.08); min-width: 1px; margin: 6px 6px; }
.status { background-color: #202020; padding: 4px 12px; border-top: 1px solid rgba(255,255,255,0.06); }
.status label { font-size: 12px; color: rgba(255,255,255,0.786); }
.sec { color: rgba(255,255,255,0.786); }
.ter { color: rgba(255,255,255,0.545); }
.big-title { font-size: 20px; font-weight: 600; }
.sect-title { font-size: 14px; font-weight: 600; }
entry.field, entry.fx-search { background-color: rgba(255,255,255,0.06); color: #ffffff; border: 1px solid rgba(255,255,255,0.07);
   border-bottom: 1px solid rgba(255,255,255,0.54); border-radius: 4px; min-height: 30px; padding: 0 10px; box-shadow: none;
   font-size: 12px; caret-color: #ffffff; }
entry.field:focus, entry.fx-search:focus { background-color: #1c1c1c; border-bottom: 2px solid #4CC2FF; }
entry selection, textview text selection, entry selection:focus, textview text selection:focus { background-color: #0078D4; color: #ffffff; }
scrollbar { background: transparent; border: none; }
scrollbar slider { background-color: rgba(255,255,255,0.45); border-radius: 6px; min-width: 3px; min-height: 3px; border: none; }
scrollbar:hover slider { min-width: 6px; min-height: 6px; background-color: rgba(255,255,255,0.55); }
scrollbar trough { background: transparent; border: none; }
scale trough { background-color: rgba(255,255,255,0.3); border: none; border-radius: 2px; min-height: 4px; min-width: 4px; }
scale highlight { background-color: #4CC2FF; border: none; border-radius: 2px; min-height: 4px; min-width: 4px; }
scale slider { background-color: #4CC2FF; border: 5px solid #454545; border-radius: 50%; min-width: 12px; min-height: 12px; box-shadow: none; }
scale slider:hover { border-width: 4px; }
menu, .menu, .context-menu { background-color: #2C2C2C; color: #ffffff; border: 1px solid rgba(0,0,0,0.45); border-radius: 8px; padding: 4px; }
menu menuitem { padding: 6px 12px; border-radius: 4px; color: #ffffff; min-height: 18px; }
menu menuitem:hover { background-color: rgba(255,255,255,0.06); }
menu menuitem:disabled label { color: rgba(255,255,255,0.36); }
menu menuitem label { color: #ffffff; font-size: 12px; }
menu menuitem arrow { color: rgba(255,255,255,0.786); }
menu separator { background-color: rgba(255,255,255,0.08); margin: 4px 0; min-height: 1px; }
window.fx button, window.fx-dialog button { background-image: none; text-shadow: none; -gtk-icon-shadow: none; }
button.primary { background-color: #4CC2FF; color: #000000; border: none; border-radius: 4px; min-height: 30px; padding: 0 16px; box-shadow: none; }
button.primary label { color: #000000; }
button.primary:hover { background-color: #48B1E8; }
button.secondary { background-color: rgba(255,255,255,0.06); color: #ffffff; border: 1px solid rgba(255,255,255,0.09); border-radius: 4px; min-height: 30px; padding: 0 16px; box-shadow: none; }
button.secondary:hover { background-color: rgba(255,255,255,0.09); }
.dlg-body { background-color: #2B2B2B; padding: 24px; }
.dlg-foot { background-color: #202020; padding: 22px 24px; border-top: 1px solid rgba(0,0,0,0.3); }
.dlg-title { font-size: 20px; font-weight: 600; }
.fx-dialog label { color: #ffffff; }
.fx-dialog label.sec { color: rgba(255,255,255,0.786); }
.fx-dialog label.ter { color: rgba(255,255,255,0.545); }
checkbutton check { background-color: rgba(0,0,0,0.1); border: 1px solid rgba(255,255,255,0.6); border-radius: 4px; min-width: 18px; min-height: 18px; -gtk-icon-source: none; color: #000000; }
checkbutton check:checked { background-color: #4CC2FF; border-color: #4CC2FF; -gtk-icon-source: -gtk-icontheme("object-select-symbolic"); }
checkbutton label { color: #ffffff; font-size: 12px; margin-left: 6px; }
radiobutton radio { background-color: rgba(0,0,0,0.1); border: 1px solid rgba(255,255,255,0.6); border-radius: 50%; min-width: 18px; min-height: 18px; -gtk-icon-source: none; }
radiobutton radio:checked { background-color: #000000; border: 5px solid #4CC2FF; }
radiobutton label { color: #ffffff; font-size: 12px; margin-left: 6px; }
switch { background-color: transparent; border: 1px solid rgba(255,255,255,0.6); border-radius: 12px; min-width: 40px; min-height: 18px; }
switch:checked { background-color: #4CC2FF; border-color: #4CC2FF; }
switch slider { background-color: rgba(255,255,255,0.8); border-radius: 50%; min-width: 12px; min-height: 12px; margin: 3px; border: none; box-shadow: none; }
switch:checked slider { background-color: #000000; }
switch image { color: transparent; }
combobox button, combobox box { background-color: rgba(255,255,255,0.06); color: #ffffff; border: 1px solid rgba(255,255,255,0.07); border-radius: 4px; box-shadow: none; min-height: 30px; }
combobox button cellview, combobox button label, combobox arrow { color: #ffffff; }
spinbutton { background-color: rgba(255,255,255,0.06); color: #ffffff; border: 1px solid rgba(255,255,255,0.07); border-radius: 4px; box-shadow: none; }
spinbutton entry { background: transparent; border: none; box-shadow: none; color: #ffffff; }
spinbutton button { background: transparent; border: none; box-shadow: none; color: #ffffff; }
tooltip, tooltip.background { background-color: #2C2C2C; border: 1px solid rgba(0,0,0,0.4); border-radius: 4px; }
tooltip label { color: #ffffff; font-size: 12px; }
.set-group { background-color: rgba(255,255,255,0.05); border-radius: 4px; border: 1px solid rgba(0,0,0,0.2); padding: 12px 16px; }
.set-head { font-size: 13px; }
.set-desc { font-size: 12px; color: rgba(255,255,255,0.6); }
"""


def apply_css(extra=""):
    prov = Gtk.CssProvider()
    prov.load_from_data((BASE_CSS + extra).encode())
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), prov,
                                             Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 10)
    Gtk.Settings.get_default().set_property("gtk-application-prefer-dark-theme", True)


def draw_glyph_extra(cr, name, L, pi):
    if name == "save":
        _rr(cr, 2, 2, 12, 12, 1.5)
        cr.stroke()
        _rr(cr, 4.5, 2, 6, 4, 0.5)
        cr.stroke()
        _rr(cr, 4.5, 9, 7, 5, 0.5)
        cr.stroke()
    elif name == "undo":
        cr.move_to(3, 7)
        cr.curve_to(6, 3.5, 13, 4.5, 13, 10)
        cr.stroke()
        L((3, 3), (3, 7), (7, 7))
    elif name == "redo":
        cr.move_to(13, 7)
        cr.curve_to(10, 3.5, 3, 4.5, 3, 10)
        cr.stroke()
        L((13, 3), (13, 7), (9, 7))
    elif name == "replace":
        L((2, 5), (10, 5))
        L((7.5, 2.5), (10, 5), (7.5, 7.5))
        L((14, 11), (6, 11))
        L((8.5, 8.5), (6, 11), (8.5, 13.5))
    elif name == "zoomin":
        cr.arc(6.6, 6.6, 4.6, 0, 2 * pi)
        cr.stroke()
        L((10, 10), (14, 14))
        L((4.6, 6.6), (8.6, 6.6))
        L((6.6, 4.6), (6.6, 8.6))
    elif name == "zoomout":
        cr.arc(6.6, 6.6, 4.6, 0, 2 * pi)
        cr.stroke()
        L((10, 10), (14, 14))
        L((4.6, 6.6), (8.6, 6.6))
    elif name == "fit":
        L((2, 5.5), (2, 2), (5.5, 2))
        L((10.5, 2), (14, 2), (14, 5.5))
        L((14, 10.5), (14, 14), (10.5, 14))
        L((5.5, 14), (2, 14), (2, 10.5))
    elif name == "wrap":
        L((2, 3), (14, 3))
        cr.move_to(2, 8)
        cr.line_to(11.5, 8)
        cr.curve_to(15, 8, 15, 13, 11.5, 13)
        cr.line_to(8, 13)
        cr.stroke()
        L((9.5, 11.3), (8, 13), (9.5, 14.7))
        L((2, 13), (5, 13))
    elif name == "play":
        cr.move_to(4.5, 2.5)
        cr.line_to(13, 8)
        cr.line_to(4.5, 13.5)
        cr.close_path()
        cr.fill()
    elif name == "pause":
        _rr(cr, 3.5, 2.5, 3, 11, 0.8)
        cr.fill()
        _rr(cr, 9.5, 2.5, 3, 11, 0.8)
        cr.fill()
    elif name in ("next", "prev"):
        if name == "prev":
            cr.translate(16, 0)
            cr.scale(-1, 1)
        cr.move_to(3, 3)
        cr.line_to(10.5, 8)
        cr.line_to(3, 13)
        cr.close_path()
        cr.fill()
        _rr(cr, 11, 3, 2, 10, 0.6)
        cr.fill()
    elif name == "shuffle":
        L((2, 4), (5, 4), (11, 12), (14, 12))
        L((2, 12), (5, 12), (11, 4), (14, 4))
        L((12, 2), (14, 4), (12, 6))
        L((12, 10), (14, 12), (12, 14))
    elif name in ("repeat", "repeat1"):
        cr.move_to(3, 9)
        cr.line_to(3, 6)
        cr.arc(5, 6, 2, pi, 1.5 * pi)
        cr.line_to(13, 4)
        cr.stroke()
        L((11, 2), (13, 4), (11, 6))
        cr.move_to(13, 7)
        cr.line_to(13, 10)
        cr.arc(11, 10, 2, 0, 0.5 * pi)
        cr.line_to(3, 12)
        cr.stroke()
        L((5, 10), (3, 12), (5, 14))
        if name == "repeat1":
            cr.set_font_size(5)
            cr.move_to(6.8, 9.8)
            cr.show_text("1")
    elif name in ("volume", "mute"):
        cr.move_to(1.5, 6)
        cr.line_to(4.5, 6)
        cr.line_to(8, 2.5)
        cr.line_to(8, 13.5)
        cr.line_to(4.5, 10)
        cr.line_to(1.5, 10)
        cr.close_path()
        cr.stroke()
        if name == "mute":
            L((10.5, 6), (14.5, 10))
            L((14.5, 6), (10.5, 10))
        else:
            cr.arc(8, 8, 3.5, -pi / 3.5, pi / 3.5)
            cr.stroke()
            cr.arc(8, 8, 6.2, -pi / 3.5, pi / 3.5)
            cr.stroke()
    elif name == "fullscreen":
        L((2, 6), (2, 2), (6, 2))
        L((10, 2), (14, 2), (14, 6))
        L((14, 10), (14, 14), (10, 14))
        L((6, 14), (2, 14), (2, 10))
        L((2, 2), (6, 6))
        L((14, 14), (10, 10))
    elif name == "unfullscreen":
        L((6, 2), (6, 6), (2, 6))
        L((10, 2), (10, 6), (14, 6))
        L((10, 14), (10, 10), (14, 10))
        L((6, 14), (6, 10), (2, 10))
    elif name == "rotate":
        cr.arc(8, 9, 5, pi * 1.15, pi * 2.85)
        cr.stroke()
        L((2.5, 2.5), (3.4, 6.4), (7.2, 5.4))
    elif name == "heart":
        cr.move_to(8, 13.5)
        cr.curve_to(1, 8, 1.5, 2.5, 5, 2.5)
        cr.curve_to(6.5, 2.5, 7.5, 3.5, 8, 4.5)
        cr.curve_to(8.5, 3.5, 9.5, 2.5, 11, 2.5)
        cr.curve_to(14.5, 2.5, 15, 8, 8, 13.5)
        cr.stroke()
    elif name == "pen":
        L((2.5, 13.5), (3.2, 10.5), (11, 2.7), (13.3, 5), (5.5, 12.8), (2.5, 13.5))
        L((9.5, 4.2), (11.8, 6.5))
    elif name == "highlighter":
        L((3, 13.5), (13, 13.5))
        cr.move_to(5, 11)
        cr.line_to(11, 3)
        cr.line_to(13.5, 5)
        cr.line_to(7.5, 12.5)
        cr.line_to(5, 12.5)
        cr.close_path()
        cr.stroke()
    elif name == "eraser":
        cr.move_to(2.5, 10)
        cr.line_to(9, 3.5)
        cr.line_to(13.5, 8)
        cr.line_to(8, 13.5)
        cr.line_to(5.5, 13.5)
        cr.close_path()
        cr.stroke()
        L((6, 6.5), (10.5, 11))
        L((8, 13.5), (14, 13.5))
    elif name == "crop":
        L((4.5, 1.5), (4.5, 11.5), (14.5, 11.5))
        L((1.5, 4.5), (11.5, 4.5), (11.5, 14.5))
    elif name == "camera":
        _rr(cr, 1.5, 4, 13, 9.5, 1.6)
        cr.stroke()
        L((5, 4), (6, 2.5), (10, 2.5), (11, 4))
        cr.arc(8, 8.8, 2.6, 0, 2 * pi)
        cr.stroke()
    elif name == "timer":
        cr.arc(8, 9, 5.5, 0, 2 * pi)
        cr.stroke()
        L((8, 9), (8, 5.8))
        L((6.3, 1.8), (9.7, 1.8))
    elif name == "settings":
        n = 8
        cr.new_path()
        for i in range(n * 2):
            a = i * pi / n
            r = 6.6 if i % 2 == 0 else 5.0
            a1, a2 = a - pi / (n * 2.4), a + pi / (n * 2.4)
            cr.line_to(8 + r * math.cos(a1), 8 + r * math.sin(a1))
            cr.line_to(8 + r * math.cos(a2), 8 + r * math.sin(a2))
        cr.close_path()
        cr.stroke()
        cr.arc(8, 8, 2.2, 0, 2 * pi)
        cr.stroke()
    elif name == "history":
        cr.arc(8, 8, 6, pi * 1.05, pi * 2.85)
        cr.stroke()
        L((1.2, 6.2), (2.3, 8.6), (4.6, 7.3))
        L((8, 4.6), (8, 8.2), (10.5, 9.7))
    elif name == "image":
        _rr(cr, 1.5, 2.5, 13, 11, 1.5)
        cr.stroke()
        L((1.5, 11), (5.5, 7), (9, 10.5), (11, 8.5), (14.5, 12))
        cr.arc(10.5, 5.5, 1.2, 0, 2 * pi)
        cr.stroke()
    elif name == "music":
        cr.arc(4.5, 12, 2, 0, 2 * pi)
        cr.stroke()
        cr.arc(12, 10.5, 2, 0, 2 * pi)
        cr.stroke()
        L((6.5, 12), (6.5, 3.5), (14, 2), (14, 10.5))
    elif name == "video":
        _rr(cr, 1.5, 3.5, 9.5, 9, 1.5)
        cr.stroke()
        L((11, 6.5), (14.5, 4.5), (14.5, 11.5), (11, 9.5))
    elif name == "queue":
        for y in (3, 7):
            L((2, y), (14, y))
        L((2, 11), (8, 11))
        cr.move_to(10.5, 9)
        cr.line_to(14, 11.5)
        cr.line_to(10.5, 14)
        cr.close_path()
        cr.fill()
    elif name == "edit":
        L((2.5, 13.5), (3.2, 10.5), (11, 2.7), (13.3, 5), (5.5, 12.8), (2.5, 13.5))
    elif name == "slideshow":
        _rr(cr, 1.5, 2.5, 13, 9, 1.5)
        cr.stroke()
        cr.move_to(6.5, 5)
        cr.line_to(10, 7)
        cr.line_to(6.5, 9)
        cr.close_path()
        cr.fill()
        L((5, 14), (11, 14))
    elif name == "print":
        _rr(cr, 1.5, 6, 13, 6, 1.2)
        cr.stroke()
        L((4.5, 6), (4.5, 1.5), (11.5, 1.5), (11.5, 6))
        _rr(cr, 4.5, 9.5, 7, 5, 0.5)
        cr.stroke()
    elif name == "wallpaper":
        _rr(cr, 1.5, 2.5, 13, 9, 1.2)
        cr.stroke()
        L((1.5, 9.5), (5, 6), (8, 9), (10, 7), (14.5, 10.5))
        L((5.5, 14), (10.5, 14))
        L((8, 11.5), (8, 14))
    elif name == "list":
        for y in (3.5, 8, 12.5):
            cr.arc(2.5, y, 0.9, 0, 2 * pi)
            cr.fill()
            L((5.5, y), (14, y))
    elif name == "add":
        L((8, 2.5), (8, 13.5))
        L((2.5, 8), (13.5, 8))
    elif name == "split":
        _rr(cr, 1.5, 2.5, 13, 11, 1.5)
        cr.stroke()
        L((8, 2.5), (8, 13.5))
    elif name == "keyboard":
        _rr(cr, 1, 3.5, 14, 9, 1.5)
        cr.stroke()
        for x in (4, 6.7, 9.3, 12):
            cr.rectangle(x - 0.5, 6, 1, 1)
        cr.fill()
        L((4.5, 10), (11.5, 10))


class Icon(Gtk.DrawingArea):
    """Monochrome glyph icon."""

    def __init__(self, name, size=16, color=None):
        super().__init__()
        self.name = name
        self.size = size
        self.color = color
        self.set_size_request(size, size)
        self.set_valign(Gtk.Align.CENTER)
        self.connect("draw", self._draw)

    def set_icon(self, name):
        self.name = name
        self.queue_draw()

    def _draw(self, w, cr):
        col = self.color or (1, 1, 1, 1)
        p = self.get_parent()
        if not self.is_sensitive() or (p and not p.is_sensitive()):
            col = (1, 1, 1, 0.36)
        draw_glyph(cr, self.name, self.size, col)


class WinTitlebar(Gtk.HeaderBar):
    """Title bar with Windows 11 caption buttons. Pack your own widgets with pack_start()."""

    def __init__(self, window):
        super().__init__()
        self.win = window
        self.get_style_context().add_class("fx-title")
        self.set_show_close_button(False)
        self.set_custom_title(Gtk.Box())
        wc = Gtk.Box(spacing=0)
        wc.set_valign(Gtk.Align.START)
        for name, cb, extra in (("min", lambda *_: window.iconify(), ""),
                                ("max", lambda *_: self.toggle_max(), ""),
                                ("close", lambda *_: window.close(), "close")):
            b = Gtk.Button()
            b.get_style_context().add_class("wc")
            if extra:
                b.get_style_context().add_class(extra)
            ic = Icon(name, 10)
            b.add(ic)
            b.connect("clicked", cb)
            if name == "max":
                self.max_icon = ic
            wc.pack_start(b, False, False, 0)
        self.pack_end(wc)
        window.connect("window-state-event", self._wstate)
        window.set_titlebar(self)

    def toggle_max(self):
        if self.win.is_maximized():
            self.win.unmaximize()
        else:
            self.win.maximize()

    def _wstate(self, w, ev):
        maxed = bool(ev.new_window_state & Gdk.WindowState.MAXIMIZED)
        self.max_icon.set_icon("restore" if maxed else "max")
        return False


def app_title(text, logo_draw):
    """Little logo + app name for the left of the title bar."""
    box = Gtk.Box(spacing=8)
    box.set_margin_start(14)
    da = Gtk.DrawingArea()
    da.set_size_request(16, 16)
    da.set_valign(Gtk.Align.CENTER)
    da.connect("draw", lambda w, cr: logo_draw(cr, 16))
    box.pack_start(da, False, False, 0)
    lb = Gtk.Label(label=text)
    lb.get_style_context().add_class("app-title")
    box.pack_start(lb, False, False, 0)
    return box, lb


class JsonSettings(dict):
    def __init__(self, app_dir, defaults):
        super().__init__(defaults)
        self.dir = os.path.join(HOME, ".config", app_dir)
        self.file = os.path.join(self.dir, "settings.json")
        try:
            with open(self.file) as f:
                self.update(json.load(f))
        except (OSError, ValueError):
            pass

    def save(self):
        try:
            os.makedirs(self.dir, exist_ok=True)
            tmp = self.file + ".tmp"
            with open(tmp, "w") as f:
                json.dump(self, f, indent=1)
            os.replace(tmp, self.file)
        except OSError:
            pass


def vsep():
    s = Gtk.Box()
    s.get_style_context().add_class("vsep")
    return s


def logo_pixbuf(draw, size):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    draw(cairo.Context(surf), size)
    return Gdk.pixbuf_get_from_surface(surf, 0, 0, size, size)
def label(text="", cls=None, xalign=0.0, ellipsize=False, wrap=False, markup=False):
    lb = Gtk.Label()
    if markup:
        lb.set_markup(text)
    else:
        lb.set_text(text)
    lb.set_xalign(xalign)
    if cls:
        for c in cls.split():
            lb.get_style_context().add_class(c)
    if ellipsize:
        lb.set_ellipsize(Pango.EllipsizeMode.END)
    if wrap:
        lb.set_line_wrap(True)
        lb.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
    return lb


def add_cls(w, *cls):
    ctx = w.get_style_context()
    for c in cls:
        ctx.add_class(c)
    return w


def tb_button(icon, text, cb=None, chev=False, tip=None):
    b = Gtk.Button()
    add_cls(b, "tb")
    box = Gtk.Box(spacing=7)
    if icon:
        box.pack_start(Icon(icon), False, False, 0)
    if text:
        box.pack_start(Gtk.Label(label=text), False, False, 0)
    if chev:
        box.pack_start(Icon("chevdown", 10), False, False, 0)
    b.add(box)
    b.set_relief(Gtk.ReliefStyle.NONE)
    b.set_tooltip_text(tip or text or None)
    if cb:
        b.connect("clicked", lambda w: cb(w))
    return b


def icon_button(icon, cb, cls="nb", tip=None, size=16):
    b = Gtk.Button()
    add_cls(b, cls)
    b.add(Icon(icon, size))
    b.set_relief(Gtk.ReliefStyle.NONE)
    if tip:
        b.set_tooltip_text(tip)
    b.connect("clicked", lambda w: cb(w))
    return b


def build_menu(spec):
    """spec: list of None (separator) or dicts: label, cb, icon, place, accel, sensitive, checked, sub."""
    menu = Gtk.Menu()
    add_cls(menu, "context-menu")
    for it in spec:
        if it is None:
            menu.append(Gtk.SeparatorMenuItem())
            continue
        mi = Gtk.MenuItem()
        box = Gtk.Box(spacing=12)
        ic = None
        if it.get("checked"):
            ic = Icon("check", 16)
        elif it.get("pixbuf") is not None:
            ic = Gtk.Image.new_from_pixbuf(it["pixbuf"])
        elif it.get("icon"):
            ic = Icon(it["icon"], 16)
        if ic is None:
            ic = Gtk.Box()
            ic.set_size_request(16, 16)
        box.pack_start(ic, False, False, 0)
        lb = Gtk.Label(label=it["label"])
        lb.set_xalign(0)
        box.pack_start(lb, True, True, 0)
        if it.get("accel"):
            al = Gtk.Label(label=it["accel"])
            al.get_style_context().add_class("dim-label")
            al.set_opacity(0.55)
            al.set_margin_start(24)
            box.pack_end(al, False, False, 0)
        mi.add(box)
        mi.set_sensitive(it.get("sensitive", True))
        if it.get("sub") is not None:
            mi.set_submenu(build_menu(it["sub"]))
        elif it.get("cb"):
            cb = it["cb"]
            mi.connect("activate", lambda w, cb=cb: GLib.idle_add(cb))
        menu.append(mi)
    menu.show_all()
    return menu


def popup_menu(menu, widget, event=None):
    menu.attach_to_widget(widget, None)
    if event is not None:
        menu.popup_at_pointer(event)
    else:
        menu.popup_at_widget(widget, Gdk.Gravity.SOUTH_WEST, Gdk.Gravity.NORTH_WEST, None)


# ----------------------------------------------------------------------------
# Windows 11 style dialogs
# ----------------------------------------------------------------------------
class WinDialog(Gtk.Window):
    def __init__(self, parent, title, body=None, primary="OK", secondary="Cancel", width=440, extra=None,
                 markup=False):
        super().__init__(transient_for=parent, modal=True)
        add_cls(self, "fx-dialog")
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_default_size(width, -1)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.set_title(title)
        self.cb = None
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        add_cls(self.body, "dlg-body")
        self.body.pack_start(label(title, "dlg-title"), False, False, 0)
        if body:
            lb = label(body, wrap=True, markup=markup)
            lb.set_max_width_chars(60)
            self.body.pack_start(lb, False, False, 0)
        if extra:
            self.body.pack_start(extra, False, False, 0)
        outer.pack_start(self.body, True, True, 0)
        self.foot = Gtk.Box(spacing=8, homogeneous=True)
        add_cls(self.foot, "dlg-foot")
        self.primary_btn = None
        if primary:
            pb = Gtk.Button(label=primary)
            add_cls(pb, "primary")
            pb.connect("clicked", lambda *_: self.done(True))
            self.foot.pack_start(pb, True, True, 0)
            pb.set_can_default(True)
            self.set_default(pb)
            self.primary_btn = pb
        if secondary:
            sb = Gtk.Button(label=secondary)
            add_cls(sb, "secondary")
            sb.connect("clicked", lambda *_: self.done(False))
            self.foot.pack_start(sb, True, True, 0)
        if primary or secondary:
            outer.pack_start(self.foot, False, False, 0)
        self.add(outer)
        self.connect("key-press-event", self._key)

    def _key(self, w, ev):
        if ev.keyval == Gdk.KEY_Escape:
            self.done(False)
            return True
        return False

    def done(self, ok):
        cb = self.cb
        self.cb = None
        self.hide()
        if cb:
            cb(ok)
        self.destroy()

    def ask(self, cb=None):
        self.cb = cb
        self.show_all()
        if self.primary_btn:
            self.primary_btn.grab_focus()


def info_dialog(parent, title, body):
    WinDialog(parent, title, body, primary="OK", secondary=None).ask()


def confirm(parent, title, body, yes, cb, no="Cancel"):
    WinDialog(parent, title, body, primary=yes, secondary=no).ask(cb)


def error_list_dialog(parent, title, errors):
    lines = []
    for p, msg in errors[:12]:
        lines.append(f"{os.path.basename(p) or p}: {msg}" if p else msg)
    if len(errors) > 12:
        lines.append(f"...and {len(errors) - 12} more")
    info_dialog(parent, title, "\n".join(lines))




# ----------------------------------------------------------------------------
# Notepad
# ----------------------------------------------------------------------------
gi.require_version("GtkSource", "4")
from gi.repository import GtkSource  # noqa: E402

APP_ID = "io.github.pinotepad"
DATA_DIR = os.path.join(GLib.get_user_data_dir(), "pi-notepad")
SESSION_DIR = os.path.join(DATA_DIR, "session")
DEFAULTS = {"width": 960, "height": 640, "maximized": False, "font": "Monospace 11", "wrap": True,
            "statusbar": True, "zoom": 100, "restore": True, "recent": [], "match_case": False,
            "wrap_around": True}

CSS = """
.menubar { background-color: #2C2C2C; padding: 2px 6px; }
button.mb { background: transparent; border: none; border-radius: 4px; min-height: 30px; padding: 0 10px; box-shadow: none; }
button.mb:hover { background-color: rgba(255,255,255,0.06); }
button.mb label { font-size: 12px; }
textview.np, textview.np text { background-color: #272727; color: #ffffff; }
textview.np { padding: 6px 4px; }
.findbar { background-color: #2C2C2C; border: 1px solid rgba(0,0,0,0.35); border-radius: 0 0 8px 8px; padding: 8px; }
.findbar entry { min-width: 220px; }
button.dot { background: transparent; border: none; border-radius: 4px; min-width: 24px; min-height: 24px; padding: 0; box-shadow: none; }
.settings-page { background-color: #272727; }
.settings-page .big-title { font-size: 28px; }
"""


def draw_logo(cr, s):
    cr.save()
    cr.scale(s / 16.0, s / 16.0)
    g = cairo.LinearGradient(0, 0, 0, 16)
    g.add_color_stop_rgb(0, 0.33, 0.73, 0.98)
    g.add_color_stop_rgb(1, 0.13, 0.45, 0.86)
    _rr(cr, 2, 1, 12, 14, 2)
    cr.set_source(g)
    cr.fill()
    cr.set_source_rgba(1, 1, 1, 0.92)
    cr.set_line_width(1.1)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    for y in (5, 8, 11):
        cr.move_to(5, y)
        cr.line_to(11 if y < 11 else 9, y)
        cr.stroke()
    cr.restore()


SCHEME_XML = """<?xml version="1.0" encoding="UTF-8"?>
<style-scheme id="pi-notepad-dark" name="Notepad Dark" version="1.0">
  <style name="text" foreground="#FFFFFF" background="#272727"/>
  <style name="selection" foreground="#FFFFFF" background="#0078D4"/>
  <style name="selection-unfocused" foreground="#FFFFFF" background="#3A3A3A"/>
  <style name="cursor" foreground="#FFFFFF"/>
  <style name="current-line" background="#272727"/>
  <style name="search-match" foreground="#000000" background="#4CC2FF"/>
  <style name="bracket-match" background="#3A3A3A"/>
</style-scheme>
"""


def install_scheme():
    d = os.path.join(DATA_DIR, "styles")
    try:
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, "pi-notepad-dark.xml")
        if not os.path.exists(p) or open(p).read() != SCHEME_XML:
            with open(p, "w") as f:
                f.write(SCHEME_XML)
    except OSError:
        return None
    mgr = GtkSource.StyleSchemeManager.get_default()
    mgr.append_search_path(d)
    mgr.force_rescan()
    return mgr.get_scheme("pi-notepad-dark")


def read_text(path):
    with open(path, "rb") as f:
        raw = f.read()
    enc = "UTF-8"
    if raw.startswith(b"\xef\xbb\xbf"):
        text = raw[3:].decode("utf-8", errors="replace")
        enc = "UTF-8 with BOM"
    else:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("latin-1")
            enc = "ANSI"
    eol = "CRLF" if "\r\n" in text else "LF"
    text = text.replace("\r\n", "\n")
    return text, enc, eol


class Doc(Gtk.Box):
    """One tab: a text buffer tied (or not) to a file."""
    counter = 0

    def __init__(self, win, path=None, text="", sid=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.win = win
        self.path = path
        self.enc = "UTF-8"
        self.eol = "CRLF" if False else "LF"
        Doc.counter += 1
        self.sid = sid or f"{int(time.time() * 1000)}-{Doc.counter}"
        self.buf = GtkSource.Buffer()
        self.buf.set_highlight_syntax(False)
        self.buf.set_highlight_matching_brackets(False)
        if win.app.scheme:
            self.buf.set_style_scheme(win.app.scheme)
        self.view = GtkSource.View(buffer=self.buf)
        self.view.get_style_context().add_class("np")
        self.view.set_left_margin(10)
        self.view.set_right_margin(10)
        self.view.set_top_margin(6)
        self.view.set_pixels_above_lines(1)
        sw = Gtk.ScrolledWindow()
        sw.add(self.view)
        self.sw = sw
        self.pack_start(sw, True, True, 0)
        if path:
            self.load(path)
        else:
            self.buf.begin_not_undoable_action()
            self.buf.set_text(text)
            self.buf.end_not_undoable_action()
        self.saved_text = self.get_text() if path else ""
        self.buf.connect("changed", self._changed)
        self.buf.connect("mark-set", lambda *a: self.win.update_status())
        self.view.connect("scroll-event", self._scroll)
        self.search = GtkSource.SearchContext.new(self.buf, None)
        self.search.set_highlight(True)
        self.show_all()

    def load(self, path):
        text, enc, eol = read_text(path)
        self.enc, self.eol = enc, eol
        self.buf.begin_not_undoable_action()
        self.buf.set_text(text)
        self.buf.end_not_undoable_action()
        self.buf.place_cursor(self.buf.get_start_iter())
        self.path = path
        self.saved_text = text

    def get_text(self):
        return self.buf.get_text(self.buf.get_start_iter(), self.buf.get_end_iter(), True)

    def modified(self):
        return self.get_text() != self.saved_text

    def title(self):
        if self.path:
            return os.path.basename(self.path)
        first = self.get_text().strip().split("\n", 1)[0][:30].strip()
        return first or "Untitled"

    def _changed(self, *a):
        self.win.doc_changed(self)

    def _scroll(self, w, ev):
        if ev.state & Gdk.ModifierType.CONTROL_MASK:
            dy = ev.delta_y if ev.direction == Gdk.ScrollDirection.SMOOTH else (
                -1 if ev.direction == Gdk.ScrollDirection.UP else 1)
            if dy:
                self.win.zoom(10 if dy < 0 else -10)
            return True
        return False

    def save(self, path=None):
        path = path or self.path
        text = self.get_text()
        out = text.replace("\n", "\r\n") if self.eol == "CRLF" else text
        data = out.encode("latin-1", errors="replace") if self.enc == "ANSI" else out.encode("utf-8")
        if self.enc == "UTF-8 with BOM":
            data = b"\xef\xbb\xbf" + data
        tmp = path + ".pinotepad-tmp"
        with open(tmp, "wb") as f:
            f.write(data)
        try:
            os.chmod(tmp, os.stat(path).st_mode & 0o7777)
        except OSError:
            pass
        os.replace(tmp, path)
        self.path = path
        self.saved_text = text
        try:
            Gtk.RecentManager.get_default().add_item(Gio.File.new_for_path(path).get_uri())
        except Exception:
            pass


class TabButton(Gtk.Button):
    def __init__(self, win, doc):
        super().__init__()
        self.win = win
        self.doc = doc
        self.get_style_context().add_class("tab")
        self.set_relief(Gtk.ReliefStyle.NONE)
        box = Gtk.Box(spacing=8)
        self.lbl = label("", ellipsize=True)
        self.lbl.set_width_chars(14)
        self.lbl.set_max_width_chars(22)
        box.pack_start(self.lbl, True, True, 0)
        self.x = Gtk.Button()
        self.x.get_style_context().add_class("tab-x")
        self.xi = Icon("close", 10)
        self.x.add(self.xi)
        self.x.set_relief(Gtk.ReliefStyle.NONE)
        self.x.connect("clicked", lambda *_: win.close_doc(doc))
        self.x.connect("enter-notify-event", lambda *a: self.xi.set_icon("close") or False)
        self.x.connect("leave-notify-event", lambda *a: self.update() or False)
        box.pack_start(self.x, False, False, 0)
        self.add(box)
        self.connect("clicked", lambda *_: win.switch(doc))
        self.connect("button-press-event", self._press)

    def _press(self, w, ev):
        if ev.button == 2:
            self.win.close_doc(self.doc)
            return True
        if ev.button == 3:
            m = build_menu([
                {"label": "New tab", "icon": "plus", "accel": "Ctrl+N", "cb": lambda: self.win.new_doc()},
                None,
                {"label": "Close tab", "icon": "close", "accel": "Ctrl+W", "cb": lambda: self.win.close_doc(self.doc)},
                {"label": "Close other tabs", "sensitive": len(self.win.docs) > 1,
                 "cb": lambda: self.win.close_others(self.doc)},
            ])
            self.win._menu = m
            popup_menu(m, self, ev)
            return True
        return False

    def update(self):
        self.lbl.set_text(self.doc.title())
        self.set_tooltip_text(self.doc.path or "Untitled")
        self.xi.set_icon("dot" if self.doc.modified() else "close")

    def set_active(self, on):
        ctx = self.get_style_context()
        (ctx.add_class if on else ctx.remove_class)("active")


_orig_extra = draw_glyph_extra


def draw_glyph_extra(cr, name, L, pi):  # noqa: F811
    if name == "dot":
        cr.arc(8, 8, 3.2, 0, 2 * pi)
        cr.fill()
    elif name == "chevup":
        L((4, 10), (8, 6), (12, 10))
    elif name == "down":
        L((8, 2.5), (8, 13.5))
        L((3.5, 9), (8, 13.5), (12.5, 9))
    else:
        _orig_extra(cr, name, L, pi)


class NotepadWindow(Gtk.ApplicationWindow):
    def __init__(self, app, paths=None, fresh=False):
        super().__init__(application=app)
        self.app = app
        st = app.settings
        self.st = st
        self.docs = []
        self.tabs = {}
        self.cur = None
        self._menu = None
        self._session_to = None
        self.set_icon_name("pi-notepad")
        self.get_style_context().add_class("fx")
        self.set_default_size(st["width"], st["height"])
        if st.get("maximized"):
            self.maximize()
        self.connect("delete-event", self._on_close)
        self.connect("key-press-event", self._key)
        self.connect("configure-event", self._configure)

        tb = WinTitlebar(self)
        strip = Gtk.Box()
        strip.get_style_context().add_class("tabstrip")
        strip.set_valign(Gtk.Align.END)
        self.tabbox = Gtk.Box()
        strip.pack_start(self.tabbox, False, False, 0)
        nt = icon_button("plus", lambda w: self.new_doc(), cls="tab-new", tip="Add New Tab (Ctrl+N)", size=14)
        nt.set_valign(Gtk.Align.CENTER)
        strip.pack_start(nt, False, False, 0)
        tb.pack_start(strip)
        tb.show_all()

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        mb = Gtk.Box(spacing=2)
        mb.get_style_context().add_class("menubar")
        for name, fn in (("File", self._file_menu), ("Edit", self._edit_menu), ("View", self._view_menu)):
            b = Gtk.Button(label=name)
            b.get_style_context().add_class("mb")
            b.connect("clicked", fn)
            mb.pack_start(b, False, False, 0)
        gear = icon_button("settings", lambda w: self.show_settings(), tip="Settings")
        mb.pack_end(gear, False, False, 0)
        root.pack_start(mb, False, False, 0)

        ov = Gtk.Overlay()
        self.stack = Gtk.Stack()
        ov.add(self.stack)
        self.findbar = self._build_findbar()
        ov.add_overlay(self.findbar)
        root.pack_start(ov, True, True, 0)

        sb = Gtk.Box(spacing=0)
        sb.get_style_context().add_class("status")
        self.l_pos = label("Ln 1, Col 1")
        self.l_chars = label("0 characters")
        self.l_zoom = label("100%")
        self.l_eol = label("Unix (LF)")
        self.l_enc = label("UTF-8")
        sb.pack_start(self.l_pos, False, False, 0)
        sb.pack_start(vsep(), False, False, 0)
        sb.pack_start(self.l_chars, False, False, 0)
        for w in (self.l_enc, self.l_eol, self.l_zoom):
            sb.pack_end(w, False, False, 0)
            sb.pack_end(vsep(), False, False, 0)
        self.statusbar = sb
        root.pack_start(sb, False, False, 0)
        self.add(root)
        root.show_all()
        self.findbar.hide()
        self.statusbar.set_visible(st["statusbar"])
        self.settings_page = None

        self.targets = [Gtk.TargetEntry.new("text/uri-list", 0, 0)]
        self.drag_dest_set(Gtk.DestDefaults.ALL, self.targets, Gdk.DragAction.COPY)
        self.connect("drag-data-received", self._drop)

        restored = False
        if not fresh and st.get("restore", True) and not app.restored:
            restored = self.restore_session()
            app.restored = True
        for p in paths or []:
            self.open_path(p)
        if not self.docs:
            self.new_doc()
        if not paths and restored and self.cur is None:
            self.switch(self.docs[0])
        self.apply_prefs()

    # ---------------- tabs
    def new_doc(self, path=None, text="", sid=None, switch=True):
        d = Doc(self, path, text, sid)
        self.docs.append(d)
        self.stack.add(d)
        tb = TabButton(self, d)
        self.tabs[d] = tb
        self.tabbox.pack_start(tb, False, False, 0)
        tb.show_all()
        tb.update()
        self.apply_prefs(d)
        if switch:
            self.switch(d)
        return d

    def switch(self, d):
        if self.settings_page and self.stack.get_visible_child() is self.settings_page:
            self.settings_page.hide()
        self.cur = d
        self.stack.set_visible_child(d)
        for dd, tb in self.tabs.items():
            tb.set_active(dd is d)
        self.set_title(f"{d.title()} - Notepad")
        d.view.grab_focus()
        self.update_status()
        if self.findbar.get_visible():
            self._find_changed()

    def close_doc(self, d, then=None):
        def really():
            self.docs.remove(d)
            self.tabs.pop(d).destroy()
            d.destroy()
            self._remove_session_file(d)
            if not self.docs:
                self.new_doc()
            elif self.cur is d:
                self.switch(self.docs[-1])
            self.save_session()
            if then:
                then()
        if d.modified() and (d.path or d.get_text().strip()):
            self.switch(d)
            self.ask_save(d, really)
        else:
            really()

    def close_others(self, keep):
        others = [d for d in self.docs if d is not keep]

        def step():
            if others:
                self.close_doc(others.pop(), step)
        step()

    def ask_save(self, d, after):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        dlg = WinDialog(self, "Notepad", f"Do you want to save changes to {d.path or d.title()}?",
                        primary="Save", secondary="Cancel", extra=box)
        dont = Gtk.Button(label="Don't save")
        dont.get_style_context().add_class("secondary")
        dlg.foot.pack_start(dont, True, True, 0)
        dlg.foot.reorder_child(dont, 1)

        def nosave(*a):
            dlg.cb = None
            dlg.destroy()
            after()
        dont.connect("clicked", nosave)

        def done(ok):
            if ok:
                self.save(d, after)
        dlg.ask(done)

    def doc_changed(self, d):
        tb = self.tabs.get(d)
        if tb:
            tb.update()
        if d is self.cur:
            self.set_title(f"{'*' if d.modified() else ''}{d.title()} - Notepad")
            self.update_status()
        if self._session_to:
            GLib.source_remove(self._session_to)
        self._session_to = GLib.timeout_add(1200, self._session_tick)

    def _session_tick(self):
        self._session_to = None
        self.save_session()
        return False

    # ---------------- files
    def open_path(self, path):
        path = os.path.abspath(path)
        for d in self.docs:
            if d.path == path:
                self.switch(d)
                return d
        if not os.path.exists(path):
            d = self.new_doc()
            d.path = path
            d.saved_text = ""
            self.tabs[d].update()
            return d
        try:
            # reuse an empty untitled tab
            if self.cur and not self.cur.path and not self.cur.get_text():
                d = self.cur
                d.load(path)
                self.tabs[d].update()
                self.switch(d)
            else:
                d = self.new_doc(path)
        except OSError as e:
            info_dialog(self, "Notepad", f"Couldn't open {path}: {e.strerror}")
            return None
        self._add_recent(path)
        return d

    def _add_recent(self, path):
        r = [p for p in self.st["recent"] if p != path]
        r.insert(0, path)
        self.st["recent"] = r[:10]
        try:
            Gtk.RecentManager.get_default().add_item(Gio.File.new_for_path(path).get_uri())
        except Exception:
            pass

    def open_dialog(self):
        dlg = Gtk.FileChooserDialog(title="Open", transient_for=self, action=Gtk.FileChooserAction.OPEN)
        dlg.add_buttons("Cancel", Gtk.ResponseType.CANCEL, "Open", Gtk.ResponseType.OK)
        dlg.set_select_multiple(True)
        if self.cur and self.cur.path:
            dlg.set_current_folder(os.path.dirname(self.cur.path))
        else:
            dlg.set_current_folder(HOME)
        for name, pats in (("Text documents (*.txt)", ["*.txt"]), ("All files", ["*"])):
            f = Gtk.FileFilter()
            f.set_name(name)
            for p in pats:
                f.add_pattern(p)
            dlg.add_filter(f)
        dlg.set_filter(dlg.list_filters()[1])
        if dlg.run() == Gtk.ResponseType.OK:
            for p in dlg.get_filenames():
                self.open_path(p)
        dlg.destroy()

    def save(self, d=None, after=None, save_as=False):
        d = d or self.cur
        if d.path and not save_as:
            try:
                d.save()
            except OSError as e:
                info_dialog(self, "Notepad", f"Couldn't save {d.path}: {e.strerror}")
                return
            self._saved(d)
            if after:
                after()
            return
        dlg = Gtk.FileChooserDialog(title="Save as", transient_for=self, action=Gtk.FileChooserAction.SAVE)
        dlg.add_buttons("Cancel", Gtk.ResponseType.CANCEL, "Save", Gtk.ResponseType.OK)
        dlg.set_do_overwrite_confirmation(True)
        if d.path:
            dlg.set_filename(d.path)
        else:
            dlg.set_current_folder(os.path.join(HOME, "Documents") if os.path.isdir(os.path.join(HOME, "Documents"))
                                   else HOME)
            name = re.sub(r"[/\\:*?\"<>|]", "", d.title())[:40].strip() or "Untitled"
            dlg.set_current_name(name + ".txt" if name != "Untitled" else "Untitled.txt")
        ok = dlg.run() == Gtk.ResponseType.OK
        path = dlg.get_filename()
        dlg.destroy()
        if not ok or not path:
            return
        try:
            d.save(path)
        except OSError as e:
            info_dialog(self, "Notepad", f"Couldn't save {path}: {e.strerror}")
            return
        self._add_recent(path)
        self._saved(d)
        if after:
            after()

    def _saved(self, d):
        self.tabs[d].update()
        self.doc_changed(d)

    def save_all(self):
        for d in list(self.docs):
            if d.modified() and d.path:
                self.save(d)

    def _drop(self, w, ctx, x, y, data, info, t):
        for u in data.get_uris() or []:
            p = Gio.File.new_for_uri(u).get_path()
            if p and os.path.isfile(p):
                self.open_path(p)

    # ---------------- session (restore tabs like Windows 11 Notepad)
    def _remove_session_file(self, d):
        try:
            os.remove(os.path.join(SESSION_DIR, d.sid + ".txt"))
        except OSError:
            pass

    def save_session(self):
        if not self.st.get("restore", True) or self is not self.app.main_window():
            return
        try:
            os.makedirs(SESSION_DIR, exist_ok=True)
            tabs = []
            keep = set()
            for d in self.docs:
                ent = {"sid": d.sid, "path": d.path, "modified": d.modified(),
                       "cursor": d.buf.get_iter_at_mark(d.buf.get_insert()).get_offset()}
                if d.modified() or not d.path:
                    with open(os.path.join(SESSION_DIR, d.sid + ".txt"), "w") as f:
                        f.write(d.get_text())
                    keep.add(d.sid + ".txt")
                tabs.append(ent)
            with open(os.path.join(SESSION_DIR, "tabs.json"), "w") as f:
                json.dump({"tabs": tabs, "active": self.docs.index(self.cur) if self.cur in self.docs else 0}, f)
            for n in os.listdir(SESSION_DIR):
                if n.endswith(".txt") and n not in keep:
                    os.remove(os.path.join(SESSION_DIR, n))
        except OSError:
            pass

    def restore_session(self):
        try:
            with open(os.path.join(SESSION_DIR, "tabs.json")) as f:
                data = json.load(f)
        except (OSError, ValueError):
            return False
        for t in data.get("tabs", []):
            sfile = os.path.join(SESSION_DIR, t["sid"] + ".txt")
            text = None
            if os.path.exists(sfile):
                with open(sfile) as f:
                    text = f.read()
            path = t.get("path")
            if path and os.path.exists(path):
                d = self.new_doc(path, sid=t["sid"], switch=False)
                if text is not None and t.get("modified"):
                    d.buf.set_text(text)
            elif text is not None and (text.strip() or path):
                d = self.new_doc(None, text, sid=t["sid"], switch=False)
                if path:
                    d.path = path
                    d.saved_text = ""
            else:
                continue
            try:
                d.buf.place_cursor(d.buf.get_iter_at_offset(int(t.get("cursor", 0))))
            except (TypeError, ValueError):
                pass
            self.tabs[d].update()
        if self.docs:
            i = min(data.get("active", 0), len(self.docs) - 1)
            self.switch(self.docs[i])
            return True
        return False

    # ---------------- prefs
    def apply_prefs(self, only=None):
        st = self.st
        fd = Pango.FontDescription.from_string(st["font"])
        if fd.get_size():
            size = fd.get_size() / Pango.SCALE
            fd.set_size(int(max(4, size * st["zoom"] / 100) * Pango.SCALE))
        css = (f"textview.np {{ font-family: \"{fd.get_family() or 'Monospace'}\"; "
               f"font-size: {fd.get_size() / Pango.SCALE:.1f}pt; "
               f"font-weight: {int(fd.get_weight())}; "
               f"font-style: {'italic' if fd.get_style() == Pango.Style.ITALIC else 'normal'}; }}")
        if not hasattr(self.app, "font_prov"):
            self.app.font_prov = Gtk.CssProvider()
            Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), self.app.font_prov,
                                                     Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 20)
        self.app.font_prov.load_from_data(css.encode())
        for d in ([only] if only else self.docs):
            d.view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR if st["wrap"] else Gtk.WrapMode.NONE)
        self.statusbar.set_visible(st["statusbar"])
        self.update_status()

    def zoom(self, delta=None, reset=False):
        z = 100 if reset else max(10, min(500, self.st["zoom"] + delta))
        self.st["zoom"] = z
        for w in self.app.get_windows():
            if isinstance(w, NotepadWindow):
                w.apply_prefs()

    def update_status(self):
        d = self.cur
        if not d or not self.statusbar.get_visible():
            return
        it = d.buf.get_iter_at_mark(d.buf.get_insert())
        line = it.get_line() + 1
        col = it.get_line_offset() + 1
        self.l_pos.set_text(f"Ln {line}, Col {col}")
        b = d.buf.get_selection_bounds()
        n = d.buf.get_char_count()
        if b:
            self.l_chars.set_text(f"{abs(b[1].get_offset() - b[0].get_offset()):,} of {n:,} characters")
        else:
            self.l_chars.set_text(f"{n:,} characters")
        self.l_zoom.set_text(f"{self.st['zoom']}%")
        self.l_eol.set_text("Windows (CRLF)" if d.eol == "CRLF" else "Unix (LF)")
        self.l_enc.set_text(d.enc)

    # ---------------- menus
    def _popup(self, w, spec):
        m = build_menu(spec)
        self._menu = m
        popup_menu(m, w)

    def _file_menu(self, w):
        recent = [{"label": p, "cb": (lambda p=p: self.open_path(p))} for p in self.st["recent"] if os.path.exists(p)]
        self._popup(w, [
            {"label": "New tab", "accel": "Ctrl+N", "cb": lambda: self.new_doc()},
            {"label": "New window", "accel": "Ctrl+Shift+N", "cb": lambda: self.app.new_window(fresh=True)},
            {"label": "Open", "icon": "open", "accel": "Ctrl+O", "cb": self.open_dialog},
            {"label": "Recent", "icon": "history", "sub": recent or [{"label": "No recent files", "sensitive": False}]},
            None,
            {"label": "Save", "icon": "save", "accel": "Ctrl+S", "cb": lambda: self.save()},
            {"label": "Save as", "accel": "Ctrl+Shift+S", "cb": lambda: self.save(save_as=True)},
            {"label": "Save all", "accel": "Ctrl+Alt+S", "cb": self.save_all},
            None,
            {"label": "Line endings", "sub": [
                {"label": "Unix (LF)", "checked": self.cur.eol == "LF", "cb": lambda: self._set_eol("LF")},
                {"label": "Windows (CRLF)", "checked": self.cur.eol == "CRLF", "cb": lambda: self._set_eol("CRLF")},
            ]},
            None,
            {"label": "Close tab", "accel": "Ctrl+W", "cb": lambda: self.close_doc(self.cur)},
            {"label": "Close window", "accel": "Ctrl+Shift+W", "cb": self.close},
            {"label": "Exit", "cb": self.app.quit_all},
        ])

    def _set_eol(self, eol):
        if self.cur.eol != eol:
            self.cur.eol = eol
            self.cur.saved_text = None if self.cur.path else self.cur.saved_text
            self.doc_changed(self.cur)

    def _edit_menu(self, w):
        d = self.cur
        has_sel = bool(d.buf.get_has_selection())
        self._popup(w, [
            {"label": "Undo", "icon": "undo", "accel": "Ctrl+Z", "sensitive": d.buf.can_undo(), "cb": self.undo},
            {"label": "Redo", "icon": "redo", "accel": "Ctrl+Y", "sensitive": d.buf.can_redo(), "cb": self.redo},
            None,
            {"label": "Cut", "icon": "cut", "accel": "Ctrl+X", "sensitive": has_sel, "cb": lambda: self._clip("cut")},
            {"label": "Copy", "icon": "copy", "accel": "Ctrl+C", "sensitive": has_sel, "cb": lambda: self._clip("copy")},
            {"label": "Paste", "icon": "paste", "accel": "Ctrl+V", "cb": lambda: self._clip("paste")},
            {"label": "Delete", "icon": "trash", "accel": "Del", "sensitive": has_sel,
             "cb": lambda: d.buf.delete_selection(True, True)},
            None,
            {"label": "Find", "icon": "search", "accel": "Ctrl+F", "cb": lambda: self.show_find(False)},
            {"label": "Find next", "accel": "F3", "cb": lambda: self.find_step(True)},
            {"label": "Find previous", "accel": "Shift+F3", "cb": lambda: self.find_step(False)},
            {"label": "Replace", "icon": "replace", "accel": "Ctrl+H", "cb": lambda: self.show_find(True)},
            {"label": "Go to", "accel": "Ctrl+G", "cb": self.goto_line},
            None,
            {"label": "Select all", "accel": "Ctrl+A", "cb": lambda: d.buf.select_range(d.buf.get_start_iter(),
                                                                                      d.buf.get_end_iter())},
            {"label": "Time/Date", "accel": "F5", "cb": self.insert_date},
            None,
            {"label": "Font", "cb": self.show_settings},
        ])

    def _view_menu(self, w):
        st = self.st
        self._popup(w, [
            {"label": "Zoom", "icon": "zoomin", "sub": [
                {"label": "Zoom in", "accel": "Ctrl+Plus", "cb": lambda: self.zoom(10)},
                {"label": "Zoom out", "accel": "Ctrl+Minus", "cb": lambda: self.zoom(-10)},
                {"label": "Restore default zoom", "accel": "Ctrl+0", "cb": lambda: self.zoom(reset=True)},
            ]},
            {"label": "Status bar", "checked": st["statusbar"], "cb": lambda: self._toggle("statusbar")},
            {"label": "Word wrap", "checked": st["wrap"], "cb": lambda: self._toggle("wrap")},
        ])

    def _toggle(self, key):
        self.st[key] = not self.st[key]
        for w in self.app.get_windows():
            if isinstance(w, NotepadWindow):
                w.apply_prefs()

    # ---------------- editing helpers
    def undo(self):
        if self.cur.buf.can_undo():
            self.cur.buf.undo()

    def redo(self):
        if self.cur.buf.can_redo():
            self.cur.buf.redo()

    def _clip(self, what):
        cb = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        b = self.cur.buf
        if what == "cut":
            b.cut_clipboard(cb, True)
        elif what == "copy":
            b.copy_clipboard(cb)
        else:
            b.paste_clipboard(cb, None, True)
        self.cur.view.grab_focus()

    def insert_date(self):
        now = time.localtime()
        h = now.tm_hour % 12 or 12
        s = f"{h}:{now.tm_min:02d} {'AM' if now.tm_hour < 12 else 'PM'} {now.tm_mon}/{now.tm_mday}/{now.tm_year}"
        self.cur.buf.delete_selection(True, True)
        self.cur.buf.insert_at_cursor(s)

    def goto_line(self):
        d = self.cur
        n = d.buf.get_line_count()
        ent = Gtk.Entry()
        ent.get_style_context().add_class("field")
        ent.set_text(str(d.buf.get_iter_at_mark(d.buf.get_insert()).get_line() + 1))
        ent.set_activates_default(True)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.pack_start(label("Line number"), False, False, 0)
        box.pack_start(ent, False, False, 0)
        dlg = WinDialog(self, "Go to line", None, primary="Go to", extra=box, width=340)

        def done(ok):
            if not ok:
                return
            try:
                ln = int(ent.get_text().strip())
            except ValueError:
                return
            if not 1 <= ln <= n:
                info_dialog(self, "Notepad", "The line number is beyond the total number of lines.")
                return
            it = d.buf.get_iter_at_line(ln - 1)
            d.buf.place_cursor(it)
            d.view.scroll_to_iter(it, 0.2, False, 0, 0)
            d.view.grab_focus()
        dlg.ask(done)
        ent.grab_focus()
        ent.select_region(0, -1)

    # ---------------- find / replace
    def _build_findbar(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.get_style_context().add_class("findbar")
        box.set_halign(Gtk.Align.END)
        box.set_valign(Gtk.Align.START)
        box.set_margin_end(24)
        r1 = Gtk.Box(spacing=4)
        self.exp_btn = icon_button("chevdown", lambda w: self._toggle_replace(), tip="Toggle replace")
        r1.pack_start(self.exp_btn, False, False, 0)
        self.find_entry = Gtk.Entry()
        self.find_entry.get_style_context().add_class("field")
        self.find_entry.set_placeholder_text("Find")
        self.find_entry.connect("changed", lambda *a: self._incremental())
        self.find_entry.connect("activate", lambda *a: self.find_step(True))
        r1.pack_start(self.find_entry, True, True, 0)
        self.find_count = label("", "ter")
        self.find_count.set_width_chars(9)
        r1.pack_start(self.find_count, False, False, 0)
        r1.pack_start(icon_button("up", lambda w: self.find_step(False), tip="Find previous (Shift+F3)"), False, False, 0)
        r1.pack_start(icon_button("down", lambda w: self.find_step(True), tip="Find next (F3)"), False, False, 0)
        r1.pack_start(icon_button("settings", self._find_options, tip="Options"), False, False, 0)
        r1.pack_start(icon_button("close", lambda w: self.hide_find(), tip="Close (Esc)"), False, False, 0)
        box.pack_start(r1, False, False, 0)
        r2 = Gtk.Box(spacing=4)
        sp = Gtk.Box()
        sp.set_size_request(34, -1)
        r2.pack_start(sp, False, False, 0)
        self.repl_entry = Gtk.Entry()
        self.repl_entry.get_style_context().add_class("field")
        self.repl_entry.set_placeholder_text("Replace")
        self.repl_entry.connect("activate", lambda *a: self.replace_one())
        r2.pack_start(self.repl_entry, True, True, 0)
        b1 = Gtk.Button(label="Replace")
        b1.get_style_context().add_class("secondary")
        b1.connect("clicked", lambda *a: self.replace_one())
        b2 = Gtk.Button(label="Replace all")
        b2.get_style_context().add_class("secondary")
        b2.connect("clicked", lambda *a: self.replace_all())
        r2.pack_start(b1, False, False, 0)
        r2.pack_start(b2, False, False, 0)
        self.repl_row = r2
        box.pack_start(r2, False, False, 0)
        r2.show_all()
        r2.set_no_show_all(True)
        r2.hide()
        return box

    def _find_options(self, w):
        st = self.st
        self._popup(w, [
            {"label": "Match case", "checked": st["match_case"], "cb": lambda: self._fopt("match_case")},
            {"label": "Wrap around", "checked": st["wrap_around"], "cb": lambda: self._fopt("wrap_around")},
        ])

    def _fopt(self, k):
        self.st[k] = not self.st[k]
        self._find_changed()

    def _toggle_replace(self):
        if self.repl_row.get_visible():
            self.repl_row.hide()
            self.exp_btn.get_child().set_icon("chevdown")
        else:
            self.repl_row.set_visible(True)
            self.exp_btn.get_child().set_icon("chevup")

    def show_find(self, replace):
        self.findbar.show()
        b = self.cur.buf.get_selection_bounds()
        if b and b[0].get_line() == b[1].get_line():
            self.find_entry.set_text(self.cur.buf.get_text(b[0], b[1], False))
        if replace and not self.repl_row.get_visible():
            self._toggle_replace()
        self.find_entry.grab_focus()
        self.find_entry.select_region(0, -1)
        self._find_changed()

    def hide_find(self):
        self.findbar.hide()
        for d in self.docs:
            d.search.get_settings().set_search_text(None)
        self.cur.view.grab_focus()

    def _find_changed(self):
        d = self.cur
        s = d.search.get_settings()
        s.set_search_text(self.find_entry.get_text() or None)
        s.set_case_sensitive(self.st["match_case"])
        s.set_wrap_around(self.st["wrap_around"])
        GLib.timeout_add(60, self._update_count)

    def _update_count(self):
        d = self.cur
        n = d.search.get_occurrences_count()
        if not self.find_entry.get_text():
            self.find_count.set_text("")
        elif n < 0:
            return True
        else:
            b = d.buf.get_selection_bounds()
            pos = d.search.get_occurrence_position(b[0], b[1]) if b else 0
            self.find_count.set_text(f"{pos if pos > 0 else '-'} of {n}" if n else "No results")
        return False

    def _incremental(self):
        self._find_changed()
        if not self.find_entry.get_text():
            return
        d = self.cur
        b = d.buf.get_selection_bounds()
        start = b[0] if b else d.buf.get_iter_at_mark(d.buf.get_insert())
        ok, s, e, wrapped = d.search.forward(start)
        if ok:
            d.buf.select_range(s, e)
            d.view.scroll_to_iter(s, 0.2, False, 0, 0)
        GLib.timeout_add(60, self._update_count)

    def find_step(self, forward):
        d = self.cur
        if not self.find_entry.get_text():
            self.show_find(False)
            return
        self._find_changed()
        ins = d.buf.get_iter_at_mark(d.buf.get_insert())
        b = d.buf.get_selection_bounds()
        if forward:
            start = b[1] if b else ins
            ok, s, e, wrapped = d.search.forward(start)
        else:
            start = b[0] if b else ins
            ok, s, e, wrapped = d.search.backward(start)
        if ok:
            d.buf.select_range(s, e)
            d.view.scroll_to_iter(s, 0.2, False, 0, 0)
        GLib.timeout_add(60, self._update_count)

    def replace_one(self):
        d = self.cur
        b = d.buf.get_selection_bounds()
        rep = self.repl_entry.get_text()
        if b:
            try:
                d.search.replace(b[0], b[1], rep, -1)
            except GLib.Error:
                pass
        self.find_step(True)

    def replace_all(self):
        d = self.cur
        self._find_changed()
        try:
            n = d.search.replace_all(self.repl_entry.get_text(), -1)
        except GLib.Error:
            n = 0
        self.find_count.set_text(f"Replaced {n}")

    # ---------------- settings page
    def show_settings(self):
        if self.settings_page is None:
            self.settings_page = self._build_settings()
            self.stack.add(self.settings_page)
        self.settings_page.show_all()
        self.stack.set_visible_child(self.settings_page)
        for tb in self.tabs.values():
            tb.set_active(False)
        self.set_title("Settings - Notepad")

    def _build_settings(self):
        st = self.st
        sw = Gtk.ScrolledWindow()
        sw.get_style_context().add_class("settings-page")
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        col.set_margin_start(40)
        col.set_margin_end(40)
        col.set_margin_top(28)
        col.set_margin_bottom(28)
        top = Gtk.Box()
        top.pack_start(label("Settings", "big-title"), False, False, 0)
        back = Gtk.Button(label="Back to document")
        back.get_style_context().add_class("secondary")
        back.connect("clicked", lambda *a: self.switch(self.cur))
        top.pack_end(back, False, False, 0)
        col.pack_start(top, False, False, 12)

        def group(title, desc, widget):
            g = Gtk.Box(spacing=12)
            g.get_style_context().add_class("set-group")
            t = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            t.pack_start(label(title, "set-head"), False, False, 0)
            if desc:
                t.pack_start(label(desc, "set-desc", wrap=True), False, False, 0)
            g.pack_start(t, True, True, 0)
            widget.set_valign(Gtk.Align.CENTER)
            g.pack_end(widget, False, False, 0)
            col.pack_start(g, False, False, 0)

        col.pack_start(label("Text formatting", "sect-title"), False, False, 8)
        fb = Gtk.FontButton()
        fb.set_font(st["font"])
        fb.set_use_font(True)
        fb.connect("font-set", lambda b: (st.__setitem__("font", b.get_font()), self._apply_all()))
        group("Font", "Family, style and size", fb)

        def sw_(key):
            s = Gtk.Switch()
            s.set_active(bool(st[key]))
            s.connect("notify::active", lambda s, p: (st.__setitem__(key, s.get_active()), self._apply_all()))
            return s
        group("Word wrap", "Fit text to the window width", sw_("wrap"))
        group("Status bar", "Show line, column and character count", sw_("statusbar"))
        col.pack_start(label("Opening Notepad", "sect-title"), False, False, 8)
        group("Continue previous session",
              "Open the tabs you had last time, including unsaved changes. Turn off to start fresh every time.",
              sw_("restore"))
        col.pack_start(label("About", "sect-title"), False, False, 8)
        col.pack_start(label("Notepad for Raspberry Pi  (pi-notepad)", "sec"), False, False, 0)
        sw.add(col)
        return sw

    def _apply_all(self):
        for w in self.app.get_windows():
            if isinstance(w, NotepadWindow):
                w.apply_prefs()
        self.st.save()

    # ---------------- window
    def _configure(self, w, ev):
        if not self.is_maximized():
            self.st["width"], self.st["height"] = self.get_size()
        return False

    def _on_close(self, *a):
        self.st["maximized"] = self.is_maximized()
        if self is self.app.main_window() and self.st.get("restore", True):
            self.save_session()
            self.st.save()
            return False
        # not restoring: ask about unsaved tabs one by one
        unsaved = [d for d in self.docs if d.modified() and (d.path or d.get_text().strip())]
        if not unsaved:
            self.st.save()
            return False

        def step():
            if unsaved:
                d = unsaved.pop(0)
                self.switch(d)
                self.ask_save(d, step)
            else:
                self.st.save()
                self.destroy()
        step()
        return True

    def _key(self, w, ev):
        k = Gdk.keyval_to_lower(ev.keyval)
        ctrl = bool(ev.state & Gdk.ModifierType.CONTROL_MASK)
        shift = bool(ev.state & Gdk.ModifierType.SHIFT_MASK)
        alt = bool(ev.state & Gdk.ModifierType.MOD1_MASK)
        if ctrl and not shift and k == Gdk.KEY_n:
            self.new_doc()
        elif ctrl and shift and k == Gdk.KEY_n:
            self.app.new_window(fresh=True)
        elif ctrl and k == Gdk.KEY_o:
            self.open_dialog()
        elif ctrl and alt and k == Gdk.KEY_s:
            self.save_all()
        elif ctrl and shift and k == Gdk.KEY_s:
            self.save(save_as=True)
        elif ctrl and k == Gdk.KEY_s:
            self.save()
        elif ctrl and shift and k == Gdk.KEY_w:
            self.close()
        elif ctrl and k == Gdk.KEY_w:
            self.close_doc(self.cur)
        elif ctrl and k in (Gdk.KEY_Tab, Gdk.KEY_ISO_Left_Tab, Gdk.KEY_Page_Down, Gdk.KEY_Page_Up):
            back = shift or k == Gdk.KEY_Page_Up
            i = self.docs.index(self.cur)
            self.switch(self.docs[(i + (-1 if back else 1)) % len(self.docs)])
        elif ctrl and k == Gdk.KEY_f:
            self.show_find(False)
        elif ctrl and k == Gdk.KEY_h:
            self.show_find(True)
        elif ctrl and k == Gdk.KEY_g:
            self.goto_line()
        elif k == Gdk.KEY_F3:
            self.find_step(not shift)
        elif k == Gdk.KEY_F5:
            self.insert_date()
        elif ctrl and k in (Gdk.KEY_plus, Gdk.KEY_equal, Gdk.KEY_KP_Add):
            self.zoom(10)
        elif ctrl and k in (Gdk.KEY_minus, Gdk.KEY_KP_Subtract):
            self.zoom(-10)
        elif ctrl and k in (Gdk.KEY_0, Gdk.KEY_KP_0):
            self.zoom(reset=True)
        elif ctrl and k == Gdk.KEY_y:
            self.redo()
        elif ctrl and shift and k == Gdk.KEY_z:
            self.redo()
        elif ctrl and k == Gdk.KEY_z:
            self.undo()
        elif k == Gdk.KEY_Escape and self.findbar.get_visible():
            self.hide_find()
        else:
            return False
        return True


class NotepadApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.restored = False

    def do_startup(self):
        Gtk.Application.do_startup(self)
        self.settings = JsonSettings("pi-notepad", DEFAULTS)
        apply_css(CSS)
        self.scheme = install_scheme()

    def main_window(self):
        for w in self.get_windows():
            if isinstance(w, NotepadWindow):
                return w
        return None

    def new_window(self, paths=None, fresh=False):
        w = NotepadWindow(self, paths, fresh)
        w.present()
        return w

    def do_command_line(self, cmd):
        cwd = cmd.get_cwd() or HOME
        paths = []
        for a in cmd.get_arguments()[1:]:
            if a.startswith("-"):
                continue
            p = Gio.File.new_for_uri(a).get_path() if "://" in a else os.path.join(cwd, os.path.expanduser(a))
            if p:
                paths.append(p)
        w = self.main_window()
        if w:
            for p in paths:
                w.open_path(p)
            if not paths:
                w.new_doc()
            w.present()
        else:
            self.new_window(paths)
        return 0

    def quit_all(self):
        for w in list(self.get_windows()):
            w.close()


def main():
    GLib.set_prgname("pi-notepad")
    GLib.set_application_name("Notepad")
    app = NotepadApp()
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
