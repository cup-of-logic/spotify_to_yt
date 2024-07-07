import pickle
import time
import os
from datetime import datetime
import colorama
from colorama import Fore, Back, Style
from pprint import pprint

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys


SPOTIFY_URL = "https://open.spotify.com"
YOUTUBE_URL = "https://www.youtube.com"

LOG_COLORS = {
    "INFO": Fore.WHITE + Style.BRIGHT,
    "ERROR": Fore.RED + Style.BRIGHT,
    "DEBUG": Fore.CYAN + Style.DIM,
    "CRITICAL": Back.RED + Fore.WHITE + Style.BRIGHT
}
colorama.init()


def get_current_time():
    return datetime.now().strftime('%d-%m-%Y %H:%M:%S')


def show_log(category: str, message: str):
    category = category.upper()

    log = f"[{get_current_time()}] [{category}] {message}"
    print(LOG_COLORS[category] + log + Style.RESET_ALL)

    with open("logs.log", mode='a') as logs_file:
        logs_file.write(log + '\n')


class ScrapeSpotifyPlaylist:
    def __init__(self, email: str, password: str, playlist_name: str):
        self.email = email
        self.password = password
        self.playlist_name = playlist_name
        self.driver = None
        self.songs_map = {}

        self.main()

    def main(self):
        show_log(category='INFO',
                 message="Started Spotify scraper.")

        self.start_scraper(SPOTIFY_URL)
        show_log(category='DEBUG',
                 message="Set up Chromedriver successfully.")

        try:
            self.login()
        except Exception:
            show_log(category='ERROR',
                     message=f"Error logging in into account '{self.email}'. Please check email and password, and try again!")
            exit()
        finally:
            show_log(category='INFO',
                     message=f"Successful login into account: {self.email}")

        try:
            self.open_playlist()
        except Exception:
            show_log(category='ERROR',
                     message=f"Error opening the playlist '{self.playlist_name}'. Please check if the playlist exists and try again!")
            exit()
        finally:
            show_log(category='INFO',
                     message=f"Successfully opened playlist '{self.playlist_name}'")

        try:
            self.get_song_info()
        except Exception as e:
            show_log(category='ERROR',
                     message=f"Error gathering song info: {e}")

        self.driver.close()

        show_log(category='INFO',
                 message=f"Scraped {len(self.songs_map)} songs from playlist {self.playlist_name}")

    def start_scraper(self, link):
        try:
            service = Service(os.getenv('CHROME_DRIVER_PATH'))
            options = Options()
            options.add_argument('--headless')

            self.driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            show_log(category='ERROR',
                     message=f'Error setting up chromedriver: \"{e}\"'
                     )
            exit()

        try:
            self.driver.get(link)
            self.driver.maximize_window()
        except:
            show_log(category='ERROR',
                     message=f'Error fetching URL: \"{link}\"'
                     )
            exit()

    def login(self):
        # Click login button
        login_button = self.driver.find_element(By.CSS_SELECTOR, '#main > div > div.ZQftYELq0aOsg6tPbVbV > div.jEMA2gVoLgPQqAFrPhFw > header > div.hV9v6y_uYwdAsoiOHpzk.contentSpacing > div.rwdnt1SmeRC_lhLVfIzg > div.LKFFk88SIRC9QKKUWR5u > button.Button-sc-qlcn5g-0.bThepJ.encore-text-body-medium-bold')
        login_button.click()

        # Enter user creds
        user_field = (WebDriverWait(self.driver, timeout=10).until(
            EC.presence_of_element_located((By.ID, 'login-username'))
        ))
        pass_field = self.driver.find_element(By.ID, 'login-password')
        user_field.send_keys(self.email)
        pass_field.send_keys(self.password)

        # Click login confirmation button
        login_conf_button = self.driver.find_element(By.ID, 'login-button')
        login_conf_button.click()

    def open_playlist(self):
        playlist_button = (WebDriverWait(self.driver, timeout=10).until(
            EC.presence_of_element_located((By.XPATH, '/html/body/div[4]/div/div[2]/div[1]/nav/div[2]/div[1]/div[1]/div/div/div/div/button[1]'))
        ))

        # Select playlist option if not already selected
        if not playlist_button.is_selected():
            playlist_button.click()

        # Search the required playlist
        search_box = self.driver.find_element(By.XPATH, '/html/body/div[4]/div/div[2]/div[1]/nav/div[2]/div[1]/div[2]/div[2]/div/div[1]/div/input')
        search_box.send_keys(self.playlist_name)
        time.sleep(3)

        # Open the playlist
        selected_playlist_button = self.driver.find_element(By.XPATH, '/html/body/div[4]/div/div[2]/div[1]/nav/div[2]/div[1]/div[2]/div[2]/div/div[2]/ul/div/div[2]/li/div/div[1]')
        selected_playlist_button.click()

    def get_song_info(self):
        song_container = WebDriverWait(self.driver, timeout=10).until(
                    EC.presence_of_element_located((By.XPATH, f'/html/body/div[4]/div/div[2]/div[3]/div[1]/div[2]/div[2]/div[2]/main/div[1]/section/div[2]/div[3]/div[1]/div[2]/div[2]'))
                )

        retries = 3
        last_map_size = 0
        while retries:
            WebDriverWait(song_container, timeout=10).until(
                EC.presence_of_element_located((By.XPATH, f'./div'))
            )

            songs = song_container.find_elements(By.XPATH, f'./div')

            for song in songs:
                # Indexing the song based on the aria-rowindex which starts from 2
                song_index = int(song.get_attribute('aria-rowindex'))
                elements = song.find_elements(By.CLASS_NAME, 'encore-text')
                self.songs_map[song_index - 2] = {
                    'name': elements[1].text,
                    'singers': elements[3].text,
                    'playtime': elements[-1].text
                }

            self.driver.execute_script("arguments[0].scrollIntoView();", songs[-1])
            time.sleep(3)

            # If last length of the hashmap remains same for 3 tries, the entire playlist has been scraped
            map_size = len(self.songs_map)
            if map_size == last_map_size:
                retries -= 1
            else:
                retries = 3
                last_map_size = map_size

                show_log(category='INFO',
                         message=f"Number of songs scraped: {map_size}")

        # pickle.dump(self.songs_map, open("songs.dat", "wb"))


if __name__ == '__main__':
    data = pickle.load(open("user_info.dat", "rb"))
    ScrapeSpotifyPlaylist(**data,
                          playlist_name="Tragic Remix"
                          )
