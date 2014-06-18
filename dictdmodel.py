import os
import dictdlib

lang_codes = {'afr': 'Afrikaans', 'ara': 'Arabic', 'deu': 'Deutch',
              'eng': 'English', 'fra': 'French', 'hin': 'Hindi',
              'ita': 'Italian', 'por': 'Portuguese', 'spa': 'Spanish'}


class Dictionaries:

    def __init__(self, directory):
        self._directory = directory
        self._dict_list = []
        self._read_available_data()
        # TODO: monitor directory

    def _read_available_data(self):
        self._dict_list = []
        for file_name in os.listdir(self._directory):
            if file_name.endswith('.dict.dz'):
                self._dict_list.append(file_name.split('.')[0])

    def get_dictionaries_from(self, lang=None):
        dictionaries = []
        for dict_name in self._dict_list:
            if lang is None or dict_name.startswith('%s-' % lang):
                dictionaries.append(dict_name)
        return dictionaries

    def get_dictionaries_to(self, lang=None):
        dictionaries = []
        for dict_name in self._dict_list:
            if lang is None or dict_name.endswith('-%s' % lang):
                dictionaries.append(dict_name)
        return dictionaries

    def get_languages_from(self):
        langs = []
        for dict_name in self.get_dictionaries_from():
            lang_from = dict_name[0:3]
            if not lang_from in langs:
                langs.append(lang_from)
        return sorted(langs)

    def get_languages_to(self, lang=None):
        langs = []
        for dict_name in self.get_dictionaries_to():
            lang_to = dict_name[4:]
            if not lang_to in langs:
                langs.append(lang_to)
        return sorted(langs)


class Dictionary:

    def __init__(self, database):
        """
        database = have the format 'spa-eng' (no extension)
        """
        self._db = dictdlib.DictDB(database)

    def get_definition(self, word):
        return self._db.getdef(word)

# move to test

if __name__ == "__main__":

    dictionaries = Dictionaries('./dictd/')
    print 'All languages from'
    print dictionaries.get_languages_from()
    print

    print 'All languages to'
    print dictionaries.get_languages_to()
    print

    print 'Dictionaries from English'
    print dictionaries.get_dictionaries_from('eng')
    print 'Dictionaries from Spanish'
    print dictionaries.get_dictionaries_from('spa')
    print

    print 'Dictionaries to English'
    print dictionaries.get_dictionaries_to('eng')
    print 'Dictionaries to Spanish'
    print dictionaries.get_dictionaries_to('spa')
    print

    dictionary = Dictionary('./dictd/eng-spa')
    print 'Translation from English to Spanish word "out"'
    print dictionary.get_definition('out')
    print

    print 'Translation from English to Spanish word "box"'
    print dictionary.get_definition('box')
