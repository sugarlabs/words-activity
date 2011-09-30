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

import gtk
import logging
import pango
import os
import subprocess

from gettext import gettext as _

from sugar.activity import activity
from sugar.activity.activity import ActivityToolbox, \
     get_bundle_path, get_bundle_name

from sugar.graphics.icon import Icon
OLD_TOOLBARS = False
try:
    from sugar.graphics.toolbarbox import ToolbarBox, ToolbarButton
    from sugar.activity.widgets import ActivityButton, StopButton, \
                                        ShareButton, KeepButton, TitleEntry
except ImportError:
    OLD_TOOLBARS = True

# logging
logger = logging.getLogger('Words')


class WordsActivity(activity.Activity):
    """Words Activity as specified in activity.info"""

    def __init__(self, handle):
        """Set up the Words activity."""
        super(WordsActivity, self).__init__(handle)
        self._logger = logging.getLogger('words-activity')

        # Instantiate a language model.
        # FIXME: We should ask the language model what langs it supports.
        self.langs = ["French", "German", "Italian", "Portuguese", "Spanish"]
        # Initial values | Valores iniciales
        self.fromlang = "English"
        self.tolang   = "Spanish"
        import LanguageModel
        self.languagemodel = LanguageModel.LanguageModel()

        # We do not have collaboration features | No tenemos caracteristicas de colaboracion
        # make the share option insensitive | haciendo la opcion de compartir insensible
        self.max_participants = 1

        # Main layout | disposicion general 
        hbox = gtk.HBox(homogeneous=True, spacing=8)
        vbox = gtk.VBox(spacing=16)
        vbox.set_border_width(16)

        # Toolbar (compatibility with old-toolbars) | Toolbar, compatibilidad con barras anteriores
        if not OLD_TOOLBARS:
            toolbar_box = ToolbarBox()
            activity_button = ActivityButton(self)
            toolbar_box.toolbar.insert(activity_button, 0)
            activity_button.show()
            
            title_entry = TitleEntry(self)
            toolbar_box.toolbar.insert(title_entry, -1)
            title_entry.show()

            share_button = ShareButton(self)
            toolbar_box.toolbar.insert(share_button, -1)
            share_button.show()

            separator = gtk.SeparatorToolItem()
            separator.props.draw = False
            separator.set_expand(True)
            toolbar_box.toolbar.insert(separator, -1)
            separator.show()

            stop_button = StopButton(self)
            toolbar_box.toolbar.insert(stop_button, -1)
            stop_button.show()

            self.set_toolbox(toolbar_box)
            toolbar_box.show()
        else:
            toolbox = ActivityToolbox(self)
            self.set_toolbox(toolbox)
            toolbox.show()

        # transbox: <label> - <text entry> - <speak button>
        transbox = gtk.Table()
        transbox.resize(2, 3)
        transbox.set_row_spacings(8)
        transbox.set_col_spacings(12)

        # Labels | Etiquetas
        label1 = gtk.Label(_("Word") + ':')
        label1.set_alignment(xalign=0.0, yalign=0.5)
        label2 = gtk.Label(_("Translation") + ':')
        label2.set_alignment(xalign=0.0, yalign=0.5)
        
        # Text entry box to enter word to be translated.| caja para colocar la palabra que se va a traducir
        self.totranslate = gtk.Entry(max=50)
        self.totranslate.connect("changed", self.totranslate_cb)
        self.totranslate.modify_font(pango.FontDescription("Sans 14"))
        
        # Text entry box to receive word translated.| caja para recibir la palabra que se va a traducir
        self.translated = gtk.Entry(max=50)
        self.translated.set_property('editable', False)
        self.translated.modify_font(pango.FontDescription("Sans 14"))

        # Speak buttons.| Botones para hablar.
        speak1 = gtk.ToolButton()
        speak_icon1 = Icon(icon_name='microphone')
        speak1.set_icon_widget(speak_icon1)
        speak1.connect("clicked", self.speak1_cb)
        speak2 = gtk.ToolButton()
        speak_icon2 = Icon(icon_name='microphone')
        speak2.set_icon_widget(speak_icon2)
        speak2.connect("clicked", self.speak2_cb)
        
        transbox.attach(label1, 0, 1, 0, 1, xoptions=gtk.FILL)
        transbox.attach(self.totranslate, 1, 2, 0, 1, xoptions=gtk.FILL|gtk.EXPAND)
        transbox.attach(speak1, 2, 3, 0, 1, xoptions=gtk.FILL)

        transbox.attach(label2, 0, 1, 1, 2, xoptions=gtk.FILL)
        transbox.attach(self.translated, 1, 2, 1, 2, xoptions=gtk.FILL|gtk.EXPAND)
        transbox.attach(speak2, 2, 3, 1, 2, xoptions=gtk.FILL)

        vbox.pack_start(transbox, expand=False)

        # The language choice combo boxes. | Las cajas para escoger opciones de lenguaje
        self.lang1combo = gtk.combo_box_new_text()
        self.lang1combo.append_text("English")
        self.lang1combo.connect("changed", self.lang1combo_cb)
        self.lang1combo.set_active(0)

        self.lang2combo = gtk.combo_box_new_text()
        for x in self.langs:
            self.lang2combo.append_text(x)
        self.lang2combo.connect("changed", self.lang2combo_cb)
        self.lang2combo.set_active(4)
        
        self.lang1combo.set_size_request(600,50)
        self.lang2combo.set_size_request(600,50)

        # The "lang1" treeview box
        self.lang1model = gtk.ListStore(str)
        lang1view = gtk.TreeView(self.lang1model)
        lang1view.set_headers_visible(False)
        lang1cell = gtk.CellRendererText()
        lang1treecol = gtk.TreeViewColumn("", lang1cell, text=0)
        lang1view.get_selection().connect("changed", self.lang1sel_cb)
        lang1view.append_column(lang1treecol)
        lang1scroll = gtk.ScrolledWindow(hadjustment=None, vadjustment=None)
        lang1scroll.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        lang1scroll.add(lang1view)

        # The "lang2" box
        self.lang2model = gtk.ListStore(str)
        lang2view = gtk.TreeView(self.lang2model)
        lang2view.set_headers_visible(False)
        lang2cell = gtk.CellRendererText()
        lang2treecol = gtk.TreeViewColumn("", lang2cell, text=0)
        lang2view.get_selection().connect("changed", self.lang2sel_cb)
        lang2view.append_column(lang2treecol)
        lang2scroll = gtk.ScrolledWindow(hadjustment=None, vadjustment=None)
        lang2scroll.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        lang2scroll.add(lang2view)

        lang1_vbox = gtk.VBox(spacing=8)
        lang1_vbox.pack_start(self.lang1combo, expand=False)
        lang1_vbox.pack_start(lang1scroll)

        lang2_vbox = gtk.VBox(spacing=8)
        lang2_vbox.pack_start(self.lang2combo, expand=False)
        lang2_vbox.pack_start(lang2scroll)

        hbox.pack_start(lang1_vbox)
        hbox.pack_start(lang2_vbox)

        vbox.pack_start(hbox)
        self.set_canvas(vbox)
        self.totranslate.grab_focus()
        self.show_all()

    def say(self, text, lang):
        # No Portuguese accent yet.
        if lang == "portuguese":
            lang = "spanish"
        tmpfile = "/tmp/something.wav"
        subprocess.call(["espeak", text, "-w", tmpfile, "-v", lang])
        subprocess.call(["aplay", tmpfile])
        os.unlink(tmpfile)

    def lang1combo_cb(self, combo):
        pass

    def lang2combo_cb(self, combo):
        self.languagemodel.SetLanguages("English", self.langs[combo.get_active()])
        
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