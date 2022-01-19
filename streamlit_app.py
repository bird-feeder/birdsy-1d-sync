import os
import time
from pathlib import Path

import streamlit as st

import app

if __name__ == '__main__':
    st.set_page_config(page_title='Sync Birdsy',
                       page_icon='🐦',
                       layout='wide',
                       initial_sidebar_state='expanded')

    st.markdown("""<style> footer {visibility: hidden;} 
    footer::before { content:'NC State University & 
    NC Museum of Natural Sciences | Maintained by Mohammad Alyetama'; 
    visibility: visible; position: fixed; left: 1; right: 1; bottom: 0; 
    text-align: center; } </style>""",
                unsafe_allow_html=True)

    st.markdown("""<style>
    #MainMenu {visibility: hidden;}
    </style>""",
                unsafe_allow_html=True)

    lines_container = st.empty()
    lines = lines_container.text_area('Links to download and sync')
    with st.expander('Submitted links'):
        st.code(lines, language='')
    lines = lines.split('\n')

    links = list(set([line.rstrip() for line in lines]))

    st.sidebar.title('Controls')
    start = st.sidebar.button('▶️ Start the process')
    stop = st.sidebar.button('🛑 Stop the process')
    kill = st.sidebar.button('💀 Kill the process')

    current_process_pid = app.check_status()

    if start:
        if len(links) == 1 and links[0] == '':
            st.error('Submit links first!')
        else:
            links = app.validate(links)
            links = app.deduplicate(links)
        if len(links) == 1 and links[0] == '':
            st.error('Submit links first!')
        else:
            start_msg = st.empty()
            time.sleep(2)
            driver = app.chrome_driver(headless=True)
            app.main(driver, links)

    if stop:
        try:
            driver.quit()
        except NameError:
            pass
        try:
            st.info(f'Stopped the process')
            time.sleep(2)
            st.stop()
        except TypeError:
            pass

    if kill:
        try:
            driver.quit()
        except NameError:
            pass
        try:
            st.info(
                f'Sent kill signal to process with pid: {current_process_pid}')
            time.sleep(2)
            os.kill(current_process_pid, signal.SIGKILL)
        except TypeError:
            pass
