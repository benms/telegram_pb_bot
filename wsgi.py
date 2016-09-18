# -*- coding: utf-8 -*-
import telebot
import config
import pb
import datetime
import pytz
import json
import traceback

P_TIMEZONE = pytz.timezone(config.TIMEZONE)
TIMEZONE_COMMON_NAME = config.TIMEZONE_COMMON_NAME
bot = telebot.TeleBot(config.TOKEN)


@bot.message_handler(commands=['start'])
def start_command(message):
    """
    Handler for /start command
    :param message: deserialized Telegram Message (https://core.telegram.org/bots/api#message)
    """
    bot.send_message(
        message.chat.id,
        'Привет! Я помогу узнать тебе курс валют Приват Банка.\n' +
        'Чтобы получить курс валют, нажми /exchange.\n' +
        'Для справки нажми /help. '
    )


# @bot.message_handler(commands=['test'])
# def start_command(message):
#     """
#     Handler for /start command
#     :param message: deserialized Telegram Message (https://core.telegram.org/bots/api#message)
#     """
#     bot.send_message(
#         message.chat.id,
#         'Test ' + message.text
#     )


@bot.message_handler(commands=['usd_stat'])
def usd_stat_command(message):
    """
    Handler for /usd_stat command
    :param message: deserialized Telegram Message (https://core.telegram.org/bots/api#message)
    """
    num_list = message.text.split('/usd_stat')
    num = int(num_list[1]) if (len(num_list[1]) > 0) else 0
    month_str = 'прошлый' if (num == 0) else str(num)
    chat_id = message.chat.id
    bot.send_chat_action(chat_id, 'typing')
    str_aver_usd = str(pb.get_month_average_usd_stat(num))
    bot.send_message(
        chat_id, 'Средний курс - ' + str_aver_usd + " за доллар за " + month_str + " месяц \n"
    )


@bot.message_handler(commands=['help'])
def help_command(message):
    """
    Handler for /help command.
    :param message: deserialized Telegram Message (https://core.telegram.org/bots/api#message)
    """
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(
        telebot.types.InlineKeyboardButton('Написать разработчику', url='telegram.me/artiomtb')
    )
    bot.send_message(
        message.chat.id,
        '1) Для получения списка доступных валют нажми /exchange.\n' +
        '2) Нажми на валюту, которая тебя интересует.\n' +
        '3) Ты получишь сообщение, которое будет содержать информацию о исходной и целевой валюте, ' +
        'курс покупки и продажи.\n' +
        '4) Нажми "Обновить" для получения актуальной информации по запросу. ' +
        'Бот так же покажет разницу между предыдущим курсом и текущим.\n' +
        '5) Бот поддерживает inline. Набери @exchangetestbot в любом чате и первые буквы валюты.',
        reply_markup=keyboard
    )


@bot.message_handler(commands=['exchange'])
def exchange_command(message):
    """
    Handler for /exchange command. Sends message with inline keyboard for choosing currency.
    :param message: deserialized Telegram Message (https://core.telegram.org/bots/api#message)
    """
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.row(
        telebot.types.InlineKeyboardButton('USD', callback_data='get-USD'),
        telebot.types.InlineKeyboardButton('EUR', callback_data='get-EUR')
    )
    keyboard.row(
        telebot.types.InlineKeyboardButton('RUR', callback_data='get-RUR'),
        telebot.types.InlineKeyboardButton('BTC', callback_data='get-BTC')
    )
    bot.send_message(message.chat.id, 'Нажми на выбранную валюту:', reply_markup=keyboard)


@bot.inline_handler(func=lambda query: True)
def query_text(inline_query):
    """
    Handler for inline query. Sends inline query answer with list of currencies.
    :param inline_query: deserialized Telegram InlineQuery (https://core.telegram.org/bots/api#inlinequery)
    """
    bot.answer_inline_query(
        inline_query.id,
        get_iq_articles(pb.get_exchanges(inline_query.query))
    )


@bot.message_handler(regexp='^USD$')
def get_usd_ex(message):
    """
    Handler for text request equal 'USD'. Sends USD exchange result
    :param message: deserialized Telegram Message (https://core.telegram.org/bots/api#message)
    """
    send_exchange_result(message, 'USD')


