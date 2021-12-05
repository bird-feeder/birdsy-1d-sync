#!/usr/bin/env python
# coding: utf-8

import os
import re
import shutil
import sys
import time
from pathlib import Path

import requests
import wget
from dotenv import load_dotenv
from loguru import logger
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
from tqdm import tqdm
from webdriver_manager.chrome import ChromeDriverManager


def validate(lines):
    pattern = re.compile(r'https:\/\/birdsy\.com\/channel\/.+\/video\/.+')

    for n, line in enumerate(tqdm(lines)):
        if not pattern.match(line):
            lines.remove(line)
            logger.info(f'Removed line {n}')
        else:
            try:
                response = requests.get(line)
            except requests.ConnectionError as exception:
                lines.remove(line)
                logger.info(f'Removed line {n}')
    return lines


def chrome_driver(driver_path=None, headless=True):
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    if headless:
        options.add_argument('headless')
    if not driver_path:
        driver_path = shutil.which('chromedriver')
    if driver_path:
        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=options)
    else:
        os.environ['WDM_LOG_LEVEL'] = '0'
        os.environ['WDM_PRINT_FIRST_LINE'] = 'False'
        os.environ['WDM_LOCAL'] = '1'
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    return driver


def login(email, passwd):
    driver.get('https://birdsy.com/login')
    driver.find_element(
        By.XPATH,
        '//*[@id="root"]/div[2]/div/div/div/div/div/form/div[1]/input'
    ).send_keys(email)
    driver.find_element(
        By.XPATH,
        '//*[@id="root"]/div[2]/div/div/div/div/div/form/div[2]/input'
    ).send_keys(passwd)
    driver.find_element(By.CLASS_NAME,
                        'mb-3').find_element(By.TAG_NAME,
                                             'input').send_keys(Keys.RETURN)
    time.sleep(3)


def download(page_link):
    driver.get(page_link)
    url = WebDriverWait(driver, 5).until(
        ec.presence_of_element_located(
            (By.CLASS_NAME,
             'rc-player'))).find_element(By.TAG_NAME,
                                         'div').get_attribute('file')
    date = driver.find_element(By.TAG_NAME, 'h3').text
    out_filename = f'birdsy-uploads/{date.replace(" ", "_")}_{Path(url).name}'
    if not Path(out_filename).exists():
        wget.download(url, out_filename)
    return url, out_filename


def upload(out_filename):
    rclone_path = shutil.which('rclone')
    res = os.popen(
        f'{rclone_path} move {out_filename} GoogleDriveN:/birdsy-uploads -P'
    ).read()
    logger.debug(res)
    return res


if __name__ == '__main__':
    load_dotenv()
    logger.remove()
    logger.add(sys.stderr, level='ERROR')
    logger.add('logs.log')

    with open('videos_links.txt') as f:
        lines = f.readlines()

    links = list(set([line.rstrip() for line in lines]))
    links = validate(links)

    driver = chrome_driver(headless=True)
    login(os.environ['EMAIL'], os.environ['PASSWD'])
    for link in tqdm(links):
        url, out_filename = download(link)
        upload(out_filename)
    driver.quit()
