# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details
# http://www.gnu.org/licenses/gpl-3.0.txt

import urwid
import collections


class Style():
    """Map standard attributes to those defined in a urwid palette

    prefix: common prefix of all attributes
    extras: additional attributes (e.g. 'header')
    modes: additional subsections with 'focused' and 'unfocused' attributes
           (e.g. 'highlighted')
    focusable: True if 'focused' attributes should be mapped, False otherwise
    """

    def __init__(self, prefix, modes=(), extras=(), focusable=True):
        self._attribs = {
            'unfocused': self.dotify(prefix, 'unfocused')
        }
        for extra in extras:
            self._attribs[extra] = self.dotify(prefix, extra)

        if focusable:
            self._attribs['focused'] = self.dotify(prefix, 'focused')

        for mode in modes:
            self._attribs[mode+'.focused'] = self.dotify(prefix, mode, 'focused')
            self._attribs[mode+'.unfocused'] = self.dotify(prefix, mode, 'unfocused')

    def attrs(self, mode=None, focused=False):
        """Get attributes as specified in the urwid palette

        mode: one of the modes specified during initialization
        focused: If True the '...focused' attributes are returned,
                 '...unfocused otherwise
        """
        mode = '' if not mode else mode
        name = self.dotify(mode, 'focused' if focused else 'unfocused')
        if name in self._attribs:
            return self._attribs[name]
        else:
            return self._attribs[mode]

    @property
    def focus_map(self):
        """Map of all '...unfocused' -> '...focused' attributes"""
        focus_map = {}
        attribs = self._attribs
        for name in attribs:
            if name.endswith('unfocused'):
                name_focused = name[:-9] + 'focused'
                focus_map[attribs[name]] = attribs[name_focused]
        return focus_map

    @staticmethod
    def dotify(*strings):
        """Join non-empty strings with a '.'"""
        return '.'.join(x for x in (strings) if x)


# TODO: It would be great if some columns (e.g. rate-up/down) would shrink to
#       the widest visible value (including its header).  Other columns would
#       share the remaining width using ('weight', x), giving some of them
#       (e.g. name) more space than others (e.g. path).
class CellWidgetBase(urwid.WidgetWrap):
    """Base class for cells in items in Torrent/File/Peer/... lists"""

    style = collections.defaultdict(lambda: 'default')
    header = urwid.Padding(urwid.Text('NO HEADER SPECIFIED'))
    width = ('weight', 100)
    align = 'right'

    def __init__(self):
        self.value = None
        self.text = urwid.Text('', wrap='clip', align=self.align)
        self.attrmap = urwid.AttrMap(self.text, self.style.attrs('unfocused'))
        return super().__init__(self.attrmap)

    def update(self, data):
        self.data.update(data)
        new_value = self.get_value()
        if self.value != new_value:
            self.value = new_value
            self.text.set_text(str(new_value))
            attr = self.style.attrs(self.get_mode(), focused=False)
            self.attrmap.set_attr_map({None: attr})

    def get_value(self):
        raise NotImplementedError()

    def get_mode(self):
        return None