@bot.message_handler(regexp='^EUR$')
def get_usd_ex(message):
    """
    Handler for text request equal 'EUR'. Sends EUR exchange result
    :param message: deserialized Telegram Message (https://core.telegram.org/bots/api#message)
    """
    send_exchange_result(message, 'EUR')


@bot.message_handler(regexp='^RUR$')
def get_usd_ex(message):
    """
    Handler for text request equal 'RUR'. Sends RUR exchange result
    :param message: deserialized Telegram Message (https://core.telegram.org/bots/api#message)
    """
    send_exchange_result(message, 'RUR')


@bot.message_handler(regexp='^BTC$')
def get_btc_ex(message):
    """
    Handler for text request equal 'BTC'. Sends BTC exchange result
    :param message: deserialized Telegram Message (https://core.telegram.org/bots/api#message)
    """
    send_exchange_result(message, 'BTC')


@bot.callback_query_handler(func=lambda call: True)
def iq_callback(query):
    """
    Handler for answer callback query. Called when user taps on inline button (get currency or update currency result)
    :param query: deserialized Telegram CallbackQuery (https://core.telegram.org/bots/api#callbackquery)
    """
    data = query.data
    if data.startswith('update-'):
        old_edit_message_callback(query)
    elif data.startswith('get-'):
        get_ex_callback(query)
    else:
        try:
            if json.loads(data)['t'] == 'u':
                edit_message_callback(query)
        except ValueError:
            pass


def edit_message_callback(query):
    """
    Method called when user taps on update button. Sends message update  (works for inline and normal messages)
    :param query: deserialized Telegram CallbackQuery (https://core.telegram.org/bots/api#callbackquery)
    """
    data = json.loads(query.data)['e']
    exchange_now = pb.get_exchange(data['c'])
    text = serialize_ex(
        exchange_now,
        get_exchange_diff(
            get_ex_from_iq_data(data),
            exchange_now
        )
    ) + '\n' + get_edited_signature()
    if query.message:
        bot.edit_message_text(
            text,
            query.message.chat.id,
            query.message.message_id,
            reply_markup=get_update_keyboard(exchange_now),
            parse_mode='HTML'
        )
    elif query.inline_message_id:
        bot.edit_message_text(
            text,
            inline_message_id=query.inline_message_id,
            reply_markup=get_update_keyboard(exchange_now),
            parse_mode='HTML'
        )


def old_edit_message_callback(query):
    """
    Deprecated method. For updating old messages (with inline query format 'update-'.
    Sends message update  (works for inline and normal messages)
    :param query: deserialized Telegram CallbackQuery (https://core.telegram.org/bots/api#callbackquery)
    """
    exc = pb.get_exchange(query.data[7:])
    text = serialize_ex(exc) + '\n' + get_edited_signature()
    if query.message:
        bot.edit_message_text(
            text,
            query.message.chat.id,
            query.message.message_id,
            reply_markup=get_update_keyboard(exc),
            parse_mode='HTML'
        )
    elif query.inline_message_id:
        bot.edit_message_text(
            text,
            inline_message_id=query.inline_message_id,
            reply_markup=get_update_keyboard(exc),
            parse_mode='HTML'
        )


def get_edited_signature():
    """
    Returns string with update text (contains date in config-specific timezone)
    :return str: update text
    """
    return '<i>Обновлено ' + \
           str(datetime.datetime.now(P_TIMEZONE).strftime('%H:%M:%S')) + \
           ' (' + TIMEZONE_COMMON_NAME + ')</i>'


def get_ex_callback(query):
    """
    Sends answer for user's exchange request by inline button
    :param query: deserialized Telegram CallbackQuery (https://core.telegram.org/bots/api#callbackquery)
    """
    bot.answer_callback_query(query.id)
    send_exchange_result(query.message, query.data[4:])


