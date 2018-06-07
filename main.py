import telegram.ext
import re
import config
import json
import threading
import difflib
import copy
from datetime import (datetime, timedelta, )

from urllib import request, parse
from telegram.ext import (CommandHandler, MessageHandler)
from telegram.ext import Filters
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton)
from telegram.error import (TelegramError, Unauthorized, BadRequest,
                            TimedOut, ChatMigrated, NetworkError)
from queue import Queue

last_update_time = datetime.now()
log = []


def error_callback(bot, update, error):
    try:
        print(error)
        raise error
    except Unauthorized as un:
        print(un)
        raise
    except BadRequest as br:
        print(br)
        raise
    except TimedOut as to:
        print(to)
        raise
    except NetworkError as ne:
        print(ne)
        raise
    except ChatMigrated as e:
        print(e)
        raise
    except TelegramError as te:
        print(te)
        raise


def get_params_from_google():
    try:
        response = request.urlopen(config.GOOGLE_SHEET)
        json_data = json.loads(response.read().decode('utf-8'))
        return json_data
    except Exception:
        raise


def google_send_record_thread(client, message_for_replace_id):
    try:
        response = request.urlopen(config.GOOGLE_SHEET, parse.urlencode(client.record.google_script_fmt()).encode())
        json_data = json.loads(response.read().decode('utf-8'))
        client.edit_message(text="Запись сохранилась ✔", message_id=message_for_replace_id)

        if len(log) > 10:
            log.clear()
        log.append("{user}->{record}".format(user=client.get_name(), record=str(client.record)))

        print("Thread ending with data {}".format(json_data))
        return json_data
    except Exception as e:
        print("Thread ending with error {}".format(e))
        raise


remote_category = ('Уд. дизайнер', 'Уд. программист', 'Уд. бухгалтер',)
payment_systems = ('Счет', 'Касса', 'WebMoney', 'РИС', 'КИС', 'ДИС', 'ЯД', 'СБЕР')
expenses_category = ('Дизайн / Обучение', 'Дизайн / Удаленные сотрудники', 'Дизайн / Dropbox',
                     'Контекст / ПО', 'Корпоративные_мероприятия / Английский',
                     'Корпоративные_мероприятия / Дни рождения',
                     'Корпоративные_мероприятия / Корпоративы', 'Корпоративные_мероприятия / Подарки клиентам',
                     'Корпоративные_мероприятия / Подарки/Премии',
                     'Корпоративные_мероприятия / Прочее', 'Корпоративные_мероприятия / Спорт',
                     'Налоги / Налоги по АКР',
                     'Налоги / НДС АКР', 'Налоги / Официальная зарплата (любая)', 'Налоги / Прочее',
                     'Налоги / УСН ИП Замятин', 'Налоги / УСН ИП Мальцева', 'Налоги / УСН ООО УМ',
                     'Наша_реклама / Дизайн', 'Наша_реклама / Контекстная реклама', 'Наша_реклама / Прочее',
                     'Наша_реклама / Рейтинги', 'Офисные_нужды / 1С специалист', 'Офисные_нужды / Большие покупки',
                     'Офисные_нужды / Бухгалтер', 'Офисные_нужды / Вещи в офис', 'Офисные_нужды / Видеонаблюдение',
                     'Офисные_нужды / Вода', 'Офисные_нужды / Дни Рождения', 'Офисные_нужды / ЗП Удаленщиков',
                     'Офисные_нужды / Интернет', 'Офисные_нужды / Канцтовары', 'Офисные_нужды / Курьер',
                     'Офисные_нужды / лицензия  1с', 'Офисные_нужды / Мебель', 'Офисные_нужды / Обслуживание Битрикса',
                     'Офисные_нужды / Обслуживание р/с', 'Офисные_нужды / ПО', 'Офисные_нужды / Почта',
                     'Офисные_нужды / Продукты в офис', 'Офисные_нужды / Прочее', 'Офисные_нужды / Ремонт',
                     'Офисные_нужды / Такси', 'Офисные_нужды / Телефон', 'Офисные_нужды / Юрист',
                     'Офисные_нужды / CRM', 'Офисные_нужды / sape', 'Продажи / Агентские',
                     'Продажи / Прочее', 'Продажи / Рейтинги', 'Прочее / Прочее',
                     'Стратегические / Автоматизация Битрикса', 'Стратегические / Мебель',
                     'Стратегические / Наше обучение',
                     'Стратегические / Обучение сотрудников', 'Стратегические / Покупка техники',
                     'Стратегические / Ремонт',
                     'Стратегические / Управленческий учет', 'IT / Домены', 'IT / ЗП Удаленщиков',
                     'IT / Прочее', 'IT / Хостинг', 'SEO / ЗП Удаленщиков',
                     'SEO / ПО', 'SEO / Прочее', 'SEO / Съём позиций',
                     'SEO / Такси', 'SEO / Тексты', 'SEO / Форумок',
                     'SEO / Sape', 'SMM / Накрутка', 'SMM / Обучение',
                     'SMM / ПО', 'SMM / Пост в Типичной Перми для Real Touch', 'SMM / Посты в Соц. Сетях',
                     'SMM / Прочее', 'SMM / Таргет', 'Аренда_офиса / Аренда офиса',)