def make_ItemWidget_class(item_name, tui_columns, unfocused, focused=None):
    """Return class to be used for rows in Torrent/File/Peer/... lists"""
    clsattrs = {'palette_unfocused': unfocused,
                'palette_focused': focused}

    if focused:
        # List items are focusable - create focus map that maps <unfocused> ->
        # <focused> that we can later use in __init__ for an AttrMap wrapper
        # around the whole row.
        COLUMNS_FOCUS_MAP = {}
        for col in tui_columns.values():
            COLUMNS_FOCUS_MAP.update(col.style.focus_map)
        clsattrs['COLUMNS_FOCUS_MAP'] = COLUMNS_FOCUS_MAP

    def __init__(self, item, cells):
        self._item = item    # Info of torrent/tracker/file/peer/...
        self._cells = cells  # Group instance that combines widgets horizontally

        if hasattr(self, 'COLUMNS_FOCUS_MAP'):
            # Item is focusable
            row = urwid.AttrMap(urwid.AttrMap(cells, attr_map=None, focus_map=self.COLUMNS_FOCUS_MAP),
                                self.palette_unfocused, self.palette_focused)
        else:
            # Item is not focusable
            row = urwid.AttrMap(cells, self.palette_unfocused)
        urwid.WidgetWrap.__init__(self, row)

        # Initialize cell widgets
        self.update(item)
    clsattrs['__init__'] = __init__

    def update(self, item):
        for widget in self._cells.widgets:
            widget.update(item)
        self._item = item
    clsattrs['update'] = update

    def id(self):
        return self._item['id']
    clsattrs['id'] = property(id)

    def torrent_id(self):
        item = self._item
        return item['tid'] if 'tid' in item else item['id']
    clsattrs['torrent_id'] = property(torrent_id)

    def item(self):
        return self._item
    clsattrs['item'] = property(item)

    def is_marked_getter(self):
        return self._cells.marked.is_marked
    def is_marked_setter(self, is_marked):
        self._cells.marked.is_marked = bool(is_marked)
    clsattrs['is_marked'] = property(fget=is_marked_getter, fset=is_marked_setter)

    return type(item_name+'ItemWidget', (urwid.WidgetWrap,), clsattrs)


from .. import main as tui
from ..table import Table
from ..scroll import ScrollBar

