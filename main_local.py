from telegram.ext import Updater, CommandHandler, RegexHandler, MessageHandler, Filters
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
import enum, Levenshtein
import config, google

PAYSYSTEMS = tuple()
COSTS = tuple()
REMOTES = tuple()

BOT_STAGE = None

KEYBOARD_PAYSYSTEMS = ReplyKeyboardRemove()
KEYBOARD_COSTS = ReplyKeyboardRemove()
KEYBOARD_REMOVE = ReplyKeyboardRemove()
KEYBOARD_COMMENT = ReplyKeyboardRemove()
KEYBOARD_REMOTE = ReplyKeyboardRemove()

# TODO: dsdsds
class Stage(enum.Enum):
    CLEAR = 'clear'
    AMOUNT = 'amount'
    PAYSYSTEM = 'paysytem'
    COSTS = 'costs'
    REQUEST_COMMENT = 'request_comment'
    COMMENT = 'comment'
    REMOTE = 'check_remote'


def init():
    global PAYSYSTEMS, COSTS, REMOTES, BOT_STAGE
    try:
        sheet_data = google.get_params_from_google()
        PAYSYSTEMS = tuple(sheet_data['paysystems'])
        COSTS = tuple(sheet_data['costs'])
        REMOTES = tuple(sheet_data['remote'])
        BOT_STAGE = Stage.CLEAR
        update_keyboards()
        print("Init successfull: bot started")
    except Exception:
        raise


def update_keyboards():
    global KEYBOARD_PAYSYSTEMS, KEYBOARD_COSTS, KEYBOARD_REMOVE, KEYBOARD_COMMENT, KEYBOARD_REMOTE
    global PAYSYSTEMS, COSTS, REMOTES

    KEYBOARD_PAYSYSTEMS = ReplyKeyboardMarkup([[button] for button in PAYSYSTEMS])
    KEYBOARD_COSTS = ReplyKeyboardMarkup([[button] for button in COSTS])
    KEYBOARD_REMOTE = ReplyKeyboardMarkup([[button] for button in REMOTES])
    KEYBOARD_COMMENT = ReplyKeyboardMarkup([["Не хочу"]])
    KEYBOARD_REMOVE = ReplyKeyboardRemove()


def update_google_info():
    global PAYSYSTEMS, COSTS, REMOTES
    try:
        sheet_data = google.get_params_from_google()
        PAYSYSTEMS = tuple(sheet_data['paysystems'])
        COSTS = tuple(sheet_data['costs'])
        REMOTES = tuple(sheet_data['remote'])
        update_keyboards()
    except Exception as e:
        return False


lower_cast = lambda word: word.lower()
VALIDATORS = {
    "paysystem": lambda data: data.lower() in map(lower_cast, PAYSYSTEMS),
    "costs": lambda data: data.lower() in map(lower_cast, COSTS) or data.lower() in map(lower_cast, REMOTES),
    "amount": lambda data: isinstance(data, float),
    "comment": lambda data: True
}

MESSAGES = {
    "other_messages": "Я не в настроении разговаривать, попробуй добавить запись. Она должна начинатся с цифры",
    "amount": "Smartbot не смог обработать ваш запрос.\nПричина {}",
    "paysystem": {
        "not_found": "Не могу найти такую платежную систему, "
                     "попробуйте ввести заного или выбрать из списка на клавиатуре",
        "other": "Пожалуйста, введите или выберите платежную систему из списка на клавиатуре"
    },
    "costs": {
        "not_found": "Не могу определить категорию расходов, "
                     "попробуйте ввести заного или выбрать из списка на клавиатуре",
        "other": "Пожалуйста, введите или выберите категорию расходов из списка на клавиатуре",
    },
    "comment": "Пожалуйста введите комментарий к записи: {}",
    "untreated": "У вас есть необработанная запись {}",
    "in_work": "На обработку ушла запись: {}",
}

updater = Updater(config.TOKEN)
dispatcher = updater.dispatcher

