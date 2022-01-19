import json
import os
import re
import signal
import sys
import time
from pathlib import Path

import requests
import psutil
import streamlit as st
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


def validate(lines):
    val_write_ph_0 = st.empty()
    val_write_ph_0.write('Validation progress:')
    pattern = re.compile(r'https:\/\/birdsy\.com\/channel\/.+\/video\/.+')
    val_ph = st.empty()
    val_prog_ph = st.empty()
    val_write_ph = st.empty()
    val_bar = val_prog_ph.progress(0)
    for n, line in enumerate(tqdm(lines)):
        curr_progress = int(100 * float(n + 1) / float(len(lines)))

        val_write_ph.write(f'{n + 1}/{len(lines)}')
        if curr_progress > 100:
            curr_progress = 100
        val_bar.progress(curr_progress)
        try:
            if not pattern.match(line):
                lines.remove(line)
                logger.info(f'Removed line {n}')
            else:
                try:
                    response = requests.get(line)
                except requests.ConnectionError as exception:
                    lines.remove(line)
                    logger.info(f'Removed line {n}')
                except KeyboardInterrupt:
                    break
        except KeyboardInterrupt:
            break
        if curr_progress == len(lines):
            val_bar.progress(100)
    val_write_ph_0.write('Completed!')
    time.sleep(2)
    val_prog_ph.empty()
    val_ph.empty()
    val_write_ph.empty()
    val_write_ph_0.empty()
    return lines


def deduplicate(lines):
    logger.add('logs.log')
    ids = sorted([(line.rstrip(), line.split('/')[-1].rstrip())
                  for line in lines])
    remote_res = os.popen('/usr/bin/rclone lsjson birdsy: --config="/home/ubuntu/.config/rclone/rclone.conf"').read()
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


def login(driver, email, passwd):
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


def download(driver, page_link):
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


def check_status():
    for p in psutil.process_iter():
        try:
            if 'streamlit' in p.name():
                args = sum([y for y in [x.split('/') for x in p.cmdline()]],
                           [])
                if 'streamlit' in args:
                    current_process_pid = p.pid
        except (psutil.ZombieProcess, psutil.AccessDenied):
            continue
    return current_process_pid


def main(driver, links):
    logging_in_logs = st.empty()
    downloads_dir = f'{Path(__file__).parent}/birdsy-uploads'
    if not Path(downloads_dir).exists():
        Path(downloads_dir).mkdir(exist_ok=True)
        logger.info('Created downloads folder')

    dry_run = False
    if '--dry-run' in sys.argv:
        dry_run = True

    logger.debug('Deduplicating...')
    
    if len(links) == 0:
        logger.info('Nothing to process. Exiting...')
        sysexit = st.empty()
        raise SystemExit('Nothing to process... Everything is up-to-date.')
    logger.debug('Running the main process...')
    load_dotenv()
    logging_in_logs.write('Logging in to Birdsy...')
    driver = login(driver, os.environ['EMAIL'], os.environ['PASSWD'])
    logging_in_logs.write('Logged in!')

    
    st.markdown('---')
    main_bar = st.progress(0)
    ph_2 = st.empty()
    st.markdown('---')

    empty_cont = st.empty()
    n = 0
    for link in tqdm(links):
        progress = st.empty()
        with progress:
            progress.info(f'Currently processing {n + 1}/{len(links)} ({link})')
        n += 1
        logger.debug(f'{n}/{len(links)} Processing {link}')
        curr_progress = int(100 * float(n) / float(len(links)))
        if curr_progress > 100:
            curr_progress = 100
        main_bar.progress(curr_progress)
        try:
            url, out_filename = download(driver, link)
            upload(out_filename, dry_run=dry_run)
        except TimeoutException:
            logger.debug(
                f'{link} does not appear to contain a video... Skipping...')
        except KeyboardInterrupt:
            break
        except Exception:
            exc_type, value, _ = sys.exc_info()
            logger.error(exc_type.__name__)
            logger.error(f'Failed to download {link}')
            logger.error(value)
        progress.empty()
    st.balloons()
    st.write('Completed!')

    logger.info('Completed!')
    driver.quit()
    logging_in_logs.write('Logged out...')
    time.sleep(2)
    logging_in_logs.empty()
