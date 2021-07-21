import requests

from datetime import datetime, timedelta
from configparser import ConfigParser

from twilio.rest import Client

parser = ConfigParser()
parser.read('secrets.ini', encoding="utf-8")

ALPHAVANTAGE_API_KEY = parser.get('API_KEYS', 'ALPHAVANTAGE_API_KEY')
NEWSORG_API_KEY = parser.get('API_KEYS', 'NEWSORG_API_KEY')

TWILIO_SID = parser.get('TWILIO', 'TWILIO_SID')
TWILIO_TOKEN = parser.get('TWILIO', 'TWILIO_TOKEN')

TWILIO_NUMBER = parser.get('PHONE_NUMBERS', 'TWILIO_NUMBER')
RECIPENT_PHONE_NUMBER = parser.get('PHONE_NUMBERS', 'RECIPENT_PHONE_NUMBER')

PROXY = parser.get('PROXIES', 'PROXY', fallback=None)

today = datetime.today().date()  # '2021-03-29'


def get_btc_info():
    """
    # When STOCK price increase/decreases by 5% between yesterday and the day before yesterday then print("Get News").
    # https://www.alphavantage.co/query?function = DIGITAL_CURRENCY_DAILY & symbol = BTC & market = CNY & apikey = demo
    :return:
    """

    url = r"https://www.alphavantage.co/query"

    parameters = {
        'function': 'DIGITAL_CURRENCY_DAILY',
        'symbol': 'BTC',
        'market': 'USD',
        'apikey': ALPHAVANTAGE_API_KEY
    }

    headers = {
        'Content-Type': 'application/json',
    }

    response = requests.get(
        url=url,
        params=parameters,
        headers=headers,
        proxies={"https": PROXY} if PROXY else dict()
    )
    response.raise_for_status()

    data = response.json()
    return data


def btc_change_24hr():
    print(f"\nFetching 24hr bitcoin pricing...")

    btc_data = get_btc_info()
    btc_time_series = btc_data['Time Series (Digital Currency Daily)']

    yesterday = today - timedelta(days=1)

    today_open = btc_time_series[str(today)]['1a. open (USD)']
    last_open = btc_time_series[str(yesterday)]['1a. open (USD)']

    # Get percentage difference
    per_change = 100 - (float(today_open)/float(last_open)) * 100
    return round(per_change, 2)


# STEP 2: Use https://newsapi.org
def get_news(topic="bitcoin", number_of_articles=3):
    print(f"\nFetching {number_of_articles} {topic} news articles...")

    news_org_url = r"https://newsapi.org/v2/everything"
    params = {
        "qInTitle": topic,
        "from": today,
        "sortBy": "popularity",
        "apiKey": NEWSORG_API_KEY
    }
    response = requests.get(
        url=news_org_url,
        params=params,
        proxies={"https": PROXY} if PROXY else dict()
    )

    articles = response.json()['articles'][:number_of_articles]
    return articles


# STEP 3: Use https://www.twilio.com
# Send a separate message with the percentage change and each article's title and description to your phone number.
def send_text(stock, per_change, article_info):
    print("\nSending Text message...")

    client = Client(TWILIO_SID, TWILIO_TOKEN)

    per_change = f"\n🔺{per_change}% in last 24hrs" if per_change > 0 else f"🔻{per_change}% in last 24hrs"

    for article in article_info:
        headline, brief, link = article['title'], article['description'], article['url']

        msg_format = f"\n\n{stock.upper()}: {per_change}" \
                     f"\n\nHeadline: {headline}" \
                     f"\n\nBrief: {brief}" \
                     f"\n\nLink: {link}"

        msg = client.messages.create(
            body=msg_format,
            from_=TWILIO_NUMBER,
            to=RECIPENT_PHONE_NUMBER
        )
        print(f"\tMessage Status: {msg.status}")


if __name__ == "__main__":
    price_movement = btc_change_24hr()
    news = get_news("bitcoin")
    send_text("bitcoin", per_change=price_movement, article_info=news)
