# sysext.py
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundationat version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from gi.repository import Gtk, Adw

_ = __builtins__["_"]

import snow_first_setup.core.backend as backend

# Features surfaced prominently with their switch on by default; these match
# what the retired "loaded" image variants used to ship preinstalled.
RECOMMENDED_FEATURES = ["edge", "vscode", "bitwarden"]

@Gtk.Template(resource_path="/org/frostyard/FirstSetup/gtk/sysext.ui")
class VanillaSysext(Adw.Bin):
    __gtype_name__ = "VanillaSysext"

    recommended_group = Gtk.Template.Child()
    more_group = Gtk.Template.Child()
    more_row = Gtk.Template.Child()

    def __init__(self, window, **kwargs):
        super().__init__(**kwargs)
        self.__window = window

        self.__features = backend.list_sysext_features()
        self.__switches = {}

        self.__build_rows()

    @property
    def has_features(self) -> bool:
        return len(self.__features) > 0

    def set_page_active(self):
        self.__window.set_ready(True)
        self.__window.set_focus_on_next()

    def set_page_inactive(self):
        return

    def finish(self):
        backend.clear_sysext_deferred()
        for feature in self.__features:
            if self.__switches[feature["name"]].get_active():
                backend.enable_sysext_deferred(
                    feature["name"], feature["description"]
                )
        return True

    def __build_rows(self):
        has_recommended = False
        has_more = False

        for feature in self.__features:
            recommended = feature["name"] in RECOMMENDED_FEATURES
            row = self.__build_feature_row(feature, active=recommended or feature["enabled"])
            if recommended:
                self.recommended_group.add(row)
                has_recommended = True
            else:
                self.more_row.add_row(row)
                has_more = True

        self.recommended_group.set_visible(has_recommended)
        self.more_group.set_visible(has_more)

    def __build_feature_row(self, feature: dict, active: bool):
        row = Adw.ActionRow(
            title=feature["description"],
            subtitle=feature["name"],
        )

        switch = Gtk.Switch()
        switch.set_active(active)
        switch.set_valign(Gtk.Align.CENTER)
        switch.set_focusable(False)

        row.add_suffix(switch)
        row.set_activatable_widget(switch)

        self.__switches[feature["name"]] = switch
        return row
