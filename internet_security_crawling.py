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
from lithops.storage import Storage
from lithops.serverless import ServerlessHandler
import io
from hashlib import md5
import uuid
from flask import Flask, render_template, request
import operator


BUCKET_NAME='sd-task2'

twitter_consumer_key = "HULJLDcth2DlyCeQetSVImh0S"
twitter_consumer_secret = "UVPSLbfTudhGa4j1MlsmDA6KxXJUeY7mqGQkprdsHJD1rFcJH6"
twitter_access_token = "1313145032-gdwPOWniKGX9jbOwlUs1fqqJuDfLzue17FdNDUD"
twitter_access_token_secret = "s5YDPEylUR9hWuuNIXNIRmgTXoVkBKFwavxke2u8O49pi"

auth = tweepy.OAuthHandler(twitter_consumer_key, twitter_consumer_secret)
auth.set_access_token(twitter_access_token, twitter_access_token_secret)
api = tweepy.API(auth) 

fexec = lithops.FunctionExecutor(backend='ibm_cf', runtime='usipiton/lithops-custom1-runtime-3.9:0.1')

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')
def twitter_crawler_function(twitter_screen_name, init_path, storage):
    posts=[]
    for post in api.user_timeline(screen_name=twitter_screen_name, count=200, include_rts = False, tweet_mode = 'extended'):
        posts.append(post)
    return posts

def facebook_crawler_processing_function(facebook_token, init_path, storage):
    data={}
    graph = facebook.GraphAPI(facebook_token)
    field = ['id,name,email,birthday,link,location,gender,hometown,age_range,education,political,religion,posts']
    profile = graph.get_object(id="me",fields=field)
    posts2 = []

    path=init_path+'/facebook.csv'
    with open(path, 'a', encoding='utf-8') as f:
        writer = csv.writer(f)
        for post in profile['posts']['data']:
            if post.get('message'):
                row=["null", profile['name'], " ", profile['location'], profile['link'], 'null', 'null', 'null', 'null', 'null', 'null', 'null', profile['id'], "null", post.get('message')]
            rows_split=[]
            for field in row:
                rows_split.append(str(field).replace(',', " "))
            posts2.append(rows_split)

        with open(path, 'w', encoding='utf-8') as f:    
            writer = csv.writer(f)
            fexec.call_async(political_research, posts2)
            political_pred = fexec.get_result()
            fexec.call_async(religion_research, posts2)
            religion_pred = fexec.get_result()
            for post in posts2:
                if(len(post) > 14):
                    post[5] = political_pred
                    post[6] = religion_pred
                writer.writerow(post)

    with open(path, 'r', encoding='utf8') as csvfile:
        text = csvfile.read()
        csv_id = storage.put_cloudobject(text, BUCKET_NAME, path)
    return csv_id

def twitter_preprocessing_function(posts, init_path, storage):
    path=init_path+"/twitter.csv"
    posts2 = []
    
    for info in posts:
        try:
            row=[info.user.screen_name, info.user.name, info.user.created_at, info.user.location, 'https://twitter.com/'+info.user.screen_name, ' ', ' ', info.user.protected, info.user.geo_enabled, info.geo, info.coordinates, info.user.description, info.id, info.created_at, info.full_text]
        except:
            row=[info.user.screen_name, info.user.name, info.user.created_at, info.user.location, 'https://twitter.com/'+info.user.screen_name, ' ', ' ', info.user.protected, info.user.geo_enabled, info.geo, info.coordinates, info.user.description, info.id, info.created_at, info.text]
        rows_split=[]
        for field in row:
            rows_split.append(str(field).replace(',', " "))
        posts2.append(rows_split)
    
    with open(path, 'r+', encoding='utf-8') as f:    
        writer = csv.writer(f)
        fexec.call_async(political_research, posts2)
        political_pred = fexec.get_result()
        fexec.call_async(religion_research, posts2)
        religion_pred = fexec.get_result()
        for post in posts2:
            if(len(post) > 14):
                post[5] = political_pred
                post[6] = religion_pred
            writer.writerow(post)
        text = f.read()
        csv_id = storage.put_cloudobject(text, BUCKET_NAME, path)
    return csv_id

def check_create_dir(path, media):
    header = ['id', 'user_name', 'name', 'account_created_at', 'location', 'URL', 'political_analysis', 'religion_analysis', 'protected', 'geo_enabled ', 'geo', 'coordinates', 'description', 'post_id', 'post_created_at', 'post_text']
    if not os.path.exists(path):
        os.mkdir(path)
        f = open(path+media, 'a')
        writer = csv.writer(f)
        writer.writerow(header)
        f.close()
      
      
