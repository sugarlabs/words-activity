# Copyright 2008 Chris Ball.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""Words Activity: A multi-lingual dictionary with speech synthesis."""
"""Actividad Palabras: Un diccionario multi-lengua con sintesis de habla"""

from gi.repository import GObject
from gi.repository import Gdk
from gi.repository import Gtk 
from gi.repository import Pango

import logging
import os
import subprocess

from gettext import gettext as _

from sugar3.activity import activity
from sugar3.graphics.icon import Icon
from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.activity.widgets import ActivityToolbarButton
from sugar3.activity.widgets import StopButton
from sugar3.graphics import style
from sugar3.graphics.palettemenu import PaletteMenuItem
from sugar3.graphics.palette import Palette
from sugar3.graphics.palette import ToolInvoker

import dictdmodel


class FilterToolItem(Gtk.ToolButton):

    _LABEL_MAX_WIDTH = 18
    _MAXIMUM_PALETTE_COLUMNS = 4

    __gsignals__ = {
        'changed': (GObject.SignalFlags.RUN_LAST, None, ([])), }

    def __init__(self, default_icon, default_value, options):
        self._palette_invoker = ToolInvoker()
        self._options = options
        Gtk.ToolButton.__init__(self)
        self._label = self._options[default_value]
        self.set_is_important(True)
        self.set_size_request(style.GRID_CELL_SIZE, -1)

        self._label_widget = Gtk.Label()
        self._label_widget.set_alignment(0.0, 0.5)
        self._label_widget.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        self._label_widget.set_max_width_chars(self._LABEL_MAX_WIDTH)
        self._label_widget.set_use_markup(True)
        self._label_widget.set_markup(self._label)
        self.set_label_widget(self._label_widget)
        self._label_widget.show()

        self.set_widget_icon(icon_name=default_icon)

        self._hide_tooltip_on_click = True
        self._palette_invoker.attach_tool(self)
        self._palette_invoker.props.toggle_palette = True
        self._palette_invoker.props.lock_palette = True

        self.palette = Palette(_('Select filter'))
        self.palette.set_invoker(self._palette_invoker)

        self.props.palette.set_content(self.set_palette_list(options))

    def set_widget_icon(self, icon_name=None):
        icon = Icon(icon_name=icon_name,
                    icon_size=style.SMALL_ICON_SIZE)
        self.set_icon_widget(icon)
        icon.show()

    def _set_widget_label(self, label=None):
        # FIXME: Ellipsis is not working on these labels.
        if label is None:
            label = self._label
        if len(label) > self._LABEL_MAX_WIDTH:
            label = label[0:7] + '...' + label[-7:]
        self._label_widget.set_markup(label)
        self._label = label

    def __destroy_cb(self, icon):
        if self._palette_invoker is not None:
            self._palette_invoker.detach()

    def create_palette(self):
        return None

    def get_palette(self):
        return self._palette_invoker.palette

    def set_palette(self, palette):
        self._palette_invoker.palette = palette

    palette = GObject.property(
        type=object, setter=set_palette, getter=get_palette)

    def get_palette_invoker(self):
        return self._palette_invoker

    def set_palette_invoker(self, palette_invoker):
        self._palette_invoker.detach()
        self._palette_invoker = palette_invoker

    palette_invoker = GObject.property(
        type=object, setter=set_palette_invoker, getter=get_palette_invoker)

    def do_draw(self, cr):
        if self.palette and self.palette.is_up():
            allocation = self.get_allocation()
            # draw a black background, has been done by the engine before
            cr.set_source_rgb(0, 0, 0)
            cr.rectangle(0, 0, allocation.width, allocation.height)
            cr.paint()

        Gtk.ToolButton.do_draw(self, cr)

        if self.palette and self.palette.is_up():
            invoker = self.palette.props.invoker
            invoker.draw_rectangle(cr, self.palette)

        return False

    def set_palette_list(self, options):
        _menu_item = PaletteMenuItem(text_label=options[options.keys()[0]])
        req2 = _menu_item.get_preferred_size()[1]
        menuitem_width = req2.width
        menuitem_height = req2.height

        palette_width = Gdk.Screen.width() - style.GRID_CELL_SIZE
        palette_height = Gdk.Screen.height() - style.GRID_CELL_SIZE * 3

        nx = min(self._MAXIMUM_PALETTE_COLUMNS,
                 int(palette_width / menuitem_width))
        ny = min(int(palette_height / menuitem_height), len(options) + 1)
        if ny >= len(options):
            nx = 1
            ny = len(options)

        grid = Gtk.Grid()
        grid.set_row_spacing(style.DEFAULT_PADDING)
        grid.set_column_spacing(0)
        grid.set_border_width(0)
        grid.show()

        x = 0
        y = 0

        for key in options.keys():
            menu_item = PaletteMenuItem()
            menu_item.set_label(options[key])

            menu_item.set_size_request(style.GRID_CELL_SIZE * 3, -1)

            menu_item.connect('button-release-event', self._option_selected, key)
            grid.attach(menu_item, x, y, 1, 1)
            x += 1
            if x == nx:
                x = 0
                y += 1

            menu_item.show()

        if palette_height < (y * menuitem_height + style.GRID_CELL_SIZE):
            # if the grid is bigger than the palette, put in a scrolledwindow
            scrolled_window = Gtk.ScrolledWindow()
            scrolled_window.set_policy(Gtk.PolicyType.NEVER,
                                       Gtk.PolicyType.AUTOMATIC)
            scrolled_window.set_size_request(nx * menuitem_width,
                                             (ny + 1) * menuitem_height)
            scrolled_window.add_with_viewport(grid)
            return scrolled_window
        else:
            return grid

    def _option_selected(self, menu_item, event, key):
        self._set_widget_label(self._options[key])
        self.emit('changed', key)


