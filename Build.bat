@echo off
TITLE Falcon Remote
pyinstaller --onefile --icon=Falcon.ico --distpath=dist --workpath=build --specpath=spec --noconsole --name Falcon main.py