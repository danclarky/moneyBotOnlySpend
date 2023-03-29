import vk_api
import random
from psycopg2 import sql
import psycopg2
from datetime import datetime
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import json
import re
import calendar
import requests
import os

token = "token"
vk = vk_api.VkApi(token=token)

longpoll = VkBotLongPoll(vk, 'idbot')

user_id='53065529'
user_id_int=53065529

connection_parameters = {
    'dbname': 'Base',
    'user': 'user',
    'password': 'pass',
    'port':'port',
    'host': 'host'
    }


def update_balance_analiz(type,balance):
    conn = psycopg2.connect(**connection_parameters)
    with conn.cursor() as cursor:
        values = [(type,balance,datetime.today())]
        conn.autocommit = True
        insert = sql.SQL('INSERT INTO money_analiz (type,balance,date) VALUES {}').format(sql.SQL(',').join(map(sql.Literal, values)))
        cursor.execute(insert)

# Удаление последнего
def delete_last():
    conn = psycopg2.connect(**connection_parameters)
    with conn.cursor() as cursor:
        conn.autocommit = True
        delete = sql.SQL('DELETE FROM money_analiz WHERE code = (SELECT code FROM money_analiz ORDER BY code DESC LIMIT 1)')
        cursor.execute(delete)
    conn.close()

# Отправка вк
def write_msg(message):
    vk.method('messages.send', {'user_id': user_id, 'random_id': random.randint(1,999999999),'message': message,'keyboard':json.dumps({'buttons':[]})})

# Выборка Всего баланса
def select_from_acc(message):
    conn = psycopg2.connect(**connection_parameters)
    with conn.cursor() as cursor:
        cursor.execute("select balance,name from money_account ORDER BY code")
        for row in cursor:
            message+= row[1]+' '+row[0]+'\n'
    conn.close()
    return message

# Обновление баланса счета
def update_money_acc(balance,type):
    conn = psycopg2.connect(**connection_parameters)
    with conn.cursor() as cursor:
        conn.autocommit = True
        update = sql.SQL("update money_account set balance ='"+str(balance)+"' where name = '"+type+"'")
        cursor.execute(update)
    conn.close()

# Выборка баланса
def select_balance(type):
    balance = 0
    conn = psycopg2.connect(**connection_parameters)
    with conn.cursor() as cursor:
        cursor.execute("select balance from money_account where name = '"+type+"'")
        for row in cursor:
            balance = int(row[0])
    conn.close()
    return balance

# Выборка имени счета
def select_name_from_acc(synonym):
    conn = psycopg2.connect(**connection_parameters)
    with conn.cursor() as cursor:
        cursor.execute("select name from money_account where POSITION ('"+synonym+"' in synonyms) <> '0'")
        if(cursor.rowcount == 0):
            write_msg('Неправильно указан счет')
            type='false'
        for row in cursor:
            type = row[0]
    conn.close()
    return type

# Проверка есть ли комент
def check_comment(commentar):
    comment=''
    if len(commentar)>1:
        comment=commentar[1]
    return comment

# Помощь
def help():
    conn = psycopg2.connect(**connection_parameters)
    with conn.cursor() as cursor:
        message='Напоминалка\nСчета:\n'
        cursor.execute("select name,synonyms from money_account order by name")
        for row in cursor:
            message+= row[0]+' '+row[1]+'\n'
    with conn.cursor() as cursor:
        message+='Расходы:\n'
        cursor.execute("select name,synonyms,view from money_category_types where view='Расходы' order by name")
        for row in cursor:
            message+= row[0]+' '+row[1]+'\n'
    with conn.cursor() as cursor:
        message+='Доходы:\n'
        cursor.execute("select name,synonyms,view from money_category_types where view='Доходы' order by name")
        for row in cursor:
            message+= row[0]+' '+row[1]+'\n'
    conn.close()
    message+='Примеры:\nСбер 100 еда или Перевод сбер вклад 1000'
    return message

def select_delta_date(type,firstdate):
    conn = psycopg2.connect(**connection_parameters)
    delta = 0
    with conn.cursor() as cursor:
        cursor.execute("select SUM(cast(sum as int)) from money_analiz where type = '"+type+"' and date = '"+firstdate.strftime('%Y-%m-%d')+"'")
        for row in cursor:
            delta = row[0]
    conn.close()
    return delta




try:
    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW:
            if event.obj.from_id == user_id_int:
                request = event.obj.text
                commentar = request.split("*")
                txt = commentar[0].split(" ")
                # расход доход
                # Перевод
                if txt[0].lower() == 'баланс':
                    message='Сегодня: \n'
                    now = datetime.now()
                    message+='Расходы: '+str(select_delta_date('Расходы',now))+'\n'
                    write_msg(select_from_acc(message))
                else:
                    if len(txt)==3:
                        # Сумма
                        spent = txt[1]
                        date = txt[0]
                        # Проверка есть ли комент
                        comment = check_comment(commentar)
                        
                        # Запись в базу
                        conn = psycopg2.connect(**connection_parameters)
                        with conn.cursor() as cursor:
                            values = [('Spend',spent,'',date,'',comment)]
                            conn.autocommit = True
                            insert = sql.SQL('INSERT INTO money_analiz (type,sum,type_money,date,category,comment) VALUES {}').format(sql.SQL(',').join(map(sql.Literal, values)))
                            cursor.execute(insert)
                        conn.close()
                        
                        
                        # Отправка сообщения
                        message ='Сумма: '+spent+'р.'
                        if comment!='':
                            message +='Примечание: '+comment+'\n'
                        else:
                            message +='\n'
                        write_msg(message)
                    else:
                        write_msg('Допустил ошибку')
except (requests.exceptions.ConnectionError, TimeoutError, requests.exceptions.Timeout,requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout):
    os.startfile('vkbot.cmd')
