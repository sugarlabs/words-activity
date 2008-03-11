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
import gtk
import logging
import pango
import re, os, os.path
import subprocess

from gettext import gettext as _
from dbus.service import method, signal

from activity import ViewSourceActivity
from sugar.activity.activity import ActivityToolbox, \
     get_bundle_path, get_bundle_name

SERVICE = "org.laptop.Words"
IFACE = SERVICE
PATH = "/org/laptop/Words"

class WordsActivity(ViewSourceActivity):
    """Words Activity as specified in activity.info"""
    def __init__(self, handle):
        """Set up the Words activity."""
        super(WordsActivity, self).__init__(handle)
        self._logger = logging.getLogger('words-activity')

        from sugar.graphics.menuitem import MenuItem
        from sugar.graphics.icon import Icon

        # Instantiate a language model.
        # FIXME: We should ask the language model what langs it supports.
        self.langs = ["French", "German", "Italian", "Portuguese", "Spanish"]
        # Initial values.
        self.fromlang = "English"
        self.tolang   = "Spanish"
        import LanguageModel
        self.languagemodel = LanguageModel.LanguageModel()

        # Main layout.
        hbox = gtk.HBox(homogeneous=True)
        vbox = gtk.VBox()

        # Toolbar.
        toolbox = ActivityToolbox(self)
        self.set_toolbox(toolbox)
        toolbox.show()

        # transbox: <label> - <text entry> - <speak button>
        transbox1 = gtk.HBox()
        transbox2 = gtk.HBox()

        # Labels.
        label1 = gtk.Label("Word to translate")
        label2 = gtk.Label("Translation")
        
        # Text entry box to enter word to be translated.
        self.totranslate = gtk.Entry(max=50)
        self.totranslate.connect("changed", self.totranslate_cb)
        self.totranslate.modify_font(pango.FontDescription("Sans 14"))
        
        # Text entry box to receive word translated.
        self.translated = gtk.Entry(max=50)
        self.translated.set_property('editable', False)
        self.translated.modify_font(pango.FontDescription("Sans 14"))

        # Speak buttons.
        speak1 = gtk.Button("Speak")
        speak1.connect("clicked", self.speak1_cb)
        speak2 = gtk.Button("Speak")
        speak2.connect("clicked", self.speak2_cb)
        
        transbox1.pack_start(label1, expand=False)
        transbox1.pack_start(self.totranslate)
        transbox1.pack_start(speak1, expand=False)

        transbox2.pack_start(label2, expand=False)
        transbox2.pack_start(self.translated)
        transbox2.pack_start(speak2, expand=False)

        vbox.pack_start(transbox1, expand=False)
        vbox.pack_start(transbox2, expand=False) 

        # The language choice combo boxes.
        combohbox = gtk.HBox(homogeneous=True)
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
        combohbox.pack_start(self.lang1combo, expand=False)
        combohbox.pack_start(self.lang2combo, expand=False)
        vbox.pack_start(combohbox, expand=False)

        # The "lang1" treeview box
        self.lang1model = gtk.ListStore(str)
        lang1view = gtk.TreeView(self.lang1model)
        lang1cell = gtk.CellRendererText()
        lang1treecol = gtk.TreeViewColumn("", lang1cell, text=0)
        lang1view.get_selection().connect("changed", self.lang1sel_cb)
        lang1view.append_column(lang1treecol)

        # The "lang2" box
        self.lang2model = gtk.ListStore(str)
        lang2view = gtk.TreeView(self.lang2model)
        lang2cell = gtk.CellRendererText()
        lang2treecol = gtk.TreeViewColumn("", lang2cell, text=0)
        lang2view.get_selection().connect("changed", self.lang2sel_cb)
        lang2view.append_column(lang2treecol)

        hbox.pack_start(lang1view)
        hbox.pack_start(lang2view)

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
            
############# TEMPLATES AND INLINE FILES ##############
ACTIVITY_INFO_TEMPLATE = """
[Activity]
name = %(title)s
bundle_id = %(bundle_id)s
service_name = %(bundle_id)s
class = %(class)s
icon = activity-icon
activity_version = %(version)d
mime_types = %(mime_types)s
show_launcher = yes
%(extra_info)s
"""

