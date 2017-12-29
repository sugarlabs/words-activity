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

import gi
gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.0')
gi.require_version('Gst', '1.0')

from gi.repository import GObject
GObject.threads_init()
from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import Pango
from gi.repository import WebKit2 as WebKit


import logging
import os
import re
import json

from gettext import gettext as _

from sugar3.activity import activity
from sugar3.graphics.icon import Icon
from sugar3.graphics import iconentry
from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.activity.widgets import ActivityToolbarButton
from sugar3.activity.widgets import StopButton
from sugar3.graphics import style
from sugar3.graphics.palettemenu import PaletteMenuItem
from sugar3.graphics.palette import Palette
from sugar3.graphics.palette import ToolInvoker
from sugar3.graphics.alert import ErrorAlert

import dictdmodel
from roundbox import RoundBox
from speech import get_speech_manager

EMPTY_HTML = '<body bgcolor="#E5E5E5"></body>'
_AUTOSEARCH_TIMEOUT = 1000

def save_to_debug(methods_list):
    print(type(methods_list))
    if type(methods_list) is list:
        with open('index.txt', 'a') as file:
            for method in methods_list:
                file.write(method + '\n')
    else:
        with open('index.txt', 'a') as file:
                file.write(methods_list + '\n')

class FilterToolItem(Gtk.ToolButton):

    _LABEL_MAX_WIDTH = 18
    _MAXIMUM_PALETTE_COLUMNS = 4

    __gsignals__ = {
        'changed': (GObject.SignalFlags.RUN_LAST, None, ([str])), }

    def __init__(self, default_icon, default_value, options):
        self._palette_invoker = ToolInvoker()
        self._options = options
        Gtk.ToolButton.__init__(self)
        logging.debug('filter options %s', options)
        self._value = default_value
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

        self.palette = Palette(_('Select language'))
        self.palette.set_invoker(self._palette_invoker)

        self.props.palette.set_content(self.set_palette_list(options))

    def set_options(self, options):
        self._options = options
        self.palette = Palette(_('Select language'))
        self.palette.set_invoker(self._palette_invoker)
        self.props.palette.set_content(self.set_palette_list(options))
        if self._value not in self._options.keys():
            new_value = self._options.keys()[0]
            self._value = new_value
            self._set_widget_label(self._options[new_value])
            self.emit('changed', new_value)

    def set_widget_icon(self, icon_name=None):
        icon = Icon(icon_name=icon_name,
                    pixel_size=style.SMALL_ICON_SIZE)
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

            menu_item.connect('button-release-event', self._option_selected,
                              key)
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
        self._value = key
        self.emit('changed', key)