def do_predictions(dir_path, tcsv_id, fcsv_id, storage):
    score = 0
    facebook_csv = storage.get_cloudobject(fcsv_id)
    twitter_csv = storage.get_cloudobject(tcsv_id)
    facebook_csv = facebook_csv.decode()
    twitter_csv = twitter_csv.decode()
    i=0
    valid_post=False
    posts = twitter_csv.split('\n')
    posts.extend(facebook_csv.split('\n'))
    post = ""
    while(i<len(posts) and valid_post is False):
        if(posts[i] != ' ' and posts[i] != '' and i != 0):
            post = posts[i]
            if(len(post) > 14):
                valid_post=True
        i+=1
    score+=profile_security_research(post.split(','))
    score+=prediction_analysis(post.split(','))
    return score

### Vulnerability Scoring (CVSS Score):
#     0-39 -->Low
#     40-69 -->Medium
#     70-89 -->High
#     90-∞ -->Critical
# Parameters:
#     public profile-->+35 points
#     geo_enabled-->+90 points
#     location-->+5 points
#     political idelogy != neutral-->+40 points
#     religion ideology not neutral-->+40 points
def profile_security_research(post):
    score=0
    #print(len(post[3]))
    if(len(post) > 14):
        if(len(post[3]) > 0 ): score+=5           #location
        if(post[7] !=  "True"): score+=10      #public profile
        if((post[8] != "False") and (post[9] != "None") and (post[10] != "None")): score+=90     #geo enabled and the position is visible
    return score

def prediction_analysis(post):
    score = 0
    if(len(post) > 14):
        if(post[5] != "neutral"): score+=40   #politic
        if(post[6] != "neutral"): score+=40   #religion
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
    for post in posts:
        if(len(post) > 14):
            for word in democrats_words:
                if(word in post[11] or word in post[14]):
                    democrat_words_freq+=1
            for word in republicans_words:
                if(word in post[11] or word in post[14]):
                    republican_words_freq+=1
    if democrat_words_freq>republican_words_freq:
        return "democrat"
    if democrat_words_freq<republican_words_freq:
        return "republican"
    else:
        return "neutral"

def religion_research(posts):
    islam_words = ["allah", "fatwa", "hadj", "hajj","hijjah" "islam", "mecca", "muhammad", "mosque", "muslim", 
        "prophet", "ramadan", "salam", "salaam", "sharia", "suhoor", "sunna", "sunnah", "sunni", "koran", "coran", 
        "qur'an", "hijab", "halal", "hadith", "imam", "madrassah", "salat", "sawm", "shahada", "sura", "tafsir",
        "zakat", "kaaba", "eid al fitr","khutbah", "eid al adha", "p.b.u.h"]
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
    for post in posts:
        if(len(post) > 14):
            descr = post[11].lower()
            post_text = post[14].lower()
            for word in islam_words:
                if(word in descr or word in post_text):
                    islam_words_freq+=1
            for word in catholic_words:
                if(word in descr or word in post_text):
                    catholic_words_freq+=1
            for word in jewish_words:
                if(word in descr or word in post_text):
                    jewish_words_freq+=1
            for word in budism_words:
                if(word in descr or word in post_text):
                    budism_words_freq+=1
    results={}
    results["catholic"]=catholic_words_freq
    results["islam"]=islam_words_freq
    results["jewish"]=jewish_words_freq
    results["budism"]=budism_words_freq
    max_value=max(results.items(), key=operator.itemgetter(1))[0]
    if (results.get(max_value) > 0):
        return max_value
    else:
        return "neutral"

@app.route('/do_security_analysis')
def do_security_analysis():
    registred_users = {}
    #avatar = request.args.get('avatar')
    avatar="usipiton"
    if(avatar in registred_users.keys()):
        init_path = registred_users.get(avatar)
    else:
        init_path = registred_users[avatar] = str(uuid.uuid4())
    
    fexec.call_async(twitter_crawler_function, (request.args.get('tname'), init_path))
    posts = fexec.get_result()
    fexec.call_async(twitter_preprocessing_function, (posts, init_path))
    tcsv_id = fexec.get_result()
    fexec.call_async(facebook_crawler_processing_function, (request.args.get('fname'), init_path))
    fcsv_id = fexec.get_result()
    fexec.call_async(do_predictions, (init_path, tcsv_id, fcsv_id))
    return str(fexec.get_result())

if __name__ == '__main__':
  app.run(debug=True)  