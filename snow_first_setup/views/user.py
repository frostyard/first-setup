# user.py
#
# Copyright 2023 mirkobrombin
# Copyright 2023 muqtadir
#
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

import re
import subprocess
from gi.repository import Gtk, Adw
_ = __builtins__["_"]

import snow_first_setup.core.backend as backend

@Gtk.Template(resource_path="/org/frostyard/FirstSetup/gtk/user.ui")
class VanillaUser(Adw.Bin):
    __gtype_name__ = "VanillaUser"

    fullname_entry = Gtk.Template.Child()
    username_entry = Gtk.Template.Child()
    error = Gtk.Template.Child()
    password_entry = Gtk.Template.Child()
    password_confirmation = Gtk.Template.Child()
    shell_entry = Gtk.Template.Child()
    shell_list = Gtk.Template.Child()

    username = ""
    __user_changed_username = False

    fullname = ""
    shell = "/usr/bin/bash"

    __automatic_username = ""

    def __init__(self, window, **kwargs):
        super().__init__(**kwargs)
        self.__window = window

        self.fullname_entry.connect("changed", self.__on_fullname_entry_changed)
        self.username_entry.connect("changed", self.__on_username_entry_changed)
        self.fullname_entry.connect("entry-activated", self.__on_activate)
        self.username_entry.connect("entry-activated", self.__on_activate)
        self.password_entry.connect("changed", self.__on_password_entry_changed)
        self.password_confirmation.connect("changed", self.__on_password_confirmation_changed)

        self.existing_users = subprocess.Popen("getent passwd | cut -d: -f1", shell=True,
                                          stdout=subprocess.PIPE).stdout.read().decode().splitlines()

        # Load and populate available shells
        self.__populate_shell_list()

    def set_page_active(self):
        self.fullname_entry.grab_focus()
        self.__verify_continue()

    def set_page_inactive(self):
        return

    def finish(self):
        backend.add_user_deferred(self.username, self.fullname, self.password, self.shell)
        return True

    def __populate_shell_list(self):
        """Read shells from /etc/shells and populate the shell list with /bin/ shells only."""
        try:
            with open("/etc/shells", "r") as f:
                shells = f.readlines()

            # Filter to only include shells that start with /usr/ and are not comments
            filtered_shells = []
            for shell in shells:
                shell = shell.strip()
                if shell and not shell.startswith("#") and shell.startswith("/usr/"):
                    filtered_shells.append(shell)

            # Remove duplicates and sort
            filtered_shells = sorted(set(filtered_shells))

            # Clear existing entries and populate the list
            # self.shell_list
            for shell in filtered_shells:
                self.shell_list.append(shell)

            # Set default selection to /usr/bin/bash if available
            if "/usr/bin/bash" in filtered_shells:
                self.shell_entry.set_selected(filtered_shells.index("/usr/bin/bash"))
                self.shell = "/usr/bin/bash"
            elif filtered_shells:
                self.shell_entry.set_selected(0)
                self.shell = filtered_shells[0]

            # Connect to selection changes
            self.shell_entry.connect("notify::selected", self.__on_shell_changed)

        except Exception as e:
            print(f"Error reading /etc/shells: {e}")
            # Fallback to default bash
            self.shell_list.remove_all()
            self.shell_list.append("/bin/bash")
            self.shell_entry.set_selected(0)
            self.shell = "/bin/bash"

    def __on_shell_changed(self, dropdown, _):
        """Handle shell selection changes."""
        selected = dropdown.get_selected()
        if selected != Gtk.INVALID_LIST_POSITION:
            self.shell = self.shell_list.get_string(selected)

    def __on_activate(self, widget):
        self.__window.finish_step()

    def __on_fullname_entry_changed(self, *args):
        fullname = self.fullname_entry.get_text()

        self.fullname = fullname
        self.__verify_continue()

        self.__generate_username_from_fullname()

    def __on_username_entry_changed(self, *args):
        entry_text = self.username_entry.get_text()
        if entry_text != "" and entry_text != self.__automatic_username:
            self.__user_changed_username = True

        err = self.__verify_username()

        if err != "":
            self.username = ""
            self.username_entry.add_css_class("error")
            self.error.set_label(err)
            self.error.set_opacity(1)
            self.__verify_continue()
            return

        self.username = entry_text
        self.username_entry.remove_css_class("error")
        self.error.set_opacity(0)
        self.__verify_continue()

    def __generate_username_from_fullname(self):
        if self.__user_changed_username:
            return

        if self.fullname == "":
            return

        username_stripped = self.fullname.strip()
        username_no_whitespace = "-".join(username_stripped.split())
        username_lowercase = username_no_whitespace.lower()

        self.__automatic_username = username_lowercase
        self.username_entry.set_text(username_lowercase)

    def __verify_continue(self):
        password_err = self.__verify_password()
        ready = self.username != "" and self.fullname != "" and password_err == ""
        self.__window.set_ready(ready)

    def __verify_username(self) -> str:
        input = self.username_entry.get_text()

        if not input:
            return _("Username cannot be empty.")

        if len(input) > 32:
            return _("Username cannot be longer than 32 characters.")

        if re.search(r"[^a-z0-9_-]", input):
            return _("Username cannot contain special characters or uppercase letters.")

        if input in self.existing_users:
            _status = False
            return _("This username is already in use.")

        return ""

    def __verify_password(self) -> str:
        password = self.password_entry.get_text()
        confirmation = self.password_confirmation.get_text()

        if not password:
            return _("Password cannot be empty.")

        if password != confirmation:
            return _("Passwords do not match.")

        return ""

    def __on_password_entry_changed(self, *args):
        self.password = self.password_entry.get_text()
        self.__update_password_styles()
        self.__verify_continue()

    def __on_password_confirmation_changed(self, *args):
        self.__update_password_styles()
        self.__verify_continue()

    def __update_password_styles(self):
        err = self.__verify_password()
        if err != "":
            self.password_entry.add_css_class("error")
            self.password_confirmation.add_css_class("error")
            self.error.set_text(err)
            self.error.set_opacity(1)
        else:
            self.password_entry.remove_css_class("error")
            self.password_confirmation.remove_css_class("error")
            self.error.set_opacity(0)