class WordsActivity(activity.Activity):
    """Words Activity as specified in activity.info"""

    def __init__(self, handle):
        """Set up the Words activity."""
        super(WordsActivity, self).__init__(handle)

        self._dictionaries = dictdmodel.Dictionaries('./dictd/')

        self._from_languages = self._dictionaries.get_languages_from()
        self._from_lang_options = {}
        for lang in self._from_languages:
            self._from_lang_options[lang] = dictdmodel.lang_codes[lang]

        # Instantiate a language model.
        # FIXME: We should ask the language model what langs it supports.
        self.langs = ["French", "German", "Italian", "Portuguese", "Spanish"]
        # Initial values | Valores iniciales
        self.fromlang = "English"
        self.tolang = "Spanish"
        import LanguageModel
        self.languagemodel = LanguageModel.LanguageModel()

        self.max_participants = 1

        # Main layout | disposicion general
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, homogeneous=True, spacing=8)
        vbox =  Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        toolbar_box = ToolbarBox()

        activity_button = ActivityToolbarButton(self)
        toolbar_box.toolbar.insert(activity_button, 0)
        activity_button.show()

        toolbar_box.toolbar.insert(Gtk.SeparatorToolItem(), -1)

        from_toolitem = Gtk.ToolItem()
        from_toolitem.add(Gtk.Label(_('From:')))
        from_toolitem.show_all()
        toolbar_box.toolbar.insert(from_toolitem, -1)

        self._default_from_language = 'eng'
        self._default_to_language = 'spa'

        self._from_button = FilterToolItem('go-down',
                                           self._default_from_language,
                                           self._from_lang_options)
        toolbar_box.toolbar.insert(self._from_button, -1)

        to_toolitem = Gtk.ToolItem()
        to_toolitem.add(Gtk.Label('    ' + _('To:')))
        to_toolitem.show_all()
        toolbar_box.toolbar.insert(to_toolitem, -1)

        self._to_languages = self._dictionaries.get_languages_to(
            self._default_from_language)
        self._to_lang_options = {}
        for lang in self._to_languages:
            self._to_lang_options[lang] = dictdmodel.lang_codes[lang]

        self._to_button = FilterToolItem('go-down',
                                         self._default_to_language,
                                         self._to_lang_options)
        toolbar_box.toolbar.insert(self._to_button, -1)

        separator = Gtk.SeparatorToolItem()
        separator.props.draw = False
        separator.set_expand(True)
        toolbar_box.toolbar.insert(separator, -1)
        separator.show()

        stop_button = StopButton(self)
        toolbar_box.toolbar.insert(stop_button, -1)
        stop_button.show()

        self.set_toolbar_box(toolbar_box)
        toolbar_box.show()

        # transbox: <label> - <text entry> - <speak button>
        transbox = Gtk.Table()
        transbox.resize(2, 3)
        transbox.set_row_spacings(8)
        transbox.set_col_spacings(12)
        transbox.set_border_width(20)

        # Labels
        label1 = Gtk.Label(label=_("Word") + ':')
        label1.set_alignment(xalign=0.0, yalign=0.5)
        label2 = Gtk.Label(label=_("Translation") + ':')
        label2.set_alignment(xalign=0.0, yalign=0.5)
        
        # Text entry box to enter word to be translated
        self.totranslate = Gtk.Entry()
        self.totranslate.set_max_length(50)
        self.totranslate.connect("changed", self.totranslate_cb)
        self.totranslate.modify_font(Pango.FontDescription("Sans 14"))
        
        # Text entry box to receive word translated
        self.translated = Gtk.Entry()
        self.translated.set_max_length(50)
        self.translated.set_property('editable', False)
        self.translated.modify_font(Pango.FontDescription("Sans 14"))

        # Speak buttons
        speak1 = Gtk.ToolButton()
        speak_icon1 = Icon(icon_name='microphone')
        speak1.set_icon_widget(speak_icon1)
        speak1.connect("clicked", self.speak1_cb)
        speak2 = Gtk.ToolButton()
        speak_icon2 = Icon(icon_name='microphone')
        speak2.set_icon_widget(speak_icon2)
        speak2.connect("clicked", self.speak2_cb)
        
        transbox.attach(label1, 0, 1, 0, 1, xoptions=Gtk.AttachOptions.FILL)
        transbox.attach(self.totranslate, 1, 2, 0, 1, xoptions=Gtk.AttachOptions.FILL|Gtk.AttachOptions.EXPAND)
        transbox.attach(speak1, 2, 3, 0, 1, xoptions=Gtk.AttachOptions.FILL)

        transbox.attach(label2, 0, 1, 1, 2, xoptions=Gtk.AttachOptions.FILL)
        transbox.attach(self.translated, 1, 2, 1, 2, xoptions=Gtk.AttachOptions.FILL|Gtk.AttachOptions.EXPAND)
        transbox.attach(speak2, 2, 3, 1, 2, xoptions=Gtk.AttachOptions.FILL)

        vbox.pack_start(transbox, expand=False, fill=True, padding=0)
        
        # The "lang1" treeview box
        self.lang1model = Gtk.ListStore(str)
        lang1view = Gtk.TreeView(self.lang1model)
        lang1view.set_headers_visible(False)
        lang1cell = Gtk.CellRendererText()
        lang1cell.props.ellipsize_set = True
        lang1cell.props.ellipsize = Pango.EllipsizeMode.END
        lang1treecol = Gtk.TreeViewColumn("", lang1cell, text=0)
        lang1view.get_selection().connect("changed", self.lang1sel_cb)
        lang1view.append_column(lang1treecol)
        lang1scroll = Gtk.ScrolledWindow(hadjustment=None, vadjustment=None)
        lang1scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        lang1scroll.add(lang1view)

        # The "lang2" box
        self.lang2model = Gtk.ListStore(str)
        lang2view = Gtk.TreeView(self.lang2model)
        lang2view.set_headers_visible(False)
        lang2cell = Gtk.CellRendererText()
        lang2cell.props.ellipsize_set = True
        lang2cell.props.ellipsize = Pango.EllipsizeMode.END
        lang2treecol = Gtk.TreeViewColumn("", lang2cell, text=0)
        lang2view.get_selection().connect("changed", self.lang2sel_cb)
        lang2view.append_column(lang2treecol)
        lang2scroll = Gtk.ScrolledWindow(hadjustment=None, vadjustment=None)
        lang2scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        lang2scroll.add(lang2view)

        lang1_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)  # Gtk.VBox(spacing=8)
        lang1_vbox.pack_start(lang1scroll, expand=True, fill=True, padding=0)

        lang2_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)  # Gtk.VBox(spacing=8)
        lang2_vbox.pack_start(lang2scroll, expand=True, fill=True, padding=0)

        hbox.pack_start(lang1_vbox, expand=True, fill=True, padding=0)
        hbox.pack_start(lang2_vbox, expand=True, fill=True,padding=0)

        vbox.pack_start(hbox, expand=True, fill=True, padding=0)
        self.set_canvas(vbox)
        self.totranslate.grab_focus()
        self.show_all()

    def say(self, text, lang):
        # No Portuguese accent yet.
        if lang == "portuguese":
            lang = "spanish"
        #AU costumization
        elif lang == "english":
            lang = "english_rp"

        tmpfile = "/tmp/something.wav"
        subprocess.call(["espeak", text, "-w", tmpfile, "-v", lang])
        subprocess.call(["aplay", tmpfile])
        os.unlink(tmpfile)

    def lang1sel_cb(self, column):
        # FIXME: Complete the text entry box
        model, _iter = column.get_selected()
        value = model.get_value(_iter,0)
        translations = self.languagemodel.GetTranslations(0, value)
        self.translated.set_text(",".join(translations))

    def lang2sel_cb(self, column):
        model, _iter = column.get_selected()
        value = model.get_value(_iter,0)
        translations = self.languagemodel.GetTranslations(1, value)
        self.translated.set_text(",".join(translations))

    def speak1_cb(self, button):
        text = self.totranslate.get_text()
        lang = self.fromlang.lower()
        self.say(text, lang)

    def speak2_cb(self, button):
        text = self.translated.get_text()
        lang = self.tolang.lower()
        self.say(text, lang)

    def totranslate_cb(self, totranslate):
        entry = totranslate.get_text()
        # Ask for completion suggestions
        if not entry:
            return
        
        (list1, list2) = self.languagemodel.GetSuggestions(entry)
        self.lang1model.clear()
        self.lang2model.clear()
        for x in list1:
            self.lang1model.append([x])
        for x in list2:
            self.lang2model.append([x])

        # If we think we know what the word will be, translate it.
        if entry in list1 or len(list1) == 1 and len(list2) == 0:
            langiter = self.lang2combo.get_active()
            lang = self.langs[langiter].lower()
            self.fromlang = "English"
            self.tolang   = lang
            translations = self.languagemodel.GetTranslations(0, list1[0])
            self.translated.set_text(",".join(translations))

        elif entry in list2 or len(list1) == 0 and len(list2) == 1:
            langiter = self.lang2combo.get_active()
            lang = self.langs[langiter].lower()
            self.fromlang = lang
            self.tolang   = "English"
            translations = self.languagemodel.GetTranslations(1, list2[0])
            self.translated.set_text(",".join(translations))