record_queue = Queue()


def build_payment_keyboard(data_list, message=""):
    if not message.strip():
        return ReplyKeyboardMarkup([[data] for data in data_list])
    else:
        original_values = {data.lower(): data for data in data_list}
        matches = difflib.get_close_matches(message.lower(), [data.lower() for data in data_list])
        build_list = list(data_list)
        for match in matches:
            del build_list[build_list.index(original_values[match])]

        matches_original_values = list(map(lambda x: original_values[x], matches))
        return ReplyKeyboardMarkup([[ps] for ps in matches_original_values + build_list])


def build_expenses_keyboard(message=""):
    if not message.strip():
        return ReplyKeyboardMarkup([[data] for data in expenses_category])

    original_values = {data.lower(): data for data in expenses_category}
    build_list = list(expenses_category)
    found_matches_keys = []
    found_matches_rows = []
    lower_split_values = [row.lower().split() for row in expenses_category]

    for key, words_list in enumerate(lower_split_values):
        matches = difflib.get_close_matches(message.lower(), words_list)
        if matches:
            found_matches_keys.append(key)

    for key in found_matches_keys:
        found_matches_rows.append(original_values[" ".join(lower_split_values[key])])

    for match in found_matches_rows:
        del build_list[build_list.index(match)]

    return ReplyKeyboardMarkup([[ps] for ps in found_matches_rows + build_list])


def find_in_payment_systems(message):
    return message.lower() in list(map(lambda x: x.lower(), payment_systems))


def find_in_expenses_category(message):
    return message.lower() in list(map(lambda x: x.lower(), expenses_category))


def get_original_value(model, key):
    original_values = {row.lower(): row for row in model}
    return original_values[key.lower()]


class Clients(object):
    __instance = None

    @staticmethod
    def instance():
        if not Clients.__instance:
            Clients.__instance = Clients()
        return Clients.__instance

    def __init__(self):
        self.clients = dict()

    def append_client(self, bot, update):
        if update.message.chat_id not in self.clients:
            self.clients[update.message.chat_id] = Client(
                bot,
                update.message.from_user.id,
                update.message.chat_id,
                update.message.from_user.first_name,
                update.message.from_user.last_name,
                update.message.from_user.username
            )
        return self.get_client(update)

    def get_client(self, update):
        if update.message.chat_id in self.clients:
            return self.clients[update.message.chat_id]
        return None

    def has_client(self, update):
        return update.message.chat_id in self.clients

    def __str__(self):
        return repr(self.clients)


class Client(object):
    def __init__(self, bot, id, chat_id, name, surname, username):
        self.id = id
        self.name = name
        self.surname = surname
        self.username = username
        self.record = Record(self)
        self.fsm = FSM(self)
        self.bot = bot
        self.chat_id = chat_id

    def reply(self, clear_keyboard=True, **kwargs):
        if 'reply_markup' not in kwargs and clear_keyboard:
            return self.bot.send_message(chat_id=self.chat_id, reply_markup=ReplyKeyboardRemove(), **kwargs)
        elif 'reply_markup' not in kwargs and not clear_keyboard:
            return self.bot.send_message(chat_id=self.chat_id, **kwargs)
        else:
            return self.bot.send_message(chat_id=self.chat_id, **kwargs)

    def edit_message(self, **kwargs):
        self.bot.edit_message_text(chat_id=self.chat_id, **kwargs)

    def get_name(self):
        if self.name:
            return self.name
        elif self.username:
            return self.username

    def __str__(self):
        return "{name}".format(name=self.get_name())


