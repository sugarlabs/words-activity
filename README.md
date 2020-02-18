What is this?
=============
Words activity is a multilingual dictionary activity for the Sugar environment.

How to use?
===========
Words activity is relatively easy to use. There are four text boxes;
one for typing text, one gives synonyms, one gives you the translated
text, and the last gives you the meaning of the translated text.

How to upgrade?
===============
On sugar desktop systems;
* use [My settings](https://help.sugarlabs.org/my_settings.html), [Software update](https://help.sugarlabs.org/my_settings.html#software-update), or;
* use Browse to open [activities.sugarlabs.org](activities.sugarlabs.org) and search for `Words` and download.

How to develop?
===============

* Setup a development environment for Sugar desktop,
* Clone this repository,
* Edit source files,
* Test in the Terminal by typing `sugar-activity3`,
* Test in Sugar by starting the activity from the Home View.

Use dictionaries in dictd format. Is possible to add more languages
without need to modify the activity.  The dictionaries were downloaded
from [FreeDict](https://freedict.org/). A few were selected, but
more can added.  The options in the toolbar buttons are updated based
on the available dictionaries.  Also added the [GCIDE English
dictionary](https://en.wikipedia.org/wiki/GCIDE).  When available, a
definition of the english word will be displayed.
