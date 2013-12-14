#
# __linter__.py
# Linter for SublimeLinter3, a code checking framework for Sublime Text 3
#
# Written by __user__
# Copyright (c) __year__ __user__
#
# License: MIT
#

"""This module exports the __class__ plugin class."""

from SublimeLinter.lint import __superclass__


class __class__(__superclass__):

    """Provides an interface to __linter__."""

    language = '__language__'
    cmd = '__cmd__'
    executable = None
    regex = r''
    multiline = False
    line_col_base = (1, 1)
    tempfile_suffix = None
    selectors = {}
    word_re = None
    defaults = {}
    inline_settings = None
    inline_overrides = None
    __extra_attributes__