record = dict()


def keyboard_search_paysytems_levenshtein(data):
    paysystems = list(PAYSYSTEMS)
    buttons = []
    index_of_search = len(data) * 0.7
    for key, paysytem in enumerate(paysystems):
        if Levenshtein.distance(data.lower(), paysytem.lower()) <= index_of_search:
            buttons.append(paysytem)
            del paysystems[key]
    return ReplyKeyboardMarkup([[button] for button in (buttons + paysystems)])


def check_word(sequence, word):
    indexes = []
    for sequence_word in sequence:
        indexes.append(Levenshtein.distance(word.lower(), sequence_word.lower()))
    return indexes


def test_search(inrow):
    costs = list(COSTS)
    res = dict()
    for key, row in enumerate(costs):
        res[row] = []
        for inword in inrow.split(' '):
            if len(inword) > 2:
                res[row].append(check_word(row.split(' '), inword))
    array = []

    for key in res:
        for i, indexes in enumerate(res[key]):
            res[key][i] = min(indexes)
        array.append((key, res[key]))

    array.sort(key=lambda item: min(item[1]))
    return ReplyKeyboardMarkup([[tuple_data[0]] for tuple_data in array])


def get_next_stage(current_stage):
    return {
        Stage.CLEAR: Stage.PAYSYSTEM,
        Stage.AMOUNT: Stage.PAYSYSTEM,
        Stage.PAYSYSTEM: Stage.COSTS,
        Stage.COSTS: Stage.COMMENT,
        Stage.REMOTE: Stage.COMMENT,
        Stage.COMMENT: Stage.CLEAR
    }[current_stage]


def check_and_write_to_record(field, data):
    global BOT_STAGE
    if not VALIDATORS[field](data):
        return False

    record[field] = data
    BOT_STAGE = get_next_stage(BOT_STAGE)
    return True


