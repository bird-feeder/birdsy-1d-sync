import os
import sys
import time
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

import app


def login():
    logged_in = False
    if not st.session_state['authentication_status']:
        load_dotenv(f'{Path(__file__).parent}/.env')
        login_form = st.empty()
        with login_form:
            with st.form("Login Form"):
                email = st.text_input("Email")
                passwd = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Login")
                if submitted:
                    try:
                        assert email in os.environ['EMAILS']
                        assert passwd == os.environ['LOGIN_PASSWD']
                        logged_in = True
                    except AssertionError:
                        st.error('Incorrect login credentials!')

        if logged_in:
            login_form.success('Logged in successfully!')
            time.sleep(1)
            login_form.empty()
            return True


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

    login_container = st.empty()

    with login_container:
        if 'authentication_status' not in st.session_state:
            st.session_state['authentication_status'] = False

        if login():
            st.session_state['authentication_status'] = True
            login_container.empty()

    if st.session_state['authentication_status']:
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
