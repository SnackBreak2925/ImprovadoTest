import vk_api
import sys
import datetime
from getpass import getpass
import msvcrt
import os
import re
import csv
import json


def resolve_url(url, api):
    screen_name = url.split('/')[-1]
    user_id = api.utils.resolveScreenName(screen_name=screen_name)
    return user_id['object_id']


def parse_answer(friend_list, keys):
    # функция для парсинга ответа от сервера и записи нужных данных
    adapted_list = []
    for i in range(len(friend_list)):
        adapted_list.append(dict.fromkeys(keys))
        adapted_list[i]['first_name'] = friend_list[i].get('first_name')
        if friend_list[i].get('last_name'):
            adapted_list[i]['last_name'] = friend_list[i].get('last_name')
        else:
            adapted_list[i]['last_name'] = None
        if friend_list[i].get('country'):
            adapted_list[i]['country'] = friend_list[i].get('country').get('title')
        else:
            adapted_list[i]['country'] = None
        if friend_list[i].get('city'):
            adapted_list[i]['city'] = friend_list[i].get('city').get('title')
        else:
            adapted_list[i]['city'] = None
        if friend_list[i].get('bdate'):
            if re.findall(r'\d{1,2}.\d{1,2}.\d{4}', friend_list[i].get('bdate')):
                adapted_list[i]['bdate'] = datetime.datetime.strptime(friend_list[i].get('bdate'),
                                                                      '%d.%m.%Y').date().isoformat()
            else:
                adapted_list[i]['bdate'] = datetime.datetime.strptime(friend_list[i].get('bdate') + '.1600',  # костыль
                                                                      '%d.%m.%Y').date().isoformat()
            # если пользователь не указывал год рождения библиотека datetime по умолчанию ставит 1900 год,
            # что вызывает ошибки если пользователь указал 29 февраля днем рождения, но 1900 год не является високосным
            # что вызывает ошибку
            # те, у кого не указан либо не виден год рождения в итоговом списке будут иметь 1600 год рождения
            # отсутствие года в формате ISO недопустимо (насколько я понял формат)
        else:
            adapted_list[i]['bdate'] = None
        if friend_list[i].get('sex') == 1:
            adapted_list[i]['sex'] = 'female'
        else:
            adapted_list[i]['sex'] = 'male'
    return adapted_list


def captcha_handler(captcha):
    image_text = input("Enter captcha code {0}: ".format(captcha.get_url())).strip()
    return captcha.try_again(image_text)


def auth_handler():
    fa_code = input('2FA Code: ')
    save_device = True
    return fa_code, save_device


def authorization():
    while True:
        os.system('cls')
        login = input('Login: ')
        password = getpass('Password: ')
        session = vk_api.VkApi(login=login, password=password, auth_handler=auth_handler,
                               captcha_handler=captcha_handler, api_version='5.131')
        try:
            session.auth()
            return session.get_api()
        except Exception as ex:
            print(ex)
            print('Press any key to try again')
            msvcrt.getch()


def to_csv(friend_list, out, keys):
    csv_writer = csv.DictWriter(out, fieldnames=keys)
    for i in friend_list:
        csv_writer.writerow(i)


def to_tsv(friend_list, out, keys):
    # используется модуль csv так как отличие csv и tsv в разделителе запятой и табуляции соответвенно
    # это единственное отличие и записать в файл через модуль используя табуляции вместо запятых возможно
    tsv_writer = csv.DictWriter(out, fieldnames=keys, delimiter='\t')
    for i in friend_list:
        tsv_writer.writerow(i)


def to_json(friend_list, out):
    out.write(json.dumps(friend_list, ensure_ascii=False, indent=4))


def get_friend_list(vk, keys):
    user_id = 0
    while True:
        target = input('Enter the URl address of the user for whom you want to get a list of friends: ')
        user_id = resolve_url(target, vk)
        if vk.users.get(user_id=user_id)[0]['can_access_closed']:
            break
        else:
            print('Account is closed for you enter another user')
    friends_count = vk.friends.get(user_id=user_id, count=1)['count']
    # при подобных запросах невозможно получить информацию более чем о 5000 друзьях потому запрос
    # должен дублироваться со смещением
    # так же вк имеет ограничение на 10000 друзей у одного пользователя
    raw_list = vk.friends.get(user_id=user_id, order='name', count=friends_count, fields='country,city,bdate,sex',
                              name_case='nom')['items']
    friend_list = parse_answer(raw_list, keys)
    if friends_count > 5000:
        raw_list = vk.friends.get(user_id=user_id, order='name',
                                  count=friends_count - 5000, offset=10000 - friends_count,
                                  fields='country,city,bdate,sex',
                                  name_case='nom')['items']
        friend_list.extend(parse_answer(raw_list, keys))

    return friend_list


def main():
    keys = ['first_name', 'last_name', 'country', 'city', 'bdate', 'sex']
    # ключи итогового списка вынесены сюда и тащаться по функциям до одной потому что они понадобятся при записи в файл
    vk = authorization()
    os.system('cls')
    friend_list = get_friend_list(vk, keys)
    filetype = 'csv'
    filename = 'report'
    path = ''
    out = ''
    format_re = re.compile(r'json|tsv|csv')
    name_re = re.compile(r'[^\\/:*?\"<>|]+')
    while True:
        select_path = input('Enter a folder to save the report (empty if deafult): ')
        select_name = input('Enter name of report file (empty if deafult): ')
        select_type = input('Enter type of file (csv/tsv/json) (empty if deafult): ')
        if (not select_type or format_re.fullmatch(select_type)) and (
                not select_name or name_re.fullmatch(select_name)):
            if select_type:
                filetype = select_type
            if select_name:
                filename = select_name
            path = select_path
            if path:
                pathname = path + '\\' + filename + '.' + filetype
            else:
                pathname = filename + '.' + filetype
            out = open(pathname, 'w')
            if out:
                break
            else:
                print('Wrong input try again')
        else:
            print('Wrong input try again')

    if filetype == 'csv':
        to_csv(friend_list, out, keys)
    elif filetype == 'tsv':
        to_tsv(friend_list, out, keys)
    elif filetype == 'json':
        to_json(friend_list, out)

    out.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
