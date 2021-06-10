import tweepy
import lithops
import urllib3
import csv
import os
import sys
import redis
import json
from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.server import SimpleXMLRPCRequestHandler

twitter_consumer_key = "HULJLDcth2DlyCeQetSVImh0S"
twitter_consumer_secret = "UVPSLbfTudhGa4j1MlsmDA6KxXJUeY7mqGQkprdsHJD1rFcJH6"
twitter_access_token = "1313145032-gdwPOWniKGX9jbOwlUs1fqqJuDfLzue17FdNDUD"
twitter_access_token_secret = "s5YDPEylUR9hWuuNIXNIRmgTXoVkBKFwavxke2u8O49pi"
userID = "usama12_usama"
header = ['user_name', 'name', 'account_created_at', 'location', 'URL', 'sentiment_analysis', 'protected', 'geo_enabled ', 'description', 'post_id', 'post_created_at', 'post_text']

auth = tweepy.OAuthHandler(twitter_consumer_key, twitter_consumer_secret)
auth.set_access_token(twitter_access_token, twitter_access_token_secret)
api = tweepy.API(auth) 

class Master():

    def __init__(self,ip,port):
        self.redis_connection=redis.Redis(
            host=os.getenv("REDIS_HOST", ip),
            port=os.getenv("REDIS_PORT", port),
        )
        self.TASKS={}
        self.TASK_ID=0
        self.WORKERS ={}
        self.WORKER_ID = 0

    def twitter_crawler_worker(self):
        post = []
        while True:
            screen_name=self.redis_connection.rpop('queue:users')
            user=api.get_user(screen_name)
            for info in api.user_timeline(screen_name=screen_name, count=200, include_rts = True, tweet_mode = 'extended'):
                status = api.get_status(info.id)
                post.append()
                self.redis_connection.rpush('queue:posts', json.dumps([result, id]))
            for favorite in tweepy.Cursor(api.favorites, id=screen_name).items(20):
            
    
    def preprocessing_worker(self):
        while True:
            if screen_name:
                screen_name=json.loads(screen_name)
                if screen_name:
                    try:
                        user=api.get_user(screen_name)
                        if not os.path.exists(str(user.id)):
                            os.makedirs(str(user.id))
                            f = open(str(user.id)+'/twitter.txt', 'a')
                            writer = csv.writer(f)
                            writer.writerow(header)
                        for info in api.user_timeline(screen_name=screen_name, count=200, include_rts = True, tweet_mode = 'extended'):
                            status = api.get_status(info.id)
                            row=[info.user.screen_name, info.user.name, info.user.created_at, info.user.location, 'https://twitter.com/'+info.user.screen_name, ' ', info.user.protected, info.user.geo_enabled, info.user.description, info.id, info.created_at, info.full_text]
                            writer.writerow(row)
                        for favorite in tweepy.Cursor(api.favorites, id=screen_name).items(20):
                            row=[info.user.screen_name, info.user.name, info.user.created_at, info.user.location, 'https://twitter.com/'+info.user.screen_name, ' ', info.user.protected, info.user.geo_enabled, info.user.description, favorite.id, favorite.created_at, favorite.text]
                            writer.writerow(row)
                        f.close
                    except ValueError:
                        print("user not found")

def political_research(posts):
    ###clarification: all keywords have been selected based on the frequency of their use, rather than personal opinions
    democrats_words = ["family", "care", "cut", "support", "thank", "new", "student", "need", "help", "equal pay", "fair", 
        "bin laden", "wall street", "worker", "veteran", "fight", "invest", "education", "military", "war", "medicare", "science", 
        "forward", "women", "seniors", "biden"]
    republicans_words = ["good", "security", "great", "unite", "senate", "thank", "good", "meet", "hear", "join", "government", 
        "flag", "church", "unemployment", "regulation", "obamacare", "fail", "better", "faith", "business", "small business", "romney", 
        "leadership", "god", "debt", "spending", "success"]

    democrat_words_freq=0
    republican_words_freq=0
    for field in posts:
        for word in democrats_words:
            if word in field:
                democrat_words_freq+=1
        for word in republicans_words:
            if word in field:
                republican_words_freq+=1

    if democrat_words_freq>republican_words_freq:
        return "democrat"
    if democrat_words_freq<republican_words_freq:
        return "republican"
    else:
        return "neutral"

def religion_research(posts):
    islam_words = ["allah", "fatwa", "hadj", "hajj", "islam", "mecca", "muhammad", "mosque", "muslim", 
        "prophet", "ramadan", "salam", "salaam", "sharia", "suhoor", "sunna", "sunnah", "sunni", "koran", "coran", 
        "qur'an", "hijab", "halal", "hadith", "imam", "madrassah", "salat", "sawm", "shahada", "sura", "tafsir",
        "zakat", "kaaba", "eid al-fitr", "eid al-adha", "p.b.u.h"]
    catholic_words = ["apostle", "assembly", "bible", "blessed sacrament", "celebrant", "discernment", "disciple", 
        "easter", "gospel", "eucharist", "grace", "communion", "holy water", "jesus", "christ", "new testament", "old testament",
        "sacrament", "catholic", "christmas", "christian", "confession", "convent", "godparent", "immaculate", "pentateuch", "saint",
        "prophet", "protestant", "church", "ecclesiastic", "episcopal"]
    jewish_words = ["torah", "shalom", "kosher", "chutzpah", "kippah", "mazel tov", "adar", "achashverosh", "bimah",
        "daven", "gelilah", "hakafot", "halachah", "iyar", "kiddish", "nisan", "nine day", "shmot", "shul", "simchat",
        "vayikra", "yizkor", "zichrono livracha", "yerushalayim", "yisrael"]
    budism_words = ["ajahn chah", "advaita vedanta", "ayya khema", "bhikkhu payutto", "buddha", "buddhism", "buddhist",
        "chan", "chi kung", "dana", "dharma", "dhamma", "gelugpa", "jhana", "koan", "mahasi", "mahayana", "nibbana", 
        "nirvana", "pali", "seva", "sanskrit", "zen"]

    islam_words_freq=0
    catholic_words_freq=0
    jewish_words_freq=0
    budism_words_freq=0
    for field in posts:
        for word in islam_words:
            if word in field:
                islam_words_freq+=1
        for word in catholic_words:
            if word in field:
                catholic_words_freq+=1
        for word in jewish_words:
            if word in field:
                jewish_words_freq+=1
        for word in budism_words:
            if word in field:
                budism_words_freq+=1

###falta adaptarlo, esta es la idea
master=Master("localhost","6379")
# Ceate server
server=SimpleXMLRPCServer(('localhost', 9000),
    requestHandler=RequestHandler,
    logRequests=True,
    allow_none=True)

server.register_multicall_functions()
server.register_introspection_functions
server.register_instance(master)
server.register_function(create_w, 'create_w')
server.register_function(delete_w, 'delete_w')
server.register_function(get_result, 'get_result')
server.register_function(list_workers, 'list_workers')
# Run the server's main loop
try:
    print('Use Control-C to exit')
    server.serve_forever()
except KeyboardInterrupt:
    print('Exiting')