class WordsActivity(activity.Activity):
    """Words Activity as specified in activity.info"""

    def __init__(self, handle):
        """Set up the Words activity."""
        activity.Activity.__init__(self, handle)

        self._dictd_data_dir = './dictd/'
        self._dictionaries = dictdmodel.Dictionaries(self._dictd_data_dir)

        self._origin_languages = self._dictionaries.get_all_languages_origin()
        self._origin_lang_options = {}
        for lang in self._origin_languages:
            self._origin_lang_options[lang] = dictdmodel.lang_codes[lang]

        self.max_participants = 1

        toolbar_box = ToolbarBox()

        activity_button = ActivityToolbarButton(self)
        toolbar_box.toolbar.insert(activity_button, 0)
        toolbar_box.toolbar.set_style(Gtk.ToolbarStyle.BOTH_HORIZ)
        activity_button.show()

        toolbar_box.toolbar.insert(Gtk.SeparatorToolItem(), -1)

        from_toolitem = Gtk.ToolItem()
        from_toolitem.add(Gtk.Label(_('From:')))
        from_toolitem.show_all()
        toolbar_box.toolbar.insert(from_toolitem, -1)

        if 'origin' in self.metadata:
            origin = self.metadata['origin']
        else:
            origin = 'eng'

        if 'destination' in self.metadata:
            destination = self.metadata['destination']
        else:
            destination = 'spa'

        if 'searches' in self.metadata:
            self._searches = json.loads(self.metadata['searches'])
        else:
            self._searches = {}

        # Initial values | Valores iniciales
        self.origin_lang = origin
        self.destination_lang = destination
        self._dictionary = dictdmodel.Dictionary(self._dictd_data_dir,
                                                 self.origin_lang,
                                                 self.destination_lang)

        self._autosearch_timer = None
        self._english_dictionary = None

        self._alert = ErrorAlert()
        self._alert.props.title = _('Wait...')
        self._alert.props.msg = _('Loading dictionary data')
        self.add_alert(self._alert)
        self._alert.connect('response', self._alert_cancel_cb)
        self._alert.show()

        GObject.idle_add(self._init_english_dictionary)
        self._last_word_translated = None

        self._from_button = FilterToolItem('go-down',
                                           origin,
                                           self._origin_lang_options)
        self._from_button.connect("changed", self.__from_language_changed_cb)
        toolbar_box.toolbar.insert(self._from_button, -1)

        to_toolitem = Gtk.ToolItem()
        to_toolitem.add(Gtk.Label('    ' + _('To:')))
        to_toolitem.show_all()
        toolbar_box.toolbar.insert(to_toolitem, -1)

        self._init_destination_language()
        self._to_button = FilterToolItem('go-down',
                                         self.destination_lang,
                                         self._destination_lang_options)
        self._to_button.connect("changed", self.__to_language_changed_cb)
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

        font_size = int(style.FONT_SIZE * 1.5)
        font = Pango.FontDescription("Sans %d" % font_size)

        # This box will change the orientaion when the screen rotates
        self._big_box = Gtk.Box(Gtk.Orientation.HORIZONTAL)
        self._big_box.set_homogeneous(True)
        self._big_box.set_margin_top(style.DEFAULT_SPACING)
        self._big_box.set_margin_bottom(style.DEFAULT_SPACING)

        lang1_container = Gtk.Grid()
        lang1_container.set_row_spacing(style.DEFAULT_SPACING)
        lang1_container.set_border_width(style.DEFAULT_SPACING)

        lang1_round_box = RoundBox()
        lang1_round_box.background_color = style.COLOR_BUTTON_GREY
        lang1_round_box.border_color = style.COLOR_BUTTON_GREY

        lang1_round_box.pack_start(lang1_container, True, True,
                                   style.DEFAULT_SPACING)

        self._big_box.pack_start(lang1_round_box, True, True, 0)

        # Labels
        label1 = Gtk.Label()
        label1.set_markup('<span font="%d" color="white">%s</span>' %
                          (font_size, _("Word")))
        label1.set_halign(Gtk.Align.START)
        lang1_container.attach(label1, 0, 0, 1, 1)

        speak1 = Gtk.ToolButton()
        speak1.set_icon_widget(Icon(icon_name='microphone'))
        speak1.set_halign(Gtk.Align.END)
        speak1.connect("clicked", self.__speak_word_cb)
        lang1_container.attach(speak1, 1, 0, 1, 1)

        # Text entry box to enter word to be translated
        self.totranslate = iconentry.IconEntry()
        self.totranslate.set_icon_from_name(iconentry.ICON_ENTRY_PRIMARY,
                                            'entry-search')
        # self.search_entry.set_placeholder_text(text)
        self.totranslate.add_clear_button()

        self.totranslate.connect('activate', self.__totranslate_activated_cb)
        self._totranslate_changed_id = self.totranslate.connect(
            "changed", self.__totranslate_changed_cb)
        self.totranslate.modify_font(font)
        self.totranslate.set_hexpand(True)

        lang1_container.attach(self.totranslate, 0, 1, 2, 1)

        label1 = Gtk.Label()
        label1.set_markup('<span font="%d" color="white">%s</span>' %
                          (font_size, _("Suggestions")))
        label1.set_halign(Gtk.Align.START)
        lang1_container.attach(label1, 0, 2, 2, 1)

        # The "lang1" treeview box
        self._suggestions_model = Gtk.ListStore(str)
        suggest_treeview = Gtk.TreeView(self._suggestions_model)
        suggest_treeview.modify_font(font)
        suggest_treeview.set_enable_search(False)

        suggest_treeview.set_headers_visible(False)
        lang1cell = Gtk.CellRendererText()
        lang1cell.props.ellipsize_set = True
        lang1cell.props.ellipsize = Pango.EllipsizeMode.END
        lang1treecol = Gtk.TreeViewColumn("", lang1cell, text=0)
        self._suggestion_changed_cb_id = suggest_treeview.connect(
            'cursor-changed', self.__suggestion_selected_cb)
        suggest_treeview.append_column(lang1treecol)
        scroll = Gtk.ScrolledWindow(hadjustment=None, vadjustment=None)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add(suggest_treeview)
        scroll.set_vexpand(True)
        lang1_container.attach(scroll, 0, 3, 2, 1)

        # This container have the result data
        result_container = Gtk.Grid()
        result_container.set_row_spacing(style.DEFAULT_SPACING)
        result_container.set_border_width(style.DEFAULT_SPACING)

        lang2_round_box = RoundBox()
        lang2_round_box.background_color = style.COLOR_BUTTON_GREY
        lang2_round_box.border_color = style.COLOR_BUTTON_GREY

        lang2_round_box.pack_start(result_container, True, True,
                                   style.DEFAULT_SPACING)

        self._big_box.pack_start(lang2_round_box, True, True, 0)

        # Text entry box to receive word translated

        label = Gtk.Label()
        label.set_markup('<span font="%d" color="white">%s</span>' %
                         (font_size, _("Translation")))
        label.set_halign(Gtk.Align.START)
        result_container.attach(label, 0, 0, 1, 1)

        speak2 = Gtk.ToolButton()
        speak2.set_icon_widget(Icon(icon_name='microphone'))
        speak2.set_halign(Gtk.Align.END)
        speak2.connect("clicked", self.__speak_translation_cb)
        result_container.attach(speak2, 1, 0, 1, 1)

        self.translated = Gtk.TextView()
        self.translated.modify_font(font)
        self.translated.set_buffer(Gtk.TextBuffer())
        self.translated.set_left_margin(style.DEFAULT_PADDING)
        self.translated.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.translated.set_editable(False)
        self.translated.modify_bg(
            Gtk.StateType.NORMAL, style.COLOR_TEXT_FIELD_GREY.get_gdk_color())
        self.translated.modify_bg(
            Gtk.StateType.SELECTED, style.COLOR_SELECTION_GREY.get_gdk_color())

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC,
                            Gtk.PolicyType.AUTOMATIC)
        scrolled.add(self.translated)
        scrolled.set_hexpand(True)
        scrolled.set_size_request(-1, style.GRID_CELL_SIZE * 2)

        result_container.attach(scrolled, 0, 1, 2, 1)

        label = Gtk.Label()
        label.set_markup('<span font="%d" color="white">%s</span>' %
                         (font_size, _("Dictionary")))
        label.set_halign(Gtk.Align.START)
        result_container.attach(label, 0, 2, 1, 1)

        speak2 = Gtk.ToolButton()
        speak2.set_icon_widget(Icon(icon_name='microphone'))
        speak2.set_halign(Gtk.Align.END)
        speak2.connect("clicked", self.__speak_dictionary_cb)
        result_container.attach(speak2, 1, 2, 1, 1)
        self.dictionary = WebKit.WebView()
        self.dictionary.load_html(EMPTY_HTML, 'file:///')
        self.dictionary.set_zoom_level(0.75)
        # Removes right-click context menu
        self.dictionary.connect("button-press-event", lambda w, e: e.button == 3)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC,
                            Gtk.PolicyType.AUTOMATIC)
        scrolled.add(self.dictionary)
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)

        result_container.attach(scrolled, 0, 3, 2, 1)

        self._big_box.show_all()
        self.set_canvas(self._big_box)
        self.totranslate.grab_focus()
        self.show_all()

    def write_file(self, file_path):
        ''' Write the project to the Journal. '''
        self.metadata['origin'] = self.origin_lang
        self.metadata['destination'] = self.destination_lang
        self.metadata['searches'] = json.dumps(self._searches)

    def _init_english_dictionary(self):
        # the english_dictionary is fixed, if we add more,
        # can generalize the code
        if os.path.exists('./dictd-en/hEnglish___advanced_version.dict'):
            self._english_dictionary = dictdmodel.EnglishDictionary(
                './dictd-en/hEnglish___advanced_version')
        if self._alert is not None:
            self.remove_alert(self._alert)
            self._alert = None

    def _alert_cancel_cb(self, alert, response_id):
        pass

    def __from_language_changed_cb(self, widget, value):
        logging.debug('selected translate from %s', value)
        self.origin_lang = value
        self._init_destination_language()
        logging.debug('destination languages %s',
                      self._destination_lang_options)
        self._to_button.set_options(self._destination_lang_options)
        self._translate()

    def __to_language_changed_cb(self, widget, value):
        logging.debug('selected translate to %s', value)
        self.destination_lang = value
        self._translate()

    def _init_destination_language(self):
        destination_languages = self._dictionaries.get_languages_from(
            self.origin_lang)
        self._destination_lang_options = {}
        for lang in destination_languages:
            self._destination_lang_options[lang] = dictdmodel.lang_codes[lang]

    def _say(self, text, lang):
        speech_manager = get_speech_manager()
        if speech_manager.get_is_playing():
            speech_manager.stop()
        else:
            speech_manager.say_text(text, dictdmodel.espeak_voices[lang])

    def __suggestion_selected_cb(self, treeview):
        selection = treeview.get_selection()
        if selection is None:
            return
        model, treeiter = selection.get_selected()
        if treeiter is not None:
            value = model.get_value(treeiter, 0)
            treeview.handler_block(self._suggestion_changed_cb_id)
            self.totranslate.handler_block(self._totranslate_changed_id)
            if self._autosearch_timer:
                GObject.source_remove(self._autosearch_timer)
            self.totranslate.set_text(value)
            self._translate(inmediate_suggestions=True)
            self.totranslate.handler_unblock(self._totranslate_changed_id)
            treeview.handler_unblock(self._suggestion_changed_cb_id)

    def lang2sel_cb(self, column):
        model, _iter = column.get_selected()
        value = model.get_value(_iter, 0)
        translations = self.languagemodel.GetTranslations(1, value)
        self.translated.set_text(",".join(translations))

    def __speak_word_cb(self, button):
        text = self.totranslate.get_text()
        lang = self.origin_lang
        self._say(text, lang)

    def __speak_translation_cb(self, button):
        translated_buffer = self.translated.get_buffer()
        bounds = translated_buffer.get_bounds()
        text = translated_buffer.get_text(
            bounds[0], bounds[1], include_hidden_chars=False)
        # remove the lines with the english definition
        clean_text = ''
        logging.debug('text %s', text)
        for line in text.split('\n'):
            if len(line) > 0 and line[0] in (' ', '\t'):
                clean_text += line + ','
        # remove text between []
        clean_text = re.sub('\[.*?\]', '', clean_text)
        # remove text between <>
        clean_text = re.sub('<.*?>', '', clean_text)
        lang = self.destination_lang
        logging.debug('play %s (lang %s)', clean_text, lang)
        self._say(clean_text, lang)

    def __speak_dictionary_cb(self, button):
        # remove text between <>
        clean_text = re.sub('<.*?>', '', self._html_definition)
        # remove text between []
        clean_text = re.sub('\[.*?\]', '', clean_text)
        # remove text between \\
        clean_text = re.sub('\\\\.*?\\\\', '', clean_text)

        lang = self.origin_lang
        self._say(clean_text, lang)

    def __totranslate_changed_cb(self, totranslate):
        if self._autosearch_timer:
            GObject.source_remove(self._autosearch_timer)
        self._autosearch_timer = GObject.timeout_add(_AUTOSEARCH_TIMEOUT,
                                                     self._autosearch_timer_cb)

    def __totranslate_activated_cb(self, totranslate):
        if self._autosearch_timer:
            GObject.source_remove(self._autosearch_timer)
        self._translate()

    def _autosearch_timer_cb(self):
        logging.debug('_autosearch_timer_cb')
        self._autosearch_timer = None
        self._translate()
        return False

    def _translate(self, inmediate_suggestions=False):
        text = self.totranslate.get_text().lower()
        if not text:
            self._suggestions_model.clear()
            self.translated.get_buffer().set_text('')
            self._html_definition = ''
            self.dictionary.load_html(EMPTY_HTML, 'file:///')
            return

        # verify if the languagemodel is right
        if self._dictionary.get_from_lang() != self.origin_lang or \
                self._dictionary.get_to_lang() != self.destination_lang:
            self._dictionary = dictdmodel.Dictionary(self._dictd_data_dir,
                                                     self.origin_lang,
                                                     self.destination_lang)

        translations = self._dictionary.get_definition(text)

        if translations:
            self.translated.get_buffer().set_text(''.join(translations))
        else:
            self.translated.get_buffer().set_text('')

        if inmediate_suggestions:
            self._get_suggestions(text)
        else:
            GObject.idle_add(self._get_suggestions, text)

        # the word can be the same because changed the language pair
        if self._last_word_translated == text:
            return

        # register the search to save in the metadata
        lang_pair = '%s-%s' % (self.origin_lang, self.destination_lang)
        if lang_pair in self._searches:
            self._searches[lang_pair] = self._searches[lang_pair] + 1
        else:
            self._searches[lang_pair] = 1

        self._last_word_translated = text

        GObject.idle_add(self._get_definition, text)

    def _get_suggestions(self, text):
        # Ask for completion suggestions
        self._suggestions_model.clear()
        for x in self._dictionary.get_suggestions(text):
            self._suggestions_model.append([x])

    def _get_definition(self, text):
        self._html_definition = ''
        self.dictionary.load_html(EMPTY_HTML, 'file:///')
        if self.origin_lang == 'eng' and self._english_dictionary is not None:
            definition = self._english_dictionary.get_definition(text)
            if definition:
                html = ''.join(definition)
                # remove HR
                html = re.sub('<HR>', '', html)
                # remove links
                html = re.sub('<A.*?</A>', '', html)
                # set background color to #E5E5E5
                html = '<body bgcolor="#E5E5E5">' + html + '</body>'
                self._html_definition = html
                self.dictionary.load_html(html, 'file:///')
