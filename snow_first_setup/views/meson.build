pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
viewsdir = join_paths(pkgdatadir, 'snow_first_setup/views')

sources = [
  '__init__.py',
  'applications.py',
  'conn_check.py',
  'core_progress.py',
  'done.py',
  'hostname.py',
  'install_confirm.py',
  'install_disk.py',
  'install_done.py',
  'install_progress.py',
  'keyboard.py',
  'language.py',
  'locations.py',
  'logout.py',
  'progress.py',
  'recovery_key.py',
  'sysext.py',
  'theme.py',
  'timezone.py',
  'user.py',
  'welcome_user.py',
  'welcome_install.py',
  'welcome.py',
]

install_data(sources, install_dir: viewsdir)