def send_exchange_result(message, ex_code):
    """
    Sends exchange result to chat. Before sends 'typing' action.
    :param message: deserialized Telegram Message (https://core.telegram.org/bots/api#message)
    :param ex_code: string with code of currency, for example 'USD'
    """
    bot.send_chat_action(message.chat.id, 'typing')
    ex = pb.get_exchange(ex_code)
    bot.send_message(
        message.chat.id, serialize_ex(ex),
        reply_markup=get_update_keyboard(ex),
        parse_mode='HTML'
    )


def get_update_keyboard(ex):
    """
    Returns keyboard with Update and Share buttons.
    :param ex: dict with exchange information ('ccy', 'buy', 'sale', 'base_ccy')
    :return telebot.types.InlineKeyboardMarkup: prototype of Telegram InlineKeyboardMarkup
    (https://core.telegram.org/bots/api#inlinekeyboardmarkup)
    """
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.row(
        telebot.types.InlineKeyboardButton(
            'Обновить',
            callback_data=json.dumps({
                't': 'u',
                'e': {
                    'b': ex['buy'],
                    's': ex['sale'],
                    'c': ex['ccy']
                }
            }).replace(' ', '')
        ),
        telebot.types.InlineKeyboardButton('Поделиться', switch_inline_query=ex['ccy'])
    )
    return keyboard


def get_iq_articles(exchanges):
    """
    Function for transform list of exchanges tolist of Telegram InlineQueryResultArticle
    (https://core.telegram.org/bots/api#inlinequeryresultarticle)
    :param exchanges: list of exchanges dict
    :return: list of telebot.types.InlineQueryResultArticle
    """
    result = []
    for exc in exchanges:
        result.append(
            telebot.types.InlineQueryResultArticle(
                exc['ccy'],
                exc['ccy'],
                telebot.types.InputTextMessageContent(serialize_ex(exc), parse_mode='HTML'),
                reply_markup=get_update_keyboard(exc),
                description='Перевод ' + exc['base_ccy'] + ' -> ' + exc['ccy'],
                thumb_height=1
            )
        )
    return result


def get_exchange_diff(last, now):
    """
    Calculates diff between currencies in dict format with 'sale_diff' and 'buy_diff' keys
    :param last: last dict exchange with 'buy', 'sale' keys
    :param now: current dict exchange with 'buy', 'sale' keys
    :return: dict with keys 'sale_diff' and 'buy_diff'
    """
    return {
        'sale_diff': float("%.6f" % (float(now['sale']) - float(last['sale']))),
        'buy_diff': float("%.6f" % (float(now['buy']) - float(last['buy'])))
    }


def serialize_ex(ex_json, diff=None):
    """
    Serializes exchange to string. If parameter diff specified - it will be also added to result
    :param ex_json: dict with exchange information ('ccy', 'buy', 'sale', 'base_ccy')
    :param diff: dict with diff information ('buy_diff', 'sale_diff')
    :return: string with exchange information
    """
    result = '<b>' + ex_json['base_ccy'] + ' -> ' + ex_json['ccy'] + ':</b>\n\n' + \
             'Покупка: ' + ex_json['buy']
    if diff:
        result += ' ' + serialize_exchange_diff(diff['buy_diff']) + '\n' + \
                  'Продажа: ' + ex_json['sale'] + \
                  ' ' + serialize_exchange_diff(diff['sale_diff']) + '\n'
    else:
        result += '\nПродажа: ' + ex_json['sale'] + '\n'
    return result


def serialize_exchange_diff(diff):
    """
    Serializes exchange diff to string
    :param diff: dict with diff information ('buy_diff', 'sale_diff')
    :return: string with diff information
    """
    result = ''
    if diff > 0:
        result = '(' + str(diff) + ' ↗️)'
    elif diff < 0:
        result = '(' + str(diff)[1:] + ' ↘️)'
    return result


def get_ex_from_iq_data(exc_json):
    """
    Returns exchange dict from dict with keys 'b' and 's' (comes from callback_data in messages)
    :param exc_json: dict with keys 'b' and 's'
    :return: dict with keys 'buy' and 'sale'
    """
    return {
        'buy': exc_json['b'],
        'sale': exc_json['s']
    }


try:
    bot.polling(none_stop=True)
except Exception as e:
    traceback = traceback.format_exc()
    print(traceback)
    bot.send_message(config.SUPPORT_CHAT_ID, traceback)
