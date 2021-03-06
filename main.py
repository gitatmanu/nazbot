import os, json, tweepy
from time import sleep
from dotenv import load_dotenv
load_dotenv()
from tweepy import Stream
from tweepy.streaming import StreamListener
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from generate_nazbol_name import generate_nazbol_name


class Listener(StreamListener):
    def on_data(self, tweet):
        bot_name = os.getenv('ACCOUNT_NAME')
        tweet = json.loads(tweet)

        if bot_name in tweet['user']['screen_name']:
            return
        if hasattr(tweet,'retweeted_status'):
            return
        if tweet['in_reply_to_status_id'] is None:
            return

        try:
            replied_tweet = get_tweet(tweet['in_reply_to_status_id']).__dict__['_json']
        except Exception as e:
            return

        if bot_name in replied_tweet['user']['screen_name']:
            return
        
        reply_tweet(replied_tweet)
    
    def on_error(self, status_code):
        print("Error en el stream: " + str(status_code))
        return False

def set_up_auth():
    auth = tweepy.OAuthHandler(os.getenv('CONSUMER_KEY'), os.getenv('CONSUMER_SECRET'))
    auth.set_access_token(os.getenv('ACCESS_KEY'), os.getenv('ACCESS_SECRET'))
    api = tweepy.API(auth)
    return api, auth


def follow_stream():
    api, auth = set_up_auth()
    listener = Listener(StreamListener)
    stream = Stream(auth, listener)
    stream.filter(track=[os.getenv('ACCOUNT_NAME')], is_async=True, stall_warnings=True)


def reply_tweet(tweet):
    api, auth = set_up_auth()
    print('Procesando tuit de: '+ tweet['user']['screen_name'])

    tweet_url = 'https://twitter.com/{}/status/{}'.format(
        tweet['user']['screen_name'], tweet['id'])
    
    generate_image(tweet_url, tweet['user']['screen_name'])

    api.update_with_media("./capture.png",
                            status="",
                            in_reply_to_status_id=tweet['id_str'],
                            auto_populate_reply_metadata=True
                            )
    print('Procesado.')

def get_tweet(tweet_id):
    api, auth = set_up_auth()
    try:
        replied_tweet = api.get_status(tweet_id)
    except Exception as e:
        print(e)
        return
    return replied_tweet


def generate_image(tweet_url, name):
    driver = init_driver()

    # Modify HTML
    driver.get(tweet_url)
    sleep(6)
    try:
        nazbol_name = generate_nazbol_name()
        name_fields = driver.find_elements_by_xpath("//a[@href='/" + name + "']//div/div[1]/div[1]//span//span")
        emoji_images = driver.find_elements_by_xpath("//a[@href='/" + name + "']//div/div[1]/div[1]//span//img")

        NAME_FIELD_JS = """
        arguments[0].textContent='{}';
        var elm = arguments[0];
        elm.dispatchEvent(new Event('change'));
        """.format(nazbol_name)

        IMAGES_JS = """arguments[0].remove();"""

        for emoji_image in emoji_images: # Removes username emojis, Twitter render them as <img> 
            driver.execute_script(IMAGES_JS, emoji_image)

        for name_field in name_fields:
            driver.execute_script(NAME_FIELD_JS, name_field)
    except NoSuchElementException:
        pass
    
    driver.get_screenshot_as_file("capture.png")

    driver.close()
    driver.quit()


def init_driver():
    user_agent = 'Mozilla/5.0 (Linux; Android 7.0; SM-G892A Build/NRD90M; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/67.0.3396.87 Mobile Safari/537.36'
    executable_path = '/home/server/nazbot/drivers/geckodriver'
    
    # Firefox webdriver
    options = webdriver.FirefoxOptions()
    options.add_argument('--disable-extensions')
    options.add_argument("--headless")
    
    profile = webdriver.FirefoxProfile()
    profile.set_preference('general.useragent.override', user_agent)
    
    # Init driver
    driver = webdriver.Firefox(executable_path=executable_path, options=options, firefox_profile=profile, service_log_path=os.devnull)
    driver.set_window_position(0, 0)
    driver.set_window_size(500, 700)

    return driver


if __name__ == '__main__':
    while True:
        follow_stream()
        print("Se ha producido un error, reiniciando en 10 segundos")
        time.sleep(10)
        print("Reiniciando nazbot")

