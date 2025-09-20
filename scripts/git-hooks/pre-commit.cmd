@echo off
REM FI: Format & lint ennen committia. Pysäyttää commitin virheisiin.
REM EN: Format & lint before committing. Aborts commit on errors.

REM --- Activate venv if present (optional)
IF EXIST ".\venv\Scripts\activate.bat" (
  call .\venv\Scripts\activate.bat
)

echo [pre-commit] Running black...
python -m black .
IF ERRORLEVEL 1 (
  echo [pre-commit] Black failed. Fix issues and re-commit.
  exit /b 1
)

echo [pre-commit] Running ruff (E,F only)...
python -m ruff check . --select E,F
IF ERRORLEVEL 1 (
  echo [pre-commit] Ruff failed. Fix issues and re-commit.
  exit /b 1
)

echo [pre-commit] OK
exit /b 0
