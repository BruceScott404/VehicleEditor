pyinstaller \
  --onedir \
  --windowed \
  --name "Vehicle Automator" \
  --add-data "resources:resources" \
  -y \
  app.py