PIPPY_ICON = \
"""<?xml version="1.0" ?><!DOCTYPE svg  PUBLIC '-//W3C//DTD SVG 1.1//EN'  'http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd' [
	<!ENTITY stroke_color "#010101">
	<!ENTITY fill_color "#FFFFFF">
]><svg enable-background="new 0 0 55 55" height="55px" version="1.1" viewBox="0 0 55 55" width="55px" x="0px" xml:space="preserve" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" y="0px"><g display="block" id="activity-pippy">
	<path d="M28.497,48.507   c5.988,0,14.88-2.838,14.88-11.185c0-9.285-7.743-10.143-10.954-11.083c-3.549-0.799-5.913-1.914-6.055-3.455   c-0.243-2.642,1.158-3.671,3.946-3.671c0,0,6.632,3.664,12.266,0.74c1.588-0.823,4.432-4.668,4.432-7.32   c0-2.653-9.181-5.719-11.967-5.719c-2.788,0-5.159,3.847-5.159,3.847c-5.574,0-11.149,5.306-11.149,10.612   c0,5.305,5.333,9.455,11.707,10.612c2.963,0.469,5.441,2.22,4.878,5.438c-0.457,2.613-2.995,5.306-8.361,5.306   c-4.252,0-13.3-0.219-14.745-4.079c-0.929-2.486,0.168-5.205,1.562-5.205l-0.027-0.16c-1.42-0.158-5.548,0.16-5.548,5.465   C8.202,45.452,17.347,48.507,28.497,48.507z" fill="&fill_color;" stroke="&stroke_color;" stroke-linecap="round" stroke-linejoin="round" stroke-width="3.5"/>
	<path d="M42.579,19.854c-2.623-0.287-6.611-2-7.467-5.022" fill="none" stroke="&stroke_color;" stroke-linecap="round" stroke-width="3"/>
	<circle cx="35.805" cy="10.96" fill="&stroke_color;" r="1.676"/>
</g></svg><!-- " -->
"""

PIPPY_DEFAULT_ICON = \
"""<?xml version="1.0" ?><!DOCTYPE svg  PUBLIC '-//W3C//DTD SVG 1.1//EN'  'http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd' [
	<!ENTITY stroke_color "#010101">
	<!ENTITY fill_color "#FFFFFF">
]><svg enable-background="new 0 0 55 55" height="55px" version="1.1"
     viewBox="0 0 55 55" width="55px" x="0px" y="0px" xml:space="preserve"
     xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink"
><g display="block" id="activity-icon"><path
       d="M 28.497,48.507 C 34.485,48.507 43.377,45.669 43.377,37.322 C 43.377,32.6795 41.44125,30.14375 39.104125,28.651125 C 36.767,27.1585 38.482419,26.816027 39.758087,25.662766 C 39.42248,24.275242 37.206195,22.826987 36.262179,21.037968 C 34.005473,20.582994 27.526,19.113 30.314,19.113 C 30.314,19.113 36.946,22.777 42.58,19.853 C 44.168,19.03 47.012,15.185 47.012,12.533 C 47.012,9.88 37.831,6.814 35.045,6.814 C 32.257,6.814 29.886,10.661 29.886,10.661 C 24.312,10.661 12.043878,16.258005 12.043878,21.564005 C 12.043878,24.216505 16.585399,30.069973 19.144694,33.736352 C 22.438716,38.455279 27.257,31.3065 30.444,31.885 C 33.407,32.354 35.885,34.105 35.322,37.323 C 34.865,39.936 32.327,42.629 26.961,42.629 C 22.709,42.629 13.661,42.41 12.216,38.55 C 11.287,36.064 12.384,33.345 13.778,33.345 L 13.751,33.185 C 12.331,33.027 8.203,33.345 8.203,38.65 C 8.202,45.452 17.347,48.507 28.497,48.507 z "
 fill="&fill_color;" stroke="&stroke_color;" stroke-linecap="round" stroke-linejoin="round" stroke-width="3.5" />
	<path d="M42.579,19.854c-2.623-0.287-6.611-2-7.467-5.022" fill="none" stroke="&stroke_color;" stroke-linecap="round" stroke-width="3"/>
	<circle cx="35.805" cy="10.96" fill="&stroke_color;" r="1.676"/>
</g></svg><!-- " -->
"""

############# ACTIVITY META-INFORMATION ###############
# this is used by Words to generate a bundle for itself.

def pippy_activity_version():
    """Returns the version number of the generated activity bundle."""
    return 1
def pippy_activity_extra_files():
    """Returns a map of 'extra' files which should be included in the
    generated activity bundle."""
    # Cheat here and generate the map from the fs contents.
    extra = {}
    bp = get_bundle_path()
    for d in [ 'po', 'data' ]: # everybody gets library already
        for root, dirs, files in os.walk(os.path.join(bp, d)):
            for name in files:
                fn = os.path.join(root, name).replace(bp+'/', '')
                extra[fn] = open(os.path.join(root, name), 'r').read()
    extra['activity/activity-default.svg'] = PIPPY_DEFAULT_ICON
    return extra
def pippy_activity_news():
    """Return the NEWS file for this activity."""
    # Cheat again.
    return open(os.path.join(get_bundle_path(), 'NEWS')).read()
def pippy_activity_icon():
    """Return an SVG document specifying the icon for this activity."""
    return PIPPY_ICON
def pippy_activity_class():
    """Return the class which should be started to run this activity."""
    return 'pippy_app.WordsActivity'
def pippy_activity_bundle_id():
    """Return the bundle_id for the generated activity."""
    return 'org.laptop.Words'
def pippy_activity_mime_types():
    """Return the mime types handled by the generated activity, as a list."""
    return 'text/x-python'
