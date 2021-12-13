import json
import os
import re
import signal
import sys
import time
from pathlib import Path

import cronitor
import requests
import wget
from dotenv import load_dotenv
from loguru import logger
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
from tqdm import tqdm


def keyboard_interrupt_handler(sig, frame):
    logger.info(f'KeyboardInterrupt (ID: {sig}) has been caught...')
    time.sleep(2)
    try:
        driver.quit()
        logger.info('Terminated chrome driver gracefully...')
    except NameError:
        pass
    logger.info('Terminating the program...')
    sys.exit(0)


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


def deduplicate(lines):
    ids = sorted([(line.rstrip(), line.split('/')[-1].rstrip())
                  for line in lines])
    remote_res = os.popen('/usr/bin/rclone lsjson birdsy:').read()
    time.sleep(5)
    remote_files = json.loads(remote_res)
    remote_files_ids = sorted(
        [Path(''.join(x['Name'].split('_')[3:])).stem for x in remote_files])
    not_in_remote_ids = list(
        set([x[1] for x in ids]).difference(remote_files_ids))
    not_in_remote_links = sorted(
        [x[0] for x in ids if x[1] in not_in_remote_ids])
    logger.info(
        f'{len(ids) - len(not_in_remote_links)}/{len(ids)} files already exist in remote.'
    )
    logger.info(f'Number of files to process: {len(not_in_remote_links)}')
    return not_in_remote_links


def chrome_driver(driver_path='/usr/bin/chromedriver', headless=True):
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    if headless:
        options.add_argument('headless')
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def login(email, passwd):
    driver.get('https://birdsy.com/login')
    print('Logged in')
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
    time.sleep(5)
    return driver


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


def upload(out_filename, rclone_path='/usr/bin/rclone', dry_run=False):
    if dry_run:
        dry_run_arg = '--dry-run'
    else:
        dry_run_arg = ''
    res = os.popen(
        f'{rclone_path} move {out_filename} birdsy: -P {dry_run_arg}').read()
    logger.debug(res)
    return res


if __name__ == '__main__':
    load_dotenv()
    logger.add('logs.log')
    cronitor.api_key = os.environ['CRONITOR_API_KEY']
    monitor = cronitor.Monitor('Birdsy-webhook')
    monitor.ping(state='run', message='Webhook triggered')

    dry_run = False
    if '--dry-run' in sys.argv:
        dry_run = True
    with open('videos_links.txt') as f:
        lines = f.readlines()

    signal.signal(signal.SIGINT, keyboard_interrupt_handler)

    links = list(set([line.rstrip() for line in lines]))

    if not dry_run:
        logger.debug('Validating...')
        links = validate(links)

    logger.debug('Deduplicating...')
    links = deduplicate(links)
    if len(links) == 0:
        logger.info('Nothing to process. Exiting...')
        raise SystemExit(0)
    logger.debug('Running the main process...')
    driver = chrome_driver(headless=True)
    driver = login(os.environ['EMAIL'], os.environ['PASSWD'])

    n = 1
    for link in tqdm(links):
        logger.info(f'{n}/{len(links)} Processing {link}')
        n += 1
        try:
            url, out_filename = download(link)
            upload(out_filename, dry_run=dry_run)
        except TimeoutException:
            logger.warning(
                f'{link} does not appear to contain a video... Skipping...')
        except KeyboardInterrupt:
            break
        except Exception:
            exc_type, value, _ = sys.exc_info()
            logger.error(exc_type.__name__)
            logger.error(f'Failed to download {link}')
            logger.error(value)
            continue
    driver.quit()
    monitor.ping(state='complete')
    logger.info('Complete.')
