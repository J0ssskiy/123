@echo off
sc create ScheduleBot binPath= "%~dp0raspisanie.bat" start= auto DisplayName= "Telegram Schedule Bot"
sc description ScheduleBot "Telegram bot for school schedule management"
sc start ScheduleBot