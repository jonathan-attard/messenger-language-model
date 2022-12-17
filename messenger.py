import copy
import datetime
import pickle
import json
import random
import sys
from enum import Enum
import time
import os
# import regex as re
import requests

from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support.expected_conditions import presence_of_element_located, \
    presence_of_all_elements_located, visibility_of_all_elements_located, element_attribute_to_include, \
    text_to_be_present_in_element_attribute, element_to_be_selected, visibility_of_element_located
from selenium.common.exceptions import TimeoutException
from tqdm import tqdm
import json

from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import pyperclip
import urllib
import logging

from preproccess import END_QUERY, END_RESPONSE
from generator import getResp
from profanity import profanity


class Messenger:
    def __init__(self, base_url_check=None, limit_resp=5, headless=True, log=False, disable_profanity=True, log_file="events.log"):
        self.base_url_check = base_url_check
        self.limit_resp = limit_resp
        self.log = log
        self.disable_profanity = disable_profanity

        # Logging
        log_handlers = [
            logging.StreamHandler()
        ]
        if log_file is not None:
            log_handlers.append(logging.FileHandler("events.log"))
        logging.basicConfig(
            handlers=log_handlers,
            format='%(asctime)s %(message)s',
            level=logging.INFO,
            datefmt='%Y-%m-%d %H:%M:%S',
        )

        dir_path = os.getcwd()

        op = webdriver.ChromeOptions()
        op.add_argument("--window-size=1920,1080")
        op.add_argument("--disable-extensions")
        op.add_argument("--proxy-server='direct://'")
        op.add_argument("--proxy-bypass-list=*")
        op.add_argument("--start-maximized")
        op.add_argument("--disable-gpu")
        op.add_argument("--disable-dev-shm-usage")
        op.add_argument("--no-sandbox")
        op.add_argument("--ignore-certificate-errors")
        op.add_argument("--mute-audio")
        op.add_argument("--allow-running-insecure-content")
        op.add_argument("--user-data-dir={}".format(os.path.join(dir_path, "user_data")))

        if headless:
            op.add_argument('--headless')

        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=op)

    def goURL(self, url, force_reload=False):
        if not force_reload and url == self.driver.current_url:
            return
        else:
            self.driver.get(url)

    def start(self):
        logging.info("Starting messenger")
        self.driver.get("https://www.messenger.com")

        login = self.waitLogin()
        if not login:
            self.close()
            return

    def close(self):
        logging.info("Closing driver")

        self.driver.close()

    def waitLogin(self, timeout=100000):
        logging.info("Waiting for login")

        chats = WebDriverWait(self.driver, timeout).until(
            presence_of_all_elements_located((By.XPATH, "//h1[text()='Chats']")))

        if len(chats) > 0:
            logging.info("Login successful")

            return True
        else:
            logging.info("Login unsuccessful")

            return False

    def waitBaseURL(self, timeout=20):
        if self.base_url_check is None:
            return

        logging.info("Waiting for base url")

        self.driver.get(self.base_url_check)
        chats = WebDriverWait(self.driver, timeout).until(
            presence_of_all_elements_located((By.XPATH, "//h1[text()='Chats']")))

        logging.info("Base url loaded")

    def newMessages(self, timeout=20):
        self.waitBaseURL()  # Wait for non-reads

        # .//div[@aria-label='Mark as read'] and .//span[text()='1 m']
        try:
            new_messages = WebDriverWait(self.driver, timeout).until(
                presence_of_all_elements_located(
                    (By.XPATH, "//a[@href and .//div[@aria-label='Mark as read'] and .//span[text()='1 m']]")))
        except TimeoutException:
            logging.info("Timeout new messages")
            return []
        # chats = self.driver.find_elements(By.XPATH, "//a[@href]")  # Get elements

        # Extract urls
        chat_links = list()
        for message in new_messages:
            chat_url = message.get_attribute("href")
            if "www.messenger.com/t/" in chat_url:
                chat_links.append(chat_url)

        logging.info(f"New messages: {chat_links}")

        return chat_links

    def getChat(self, chat_url, timeout=20, show_raw=True):
        self.goURL(chat_url)

        chats = WebDriverWait(self.driver, timeout).until(
            presence_of_element_located((By.XPATH, "//h1[text()='Chats']")))

        time.sleep(0.2)

        body = self.driver.find_element(By.TAG_NAME, "body")
        text = body.text

        if show_raw:
            new_line_char = "%%"
            no_lines_text = text.replace('\n', new_line_char)
            logging.info(f"Raw text: {no_lines_text}")

        parsed_message = self.parseMessage(text)

        logging.info(f"User chat: {parsed_message}\n")

        return parsed_message

    @staticmethod
    def parseMessage(text):
        # print("text: ", text)

        text.replace(END_QUERY, "").replace(END_RESPONSE, "")

        lines = text.split("\n")

        start = False

        name = None
        my_name = "You sent"

        characters = ""

        lines_iter = iter(lines)
        for line in lines_iter:
            if start:
                # Message must start with user
                if line in [name, my_name, name.split(" ")[0]]:
                    user = line
                else:
                    continue

                msg = ""

                # Message must end with Enter
                next_line = next(lines_iter)
                while next_line != "Enter":
                    if msg == "":
                        msg += next_line
                    else:
                        msg += '\n' + next_line

                    try:
                        next_line = next(lines_iter)
                    except StopIteration:
                        msg = ""
                        break

                # Ignore empty messages (probably photos)
                if msg == "":
                    continue

                if user == name or user == name.split(" ")[0]:
                    symbol = '$'
                elif user == my_name:
                    symbol = '£'
                else:
                    symbol = '<ERROR>'

                characters += msg + symbol
            else:
                if "Install Messenger app" == line:
                    start = True
                    name = next(lines_iter)  # Skip next as well

        return characters

    def autoResp(self):
        logging.info("Starting auto response")

        while True:
            try:
                new_messages = self.newMessages()
                for url in new_messages:
                    user_chat = self.getChat(url)

                    responses = getResp(user_chat)

                    logging.info(f"Responses: {responses}\n")

                    for resp in responses[:self.limit_resp]:
                        if self.disable_profanity:
                            resp = profanity.censor(resp)  # Censor text
                        self.sendMsg(resp)

            except KeyboardInterrupt:
                # No need for close since Selenium already handles keyboard interrupts?
                logging.info("KeyboardInterrupt")
                break

    def sendMsg(self, text, timeout=20):
        text_box = WebDriverWait(self.driver, timeout).until(
            presence_of_element_located((By.XPATH, "//div[@aria-label='Message']")))
        text_box.send_keys(text + "\n")


if __name__ == "__main__":
    mess = Messenger(headless=True, log=True, base_url_check="https://www.messenger.com/t/100012028305554", limit_resp=3)
    mess.start()

    mess.autoResp()

    # mess.close()
