#!/usr/bin/env python3

import argparse
import datetime
import ics
import lunarcalendar
import json
import os
import sys
from dataclasses import dataclass

@dataclass
class Person:
    name: str
    year: int # 出生的农历年份
    lunar_month: int
    lunar_day: int

    def zodiac(self) -> str:
        Zodiac = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]
        return Zodiac[(self.year - 2020) % 12] # 2020年是鼠年

def die(err):
    sys.exit(err)

def json_to_persons(json_file_path:str) -> list[Person]:
    ret = []
    with open(json_file_path, 'r', encoding='utf-8') as f:
        # json key
        KEY_PERSONS='persons'
        KEY_NAME = 'name'
        KEY_BIRTHDAY = 'birthday'
        KEY_LUNAR = 'lunar'

        json_object = json.load(f)
        if KEY_PERSONS in json_object:
            for person in json_object[KEY_PERSONS]:
                if KEY_NAME not in person:
                    die(f'missing key {KEY_NAME} in {json_file_path}')

                if KEY_BIRTHDAY not in person:
                    die(f'missing key {KEY_BIRTHDAY} in {json_file_path}')

                birthday = datetime.datetime.strptime(person[KEY_BIRTHDAY], '%Y-%m-%d')
                birthday_luna: lunarcalendar.Lunar = None

                if KEY_LUNAR in person and person[KEY_LUNAR] is True:
                    birthday_luna = lunarcalendar.Lunar(birthday.year, birthday.month, birthday.day)
                else:
                    birthday_luna = lunarcalendar.Converter.Solar2Lunar(lunarcalendar.Solar(birthday.year, birthday.month, birthday.day))

                ret.append(Person(person[KEY_NAME], birthday_luna.year, birthday_luna.month, birthday_luna.day))
        else:
            die(f'missing key {KEY_PERSONS} in {json_file_path}')
    return ret

# 返回值true表示成功添加，返回false表示超过了最大年龄
def append_birthday_to_calendar(calendar, person:Person, this_year, max_age) -> bool:
    age = this_year - person.year
    if age <= 0 or age > max_age:
        return False

    try:
        # 始终指定 isleap=False，只获取正式月份的日期
        new_birthday_lunar = lunarcalendar.Lunar(this_year, person.lunar_month, person.lunar_day, isleap=False)
        new_birthday_solar = lunarcalendar.Converter.Lunar2Solar(new_birthday_lunar)

        # 创建日历事件
        icsEvent = ics.Event()
        icsEvent.name = f'{person.name}的农历{age}岁生日'
        icsEvent.description = f'生日快乐，{person.year}年出生，属{person.zodiac()}，农历{person.lunar_month:02d}-{person.lunar_day:02d}'
        icsEvent.begin = datetime.datetime(new_birthday_solar.year, new_birthday_solar.month, new_birthday_solar.day)
        icsEvent.make_all_day()
        icsEvent.created = datetime.datetime.now()
        calendar.events.add(icsEvent)

    except lunarcalendar.DateNotExist:
        # 这种情况通常发生在：出生在农历30日，但这年的该农历月份只有29天（小月）
        # 此时跳过该年，不生成事件
        # print(f'Skipping {person.name} in {this_year} due to non-existent lunar date (e.g. 30th in short month)')
        pass

    return True

if __name__ == "__main__":
    script_file = os.path.basename(sys.argv[0])
    parser = argparse.ArgumentParser(prog=script_file,
                                     formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=80),
                                     description='A simple script to generate chinese lunar calendar birthday')
    parser.add_argument('-i', metavar='config.json', help='The input config file', required=True)
    parser.add_argument('-c', metavar='COUNT', help='The number of occurrences(in years), default value: 50', default=50, type=int)
    parser.add_argument('-m', metavar='MAX_AGE', help='Max age, default value: 100', default=100, type=int)

    args = vars(parser.parse_args())
    # print(args)

    json_file_path = args['i']
    event_count = args['c']
    max_age = args['m']

    persons = json_to_persons(json_file_path)
    # print(persons)

    calendar = ics.Calendar()
    event_steps = list(range(event_count))
    today_solar_year = datetime.datetime.today().year

    for person in persons:
        for step in event_steps:
            solar_new_year = today_solar_year + step

            if not append_birthday_to_calendar(calendar, person, solar_new_year, max_age):
                break # Next person

    print(calendar.serialize())