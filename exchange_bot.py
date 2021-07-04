from config import bot_token, exchange_token
import requests
import sqlite3
import datetime
import os
import telebot
import plotly.graph_objects as go

bot = telebot.TeleBot(bot_token)


def update_database(data):
    connect = sqlite3.connect('exchange.db')
    cursor = connect.cursor()

    exchange_data = data['price']
    exchange_data['timestamp'] = data['timestamp']

    for i in exchange_data:
        exchange_data[i] = format(exchange_data[i], '.2f')

    cursor.execute(f"UPDATE exchange SET EURUSD = {exchange_data['EURUSD']}, GBPUSD = {exchange_data['GBPUSD']}, timestamp = {exchange_data['timestamp']}")

    connect.commit()


def check_for_update():
    connect = sqlite3.connect('exchange.db')
    cursor = connect.cursor()

    data = requests.get(
        f"https://fxmarketapi.com/apilive?api_key={exchange_token}&currency=EURUSD,GBPUSD"
    ).json()
    timestamp_new = data['timestamp']

    cursor.execute("SELECT timestamp FROM exchange")
    timestamp = cursor.fetchone()

    if timestamp_new - float(timestamp[0]) >= 600:
        update_database(data)


@bot.message_handler(commands=['start'])
def start_command(message):
    bot.send_message(message.chat.id, """Hello, this bot was created for discovering currency of USD
relatively EUR and GBP. Write /help to find out commands""")

    connect = sqlite3.connect('exchange.db')
    cursor = connect.cursor()

    data = requests.get(
        f"https://fxmarketapi.com/apilive?api_key={exchange_token}&currency=EURUSD,GBPUSD"
    ).json()
    exchange_data = data['price']

    for i in exchange_data:
        exchange_data[i] = format(exchange_data[i], '.2f')

    exchange_data['timestamp'] = data['timestamp']

    cursor.execute("DROP TABLE IF EXISTS exchange")

    cursor.execute("""CREATE TABLE IF NOT EXISTS exchange(
            EURUSD VARCHAR(4),
            GBPUSD VARCHAR(4),
            timestamp VARCHAR(10)
        )""")

    cursor.execute("INSERT INTO exchange(EURUSD, GBPUSD, timestamp) VALUES(:EURUSD,:GBPUSD,:timestamp);", exchange_data)

    connect.commit()

    print(f"User {message.chat.id} execute command /start")


@bot.message_handler(commands=['help'])
def help_currency(message):
    bot.send_message(message.chat.id, """/lst or /list - list of all available rates (EUR and GBP)
        
/exchange {amount} USD to {currency(EUR or GBP)} - converts to the second currency
    
/history USD/{currency(EUR or GBP)} for {amount} day(s) - image graph chart which shows the exchange rate graph/chart 
of the selected currency for the last some days""")

    print(f"User {message.chat.id} execute command /help")


@bot.message_handler(commands=['list', 'lst'])
def list_currency(message):
    connect = sqlite3.connect('exchange.db')
    cursor = connect.cursor()

    check_for_update()

    cursor.execute("SELECT * FROM exchange")
    data_exchange = cursor.fetchall()

    bot.send_message(message.chat.id, f"EUR: {data_exchange[0][0]}\nGBP: {data_exchange[0][1]}")

    print(f"User {message.chat.id} execute command /lst or /list")


@bot.message_handler(commands=['exchange'])
def exchange_currency(message):
    try:
        connect = sqlite3.connect('exchange.db')
        cursor = connect.cursor()

        check_for_update()

        get_text = message.text.split()
        currency = get_text[4] + "USD"

        cursor.execute(f"SELECT {currency} FROM exchange")
        data_currency = cursor.fetchone()

        new_value = float(get_text[1]) * float(data_currency[0][0])
        new_value = format(new_value, '.2f')

        bot.send_message(message.chat.id, '$' + str(new_value))

        print(f"User {message.chat.id} execute command /exchange (Successful)")
    except IndexError:
        bot.send_message(message.chat.id, "Try again. Sample:\n/exchange 10 USD to EUR")

        print(f"User {message.chat.id} execute command /exchange (Error)")


@bot.message_handler(commands=['history'])
def history_currency(message):
    try:
        name = str(message.chat.id) + ".png"

        if os.path.isfile(name):
            os.remove(name)

        connect = sqlite3.connect('exchange.db')
        cursor = connect.cursor()

        check_for_update()

        get_text = message.text.split()
        days = int(get_text[3])
        curr = get_text[1].replace("USD/", '')

        cursor.execute("SELECT timestamp FROM exchange")
        timestamp = cursor.fetchone()
        timestamp_end = int(timestamp[0], base=10) - 86400
        timestamp_start = timestamp_end - 86400 * days

        value_end = datetime.datetime.fromtimestamp(timestamp_end)
        value_end = value_end.strftime('%Y-%m-%d')

        value_start = datetime.datetime.fromtimestamp(timestamp_start)
        value_start = value_start.strftime('%Y-%m-%d')

        data = requests.get(
            f"https://fxmarketapi.com/apitimeseries?api_key={exchange_token}&currency=EURUSD,GBPUSD"
            f"&start_date={value_start}&end_date={value_end}&format=ohlc"
        ).json()

        date = []
        currency = []

        try:
            for i in data['price']:
                date.append(i)
                currency.append(data['price'][i][f'{curr}USD']['close'])

            fig = go.Figure(data=go.Bar(x=date, y=currency))
            fig.write_image(f'{message.chat.id}.png')

            p = open(name, 'rb')
            bot.send_photo(message.chat.id, p)

            print(f"User {message.chat.id} execute command /history (Successful)")
        except KeyError:
            bot.send_message(message.chat.id, "No exchange rate data is available for the selected currency")

            print(f"User {message.chat.id} execute command /history (Error of api)")
    except IndexError:
        bot.send_message(message.chat.id, "Try again. Sample:\n/history USD/GBP for 7 days")

        print(f"User {message.chat.id} execute command /history (Error)")
        
        
def main():
    bot.polling(none_stop=True)
        

if __name__ == '__main__':
    main()
