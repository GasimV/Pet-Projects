@echo off
REM FactoryPulse — make.bat wrapper
REM Delegates to mingw32-make so you can type: make up
REM
REM Requires mingw32-make on PATH (ships with MSYS2/MinGW).
mingw32-make %*
