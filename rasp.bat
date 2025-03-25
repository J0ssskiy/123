@echo off
SETLOCAL ENABLEDELAYEDEXPANSION
TITLE Установщик бота расписания
COLOR 0A

:: 1. Проверка и установка Python
echo Проверяем Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Устанавливаем Python 3.11...
    curl -L -o python-installer.exe https://www.python.org/ftp/python/3.11.4/python-3.11.4-amd64.exe
    start /wait python-installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_launcher=1
    del python-installer.exe
    setx PATH "%PATH%;%ProgramFiles%\Python311;%ProgramFiles%\Python311\Scripts"
    timeout /t 3
)

:: 2. Добавление пользовательских скриптов в PATH
set "PY_USER_SCRIPTS=%APPDATA%\Python\Python311\Scripts"
if exist "!PY_USER_SCRIPTS!" (
    set "PATH=!PATH!;!PY_USER_SCRIPTS!"
)

:: 3. Обновление pip
python -m pip install --upgrade pip --no-warn-script-location

:: 4. Установка зависимостей
echo Устанавливаем зависимости...
python -m pip install pandas python-telegram-bot openpyxl numpy httpx --no-warn-script-location

:: 5. Проверка файлов (с учетом русского именования)
echo Проверяем файлы расписания...
set "ALL_FILES_EXIST=1"
for %%F in (
    "ARVR.xlsx"
    "HITECH.xlsx"
    "AERO.xlsx"
    "ROBO.xlsx"
    "IT.xlsx"
    "TURISM.xlsx"
    "BUS.xlsx"
) do (
    if not exist %%F (
        echo ОШИБКА: Отсутствует файл %%F
        set "ALL_FILES_EXIST=0"
    )
)

if !ALL_FILES_EXIST! equ 0 (
    echo.
    echo -----------------------------------------------
    echo ВНИМАНИЕ: Не все файлы расписания найдены!
    echo Разместите ВСЕ указанные файлы в одной папке
    echo с rasp.bat и повторите запуск
    echo -----------------------------------------------
    pause
    exit /b 1
)

:: 6. Запуск бота
echo.
echo Запускаем бота...
python raspisanie.py

pause