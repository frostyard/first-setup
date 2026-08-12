pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
viewsdir = join_paths(pkgdatadir, 'snow_first_setup/views')

sources = [
  '__init__.py',
  'applications.py',
  'conn_check.py',
  'done.py',
  'progress.py',
  'theme.py',
  'welcome_user.py',
]

install_data(sources, install_dir: viewsdir)
