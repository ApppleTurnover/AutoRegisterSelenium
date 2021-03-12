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


def get_domains():
    url = "https://privatix-temp-mail-v1.p.rapidapi.com/request/domains/"

    response = requests.request("GET", url, headers=headers)
    return response.json()


def get_mails(email: str):
    url = os.environ.get('url_for_mail') + hashlib.md5(email.encode()).hexdigest() + '/'

    response = requests.request("GET", url, headers=headers)
    return response.json()


def save_login_and_password(email: str, login=None, password=None):
    messages = get_mails(email)
    for i in range(12):
        try:
            if messages.get('error'):
                print(messages.get('error'))
                print(f'The mail did not arrive. It will be repeated in 5 seconds ({i + 1}/12)')
                time.sleep(5)
                messages = get_mails(email)
        except AttributeError:
            break

    else:
        raise Exception('The mail did not arrive')

    for message in messages:
        if 'успешно создан' in message['mail_subject']:
            mail_text = message['mail_text_only'].replace(' ', '')
            login = re.findall(r'Логин:<strong>(.*?)</strong>', mail_text, re.DOTALL)[0]
            password = re.findall(r'Пароль:<strong>(.*?)</strong>', mail_text, re.DOTALL)[0]

    if login and password:
        with open('accounts_data.txt', 'a+') as f:
            f.write(f"[\ne:{email};\nl:{login};\np:{password}\n],\n")


def check_data(name, email):
    if not is_email_valid(email) or not len(name) > 3:
        raise Exception("Invalid data")


def input_missing(func):
    """decorator input missing elements """

    def inner():
        arguments = func()
        questions = [
            inquirer.List('browser',
                          message='What browser do you want to use?',
                          choices=browsers),
            inquirer.Text('name', message='Full name: '),
            inquirer.Text('email', message='E-Mail: ')
        ]

        if arguments.get('browser') is None:
            browser = inquirer.prompt([questions[0], ]).get('browser')
        else:
            browser = arguments.get('browser')

        if not arguments.get('rd'):
            if arguments.get('name') is None:
                name = inquirer.prompt([questions[1], ]).get('name')
            else:
                name = arguments.get('name')

            if arguments.get('email') is None:
                email = inquirer.prompt([questions[2], ]).get('email')
            else:
                email = arguments.get('email')

            check_data(name, email)

        else:
            name = random_string(20)
            email = (random_string(20) + random.choice(get_domains())).lower()

        return {
            'browser': browser,
            'name': name,
            'email': email,
            'rd': arguments.get('rd'),
        }

    return inner


def register(browser, name, email, rd):
    driver = webdriver.__dict__[browser]()
    driver.implicitly_wait(10)
    try:
        driver.get('https://timeweb.com/ru/services/hosting/')
        driver.find_element_by_xpath("//a[text() = 'Начать тест']").click()

        field_full_name = driver.find_element_by_xpath("//div[@class='label js-fiz']//input[@name='full_name']")
        field_email = driver.find_element_by_xpath("//div[@class='label']//input[@name='email']")

        field_full_name.send_keys(name)
        field_email.send_keys(email)

        driver.find_element_by_xpath("//div[text() = 'Стать клиентом']").click()
    finally:
        time.sleep(5)
        driver.quit()
        if rd:
            save_login_and_password(email)


@input_missing
def get_attr() -> dict:
    parser = argparse.ArgumentParser()
    account_settings = parser.add_argument_group('Account settings')

    # TODO: Refactor(remove duplicate code)
    account_settings.add_argument('--browser', '-b', default=None, help='Browser You Want to Use')
    account_settings.add_argument('--name', '-n', default=None, help='Full Name')
    account_settings.add_argument('--email', '-e', default=None, help='E-Mail Address')
    account_settings.add_argument('--random-data', '-r', default=False,
                                  help='Use Random Full Name and E-Mail or No. Attention! temp-mail.org mail will be updated',
                                  action=argparse.BooleanOptionalAction)

    arguments = parser.parse_args()
    return {
        'browser': arguments.browser,
        'name': arguments.name,
        'email': arguments.email,
        'rd': arguments.random_data,
    }


if __name__ == '__main__':
    args = get_attr()
    register(
        browser=args.get('browser'),
        name=args.get('name'),
        email=args.get('email'),
        rd=args.get('rd')
    )
