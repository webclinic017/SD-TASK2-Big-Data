import facebook
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
import ocs


twitter_consumer_key = "HULJLDcth2DlyCeQetSVImh0S"
twitter_consumer_secret = "UVPSLbfTudhGa4j1MlsmDA6KxXJUeY7mqGQkprdsHJD1rFcJH6"
twitter_access_token = "1313145032-gdwPOWniKGX9jbOwlUs1fqqJuDfLzue17FdNDUD"
twitter_access_token_secret = "s5YDPEylUR9hWuuNIXNIRmgTXoVkBKFwavxke2u8O49pi"
userID = "usama12_usama"
header = ['user_name', 'name', 'account_created_at', 'location', 'URL', 'political_analysis', 'religion_analysis', 'protected', 'geo_enabled ', 'geo', 'coordinates', 'description', 'post_id', 'post_created_at', 'post_text']

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

    def twitter_crawler_worker(self, twitter_screen_name, facebook_id):
        post=[]
        ###twitter requests
        user=api.get_user(twitter_screen_name)
        for post in api.user_timeline(screen_name=twitter_screen_name, count=200, include_rts = True, tweet_mode = 'extended'):
            post.append(post)
        for post in tweepy.Cursor(api.favorites, id=twitter_screen_name).items(20):
            post.append(post)
                ###parte de facebook

    def preprocessing_worker(self, posts):
        userID=posts[0].user.id
        while True:
            if not os.path.exists(str(userID)):
                os.makedirs(str(userID))
                f = open(str(userID)+'/twitter.txt', 'a')
                writer = csv.writer(f)
                writer.writerow(header)
                ocs.multi_part_upload(ocs.credentials.get('BUCKET'),str(userID),str(userID)+'.csv')
            for info in posts:
                row=[info.user.screen_name, info.user.name, info.user.created_at, info.user.location, 'https://twitter.com/'+info.user.screen_name, ' ', ' ', info.user.protected, info.user.geo_enabled, info.status.geo, info.status.coordinates, info.user.description, info.id, info.created_at, info.full_text]
                writer.writerow(row)
            f.close

### Vulnerability Scoring (CVSS Score):
#     0-39 -->Low
#     40-69 -->Medium
#     70-89 -->High
#     90-∞ -->Critical
# Parameters:
#     public profile-->+35 points
#     geo_enabled-->+90 points
#     location-->+5 points
#     political idelogy is not neutral-->+40 points
#     religion ideology not neutral-->+40 points
def profile_security_research(post):
    score=0
    if(post[3] is not ""): score+=5           #location
    if(post[6] is not "neutral"): score+=40
    if(post[7] is not "neutral"): score+=40
    if(post[8] is not "True"): score+=10      #public profile
    if((post[9] is not "False") and (post[10] is not "False") and (post[11] is not "False")): score+=90     #geo enabled and the position is visible
    return score
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
        "zakat", "kaaba", "eid al fitr", "eid al adha", "p.b.u.h"]
    catholic_words = ["apostle", "assembly", "bible", "blessed sacrament", "celebrant", "discernment", "disciple", 
        "easter", "gospel", "eucharist", "grace", "communion", "holy water", "jesus", "christ", "new testament", "old testament",
        "sacrament", "catholic", "christmas", "christian", "confession", "convent", "godparent", "immaculate", "pentateuch", "saint",
        "protestant", "church", "ecclesiastic", "episcopal"]
    jewish_words = ["torah", "shalom", "kosher", "chutzpah", "kippah", "mazel tov", "adar", "achashverosh", "bimah",
        "daven", "gelilah", "hakafot", "halachah", "iyar", "kiddish", "nisan", "nine day", "shmot", "shul", "simchat",
        "vayikra", "yizkor", "zichrono livracha", "yerushalayim", "yisrael"]
    budism_words = ["ajahn chah", "advaita vedanta", "ayya khema", "bhikkhu payutto", "buddha", "buddhism", "buddhist",
        "chan", "chi kung", "dana", "dharma", "dhamma", "gelugpa", "jhana", "koan", "mahasi", "mahayana", "nibbana", 
        "nirvana", "pali", "sanskrit", "zen"]
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
        results=[catholic_words, islam_words_freq, jewish_words, budism_words]
    if max(results)>0:
        return results.get(max(results))
    else:
        return "neutral"


def dades_facebook(token):
    graph = facebook.GraphAPI(token)
    field = ['name,email,birthday,location,gender,hometown,age_range,education,languages,political,religion,posts']
    profile = graph.get_object("me",fields=field)
    print(profile)

