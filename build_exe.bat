@echo off
setlocal

echo Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-build.txt

echo Building PhotoCullAI...

pyinstaller ^
  --noconfirm ^
  --clean ^
  --windowed ^
  --name PhotoCullAI ^
  --add-data "config.yaml;." ^
  --collect-all mediapipe ^
  --collect-all paddleocr ^
  --collect-all onnxruntime ^
  --collect-all PyQt6 ^
  main.py

echo.
echo Done. Check dist\PhotoCullAI.exe
pause