def start(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Hi")


def append(bot, update):
    global BOT_STAGE
    if not record:
        update_google_info()
        try:
            amount = config.AMOUNT_REGEXP.search(update.message.text).group(1)
            if not check_and_write_to_record('amount', float(amount)):
                raise Exception("Amount not a number")
        except Exception as e:
            bot.send_message(chat_id=update.message.chat_id,
                             text=MESSAGES['amount'].format(e))
            return
        try:
            paysystem = config.PAYSYTEM_REGEXP.search(update.message.text).group(1)
            if not check_and_write_to_record('paysystem', paysystem):
                bot.send_message(chat_id=update.message.chat_id,
                                 text=MESSAGES['paysystem']['not_found'],
                                 reply_markup=keyboard_search_paysytems_levenshtein(paysystem))
                return
        except Exception:
            bot.send_message(chat_id=update.message.chat_id,
                             text=MESSAGES['paysystem']["other"],
                             reply_markup=KEYBOARD_PAYSYSTEMS)
            return

        try:
            costs = config.COSTS_REGEXP.search(update.message.text).group(1)
            if costs.lower() == "Удаленщики".lower():
                BOT_STAGE = Stage.REMOTE
                bot.send_message(chat_id=update.message.chat_id,
                                 text="Вы указали в качестве расходов Удаленщиков, "
                                      "прийдется выбрать их на клаве или ввести",
                                 reply_markup=KEYBOARD_REMOTE)
                return
            else:
                if not check_and_write_to_record('costs', costs):
                    bot.send_message(chat_id=update.message.chat_id,
                                     text=MESSAGES['costs']['not_found'],
                                     reply_markup=test_search(costs))
                    return
        except Exception:
            bot.send_message(chat_id=update.message.chat_id,
                             text=MESSAGES['costs']['other'],
                             reply_markup=KEYBOARD_COSTS)
            return
        bot.send_message(chat_id=update.message.chat_id, text=MESSAGES['comment'].format(str(record)),
                         reply_markup=KEYBOARD_COMMENT)
    else:
        bot.send_message(chat_id=update.message.chat_id, text=MESSAGES['untreated'].format(str(record)))


def stage_handler(bot, update):
    global BOT_STAGE
    if BOT_STAGE is Stage.CLEAR:
        bot.send_message(chat_id=update.message.chat_id, text=MESSAGES['other_messages'])
    elif BOT_STAGE is Stage.PAYSYSTEM:
        if check_and_write_to_record('paysystem', update.message.text):
            bot.send_message(chat_id=update.message.chat_id, text=MESSAGES['costs']['other'],
                             reply_markup=KEYBOARD_COSTS)
        else:
            bot.send_message(chat_id=update.message.chat_id, text=MESSAGES['paysystem']['not_found'],
                             reply_markup=keyboard_search_paysytems_levenshtein(update.message.text))
    elif BOT_STAGE is Stage.COSTS:
        if update.message.text.lower() == "Удаленщики".lower():
            BOT_STAGE = Stage.REMOTE
            bot.send_message(chat_id=update.message.chat_id,
                             text="Вы указали в качестве расходов Удаленщиков, "
                                  "прийдется выбрать их на клаве или ввести",
                             reply_markup=KEYBOARD_REMOTE)
            return
        if check_and_write_to_record('costs', update.message.text):
            bot.send_message(chat_id=update.message.chat_id, text=MESSAGES['comment'].format(str(record)),
                             reply_markup=KEYBOARD_COMMENT)
        else:
            bot.send_message(chat_id=update.message.chat_id,
                             text=MESSAGES['costs']['not_found'],
                             reply_markup=test_search(update.message.text))
    elif BOT_STAGE is Stage.REMOTE:
        if check_and_write_to_record('costs', update.message.text):
            bot.send_message(chat_id=update.message.chat_id, text=MESSAGES['comment'].format(str(record)),
                             reply_markup=KEYBOARD_COMMENT)
        else:
            bot.send_message(chat_id=update.message.chat_id,
                             text=MESSAGES['costs']['not_found'],
                             reply_markup=[[button] for button in REMOTES])
    elif BOT_STAGE is Stage.COMMENT:
        if update.message.text != "Не хочу":
            check_and_write_to_record('comment', update.message.text)
        else:
            check_and_write_to_record('comment', '')

        response = google.post_record_to_google(record)
        if response['success']:
            bot.send_message(
                chat_id=update.message.chat_id,
                text="Запись успешно добавленна",
                reply_markup=KEYBOARD_REMOVE)
        else:
            bot.send_message(
                chat_id=update.message.chat_id,
                text="Произошла ошибка при добавлении: {}".format(response['message']),
                reply_markup=KEYBOARD_REMOVE)
        record.clear()


def debug(bot, update):
    bot.send_message(
        chat_id=update.message.chat_id,
        text="Record: {}\nStage: {}\nPaysystems: {}\nCosts: {}\nRemote: {}"
            .format(str(record), BOT_STAGE.name, str(PAYSYSTEMS), str(COSTS), str(REMOTES))
    )


def abort(bot, update):
    global BOT_STAGE
    record.clear()
    BOT_STAGE = Stage.CLEAR
    bot.send_message(
        chat_id=update.message.chat_id,
        text="Record: {}\nStage: {}\nPaysystems: {}\nCosts: {}"
            .format(str(record), BOT_STAGE.name, str(PAYSYSTEMS), str(COSTS)),
        reply_markup=KEYBOARD_REMOVE
    )


# dispatcher.add_handler(CommandHandler('start', start))
# dispatcher.add_handler(CommandHandler('debug', debug))
# dispatcher.add_handler(CommandHandler('abort', abort))
# dispatcher.add_handler(RegexHandler(r"^\d+\.?\d*", append))
# dispatcher.add_handler(MessageHandler(filters=Filters.text, callback=stage_handler))
#
# init()
# updater.start_polling()
# updater.idle()


if __name__ == '__main__':
    start()