desktop_file = i18n.merge_file(
  input: 'org.frostyard.FirstSetup.desktop.in',
  output: 'org.frostyard.FirstSetup.desktop',
  type: 'desktop',
  po_dir: '../po',
  install: true,
  install_dir: join_paths(get_option('datadir'), 'applications'),
)

# System-wide autostart entry (XDG autostart, not copied per-user via skel).
# The app self-gates on launch: with --autostart it exits immediately when the
# per-user completion marker exists or when running in a live session. A
# per-user file of the same name in ~/.config/autostart (from pre-0.2.16 skel
# copies) shadows this entry per the XDG autostart spec.
autostart_file = i18n.merge_file(
  input: 'org.frostyard.FirstSetup.autostart.desktop.in',
  output: 'org.frostyard.FirstSetup.autostart.desktop',
  type: 'desktop',
  po_dir: '../po',
  install: true,
  install_dir: join_paths(get_option('sysconfdir'), 'xdg', 'autostart'),
)

desktop_utils = find_program('desktop-file-validate', required: false)
if desktop_utils.found()
  test('Validate desktop file', desktop_utils,
    args: [desktop_file]
  )
  test('Validate autostart desktop file', desktop_utils,
    args: [autostart_file]
  )
endif

subdir('icons')
