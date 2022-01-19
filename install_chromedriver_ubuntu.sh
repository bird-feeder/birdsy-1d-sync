#!/bin/bash

sudo curl -sS -o - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add
sudo bash -c "echo 'deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main' >> /etc/apt/sources.list.d/google-chrome.list"
sudo apt update && sudo apt install unzip google-chrome-stable -y

LATEST_RELEASE=$(curl -s https://chromedriver.storage.googleapis.com/LATEST_RELEASE)
wget https://chromedriver.storage.googleapis.com/$LATEST_RELEASE/chromedriver_linux64.zip
unzip chromedriver_linux64.zip && rm chromedriver_linux64.zip

sudo mv chromedriver /usr/bin/chromedriver
sudo chmod +x /usr/bin/chromedriver
