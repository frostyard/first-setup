pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
scriptsdir = join_paths(pkgdatadir, 'snow_first_setup/scripts')

sources = [
  'complete-setup',
  'flatpak',
  'open-accessibility-settings',
  'open-network-settings',
  'setup-flatpak-remote',
  'setup-system',
  'theme',
]

install_data(sources, install_dir: scriptsdir)
