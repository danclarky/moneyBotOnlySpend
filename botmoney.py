import vk_api
import random
from psycopg2 import sql
import psycopg2
from datetime import datetime, timedelta
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import json
import re
import calendar
import requests
import os

with open('cred.json', 'r', encoding='utf-8') as f:
    text = json.load(f)

token = text['vk']['token']
vk = vk_api.VkApi(token=token)

longpoll = VkBotLongPoll(vk, text['vk']['group_id'])

user_id = text['vk']['user_id']
user_id_int = text['vk']['user_id_int']

connection_parameters = text['db']

# Удаление последнего
def delete_last():
    conn = psycopg2.connect(**connection_parameters)
    with conn.cursor() as cursor:
        conn.autocommit = True
        delete = sql.SQL(
            'DELETE FROM money_analiz WHERE code = (SELECT code FROM money_analiz ORDER BY code DESC LIMIT 1)'
        )
        cursor.execute(delete)
    conn.close()


# Отправка вк
def write_msg(message):
    vk.method(
        'messages.send', {
            'user_id': user_id,
            'random_id': random.randint(1, 999999999),
            'message': message,
            'keyboard': json.dumps({'buttons': []})
        })

def select_delta_date(type, firstdate):
    dates = ''
    typeSQL = 0
    if(not isinstance(firstdate, str)):
        firstdate = firstdate.strftime('%d.%m.%Y')
    else:
        dates = firstdate.split("-")
    sql = "select cast(sum as int), comment, date from money_analiz where type = '" + type + "' and date = '" + firstdate + "'"
    if len(dates) == 2:
        typeSQL = 1
        sDate = dates[0]
        eDate = dates[1]
        sql = "SELECT cast(sum as int),comment,date from money_analiz where type = '" + type + "' and date between '" + sDate + "' and '"+eDate+"' group by date,sum,comment"
    conn = psycopg2.connect(**connection_parameters)
    message = ''
    messageTxt=''
    summa = 0
    
    try:
        with conn.cursor() as cursor:                     
            cursor.execute(sql)
            for row in cursor:
                if typeSQL == 1:
                    messageTxt +=  '❗'+row[2].strftime('%d.%m.%Y')+ '\n'
                messageTxt += str(row[0]) + ' ' + row[1] +'\n'
                summa += row[0]
        conn.close()
    except:
        write_msg('Допустил ошибку')
    if summa != 0:
        if typeSQL == 0:
            message = '❗'+firstdate+'\n'
        message += messageTxt + '📌Всего: ' + str(summa)
    else:
        message = 'пусто'
    return message


try:
    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW:
            if event.obj.from_id == user_id_int:
                request = event.obj.text
                commentar = request.split("*")
                txt = commentar[0].split(" ")
                if len(txt) == 2: 
                    match txt[0]:
                        case 'баланс':
                            date = txt[1]
                            match date:
                                case 'сегодня':
                                    date = datetime.now()
                                case 'вчера':
                                    date = datetime.now() - timedelta(days=1)
                            message = str(select_delta_date('Spend', date))
                            write_msg(message)
                        case  _:
                            spent = txt[1]
                            date = txt[0]
                            match date:
                                case 'сегодня':
                                    date = datetime.now()
                                case 'вчера':
                                    date = datetime.now() - timedelta(days=1)
                            comment = commentar[1]
                            conn = psycopg2.connect(**connection_parameters)
                            try:
                                with conn.cursor() as cursor:
                                    values = [
                                        ('Spend', spent, date, comment)]
                                    conn.autocommit = True
                                    insert = sql.SQL('INSERT INTO money_analiz (type,sum,date,comment) VALUES {}').format(
                                        sql.SQL(',').join(map(sql.Literal, values)))
                                    cursor.execute(insert)
                                    conn.close()
                            except:
                                   write_msg('Допустил ошибку')
                            message = spent + '\n' + comment
                            write_msg(message)
                elif txt[0] == 'забыл':
                    write_msg('баланс вчера' + '\n' + 'баланс 29.03.2023' + '\n' + 'сегодня 500*комент' + '\n' + '01.03.2023 600*комент')
                elif txt[0] == 'удали':
                    delete_last()
                    write_msg('готово')
                else:
                    write_msg('Допустил ошибку')
except (requests.exceptions.ConnectionError, TimeoutError,
        requests.exceptions.Timeout, requests.exceptions.ConnectTimeout,
        requests.exceptions.ReadTimeout):
    os.startfile('vkbot.cmd')