class FSM(object):
    def __init__(self, client):
        self.active_state = self.__init
        self.client = client
        self.transition_table = {
            self.__init: self.__get_paysystem,
            self.__get_paysystem: self.__get_expenses_category,
            self.__get_expenses_category: self.__get_comment,
            self.__get_comment: self.__init
        }

    def set_next_state(self, message, state_fn=None):
        if state_fn is not None:
            self.active_state = state_fn
        else:
            self.active_state = self.transition_table[self.active_state]
        return self.active_state(message)

    def reset(self):
        self.active_state = self.__init
        return self.active_state()

    def run(self, message):
        return self.active_state(message)

    def __init(self, message=None):
        print("State 1 run")
        self.client.record = Record(self.client)

        if not message:
            return self.client.reply(text="Введите расход")

        pattern = re.compile(r'^(?P<amount>\d+\.?\d{,2}) ?(?P<tail>.*)$')
        match = pattern.match(message)

        try:
            self.client.record.amount = float(match.group('amount'))
            return self.set_next_state(match.group('tail'))
        except Exception:
            return self.client.reply(
                text="Не удалось определить сумму расходов, попробуйте снова",
                reply_markup=ReplyKeyboardMarkup([['Сообщить о проблеме!']]))

    def __get_paysystem(self, message):
        print("State 2 run")
        pattern = re.compile(r'^(?P<payment_system>[\w]+) ?(?P<tail>.*)$')
        match = pattern.match(message)

        if match and self.client.record.set_payment_systems(match.group('payment_system')) is not None:
            return self.set_next_state(match.group('tail'))
        elif match:
            return self.client.reply(
                text="Введите платежную систему",
                reply_markup=build_payment_keyboard(payment_systems, match.group('payment_system')))
        else:
            return self.client.reply(
                text="Введите платежную систему",
                reply_markup=build_payment_keyboard(payment_systems))

    def __get_expenses_category(self, message):
        print("State 3 run")
        pattern = re.compile(r'^(?P<expenses_category>[\w /()]+)$')
        match = pattern.match(message)

        if match and (match.group('expenses_category').lower() == 'Уд'.lower() or match.group(
                'expenses_category') == 'Удаленщики'.lower()):
            return self.set_next_state('', self.__get_remote_expenses_category)

        if match and self.client.record.set_expense_category(match.group('expenses_category')) is not None:
            return self.set_next_state(None)

        elif match:
            return self.client.reply(text="Введите категорию расходов",
                                     reply_markup=build_expenses_keyboard(match.group('expenses_category')))
        else:
            return self.client.reply(text="Введите категорию расходов",
                                     reply_markup=build_expenses_keyboard())

    def __get_remote_expenses_category(self, message):
        print("State 3.1")
        pattern = re.compile(r'^(?P<remote_expenses_category>[\w ./()]+)$')
        match = pattern.match(message)

        if match and self.client.record.set_remote_expense_category(
                match.group('remote_expenses_category')) is not None:
            return self.set_next_state(None, self.__get_comment)

        elif match:
            return self.client.reply(text="Введите категорию расходов (Уд.)",
                                     reply_markup=build_payment_keyboard(remote_category,
                                                                         match.group('remote_expenses_category')))
        else:
            return self.client.reply(text="Введите категорию расходов (Уд.)",
                                     reply_markup=build_payment_keyboard(remote_category))

    def __get_comment(self, message):
        if message:
            self.client.record.comment = message if message != "Не нужно" else ''

            self.client.reply(text="Сохраняю...")
            sent_message = self.client.reply(clear_keyboard=False, text="⌛ {client} => {record}"
                                             .format(client=str(self.client), record=str(self.client.record)))

            # threading \
            #     .Thread(target=google_send_record_thread, args=[self.client, sent_message.message_id]) \
            #     .start()

            record_queue.put((copy.deepcopy(self.client), sent_message.message_id,))

            return self.set_next_state(None)
        return self.client.reply(text="Введите комментарий", reply_markup=ReplyKeyboardMarkup([['Не нужно']]))


