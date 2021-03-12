import os
import argparse
import string
import inquirer
import random
import re
import hashlib
import requests
import time

from dotenv import load_dotenv
from selenium import webdriver

browsers = ('Chrome', 'Safari', 'Firefox', 'Opera')

load_dotenv()
headers = {
    'x-rapidapi-key': os.environ.get('x-rapidapi-key'),
    'x-rapidapi-host': os.environ.get('x-rapidapi-host')
}


def random_string(length: int) -> str:
    return ''.join(random.choice(string.ascii_letters) for _ in range(length))


def is_email_valid(email) -> bool:
    pattern = r"\"?([-a-zA-Z0-9.`?{}]+@\w+\.\w+)\"?"
    return bool(re.match(pattern, email))


def get_domains() -> list:
    """Return domains list"""
    url = "https://privatix-temp-mail-v1.p.rapidapi.com/request/domains/"

    response = requests.request("GET", url, headers=headers)
    if not isinstance(response.json(), list):
        raise Exception("Domain acquisition error")
    return response.json()


def get_mails(email: str):
    """Return mails list from random mail"""
    url = os.environ.get('url_for_mail') + hashlib.md5(email.encode()).hexdigest() + '/'

    response = requests.request("GET", url, headers=headers)
    return response.json()


def parse_and_save_data(email: str, login=None, password=None):
    messages = get_mails(email)
    for i in range(5):
        try:
            if messages.get('error'):
                print(f'The mail did not arrive. It will be repeated in 5 seconds ({i + 1}/5)')
                time.sleep(5)
                messages = get_mails(email)
        except AttributeError:
            break
    else:
        print('The mail did not arrive on' + email)

    for message in messages:
        if 'успешно создан' in message['mail_subject']:
            mail_text = message['mail_text_only'].replace(' ', '')
            login = re.findall(r'Логин:<strong>(.*?)</strong>', mail_text, re.DOTALL)[0]
            password = re.findall(r'Пароль:<strong>(.*?)</strong>', mail_text, re.DOTALL)[0]

    if login and password:
        with open('accounts_data.txt', 'a+') as f:
            f.write(f"[\ne:{email};\nl:{login};\np:{password}\n],")


def check_data(name, email):
    if not is_email_valid(email) or len(name) < 3:
        raise Exception("Invalid data")


def randomed_data():
    """Return list with random full name(index 0) email(index 1)"""
    return random_string(20), (random_string(20) + random.choice(domains)).lower()


def input_missing(func):
    """decorator input missing elements """

    def inner():
        arguments = func()
        questions = [
            inquirer.List('browser', message='What browser do you want to use?', choices=browsers),
            inquirer.Text('name', message='Full name: '),
            inquirer.Text('email', message='E-Mail: ')
        ]

        browser = arguments.get('browser') if arguments.get('browser') \
            else inquirer.prompt([questions[0], ]).get('browser')

        if arguments.get('rand'):
            return {
                'browser': browser,
                'rand': arguments.get('rand')
            }

        else:
            name, email = arguments.get('name'), arguments.get('email')

            # TODO: Refactor
            if not arguments.get('name'):
                name = inquirer.prompt((questions[1],)).get('name')
            if not arguments.get('email'):
                email = inquirer.prompt((questions[2],)).get('email')
            check_data(name, email)

            return {
                'browser': browser,
                'name': name,
                'email': email,
                'rand': arguments.get('rand'),
            }

    return inner


def register(browser, name, email, count):
    """TimeWeb account registration"""

    is_random = bool(count)
    if not is_random:
        count = 1

    for i in range(count):
        driver = webdriver.__dict__[browser]()
        driver.implicitly_wait(10)
        if is_random:
            name, email = randomed_data()
        driver.get('https://timeweb.com/ru/services/hosting/')
        driver.find_element_by_xpath("//a[text() = 'Начать тест']").click()

        field_full_name = driver.find_element_by_xpath("//div[@class='label js-fiz']//input[@name='full_name']")
        field_email = driver.find_element_by_xpath("//div[@class='label']//input[@name='email']")

        field_full_name.send_keys(name)
        field_email.send_keys(email)

        driver.find_element_by_xpath("//div[text() = 'Стать клиентом']").click()
        time.sleep(1)

        if is_random:
            parse_and_save_data(email)

        print(f"Complete \\({i + 1})")
        driver.quit()


@input_missing
def get_attr() -> dict:
    parser = argparse.ArgumentParser()
    account_settings = parser.add_argument_group('Account settings')

    arguments = {
        'browser': {
            'options': ['--browser', '-b'],
            'type': str,
            'default': None,
            'help': "Browser You Want to Use"
        },
        'name': {
            'options': ['--name', '-n'],
            'type': str,
            'default': None,
            'help': "Full Name"
        },
        'email': {
            'options': ['--email', '-e'],
            'type': str,
            'default': None,
            'help': "E-Mail Address"
        },
        'random_data': {
            'options': ['--random-data', '-r'],
            'type': int,
            'default': 0,
            'help': "number of accounts with random names and posts. (The entered name and mail will be ignored)",
        }
    }
    for argument in arguments.values():
        account_settings.add_argument(
            argument['options'][0], argument['options'][1],
            default=argument.get('default'),
            type=argument.get('type'),
            help=argument.get('help'),
        )

    arguments = parser.parse_args()
    return {
        'browser': arguments.browser,
        'name': arguments.name,
        'email': arguments.email,
        'rand': arguments.random_data,
    }


if __name__ == '__main__':
    domains = get_domains()
    args = get_attr()
    register(
        browser=args.get('browser'),
        name=args.get('name'),
        email=args.get('email'),
        count=args.get('rand'),
    )
