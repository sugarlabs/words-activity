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

from __future__ import with_statement
import time
import os

def GetSupportedLanguages():
    ret = []
    files = os.listdir("lang/")
    for name in files:
        fn, ext = os.path.splitext(name)
        if ext == ".txt":
            ret.append(fn)
    ret.sort()
    return ret

class LanguageModel():

    def SetLanguages(self, lang1, lang2):
        """Take a language pair, prepare the language model."""
        self.lang1_lang2 = {}
        self.lang2_lang1 = {}
        self.translated = str()
        # Since we only have English->lang mappings, ignore lang1.
        filename = "lang/" + lang2 + ".txt"
        with open(filename, 'r') as f:
            for line in f.readlines():
                line = line.rstrip()
                if line.startswith("#"):
                    continue

                words_list = line.split('\t')
                if words_list[0] in self.lang1_lang2:
                    self.lang1_lang2 [ words_list[0].lower() ] += ", " + words_list[-1].lower()
                else:
                    self.lang1_lang2 [ words_list[0].lower() ] = words_list[-1].lower()
                    
                if words_list[-1] in self.lang2_lang1:
                    self.lang2_lang1 [ words_list[-1].lower() ] += ", " + words_list[0].lower()
                else:
                    self.lang2_lang1 [ words_list[-1].lower() ]  = words_list[0].lower()

    def GetSuggestions(self, string):
        """Take a string, provide two lists of possible each lang completions."""
        list_1 = [k for k in self.lang1_lang2.iterkeys() if k.startswith(string)]
        list_2 = [k for k in self.lang2_lang1.iterkeys() if (k.startswith(string) or k.rfind(" " + string) > -1)]
        return [sorted(list_1), sorted(list_2)]

    def GetTranslations(self, lang, string):
        """Take a word and lang (0 for first, 1 for second), provide a list 
        (empty allowed) of translations."""
        if lang == 0: # lang1 is source
            trans_list = [self.lang1_lang2[string]]
        elif lang == 1: # lang2 is source
            trans_list = [self.lang2_lang1[string]]
        else:
            raise AssertionError("lang must be 0 or 1")

        self.translated = string
        return trans_list

if __name__ == "__main__":
    a = LanguageModel()
    a.SetLanguages("English", "Spanish")
    print a.GetSuggestions("tru")
    print a.GetTranslations(0, "dog")
