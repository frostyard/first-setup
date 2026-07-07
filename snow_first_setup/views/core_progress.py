# core_progress.py
#
# Progress view for installing core applications in configure_system_mode

import threading
import json
import os
import snow_first_setup.core.backend as backend
import snow_first_setup.core.applications as applications

from gi.repository import Gtk, Adw, GLib

_ = __builtins__["_"]

@Gtk.Template(resource_path="/org/frostyard/FirstSetup/gtk/core-progress.ui")
class VanillaCoreProgress(Adw.Bin):
    __gtype_name__ = "VanillaCoreProgress"

    action_list = Gtk.Template.Child()

    actions = {}

    __not_started = True
    __finished = False
    __already_skipped = False

    def __init__(self, window, **kwargs):
        super().__init__(**kwargs)

        self.__window = window

    def set_page_active(self):
        self.__window.set_ready(self.__finished)
        if self.__not_started:
            self.__not_started = False
            self.__load_and_install_core_apps()

    def set_page_inactive(self):
        return

    def finish(self):
        return True

    def __load_and_install_core_apps(self):
        # Load core.json and queue flatpak installations
        core_json_path = os.path.join(self.__window.moduledir, "core.json")
        
        try:
            with open(core_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            core_apps = data.get("core", [])
            
            # Queue all core apps for installation
            for app in core_apps:
                app_id = app.get("id")
                app_name = app.get("name")
                if app_id and app_name:
                    backend.install_flatpak_system_deferred(app_id, app_name)
            
        except Exception as e:
            print(f"[ERROR] Failed to load core.json: {e}")
        
        # Subscribe to progress updates and start installations
        backend.subscribe_progress(self.__on_items_changed_thread)
        thread = threading.Thread(target=backend.start_deferred_actions)
        thread.start()

    def __on_items_changed_thread(self, id: str, uid: str, state: backend.ProgressState, info: dict):
        GLib.idle_add(self.__on_items_changed, id, uid, state, info)

    def __on_items_changed(self, id: str, uid: str, state: backend.ProgressState, info: dict):
        if id == "all_actions":
            if state == backend.ProgressState.Finished:
                self.__window.set_ready(True)
                self.__finished = True
                self.__skip_page_once()
            return

        if state == backend.ProgressState.Initialized:
            self.__add_new_action(id, uid, info)
            return

        # Skip updates for actions we didn't add (like add_user)
        if uid not in self.actions:
            return

        status_suffix = None
        if state == backend.ProgressState.Running:
            status_suffix = Adw.Spinner()
        elif state == backend.ProgressState.Finished:
            status_suffix = Gtk.Image.new_from_icon_name("emblem-default-symbolic")
            status_suffix.add_css_class("success")
        elif state == backend.ProgressState.Failed:
            status_suffix = Gtk.Image.new_from_icon_name("dialog-warning-symbolic")
            status_suffix.add_css_class("error")

        if "suffix" in self.actions[uid]:
            self.actions[uid]["suffix"].set_visible(False)

        self.actions[uid]["widget"].add_suffix(status_suffix)
        self.actions[uid]["suffix"] = status_suffix

    def __add_new_action(self, id: str, uid: str, info: dict):
        # Only add flatpak installations and sysext features to this progress view
        if id == "install_flatpak":
            icon = Gtk.Image.new_from_icon_name(info["app_id"])
            applications.set_app_icon_from_id_async(icon, info["app_id"])
            title = _("Installing") + " " + info["app_name"]
        elif id == "enable_sysext":
            icon = Gtk.Image.new_from_icon_name("org.gnome.Software-symbolic")
            title = _("Enabling") + " " + info["feature_description"]
        else:
            return

        row = Adw.ActionRow()
        row.set_title(title)
        icon.add_css_class("lowres-icon")
        icon.set_icon_size(Gtk.IconSize.LARGE)

        row.add_prefix(icon)

        self.action_list.add(row)
        self.actions[uid] = {"id": id, "info": info, "widget": row}

    def __skip_page_once(self):
        if not self.__already_skipped:
            self.__already_skipped = True
            self.__window.finish_step()
