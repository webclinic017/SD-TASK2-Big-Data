import facebook
import tweepy
import lithops
import urllib3
import csv
import os
import sys
import redis
import json
from lithops.storage import Storage
from lithops.serverless import ServerlessHandler
import io
from hashlib import md5
import uuid
from flask import Flask, render_template, request
import operator
import pandas as pd

BUCKET_NAME='sd-task2'

twitter_consumer_key = "HULJLDcth2DlyCeQetSVImh0S"
twitter_consumer_secret = "UVPSLbfTudhGa4j1MlsmDA6KxXJUeY7mqGQkprdsHJD1rFcJH6"
twitter_access_token = "1313145032-gdwPOWniKGX9jbOwlUs1fqqJuDfLzue17FdNDUD"
twitter_access_token_secret = "s5YDPEylUR9hWuuNIXNIRmgTXoVkBKFwavxke2u8O49pi"

posts_header = ["political_analysis", "religion_analysis", "coordinates", "post_id", "post_created_at", "post_text"]
profile_header = ["id", "user_name", "name", "account_created_at", "location", "URL", "protected", "geo_enabled", "description"]
auth = tweepy.OAuthHandler(twitter_consumer_key, twitter_consumer_secret)
auth.set_access_token(twitter_access_token, twitter_access_token_secret)
api = tweepy.API(auth)

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

def facebook_profile_crawler(facebook_token):
    graph = facebook.GraphAPI(facebook_token)
    field = ['id,name,link,location']
    profile = graph.get_object(id="me",fields=field)
    row = [str(profile['id']).replace(',', " "), "null", str(profile['name']).replace(',', " "), "null", str(profile['location']['name']).replace(',', " "), str(profile['link']).replace(',', " "), 'null', 'null',
        "null"]
    return row

def twitter_profile_crawler(twitter_screen_name):
    user = api.get_user(twitter_screen_name)
    row = [str(user.id_str), str(user.screen_name).replace(',', " "), str(user.name).replace(',', " "), str(user.created_at).replace(',', " "), str(user.location).replace(',', " "), 
       str(user.url).replace(',', " "), str(user.protected).replace(',', " "), str(user.geo_enabled).replace(',', " "), 
       str(user.description).replace(',', " ")]
    return row

def twitter_crawler_function(twitter_screen_name):
    posts=[]
    for post in api.user_timeline(screen_name=twitter_screen_name, count=200, include_rts = False, tweet_mode = 'extended'):
        posts.append(post)
    return posts

def facebook_posts_crawler(facebook_token):
    graph = facebook.GraphAPI(facebook_token)
    field = ['posts']
    profile = graph.get_object(id="me",fields=field)

    for post in profile['posts']['data']:
        if post.get('message'):
            row = [" ", " ", str(post.get('id')), str(profile.get('created_time')), "null", "null", str(post.get('message').replace(',', " "))]
    return row

def twitter_posts_preprocessing(post):
    row = []
    try:
        row=[" ", " ", str(post.id).replace(',', " "), str(post.created_at).replace(',', " "), str(post.geo).replace(',', " "), str(post.coordinates).replace(',', " "), str(post.full_text.replace(',', " "))]
    except:
        row=[" ", " ", str(post.id).replace(',', " "), str(post.created_at).replace(',', " "), str(post.geo).replace(',', " "), str(post.coordinates).replace(',', " "), str(post.text.replace(',', " "))]
    return row

def merge_and_push_info(posts, tprofile, fprofile, path, storage):
    #posts = do_predictions(posts)
    id = storage.put_cloudobject(write_csv_body([tprofile,fprofile,posts]), BUCKET_NAME, path+".csv")
    return id

#def do_predictions(posts):
#    political_pred = political_analysis(posts)
#    religion_pred = religion_analysis(posts)
#    for post in posts:
#        if(len(post) > 5):
#            post[0] = political_pred
#            post[1] = religion_pred
#    return posts

def write_csv_body(csv_content):
    output = io.StringIO()
    w = csv.writer(output)
    i=0
    for i in range(2):
        w.writerow(csv_content[i])
    for row in csv_content[2]:
        w.writerow(row)
    return str.encode(output.getvalue())

def write_csv_posts(texts):
    output = io.StringIO()
    w = csv.writer(output)
    i=0
    for row in texts:
        w.writerow(row)
    return str.encode(output.getvalue())

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
def profile_scoring(twitter_profile, facebook_profile):
    score=0
    twitter_profile = twitter_profile.split(',')
    facebook_profile = facebook_profile.split(',')
    if(len(twitter_profile) > 8 or len(facebook_profile) > 8):
        if(len(twitter_profile[4]) > 0 or len(facebook_profile[4]) > 0): score+=5           #location
        if("True" in str(twitter_profile[6])): score+=10      #public profile
        if(("False" not in str(twitter_profile[7]))): score+=90     #geo enabled and the position is visible, twitter excl
    return score

def predictions_scoring(post):
    score = -1
    post = post.split(',')
    if(len(post) > 5):
        score =  0
        if(post[0] != "neutral"): score+=40   #politic
        if(post[1] != "neutral"): score+=40   #religion
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

    religions = [
        {'religion':'islam'},
        {'religion':'catholic'},
        {'religion':'jewish'},
        {'religion':'budism'}
    ]




    islam_words_freq=0
    catholic_words_freq=0
    jewish_words_freq=0
    budism_words_freq=0
    for post in posts:
        if(len(post) > 6):
            descr = post[4].lower()
            post_text = post[5].lower()
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
    fexec = lithops.FunctionExecutor(backend='ibm_cf', runtime='usipiton/lithops-custom1-runtime-3.9:0.1')
    registred_users = {}
    posts = []
    score = 0
    #avatar = request.args.get('avatar')
    avatar="usi"

    if(avatar in registred_users.keys()):
        path = registred_users.get(avatar)
    else:
        path = registred_users[avatar] = str(uuid.uuid4())
    
    twitter_username = request.args.get('tname')
    facebook_token = request.args.get('fname')
    if twitter_username is not None:
        fexec.call_async(twitter_profile_crawler, twitter_username)
        fexec.wait()
        twitter_profile=fexec.get_result()
        fexec.call_async(twitter_crawler_function, twitter_username)
        twitter_posts = fexec.get_result()
        posts.append(twitter_posts)
    if facebook_token is not None:
        fexec.call_async(facebook_profile_crawler, facebook_token)
        facebook_profile = fexec.get_result()
        fexec.call_async(facebook_posts_crawler, facebook_token)
        facebook_posts = fexec.get_result()
        posts.append(facebook_posts)

    fexec.call_async(merge_and_push_info, (posts, twitter_profile, facebook_profile, path))
    fexec.wait()
    obj_id = fexec.get_result()
    invoke_notebook(obj_id, fexec)
    return str(score)

if __name__ == '__main__':
  app.run(debug=True)  