class Record(object):
    def __init__(self, client, amount=None, payment_system=None, expenses_category=None):
        self.amount = amount
        self.payment_system = payment_system
        self.expenses_category = expenses_category
        self.comment = ''
        self.client = client

    def set_payment_systems(self, payment_system):
        original_values_map = {value.lower(): value for value in payment_systems}
        if payment_system.lower() in original_values_map:
            self.payment_system = original_values_map[payment_system.lower()]
            return self.payment_system
        else:
            return None

    def set_expense_category(self, expense):
        original_values_map = {value.lower(): value for value in expenses_category}
        if expense.lower() in original_values_map:
            self.expenses_category = original_values_map[expense.lower()]
            return self.expenses_category
        else:
            return None

    def set_remote_expense_category(self, remote_expense):
        original_values_map = {value.lower(): value for value in remote_category}
        if remote_expense.lower() in original_values_map:
            self.expenses_category = original_values_map[remote_expense.lower()]
            return self.expenses_category
        else:
            return None

    def google_script_fmt(self):
        return {
            'amount': self.amount,
            'paysystem': self.payment_system,
            'costs': self.expenses_category,
            'comment': self.comment,
            'user': self.client.get_name()
        }

    def __str__(self):
        return "Сумма:{} п\с:{} к\р:{}".format(self.amount, self.payment_system, self.expenses_category)


def start_callback(bot, update):
    clients = Clients.instance()
    client = clients.get_client(update) if clients.has_client(update) else clients.append_client(bot, update)
    client.reply(text="Приветствую тебя: {username}\n"
                      "Попробуй мне написать расход в формате:"
                      "\n<i>сумма платежная система категория расодов</i>"
                      "\n------------------------\n"
                      "<b>Команды управления:</b> \n"
                      "/start вывод текущей информации\n"
                      "/b очистить записи и начать с начала\n"
                      "/info статус бота\n"
                      "/u обновить данные с таблицы( dev version )"
                      "\n------------------------\n"
                      "<b>Информация о записях:</b>\n"
                      "/r текущая запись".format(username=client.get_name()),
                 clear_keyboard=True, parse_mode=telegram.ParseMode.HTML)


def back_clear_callback(bot, update):
    clients = Clients.instance()
    client = clients.get_client(update) if clients.has_client(update) else clients.append_client(bot, update)
    old_record = copy.copy(client.record)
    client.record = Record(client)
    client.reply(text="Была очищенна запись:\n{record}".format(record=str(old_record)))
    client.fsm.reset()


def info_callback(bot, update):
    clients = Clients.instance()
    client = clients.get_client(update) if clients.has_client(update) else clients.append_client(bot, update)

    client.reply(text="Клиент: {user}\n"
                      "Текущая запись: {record}\n"
                      "Текущая обработка: {fsm_state}\n"
                      "Последнее обновление данных: {time}"
                 .format(user=client,
                         record=client.record,
                         fsm_state=client.fsm.active_state.__name__,
                         time=last_update_time.strftime("%H:%M:%S")))


def record_callback(bot, update):
    clients = Clients.instance()
    client = clients.get_client(update) if clients.has_client(update) else clients.append_client(bot, update)
    client.reply(text="Запись: \n{}".format(client.record), clear_keyboard=False)


def clear_callback(bot, update):
    clients = Clients.instance()
    client = clients.get_client(update) if clients.has_client(update) else clients.append_client(bot, update)
    client.reply(text="Clear", reply_markup=ReplyKeyboardRemove(), )


def update_callback(bot, update):
    global last_update_time, payment_systems, expenses_category, remote_category
    clients = Clients.instance()
    client = clients.get_client(update) if clients.has_client(update) else clients.append_client(bot, update)
    message = client.reply(
        text="{user} настало время обновить данные, погоди минутку ⌛".format(user=client.get_name()),
        clear_keyboard=False)
    try:
        g_data = get_params_from_google()
        payment_systems = tuple(g_data['paysystems'])
        expenses_category = tuple(g_data['costs']) + ('Удаленщики',)
        remote_category = tuple(g_data['remote'])
        last_update_time = datetime.now()
        client.edit_message(text="Обновил данные с гугла ✔".format(user=client.get_name()),
                            message_id=message.message_id)
    except Exception as error:
        client.edit_message(text="Произошла ошибка: {}, попробуйте позднее или какостыляйте Сашке!".format(error),
                            message_id=message.message_id)


