pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
scriptsdir = join_paths(pkgdatadir, 'snow_first_setup/scripts')

sources = [
  'disable-lockscreen',
  'keyboard',
  'logout',
  'open-network-settings',
  'theme',
  'flatpak',
  'flatpak-system',
  'live-keyboard',
  'setup-flatpak-remote',
  'timezone',
  'hostname',
  'locale',
  'open-accessibility-settings',
  'setup-system',
  'user',
  'remove-first-setup-user',
  'complete-setup',
  'install-to-disk',
  'enroll-key',
  'recovery-key',
  'oemcomplete',
]

install_data(sources, install_dir: scriptsdir)
