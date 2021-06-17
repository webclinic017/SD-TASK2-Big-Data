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
import ast

BUCKET_NAME='sd-task2'

twitter_consumer_key = "HULJLDcth2DlyCeQetSVImh0S"
twitter_consumer_secret = "UVPSLbfTudhGa4j1MlsmDA6KxXJUeY7mqGQkprdsHJD1rFcJH6"
twitter_access_token = "1313145032-gdwPOWniKGX9jbOwlUs1fqqJuDfLzue17FdNDUD"
twitter_access_token_secret = "s5YDPEylUR9hWuuNIXNIRmgTXoVkBKFwavxke2u8O49pi"

posts_header = ["political_analysis", "religion_analysis", "protected", "geo_enabled", "geo", "coordinates", "description", "post_id", "post_created_at", "post_text"]
profile_header = ["id", "user_name", "name", "account_created_at", "location", "URL"]
auth = tweepy.OAuthHandler(twitter_consumer_key, twitter_consumer_secret)
auth.set_access_token(twitter_access_token, twitter_access_token_secret)
api = tweepy.API(auth)

fexec = lithops.FunctionExecutor(backend='ibm_cf', runtime='usipiton/lithops-custom1-runtime-3.9:0.1')
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

def facebook_profile_crawler(facebook_token):
    graph = facebook.GraphAPI(facebook_token)
    field = ['id,name,link,location']
    profile = graph.get_object(id="me",fields=field)
    row = [str(profile['id']).replace(',', " "), "null", str(profile['name']).replace(',', " "), "null", str(profile['location']).replace(',', " "), str(profile['link']).replace(',', " "), 'null', 'null',
        "null"]
    return row

def twitter_profile_crawler(twitter_screen_name):
    user = api.get_user(twitter_screen_name)
    row=[str(user.id_str), str(user.screen_name).replace(',', " "), str(user.name).replace(',', " "), str(user.created_at).replace(',', " "), str(user.location).replace(',', " "), 
       str(user.url).replace(',', " "), str(user.protected).replace(',', " "), str(user.geo_enabled).replace(',', " "), 
       str(user.description).replace(',', " ")]
    return row

def twitter_crawler_function(twitter_screen_name, storage):
    posts=[]
    for post in api.user_timeline(screen_name=twitter_screen_name, count=200, include_rts = False, tweet_mode = 'extended'):
        posts.append(post)
    return posts

def facebook_posts_crawler(facebook_token, storage):
    graph = facebook.GraphAPI(facebook_token)
    field = ['posts']
    profile = graph.get_object(id="me",fields=field)

    for post in profile['posts']['data']:
        if post.get('message'):
            row = [" ", " ", str(post.get('id')), str(profile.get('created_time')), "null", "null", str(post.get('message').replace(',', " "))]
    return row

def twitter_posts_preprocessing(post, storage):
    row = []
    try:
        row=[" ", " ", str(post.id).replace(',', " "), str(post.created_at).replace(',', " "), str(post.geo).replace(',', " "), str(post.coordinates).replace(',', " "), str(post.full_text.replace(',', " "))]
    except:
        row=[" ", " ", str(post.id).replace(',', " "), str(post.created_at).replace(',', " "), str(post.geo).replace(',', " "), str(post.coordinates).replace(',', " "), str(post.text.replace(',', " "))]
    return row

def merge_and_push_info(posts, tprofile, fprofile, path, storage):
    posts_dict = {}
    profile_dict = {}

    profile_dict = {}
    posts_dict = {}

    for k in profile_header:
        profile_dict[k] = []
    for k in posts_header:
        posts_dict[k] = []
    
    for profile_field, column_name in zip(tprofile, profile_header):
        profile_dict[column_name].append(profile_field)
    for profile_field, column_name in zip(fprofile, profile_header):
        profile_dict[column_name].append(profile_field)
    for field, column_name in zip(posts, posts_header):
        posts_dict[column_name].append(field)
    posts_dict = do_predictions(posts_dict)
    id = storage.put_cloudobject(write_csv_dict(profile_dict | posts_dict), BUCKET_NAME, path+".csv")
    return id

def do_predictions(posts_dict):
    political_pred = political_analysis(posts_dict.values())
    religion_pred = religion_analysis(posts_dict.values())
    for post in posts_dict.values():
        if(len(post) > 14):
            post[5] = political_pred
            post[6] = religion_pred
    return posts_dict

def write_csv_dict(complete_dict):
    output = io.StringIO()
    w = csv.DictWriter(output, complete_dict.keys())
    for v in complete_dict.values():
        w.writerow(v)
    return str.encode(output.getvalue())

def total_scoring(obj_id, storage):
    score = 0
    posts = storage.get_cloudobject(obj_id).decode()
    print(ast.literal_eval(posts))
    i=0
    valid_post=False
    posts = posts.split("\",")
    score+=predictions_scoring(post.split(','))
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
def profile_scoring(twitter_post, facebook_post):
    score=0
    #print(len(post[3]))
    if(len(twitter_post) > 14):
        if(len(twitter_post[3]) > 0 or len(facebook_post[3]) > 0): score+=5           #location
        if(twitter_post[7] !=  "True" or facebook_post[7] !=  "True"): score+=10      #public profile
        if((twitter_post[8] != "False") and (twitter_post[9] != "None") and (twitter_post[10] != "None")): score+=90     #geo enabled and the position is visible, twitter excl
    return score

def predictions_scoring(post):
    score = 0
    if(len(post) > 14):
        if(post[5] != "neutral"): score+=40   #politic
        if(post[6] != "neutral"): score+=40   #religion
    return score

def political_analysis(posts):
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

def religion_analysis(posts):
    islam_words = ["allah", "fatwa", "hadj", "hajj","hijjah", "islam", "mecca", "muhammad", "mosque", "muslim", 
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
    
def get_valid_post(posts):
    post = " "
    valid_post = False
    i = 0
    while(i<len(posts) and valid_post is False):
        if(posts[i] != ' ' and posts[i] != '' and i != 0):
            post = posts[i]
            if(len(post) > 14):
                valid_post=True
        i+=1
    return post

@app.route('/do_security_analysis')
def do_security_analysis():
    registred_users = {}
    posts = []
    posts2 = []
    score = 0
    #avatar = request.args.get('avatar')
    avatar="usipiton"
    storage = Storage()
    if(avatar in registred_users.keys()):
        path = registred_users.get(avatar)
    else:
        path = registred_users[avatar] = str(uuid.uuid4())
    storage = Storage()
    twitter_username = request.args.get('tname')
    facebook_token = request.args.get('fname')
    if twitter_username is not None:
        twitter_profile=twitter_profile_crawler(twitter_username)
    
        posts=twitter_crawler_function(twitter_username, storage)
        twitter_posts=[]
        for post in posts:
            twitter_posts+=twitter_posts_preprocessing(post, storage)
            

    if facebook_token is not None:
        facebook_profile=facebook_profile_crawler(facebook_token)
        facebook_posts=facebook_posts_crawler(facebook_token, storage)

    posts = twitter_posts + facebook_posts
    obj_id=merge_and_push_info(posts, twitter_profile, facebook_profile, path, storage)

    profile_scoring(twitter_profile, facebook_profile)

    total_scoring(obj_id, storage)
    return str(1)

if __name__ == '__main__':
  app.run(debug=True)  