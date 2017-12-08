import sublime
from . import util, scheme
from xml.etree import ElementTree
from .persist import settings as merged_settings
from .const import SETTINGS_FILE

import re
import os
import shutil
import json
from time import sleep

COLOR_SCHEME_PREAMBLE = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
'''


def touch_dir(dir):
    if not os.path.exists(dir):
        os.makedirs(dir)


class XmlScheme(scheme.Scheme):
    def generate_color_scheme_async(self):
        """
            Generate a modified copy of the current color scheme that contains
            SublimeLinter color entries.

            The current color scheme is checked for SublimeLinter color entries.
            If any are missing, the scheme is copied, the entries are added,
            and the color scheme is rewritten to Packages/User/SublimeLinter.
        """
        # build legacy style_parser
        from . import persist
        persist.linter_styles["default"] = {
            "types": {
                "warning": "sublimelinter.mark.warning",
                "error": "sublimelinter.mark.error"
            }
        }

        def get_mark_style():
            mark_style = persist.settings.get("mark_style", "outline")
            return re.sub(" ", "_", mark_style)

        persist.highlight_styles = {
            "sublimelinter.mark.warning": {
                "scope": "sublimelinter.mark.warning",
                "mark_style": get_mark_style(),
                "icon": persist.gutter_marks["warning"]
            },
            "sublimelinter.mark.error": {
                "scope": "sublimelinter.mark.error",
                "mark_style": get_mark_style(),
                "icon": persist.gutter_marks["error"]
            }
        }

        # Append style dicts with our styles to the style array
        scheme_text = sublime.load_resource(self.paths["scheme_orig"])
        plist = ElementTree.XML(scheme_text)
        styles = plist.find('./dict/array')

        unfound = self.parse_scheme_xml(
            persist.highlight_styles, text=scheme_text)
        if not unfound:
            return

        # create unfound styles
        xml_nodes = self.gen_xml_nodes(unfound)
        styles.extend(xml_nodes)

        mod_name = self.paths["scheme_name"] + ' (SL)'
        mod_scheme_path = os.path.join(self.paths["usr_dir_abs"],
                                       mod_name + '.hidden-tmTheme')

        content = ElementTree.tostring(plist, encoding='unicode')

        touch_dir(self.paths["usr_dir_abs"])  # ensure dir exists
        with open(mod_scheme_path, 'w', encoding='utf8') as f:
            f.write(COLOR_SCHEME_PREAMBLE + content)

        # Set the amended color scheme to the current color scheme
        scheme_path_rel = self.packages_relative_path(
            os.path.join(self.paths["usr_dir_rel"],
                         os.path.basename(mod_scheme_path)))

        self.set_scheme_path(scheme_path_rel)

    def gen_xml_nodes(self, unfound):
        nodes = []

        def get_color(key, default):
            color = merged_settings.get(key, default)
            if not color.startswith('#'):
                color = '#' + color
            return color

        d = [{
            "scope": "sublimelinter.mark.warning",
            "foreground": get_color("warning_color", "#DDB700")
        }, {
            "scope": "sublimelinter.mark.error",
            "foreground": get_color("error_color", "#D02000")
        }, {
            "scope": "sublimelinter.gutter-mark",
            "foreground": "#FFFFFF"
        }]

        filtered = [f for f in d if f["scope"] in unfound]

        for item in filtered:
            nodes.append(self.assemble_node(item["scope"], item))

        return nodes

    def assemble_node(self, scope, input_dict):
        """Assembles single node as XML ElementTree object."""
        root = ElementTree.Element('dict')

        def append_kv(first, second, root=root):
            ElementTree.SubElement(root, 'key').text = first
            ElementTree.SubElement(root, 'string').text = second

        append_kv("scope", scope)
        ElementTree.SubElement(root, "key").text = "settings"
        d = ElementTree.SubElement(root, "dict")

        if input_dict.get("foreground"):
            append_kv("foreground", input_dict.get("foreground").upper(), d)

        return root

    def packages_relative_path(self, path, prefix_packages=True):
        """
            Return a Packages-relative version of path with '/' as the path separator.

            Sublime Text wants Packages-relative paths used in settings and in the plugin API
            to use '/' as the path separator on all platforms. This method converts platform
            path separators to '/'. If insert_packages = True, 'Packages' is prefixed to the
            converted path.
        """
        components = util.get_path_components(path)

        if prefix_packages and components and components[0] != 'Packages':
            components.insert(0, 'Packages')

        return '/'.join(components)


def backup_old_settings(usr_dir_abs):
    """
        If user settigns file in old format exists it is renamed to disable it
        and back it up.
        A message will be displayed to the user.
    """
    msg = """SublimeLinter\n\nYour settings have been backed up to:\nSublimeLinter (old).sublime-settings\nin Packages/User/""" # noqa: 501
    settings_file = os.path.join(usr_dir_abs, "SublimeLinter.sublime-settings")
    if os.path.exists(settings_file):
        path = "Packages/User/SublimeLinter.sublime-settings"
        settings = sublime.decode_value(sublime.load_resource(path))

        if "user" in settings:
            new_name = "SublimeLinter (old).sublime-settings"
            new_path = os.path.join(usr_dir_abs, new_name)
            os.rename(settings_file, new_path)
            sleep(1)
            sublime.message_dialog(msg)


def rm_old_dir(usr_dir_abs):
    usr_dir_abs = os.path.join(usr_dir_abs, "SublimeLinter")
    shutil.rmtree(usr_dir_abs, ignore_errors=True)


def legacy_check(func):
    min_version = int(sublime.version()) >= 3149  # version check
    usr_dir_abs = os.path.join(sublime.packages_path(), "User")
    backup_old_settings(usr_dir_abs)

    if min_version and not merged_settings.get("force_xml_scheme"):
        # remove old User/SublimeLinter dir
        rm_old_dir(usr_dir_abs)

        def func_wrapper():
            return func

        return func_wrapper()

    return XmlScheme
