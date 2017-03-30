from urllib.parse import urlparse
import feedparser, logging, psycopg2, os, requests

class NYKParser:
    log_level = logging.DEBUG

    log = logging.Logger('parser')
    log.setLevel(log_level)

    log_handler = logging.StreamHandler()
    log_handler.setLevel(log_level)

    log_fmt = logging.Formatter('[{asctime}] [{levelname}]\n{message}\n',
                                datefmt = '%d-%m %H:%M:%S', style = '{')
    log_handler.setFormatter(log_fmt)

    log.addHandler(log_handler)


    def connect(self):
        """Connects to the database"""
        self.url = urlparse(os.environ["DATABASE_URL"])
        self.log.info('connecting to the database')
        self.db = psycopg2.connect(database=self.url.path[1:],
                                    user=self.url.username,
                                    password=self.url.password,
                                    host=self.url.hostname,
                                    port=self.url.port)

        self.log.info('connection established')

    def get_latest_title(self):
        """Retrieves the last item's title from the database"""
        c = self.db.cursor()
        c.execute('SELECT * FROM titles')

        self.latest_title = c.fetchone()[0]

        self.log.info('latest title is ' + self.latest_title)

        c.close()

    def parse(self):
        """Takes latest feed items and checks whether they are new"""
        try:
            feed = feedparser.parse('https://yandex.ru/blog/narod-karta/rss')
            self.log.info('feed parsed successfully')
        except Exception:
            self.log.warning('an error occured while parsing')
            exit()

        i = 0
        self.new_titles = []

        while True:
            if feed.items[i].title == self.latest_title:
                break

            self.new_titles.append([feed.items[i].title, feed.items[i].url])
            i += 1

    def num(self, n):
        """Gives the right form of the word"""
        if n % 10 == 1:
            return ' новый пост'
        elif n % 10 >= 11 and n % 10 <= 14:
            return ' новых постов'
        elif n % 10 >= 2 and n % 10 <= 4:
            return ' новых поста'
        else:
            return ' новых постов'

    def send(self):
        """Pushes new titles to Onesignal"""
        if not self.new_titles:
            self.log.info('no new titles, nothing to send')
            exit()

        header = {"Content-Type": "application/json",
                  "Authorization": str(os.environ['ONESIGNAL_AUTHORIZATION'])}
        payload = {"app_id": str(os.environ['ONESIGNAL_APP_ID']),
                   "headings": {"en": "Timetable"},
                   "contents": {"en": "лол кек"},
                   "url": "http://lyceum.urfu.ru/study/izmenHtml.php"
                  }


        if len(self.new_titles) == 1:
            self.log.info('sending one new title')

            payload["headings"] = {"en": self.new_titles[0][0]}
            payload["contents"] = {"en": "Нажмите для открытия поста."}
            payload[url] = self.new_titles[0][1]

        else:
            self.log.info('sending ' + str(len(self.new_titles))
                          + ' new titles')

            payload["headings"] = {"en": "В Клубе " + str(len(self.new_titles))
                                   + num(len(self.new_titles))}
            payload["contents"] = {"en": "Нажмите для открытия последнего."}
            payload[url] = self.new_titles[-1][1]

        req = requests.post("https://onesignal.com/api/v1/notifications",
                            headers = header,
                            data = json.dumps(payload))

        if req.status_code != requests.codes.ok:
            self.log.warning('error code' + str(req.status_code))
        else:
            self.log.info('sent successfully!')

    def save(self):
        """Records the latest title to the database"""

        c = self.db.cursor()
        c.execute('DELETE FROM titles')
        c.execute('INSERT INTO titles VALUES %s', (self.new_titles[-1][0],))

        self.log.info('db altering success, exiting')


parse = NYKParser()

parse.connect()
parse.get_latest_title()
parse.parse()
parse.send()
parse.save()
