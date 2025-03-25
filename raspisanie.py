import pandas as pd
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import logging
import os
import signal

def shutdown_handler(signum, frame):
    logger.info("Получен сигнал завершения")
    application.stop()
    exit(0)

signal.signal(signal.SIGTERM, shutdown_handler)
signal.signal(signal.SIGINT, shutdown_handler)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ScheduleBot:
    def __init__(self):
        """Инициализация бота с загрузкой всех расписаний"""
        self.modes = {
            "Расписание": {
                "AR/VR": "ARVR.xlsx",
                "HITECH": "HITECH.xlsx",
                "AERO": "AERO.xlsx",
                "ROBO": "ROBO.xlsx",
                "IT": "IT.xlsx",
                "Туризм": "TURISM.xlsx"
            
            },
            "Автобусы": "BUS.xlsx"
        }
        self.current_mode = None
        self.current_direction = None
        self.schedule = {}
        logger.info("Бот инициализирован")

    async def show_main_menu(self, update: Update):
        """Главное меню с выбором режима"""
        buttons = [["🚌 Автобусы", "📚 Расписание"]]
        reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
        await update.message.reply_text(
            "Выберите режим работы:",
            reply_markup=reply_markup
        )

    async def start(self, update: Update, context: CallbackContext):
        """Обработка команды /start"""
        try:
            self.current_mode = None
            self.current_direction = None
            await self.show_main_menu(update)
        except Exception as e:
            logger.error(f"Ошибка в start: {e}")
            await update.message.reply_text("⚠️ Произошла ошибка. Попробуйте позже")

    async def handle_mode(self, update: Update, context: CallbackContext):
        """Обработка выбора режима (Автобусы/Расписание)"""
        try:
            choice = update.message.text
            
            if 'автобус' in choice.lower():
                self.current_mode = "Автобусы"
                await self.handle_bus_direction(update, context)
            elif 'расписание' in choice.lower():
                self.current_mode = "Расписание"
                await self.show_directions(update)
            else:
                await self.show_main_menu(update)
                
        except Exception as e:
            logger.error(f"Ошибка в handle_mode: {e}")
            await update.message.reply_text("⚠️ Произошла ошибка. Возвращаю в главное меню")
            await self.show_main_menu(update)

    async def show_directions(self, update: Update):
        """Показывает направления для расписания"""
        try:
            buttons = [
                ["AR/VR", "HITECH"],
                ["AERO", "ROBO"],
                ["IT", "Туризм"],
                ["↩️ Назад"]
            ]
            reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
            await update.message.reply_text(
                "🏫 Выберите направление:",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Ошибка в show_directions: {e}")
            await update.message.reply_text("⚠️ Произошла ошибка. Возвращаю в главное меню")
            await self.show_main_menu(update)

    def load_schedule(self, file_path):
        """Универсальная загрузка расписания из Excel файла"""
        try:
            if not os.path.exists(file_path):
                logger.error(f"Файл {file_path} не найден")
                return {}

            df = pd.read_excel(file_path, header=0, engine='openpyxl')
            schedule = {}
            
            for _, row in df.iterrows():
                try:
                    day = str(row['ДЕНЬ НЕДЕЛИ']).strip().lower()
                    time = str(row['ВРЕМЯ']).strip()
                    
                    if day not in schedule:
                        schedule[day] = []
                    
                    lessons = []
                    
                    # Ищем все колонки с преподавателями (начинаются с "П:")
                    teacher_columns = [col for col in df.columns if str(col).startswith('П:')]
                    
                    if not teacher_columns:
                        # Если нет колонок с "П:", ищем любые другие колонки кроме ДЕНЬ НЕДЕЛИ и ВРЕМЯ
                        teacher_columns = [col for col in df.columns if col not in ['ДЕНЬ НЕДЕЛИ', 'ВРЕМЯ']]
                    
                    for col in teacher_columns:
                        teacher_name = str(col).replace('П:', '').strip()
                        subject = row[col]
                        if pd.notna(subject) and str(subject).strip():
                            lessons.append(f"{teacher_name}: {str(subject).strip()}")
                    
                    if lessons:
                        schedule[day].append({
                            'time': time,
                            'lessons': lessons
                        })
                except Exception as e:
                    logger.warning(f"Ошибка обработки строки: {e}")
                    continue
            
            # Гарантируем наличие всех дней недели
            week_days = ['понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота']
            for day in week_days:
                if day not in schedule:
                    schedule[day] = []
            
            return schedule
        
        except Exception as e:
            logger.error(f"Ошибка загрузки расписания: {e}")
            return {}

    def load_bus_schedule(self, file_path):
        """Загрузка расписания автобусов"""
        try:
            if not os.path.exists(file_path):
                logger.error(f"Файл {file_path} не найден")
                return {}

            bus_schedule = {
                "Прямой": {},
                "Обратный": {}
            }
            
            # Загрузка прямого направления (Лист1)
            df_direct = pd.read_excel(file_path, sheet_name="Лист1", header=0, engine='openpyxl')
            for _, row in df_direct.iterrows():
                stop = str(row['Остановки']).strip()
                times = [str(row[col]).strip() for col in ['отправление', 'отправление.1', 'отправление.2'] 
                         if col in row and pd.notna(row[col])]
                bus_schedule["Прямой"][stop] = times
            
            # Загрузка обратного направления (Лист2)
            df_reverse = pd.read_excel(file_path, sheet_name="Лист2", header=0, engine='openpyxl')
            for _, row in df_reverse.iterrows():
                stop = str(row['Остановки']).strip()
                times = [str(row[col]).strip() for col in ['отправление', 'отправление.1', 'отправление.2'] 
                         if col in row and pd.notna(row[col])]
                bus_schedule["Обратный"][stop] = times
            
            return bus_schedule
        
        except Exception as e:
            logger.error(f"Ошибка загрузки расписания автобусов: {e}")
            return {}

    async def handle_bus_direction(self, update: Update, context: CallbackContext):
        """Обработка выбора направления автобуса"""
        try:
            buttons = [["Прямой", "Обратный"], ["↩️ Назад"]]
            reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
            await update.message.reply_text(
                "Выберите направление автобуса:",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Ошибка в handle_bus_direction: {e}")
            await update.message.reply_text("⚠️ Произошла ошибка. Возвращаю в главное меню")
            await self.show_main_menu(update)

    async def handle_bus_schedule(self, update: Update, context: CallbackContext):
        """Обработка выбора расписания автобусов"""
        try:
            text = update.message.text
            
            if text == "↩️ Назад":
                await self.show_main_menu(update)
                return
            
            if text not in ["Прямой", "Обратный"]:
                await update.message.reply_text("Пожалуйста, выберите направление из предложенных вариантов")
                return
            
            bus_schedule = self.load_bus_schedule(self.modes["Автобусы"])
            direction_schedule = bus_schedule.get(text, {})
            
            if not direction_schedule:
                await update.message.reply_text(f"Расписание для направления '{text}' не найдено")
                return
            
            response = f"🚌 Расписание ({text} направление):\n\n"
            response += "Остановка       | 1 группа | 2 группа | 3 группа\n"
            response += "-----------------------------------------------\n"
            
            for stop, times in direction_schedule.items():
                times_formatted = [t.split()[0] if pd.notna(t) else "-" for t in times]
                response += f"{stop.ljust(15)} | {times_formatted[0].ljust(8)} | {times_formatted[1].ljust(8)} | {times_formatted[2]}\n"
            
            await update.message.reply_text(f"<pre>{response}</pre>", parse_mode='HTML')
            
            # Предлагаем выбрать другое направление или вернуться
            buttons = [["Прямой", "Обратный"], ["↩️ Назад"]]
            reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
            await update.message.reply_text(
                "Выберите действие:",
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Ошибка в handle_bus_schedule: {e}")
            await update.message.reply_text("⚠️ Произошла ошибка. Возвращаю в главное меню")
            await self.show_main_menu(update)

    async def handle_direction(self, update: Update, context: CallbackContext):
        """Обработка выбора направления"""
        try:
            text = update.message.text
            
            if text == "↩️ Назад":
                await self.show_main_menu(update)
                return
            
            if text not in self.modes["Расписание"]:
                await update.message.reply_text("❌ Такого направления нет")
                await self.show_directions(update)
                return
            
            self.current_direction = text
            file_path = self.modes["Расписание"][text]
            self.schedule = self.load_schedule(file_path)
            
            if not self.schedule:
                await update.message.reply_text(f"⚠️ Расписание для {text} не найдено")
                await self.show_directions(update)
                return
            
            await self.show_days(update)
            
        except Exception as e:
            logger.error(f"Ошибка в handle_direction: {e}")
            await update.message.reply_text("⚠️ Произошла ошибка. Возвращаю в главное меню")
            await self.show_main_menu(update)

    async def show_days(self, update: Update):
        """Показывает дни недели для выбранного направления"""
        try:
            buttons = [
                ["Понедельник", "Вторник"],
                ["Среда", "Четверг"],
                ["Пятница", "Суббота"],
                ["↩️ Назад"]
            ]
            reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
            await update.message.reply_text(
                f"📅 {self.current_direction}. Выберите день недели:",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Ошибка в show_days: {e}")
            await update.message.reply_text("⚠️ Произошла ошибка. Возвращаю в главное меню")
            await self.show_main_menu(update)

    async def handle_day(self, update: Update, context: CallbackContext):
        """Обработка выбора дня недели"""
        try:
            text = update.message.text.lower()
            
            if text == "↩️ назад":
                await self.show_directions(update)
                return
                
            day = text
            if day not in self.schedule:
                await update.message.reply_text("❌ Такого дня нет в расписании")
                return
                
            if not self.schedule[day]:
                await update.message.reply_text(f"📭 На {day.capitalize()} занятий нет")
                return
                
            response = f"📅 {self.current_direction}. Расписание на {day.capitalize()}:\n\n"
            
            for slot in self.schedule[day]:
                response += f"🕒 {slot['time']}\n"
                response += "\n".join(f"👨‍🏫 {lesson}" for lesson in slot['lessons'])
                response += "\n\n"
                
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"Ошибка в handle_day: {e}")
            await update.message.reply_text("⚠️ Произошла ошибка. Возвращаю в главное меню")
            await self.show_main_menu(update)

    async def handle_message(self, update: Update, context: CallbackContext):
        """Главный обработчик сообщений"""
        try:
            text = update.message.text
            
            if text in ["🚌 Автобусы", "📚 Расписание"]:
                await self.handle_mode(update, context)
            elif text in ["AR/VR", "HITECH", "AERO", "ROBO", "IT", "Туризм"]:
                await self.handle_direction(update, context)
            elif text in ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]:
                await self.handle_day(update, context)
            elif text in ["Прямой", "Обратный", "↩️ Назад"]:
                if self.current_mode == "Автобусы":
                    await self.handle_bus_schedule(update, context)
                else:
                    await self.show_main_menu(update)
            else:
                await self.show_main_menu(update)
                
        except Exception as e:
            logger.error(f"Ошибка в handle_message: {e}")
            await update.message.reply_text("⚠️ Произошла ошибка. Возвращаю в главное меню")
            await self.show_main_menu(update)

    def run(self):
        """Запуск бота"""
        try:
            application = Application.builder().token("7590558054:AAGdGbsaTfUqplrPF93XRktXRRCR4PTEYzA").build()
            
            application.add_handler(CommandHandler("start", self.start))
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
            
            logger.info("Бот запущен и готов к работе")
            print("✅ Бот успешно запущен. Для остановки нажмите Ctrl+C")
            
            application.run_polling()
        except Exception as e:
            logger.critical(f"Ошибка запуска бота: {e}")
            print(f"❌ Критическая ошибка: {e}")

if __name__ == "__main__":
    try:
        bot = ScheduleBot()
        bot.run()
    except Exception as e:
        print(f"Фатальная ошибка: {e}")
        input("Нажмите Enter для выхода...")