def message_callback(bot, update):
    global last_update_time, payment_systems, expenses_category, remote_category
    clients = Clients.instance()
    client = clients.get_client(update) if clients.has_client(update) else clients.append_client(bot, update)

    if datetime.now() - last_update_time > timedelta(hours=6):
        message = client.reply(
            text="{user} настало время обновить данные, погоди минутку ⌛".format(user=client.get_name()),
            clear_keyboard=False)
        try:
            g_data = get_params_from_google()
            payment_systems = tuple(g_data['paysystems'])
            expenses_category = tuple(g_data['costs']) + ('Удаленщики',)
            remote_category = tuple(g_data['remote'])
            last_update_time = datetime.now()
            client.edit_message(text="Обновил данные с гугла ✔".format(user=client.get_name()),
                                message_id=message.message_id)
        except Exception as error:
            client.edit_message(text="Произошла ошибка: {}, попробуйте позднее или какостыляйте Сашке!".format(error),
                                message_id=message.message_id)

    client.fsm.run(update.message.text)


def log_callback(bot, update):
    clients = Clients.instance()
    client = clients.get_client(update) if clients.has_client(update) else clients.append_client(bot, update)
    log_txt = "\n".join(log) if len(log) else "Пустота, тлен, одиночество..."
    client.reply(text=log_txt, clear_keyboard=False)


def main():
    updater = telegram.ext.Updater(token='330489753:AAGENGkD4sC0hrT6EG-bBoSKhff-oEmJz1I')

    clear_handler = CommandHandler('cls', clear_callback)
    start_cmd_handler = CommandHandler('start', start_callback)
    back_clear_cmd_handler = CommandHandler('b', back_clear_callback)
    info_cmd_handler = CommandHandler('info', info_callback)
    log_cmd_handler = CommandHandler('log', log_callback)
    record_cmd_handler = CommandHandler('r', record_callback)
    update_cmd_handler = CommandHandler('u', update_callback)

    message_handler = MessageHandler(filters=Filters.text, callback=message_callback)

    updater.dispatcher.add_handler(clear_handler)
    updater.dispatcher.add_handler(start_cmd_handler)
    updater.dispatcher.add_handler(back_clear_cmd_handler)
    updater.dispatcher.add_handler(info_cmd_handler)
    updater.dispatcher.add_handler(log_cmd_handler)
    updater.dispatcher.add_handler(record_cmd_handler)
    updater.dispatcher.add_handler(update_cmd_handler)

    updater.dispatcher.add_handler(message_handler)
    updater.dispatcher.add_error_handler(error_callback)

    # updater.start_polling()
    # updater.start_webhook(
    #     listen="127.0.0.1",
    #     port=5000,
    #     url_path='330489753:AAGENGkD4sC0hrT6EG-bBoSKhff-oEmJz1I')
    #
    # updater.bot.set_webhook(
    #     webhook_url="https://sasha.ml/330489753:AAGENGkD4sC0hrT6EG-bBoSKhff-oEmJz1I",
    #     certificate=open('/home/aleksandr/certificate.crt', 'rb')
    # )

    updater.start_webhook(listen='0.0.0.0',
                          port=8443,
                          url_path='330489753:AAGENGkD4sC0hrT6EG-bBoSKhff-oEmJz1I',
                          key='/home/aleksandr/ssl/private.key',
                          cert='/home/aleksandr/ssl/cert.pem',
                          webhook_url='https://sasha.ml:8443/330489753:AAGENGkD4sC0hrT6EG-bBoSKhff-oEmJz1I')
    # updater.bot.set_webhook("https://sasha.ml:8443/330489753:AAGENGkD4sC0hrT6EG-bBoSKhff-oEmJz1I")
    # updater.idle()

def message_sender():
    while True:
        try:
            client, id_message_for_replace = record_queue.get(True)
            google_send_record_thread(client, id_message_for_replace)
        except Exception as e:
            print(e)


if __name__ == '__main__':
    try:
        g_data = get_params_from_google()

        payment_systems = tuple(g_data['paysystems'])
        expenses_category = tuple(g_data['costs'])
        remote_category = tuple(g_data['remote'])

        last_update_time = datetime.now()

        threading.Thread(target=message_sender).start()
        print("Bot has running...")
        main()

    except Exception as error:
        print(error)
