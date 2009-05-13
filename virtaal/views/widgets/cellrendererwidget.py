#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009 Zuza Software Foundation
#
# This file is part of Virtaal.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import gtk
import pango
from gobject import idle_add, PARAM_READWRITE, SIGNAL_RUN_FIRST, TYPE_PYOBJECT


def flagstr(flags):
    """Create a string-representation for the given flags structure."""
    fset = []
    for f in dir(gtk):
        if not f.startswith('CELL_RENDERER_'):
            continue
        if flags & getattr(gtk, f):
            fset.append(f)
    return '|'.join(fset)


class CellRendererWidget(gtk.GenericCellRenderer):
    __gtype_name__ = 'CellRendererWidget'
    __gproperties__ = {
        'widget': (TYPE_PYOBJECT, 'Widget', 'The column containing the widget to render', PARAM_READWRITE),
    }


    # INITIALIZERS #
    def __init__(self, strfunc):
        gtk.GenericCellRenderer.__init__(self)
        self.props.mode = gtk.CELL_RENDERER_MODE_EDITABLE

        self.editablemap = {}
        self._starting_edit = False
        self.strfunc = strfunc
        self.widget = None


    # INTERFACE METHODS #
    def do_set_property(self, pspec, value):
        setattr(self, pspec.name, value)

    def do_get_property(self, pspec):
        return getattr(self, pspec.name)

    def on_activate(self, *args):
        pass

    def on_get_size(self, widget, cell_area=None):
        #print '%s>> on_get_size(cell_area=%s)' % (self.strfunc(self.widget), cell_area)
        height = width = 0
        xpad = ypad = 2

        width = widget.get_allocation().width
        if width <= 1:
            width = -1
        layout = self.create_pango_layout(self.strfunc(self.widget), widget, width)
        lw, lh = layout.get_pixel_size()

        if self.widget:
            self.widget.set_size_request(width, -1)
            self.widget.show()
            w, h = self.widget.get_size_request()
            width =  max(lw, w, hasattr(self.widget, 'min_width')  and self.widget.min_width  or 0)
            height = max(lh, h, hasattr(self.widget, 'min_height') and self.widget.min_height or 0)

        #print 'width %d | height %d | lw %d | lh %d' % (width, height, lw, lh)
        height += ypad * 2
        width  += xpad * 2

        return xpad, ypad, width, height

    def on_render(self, window, widget, bg_area, cell_area, expose_area, flags):
        #print '%s>> on_render(flags=%s)' % (self.strfunc(self.widget), flagstr(flags))
        if flags & gtk.CELL_RENDERER_SELECTED:
            self._start_editing(widget) # FIXME: This is obviously a hack, but what more do you want?
            return True
        xo, yo, w, h = self.get_size(widget, cell_area)
        x = cell_area.x + xo
        y = cell_area.y + yo
        layout = self.create_pango_layout(self.strfunc(self.widget), widget, w)
        widget.get_style().paint_layout(window, gtk.STATE_NORMAL, True, cell_area, widget, '', x, y, layout)

    def on_start_editing(self, event, tree_view, path, bg_area, cell_area, flags):
        #print '%s>> on_start_editing(flags=%s, event=%s)' % (self.strfunc(self.widget), flagstr(flags), event)
        if self.widget not in self.editablemap:
            editable = CellWidget(self.widget)
            editable.connect('editing-done', lambda *args: True)
            editable.connect('key-press-event', lambda *args: True)
            self.editablemap[self.widget] = editable
        editable = self.editablemap[self.widget]
        editable.show_all()
        editable.grab_focus()
        return editable

    # METHODS #
    def create_pango_layout(self, string, widget, width):
        font = widget.get_pango_context().get_font_description()
        layout = pango.Layout(widget.get_pango_context())
        layout.set_font_description(font)
        layout.set_wrap(pango.WRAP_WORD_CHAR)
        layout.set_width(width * pango.SCALE)
        layout.set_markup(string)
        return layout

    def _start_editing(self, treeview):
        """Force the cell to enter editing mode by going through the parent
            gtk.TextView."""
        if self._starting_edit:
            return
        self._starting_edit = True

        model, iter = treeview.get_selection().get_selected()
        path = model.get_path(iter)
        col = [c for c in treeview.get_columns() if self in c.get_cell_renderers()]
        if len(col) < 1:
            return
        treeview.set_cursor_on_cell(path, col[0], self, True)

        # XXX: Hack to make sure that the lock (_start_editing) is not released before the next on_render() is called.
        def update_lock():
            self._starting_edit = False
        idle_add(update_lock)


class CellWidget(gtk.HBox, gtk.CellEditable):
    __gtype_name__ = 'CellWidget'
    __gsignals__ = {
        'modified': (SIGNAL_RUN_FIRST, None, ())
    }

    # INITIALIZERS #
    def __init__(self, *widgets):
        super(CellWidget, self).__init__()
        for w in widgets:
            if w.parent is not None:
                w.parent.remove(w)
            self.pack_start(w)


    # INTERFACE METHODS #
    def do_editing_done(self, *args):
        pass

    def do_remove_widget(self, *args):
        pass

    def do_start_editing(self, *args):
        pass


if __name__ == "__main__":
    class Tree(gtk.TreeView):
        def __init__(self):
            self.store = gtk.ListStore(str, TYPE_PYOBJECT, bool)
            gtk.TreeView.__init__(self)
            self.set_model(self.store)
            self.set_headers_visible(True)

            self.append_column(gtk.TreeViewColumn('First', gtk.CellRendererText(), text=0))
            self.append_column(gtk.TreeViewColumn('Second', CellRendererWidget(lambda widget: '<b>' + widget.get_label() + '</b>'), widget=1))

        def insert(self, name):
            iter = self.store.append()
            btn = gtk.Button(name)
            btn.min_height = 30
            self.store.set(iter, 0, name, 1, btn, 2, True)

    w = gtk.Window()
    w.set_position(gtk.WIN_POS_CENTER)
    w.connect('delete-event', gtk.main_quit)
    t = Tree()
    t.insert('foo')
    t.insert('bar')
    t.insert('baz')
    w.add(t)

    w.show_all()
    gtk.main()