class ListWidgetBase(urwid.WidgetWrap):
    # Derived classes must set these
    TUICOLUMNS = NotImplemented
    ListItemClass = NotImplemented
    keymap_context = NotImplemented
    palette_name = NotImplemented

    # TODO: Remove all columns=[], because that [] is a singleton of that function
    def __init__(self, srvapi, keymap, columns=None, sort=None, title=None):
        self._srvapi = srvapi
        self._keymap = keymap
        self._ListItemClass = keymap.wrap(self.ListItemClass,
                                              context=self.keymap_context)

        self._items = ()
        self._marked = set()

        self._columns = columns or []
        self._sort = sort
        self._sort_orig = sort

        self._title = title
        self.title_updater = None

        self._table = Table(**self.TUICOLUMNS)
        self._table.columns = self._columns

        self._listbox = keymap.wrap(urwid.ListBox, context=self.keymap_context + 'list')(
            urwid.SimpleFocusListWalker([])
        )

        listbox_sb = urwid.AttrMap(
            ScrollBar(urwid.AttrMap(self._listbox, self.palette_name)),
            'scrollbar'
        )
        pile = urwid.Pile([
            ('pack', urwid.AttrMap(self._table.headers, self.palette_name + '.header')),
            listbox_sb
        ])
        super().__init__(pile)

    def __repr__(self):
        return '<%s %s, #%s>' % (type(self).__name__, self.title, id(self))

    def _invalidate(self):
        if self.title_updater is not None:
            # First argument can be cropped if too long, second argument is fixed
            # self.title_updater(self.title, ' [%d]' % self.count)
            self.title_updater(self.title, ' [%d]' % self.count)
        super()._invalidate()

    def render(self, size, focus=False):
        if self._items is not None:
            self._update_listitems()
            self._items = None
        return super().render(size, focus)

    def _update_listitems(self):
        # Remember focused row in case rows get added or removed
        focusedw = self.focused_widget

        walker = self._listbox.body
        item_dict = self._items
        dead_items = []
        for w in walker:  # w = *ItemWidget instance
            id = w.id
            try:
                # Update existing *ItemWidget instances with new data
                w.update(item_dict[id])
                del item_dict[id]
            except KeyError:
                # Item no longer exists in self._items anymore
                dead_items.append(w)

        # Remove dead *ItemWidget instances
        marked = self._marked
        for w in dead_items:
            walker.remove(w)
            marked.discard(w)  # self._marked may have a reference too

        # Any items that haven't been used to update an existing *ItemWidget instance are new
        if item_dict:
            table = self._table
            cls = self._ListItemClass
            for tid in item_dict:
                table.register(tid)
                row = table.get_row(tid)
                walker.append(cls(item_dict[tid], row))

        # Sort items in walker
        if self._sort is not None:
            self._sort.apply(walker,
                            item_getter=lambda w: w.item,
                            inplace=True)

        # Items could be added/removed - re-focus previously focused item if necessary
        if focusedw is not None and self.focused_widget is not None and \
           focusedw.id != self.focused_widget.id:
            focused_id = focusedw.id
            for i,w in enumerate(walker):
                if w.id == focused_id:
                    self._listbox.focus_position = i
                    break

    def clear(self):
        """Remove all list items"""
        self._table.clear()
        self._listbox.body[:] = ()
        # self._listbox.body[:] = []
        self._listbox._invalidate()
        self._marked.clear()

    @property
    def sort(self):
        """*Sorter object or `None` to keep list items unsorted"""
        return self._sort

    @sort.setter
    def sort(self, sort):
        if sort == 'RESET':
            self._sort = self._sort_orig
        else:
            self._sort = sort


    @property
    def count(self):
        """Number of listed items"""
        # If this method was called before rendering, the contents of the
        # listbox widget are inaccurate and we have to use self._items.  But if
        # we're called after rendering, self._items is reset to None and we have
        # to count items in the listbox.
        if self._items is not None:
            return len(self._items)
        else:
            return len(self._listbox.body)

    @property
    def title_name(self):
        """The base name of the title"""
        return str(self._title)

    @property
    def title_sort_order(self):
        """The sort order part of the title"""
        if self._sort is not None:
            sortstr = str(self._sort)
            if sortstr is not self._sort.DEFAULT_SORT:
                return '{%s}' % sortstr
        return ''

    @property
    def title(self):
        """Combined `title_name` and `title_sort_order`"""
        parts = [self.title_name]
        sort = self.title_sort_order
        if sort:
            parts.append(sort)
        return ' '.join(parts)


    def mark(self, toggle=False, all=False):
        """Mark the currently focused item or all items"""
        self._set_mark(True, toggle=toggle, all=all)

    def unmark(self, toggle=False, all=False):
        """Unmark the currently focused item or all items"""
        self._set_mark(False, toggle=toggle, all=all)

    @property
    def marked(self):
        """Generator that yields TorrentItemWidgets"""
        yield from self._marked

    def _set_mark(self, mark, toggle=False, all=False):
        if toggle and self.focused_widget is not None:
            mark = not self.focused_widget.is_marked

        for widget in self._select_items_for_marking(all):
            widget.is_marked = mark
            if mark:
                self._marked.add(widget)
            else:
                self._marked.discard(widget)

    def _select_items_for_marking(self, all):
        if self.focused_widget is not None:
            if all:
                yield from self._listbox.body
            else:
                yield self.focused_widget

    def refresh_marks(self):
        """Redraw the "marked" column in all rows

        This shouldn't be needed unless the marked character was changed.
        """
        for widget in self._listbox.body:
            widget.is_marked = widget.is_marked


    @property
    def focused_widget(self):
        """Currently focused widget in list"""
        return self._listbox.focus

    @property
    def focused_id(self):
        """ID of the currently focused list item or `None`"""
        focused_widget = self._listbox.focus
        if focused_widget is not None:
            return focused_widget.id
        # return self._listbox.focus.id

    @property
    def focused_torrent_id(self):
        """ID of the torrent that the currently focused list item belongs to or `None`"""
        focused_widget = self._listbox.focus
        if focused_widget is not None:
            return focused_widget.torrent_id
        # return self._listbox.focus.torrent_id

    @property
    def focus_position(self):
        """Focus position (first item is 0; `None` if list is empty)"""
        return self._listbox.focus_position

    @focus_position.setter
    def focus_position(self, focus_position):
        self._listbox.focus_position = min(focus_position, len(self._listbox.body)-1)


from . import hooks
