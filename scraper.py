import pickle
import time
import os
from datetime import datetime, timedelta
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
import undetected_chromedriver as uc


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
            show_log(category='INFO',
                     message=f"Successful login into account: {self.email}")
        except Exception:
            show_log(category='ERROR',
                     message=f"Error logging in into account '{self.email}'. Please check email and password, and try again!")
            exit()

        try:
            self.open_playlist()
            show_log(category='INFO',
                     message=f"Successfully opened playlist '{self.playlist_name}'")
        except Exception:
            show_log(category='ERROR',
                     message=f"Error opening the playlist '{self.playlist_name}'. Please check if the playlist exists and try again!")
            exit()

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
            # options.add_argument('--headless')

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
        login_button = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '/html/body/div[3]/div/div[2]/div[3]/header/div[2]/div[3]/div[1]/button[2]'))
        )
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
        playlist_button = (WebDriverWait(self.driver, timeout=20).until(
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

        pickle.dump(self.songs_map, open("songs.dat", "wb"))


class CreateYTPlaylist:
    def __init__(self, email: str, password: str, playlist_name: str, songs: dict, keep_duplicates: bool = True):
        self.driver = None
        self.email = email
        self.password = password
        self.playlist_name = playlist_name
        self.songs = songs
        self.keep_duplicates = keep_duplicates

        self.main()

    def main(self):
        self.start_scraper(YOUTUBE_URL)

        try:
            self.login()
        except:
            show_log(category='ERROR',
                     message=f"Error logging in into account '{self.email}'. Please check email and password, and try again!")
            exit()

        self.search_songs()

        self.driver.close()

    def start_scraper(self, link):
        try:
            service = Service(os.getenv('CHROME_DRIVER_PATH'))
            options = Options()
            # options.add_argument('--no-sandbox')
            # options.add_argument('--disable-dev-shm-usage')
            # options.add_argument("--window-position=-2000,0")
            # options.add_argument('--headless')

            self.driver = uc.Chrome(service=service, options=options)
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
        # Click on the sign-in button
        login_button = self.driver.find_element(By.XPATH, '/html/body/ytd-app/div[1]/div/ytd-masthead/div[4]/div[3]/div[2]/ytd-button-renderer/yt-button-shape/a')
        login_button.click()

        # Type in email and hit enter
        email_entry = WebDriverWait(self.driver, timeout=10).until(
                        EC.presence_of_element_located((By.TAG_NAME, f'input'))
                    )
        email_entry.send_keys(self.email)
        email_entry.send_keys(Keys.ENTER)

        # Type in password and hit enter
        WebDriverWait(self.driver, timeout=10).until(
            EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div[1]/div[2]/c-wiz/div/div[2]/div/div/div/form/span/section[2]/div/div/div[1]/div[3]/div/div[1]/div/div/div[1]/div/div/input[@type=\'checkbox\']'))
        )
        time.sleep(3)
        pass_entry = self.driver.find_element(By.XPATH, f'/html/body/div[1]/div[1]/div[2]/c-wiz/div/div[2]/div/div/div/form/span/section[2]/div/div/div[1]/div[1]/div/div/div/div/div[1]/div/div[1]/input')
        pass_entry.send_keys(self.password)
        pass_entry.send_keys(Keys.ENTER)

        # Click on the next button
        # next_button = self.driver.find_element(By.XPATH, '/html/body/div[1]/div[1]/div[2]/c-wiz/div/div[3]/div/div[1]/div/div/button')
        # next_button.click()

    def search_songs(self):
        search_bar = WebDriverWait(self.driver, timeout=60).until(
                        EC.presence_of_element_located((By.XPATH, f'/html/body/ytd-app/div[1]/div/ytd-masthead/div[4]/div[2]/ytd-searchbox/form/div[1]/div[1]/input'))
                    )
        index = 0
        retries = 3
        while index < len(self.songs):
            points_list = []  # [(point1, yt_result1), (point2, yt_result2), (point3, yt_result3), ...]
            song = self.songs[index]
            try:
                time.sleep(3)
                search_bar.send_keys(f"{song['name']} - {song['singers']}")
                search_bar.send_keys(Keys.RETURN)
                time.sleep(3)

                for i in range(1, 6):
                    result = WebDriverWait(self.driver, timeout=10).until(
                        EC.presence_of_element_located((By.XPATH, f'/html/body/ytd-app/div[1]/ytd-page-manager/ytd-search/div[1]/ytd-two-column-search-results-renderer/div/ytd-section-list-renderer/div[2]/ytd-item-section-renderer/div[3]/ytd-video-renderer[{i}]'))
                    )
                    info = result.find_elements(By.TAG_NAME, 'a')
                    title = info[1].text.lower()
                    playtime = info[0].text

                    singers = song['singers'].split(', ')
                    points_list.append(
                        (self.get_points(song['name'], singers, song['playtime'], title, playtime), result)
                    )

                max_point = max(points_list, key=lambda x: x[0])
                best_result = max_point[1]

                show_log(category='INFO',
                         message=f"Successfully fetched song \'{song['name']}\' (Total fetched: {index + 1})")

                self.add_to_playlist(best_result)
                show_log(category='INFO',
                         message=f"Successfully added song \'{song['name']}\' to playlist '{self.playlist_name}' (Total added: {index + 1})")
                search_bar.clear()
                index += 1
                retries = 3
            except:
                if retries:
                    show_log(category='CRITICAL',
                            message=f"Error fetching song \'{song['name']}\'. Trying Again! (Remaining retries: {retries})")
                    retries -= 1
                    continue
                else:
                    show_log(category='CRITICAL',
                             message=f"Error fetching song \'{song['name']}\'. Trying Again! (Out of Retries)")
                    exit()

    def add_to_playlist(self, result):
        # Click the three dots button
        menu_button = WebDriverWait(result, timeout=10).until(
            EC.presence_of_element_located((By.ID, 'button'))
        )
        menu_button.click()

        # Click the Save to Playlist button
        pop_up = WebDriverWait(self.driver, timeout=5).until(
            EC.visibility_of_element_located((By.ID, 'contentWrapper'))
        )
        save_button = pop_up.find_element(By.XPATH, './/ytd-menu-popup-renderer/tp-yt-paper-listbox/ytd-menu-service-item-renderer[3]')
        save_button.click()

        # Get names of all playlists
        index = 1
        while True:
            try:
                playlist_name = WebDriverWait(self.driver, timeout=5).until(
                    EC.visibility_of_element_located((By.XPATH, f'/html/body/ytd-app/ytd-popup-container/tp-yt-paper-dialog/ytd-add-to-playlist-renderer/div[2]/ytd-playlist-add-to-option-renderer[{index}]/tp-yt-paper-checkbox/div[2]/div/div/yt-formatted-string[1]'))
                )
                if playlist_name.text == self.playlist_name:
                    checkbox = self.driver.find_element(By.XPATH, f'/html/body/ytd-app/ytd-popup-container/tp-yt-paper-dialog/ytd-add-to-playlist-renderer/div[2]/ytd-playlist-add-to-option-renderer[{index}]/tp-yt-paper-checkbox')
                    if checkbox.get_attribute('aria-checked') == 'false':
                        checkbox.click()
                    break
                index += 1
            except:
                break

        # Close pop-up
        close_button = self.driver.find_element(By.XPATH, '/html/body/ytd-app/ytd-popup-container/tp-yt-paper-dialog/ytd-add-to-playlist-renderer/div[1]/yt-icon-button/button')
        close_button.click()
        time.sleep(5)

    def get_points(self, spotify_title: str, spotify_singers: list, spotify_ptime: str, yt_title: str, yt_ptime: str):
        all_present_flag = 1
        official_list = ['official video', 'official music video']
        points = {
            'title': 0,  # +5 for each common word, +10 if official
            'singers': 0,  # +10 for each common singer
            'playtime': 0  # +10 if yt_ptime >= (spotify_ptime - 3)
        }  # +(10 * no_of_words) if all words in title, all singers are present and official in yt title

        # Cleaning data
        spotify_ptime = datetime.strptime(spotify_ptime, '%M:%S')
        try:
            yt_ptime = datetime.strptime(yt_ptime, '%M:%S')
        except:
            yt_ptime = datetime.strptime('00:00', '%M:%S')

        spotify_title = spotify_title.replace('(', '')
        spotify_title = spotify_title.replace(')', '')
        spotify_words = spotify_title.split()
        spotify_words = [spotify_word for spotify_word in spotify_words if spotify_word]

        for spotify_word in spotify_words:
            if spotify_word in yt_title:
                points['title'] += 5
            else:
                all_present_flag = 0

        for official in official_list:
            if official in yt_title:
                points['title'] += 10
            else:
                all_present_flag = 0

        for singer in spotify_singers:
            if singer in yt_title:
                points['singers'] += 10
            else:
                all_present_flag = False

        if yt_ptime > spotify_ptime - timedelta(seconds=3):
            points['playtime'] += 10
        else:
            all_present_flag = 0

        return sum(points.values()) + 10 * len(spotify_words) * all_present_flag


if __name__ == '__main__':
    data = pickle.load(open("user_info.dat", "rb"))
    spotify_songs = pickle.load(open("songs.dat", "rb"))
    ScrapeSpotifyPlaylist(data['spotify_email'], data['spotify_pass'], playlist_name="Dreamland of Melodies")
    CreateYTPlaylist(data['youtube_email'], data['youtube_pass'], songs=spotify_songs, playlist_name='Dreamland of Melodies')
