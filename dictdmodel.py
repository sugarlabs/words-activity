import os
import dictdlib
import logging

lang_codes = {'afr': 'Afrikaans', 'ara': 'Arabic', 'deu': 'Deutsch',
              'eng': 'English', 'fra': 'French', 'hin': 'Hindi',
              'ita': 'Italian', 'por': 'Portuguese', 'spa': 'Spanish'}

espeak_voices = {'afr': 'afrikaans', 'ara': 'Farsi', 'deu': 'german',
                 'eng': 'english_rp', 'fra': 'french', 'hin': 'hindi',
                 'ita': 'italian', 'por': 'brazil', 'spa': 'spanish-latin-am'}


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
                logging.debug('Adding %s', file_name)

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

    def get_languages_from(self, lang):
        langs = []
        for dict_name in self.get_dictionaries_from(lang):
            lang_from = dict_name[4:]
            if lang_from not in langs:
                langs.append(lang_from)
        return sorted(langs)

    def get_languages_to(self, lang):
        langs = []
        for dict_name in self.get_dictionaries_to(lang):
            lang_to = dict_name[0:3]
            if lang_to not in langs:
                langs.append(lang_to)
        return sorted(langs)

    def get_all_languages_origin(self):
        langs = []
        for dict_name in self.get_dictionaries_from():
            lang = dict_name[0:3]
            if lang not in langs:
                langs.append(lang)
        return sorted(langs)


class Dictionary:

    def __init__(self, directory, from_lang, to_lang):
        self._db = dictdlib.DictDB("%s/%s-%s" %
                                   (directory, from_lang, to_lang))
        self._from_lang = from_lang
        self._to_lang = to_lang

    def get_definition(self, word):
        return self._db.getdef(word)

    def get_suggestions(self, word):
        return self._db.get_suggestions(word)

    def get_from_lang(self):
        return self._from_lang

    def get_to_lang(self):
        return self._to_lang


class EnglishDictionary:

    def __init__(self, database):
        self._db = dictdlib.DictDB(database)

    def get_definition(self, word):
        return self._db.getdef(word)

    def get_suggestions(self, word):
        word = word.lower()
        suggestions = []
        for key in self._db.getdeflist():
            if word in key:
                suggestions.append(key)
        return suggestions

# move to test

if __name__ == "__main__":

    dictionaries = Dictionaries('./dictd/')
    print('All languages from')
    print(dictionaries.get_all_languages_origin())
    print()

    print('Get languages to English')
    print(dictionaries.get_languages_to('eng'))
    print()

    print('Dictionaries from English')
    print(dictionaries.get_dictionaries_from('eng'))

    print('Languages from English')
    print(dictionaries.get_languages_from('eng'))

    print('Dictionaries from Spanish')
    print(dictionaries.get_dictionaries_from('spa'))
    print()

    print('Languages from Spanish')
    print(dictionaries.get_languages_from('spa'))
    print()

    print('Dictionaries to English')
    print(dictionaries.get_dictionaries_to('eng'))
    print('Dictionaries to Spanish')
    print(dictionaries.get_dictionaries_to('spa'))
    print()

    dictionary = Dictionary('./dictd/', 'eng', 'spa')
    print('Translation from English to Spanish word "out"')
    print(dictionary.get_definition('out'))
    print()

    print('Translation from English to Spanish word "box"')
    print(dictionary.get_definition('box'))
