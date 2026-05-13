pyinstaller ^
  --onedir ^
  --windowed ^
  --name "Vehicle Automator" ^
  --add-data "resources;resources" ^
  --add-data "pw-browsers;pw-browsers" ^
  -y ^
  app.py