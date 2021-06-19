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
import re
import numpy as np
import string

BUCKET_NAME='sd-task2'
fexec = lithops.FunctionExecutor(backend='ibm_cf', runtime='usipiton/lithops-custom1-runtime-3.9:0.1')
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
    row = [str(profile['id']), "null", cleaner(str(profile['name'])), "null", cleaner(str(profile['location']['name'])), cleaner(str(profile['link'])), 'null', 'null',
        "null"+"%"]
    return row

def twitter_profile_crawler(twitter_screen_name):
    user = api.get_user(twitter_screen_name)
    row = [str(user.id_str), cleaner(str(user.screen_name)), cleaner(str(user.name)), cleaner(str(user.created_at)), cleaner(str(user.location)), 
       cleaner(str(user.url)), cleaner(str(user.protected)), cleaner(str(user.geo_enabled)), cleaner(str(user.description))+"%"]
    return row

def twitter_crawler_function(twitter_screen_name):
    posts=[]
    for post in api.user_timeline(screen_name=twitter_screen_name, count=200, include_rts = False, tweet_mode = 'extended'):
        posts.append(post)
    lista=[]
    for post in posts:
        lista.append(twitter_posts_preprocessing(post))
    return lista

def facebook_posts_crawler(facebook_token):
    graph = facebook.GraphAPI(facebook_token)
    field = ['posts']
    profile = graph.get_object(id="me",fields=field)
    posts = []
    for post in profile['posts']['data']:
        if post.get('message'):
            row = ["null", "null", str(post.get('id')), str(profile.get('created_time')), "null", "null", cleaner(str(post.get('message')))+"%"]
            posts.append(row)
    return posts

def twitter_posts_preprocessing(post):
    row = []
    try:
        row=["null", "null", str(post.id), str(post.created_at), cleaner(str(post.geo)), cleaner(str(post.coordinates)), cleaner(str(post.full_text))+"%"]
    except:
        row=["null", "null", str(post.id), str(post.created_at), cleaner(str(post.geo)), cleaner(str(post.coordinates)), cleaner(str(post.text))+"%"]
    return row

def merge_and_push_info(posts, tprofile, fprofile, path, storage):
    posts = do_predictions(posts)
    id = storage.put_cloudobject(write_csv_body([tprofile,fprofile,posts]), BUCKET_NAME, "sd"+".csv")
    return id

def do_predictions(posts):
    political_pred = political_analysis(posts)
    religion_pred = religion_analysis(posts)
    for post in posts:
        if(len(post) > 5):
            post[0] = political_pred
            post[1] = religion_pred
    return posts

def write_csv_body(csv_content):
    output = io.StringIO()
    w = csv.writer(output)
    i=0
    for i in range(2):
        w.writerow(csv_content[i])
    for row in csv_content[2]:
        w.writerow(row)
    return output.getvalue().encode('utf8')


def write_csv_posts(posts):
    list_p = []
    i = 2
    for i in range(len(posts)):
        list_p.append(posts[i][6])
        i+=1
    output = io.StringIO()
    w = csv.writer(output, delimiter='\n')
    w.writerow(list_p)
    return output.getvalue().encode('utf8')

def split_posts_text(posts):
    posts_split = []
    for post in posts:
        post_split = post.split(',')
        if len(post_split)>4 and post_split[6] !='': 
            posts_split.append(post_split)
    return posts_split

def cleaner(field):
    field = re.sub("@[A-Za-z0-9]+","",field) #Remove @ sign
    field = re.sub(r"(?:\@|http?\://|https?\://|www)\S+", "", field) #Remove http links
    field = field.replace("#", "").replace("_", " ") #Remove hashtag sign but keep the text
    field = re.sub(r'\d+', '', field)
    field = field.translate(str.maketrans('', '', string.punctuation))
    field = field.strip()
    field = field.lower()
    field = field.replace('\r', '').replace('\n','')
    return field

def show_basic_statistics(df):
    count = df['posts_text'].str.split().str.len()
    count.index = count.index.astype(str) + 'words:'
    count.sort_index(inplace=True)
    #Basic statistics
    print("Total number of words", count.sum(), "words")
    print("Mean number of words per tweet:", round(count.mean(),2), "words")
    df["tweet_length"] = df["posts_text"].str.len()
    print("Total length of the dataset is:", df.tweet_length.sum(), "chars")
    print("Mean length of a tweet is: ", round(df.tweet_lenth.mean(),0), "chars")

def total_scoring(obj_id, storage):
    score = 0
    posts = storage.get_cloudobject(obj_id).decode('utf8')
    posts_split = split_posts_text(posts.split('%'))
    output = write_csv_posts(posts_split)
    storage.put_cloudobject(output,'sd-task2', 'dades.csv') #push data to notebook statistics
    posts_split = split_posts_text(posts.split('%'))

    score+=profile_scoring(posts_split[0], posts_split[1])
    score=predictions_scoring(posts_split)
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
def profile_scoring(twitter_profile, facebook_profile):
    score=0
    if(len(twitter_profile) > 8 or len(facebook_profile) > 8):
        if(len(twitter_profile[4]) > 0 or len(facebook_profile[4]) > 0): score+=5           #location
        if("True" in str(twitter_profile[6])): score+=10      #public profile
        if(("False" not in str(twitter_profile[7]))): score+=90     #geo enabled and the position is visible, twitter excl
    return score

def predictions_scoring(post):
    score = -1
    if(len(post) > 5):
        score =  0
        if(post[0] != "neutral"): score+=40   #politic
        if(post[1] != "neutral"): score+=40   #religion
    return score
   
def countFrequency(my_list, freq):
 
    # Creating an empty dictionary
    for item in my_list:
        if (item in freq.keys()):
            freq[item] += 1
    return freq
            
def political_analysis(texts):
    ###clarification: all keywords have been selected based on the frequency of their use, rather than personal opinions
    democrats_words = ["family", "care", "cut", "support", "thank", "new", "student", "need", "help", "equal pay", "fair", 
        "bin laden", "wall street", "worker", "veteran", "fight", "invest", "education", "military", "war", "medicare", "science", 
        "forward", "women", "seniors", "biden"]
    republicans_words = ["good", "security", "great", "unite", "senate", "thank", "good", "meet", "hear", "join", "government", 
        "flag", "church", "unemployment", "regulation", "obamacare", "fail", "better", "faith", "business", "small business", "romney", 
        "leadership", "god", "debt", "spending", "success"]
    democrat_dict = {}
    republican_dict = {}
    democrat_freq = 0
    republican_freq = 0

    for word in democrats_words:
        democrat_dict[word]=0
    for word in republicans_words:
        republican_dict[word]=0
    for text in texts:
        democrat_dict = countFrequency(str(text).split(" "), democrat_dict)
        republican_dict = countFrequency(str(text).split(" "), republican_dict)
    for word in democrat_dict:
        democrat_freq+=democrat_dict[word]
    for word in republican_dict:
        republican_freq+=republican_dict[word]
    
    if(democrat_freq>republican_freq):
        return "democrat"
    else:
        if(democrat_freq<republican_freq):
            return "republican"
   
        else:
            return "neutral"
    
def religion_analysis(texts):
    islam_words = ["allah", "fatwa", "hadj", "hajj","hijjah", "islam", "mecca", "muhammad", "mosque", "muslim", 
        "prophet", "ramadan", "salam", "salaam", "sharia", "suhoor", "sunna", "sunnah", "sunni", "koran", "coran", 
        "qur'an", "hijab", "halal", "hadith", "imam", "madrassah", "salat", "sawm", "shahada", "sura", "tafsir",
        "zakat", "kaaba", "eid al fitr","khutbah", "eid al adha", "p.b.u.h", "sheikh"]
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

    islam_dict = {}
    catholic_dict = {}
    jewish_dict = {}
    budism_dict = {}

    results={}
    results["catholic"]=0
    results["islam"]=0
    results["jewish"]=0
    results["budism"]=0

    for word in islam_words:
        islam_dict[word]=0
    for word in catholic_words:
        catholic_dict[word]=0
    for word in jewish_words:
        jewish_dict[word]=0
    for word in budism_words:
        budism_dict[word]=0
    
        
    for text in texts:
        islam_dict = countFrequency(str(text).split(' '), islam_dict)
        catholic_dict = countFrequency(str(text).split(' '), catholic_dict)
        jewish_dict = countFrequency(str(text).split(' '), jewish_dict)
        budism_dict = countFrequency(str(text).split(' '), budism_dict)
    for word in islam_dict:
        results["islam"]+=islam_dict[word]
    for word in catholic_dict:
        results["catholic"]+=catholic_dict[word]
    for word in jewish_dict:
        results["jewish"]+=jewish_dict[word]
    for word in budism_dict:
        results["budism"]+=budism_dict[word]

    max_value=max(results.items(), key=operator.itemgetter(1))[0]
    if (results.get(max_value) > 0):
        return max_value
    else:
        return "neutral"

@app.route('/do_security_analysis')
def do_security_analysis():
    registred_users = {}
    posts = []
    twitter_posts = []
    facebook_posts = []
    score = 0
    twitter_profile = list
    facebook_profile = list
    #avatar = request.args.get('avatar')
    avatar="usi"

    if(avatar in registred_users.keys()):
        path = registred_users.get(avatar)
    else:
        path = registred_users[avatar] = str(uuid.uuid4())
    
    twitter_username = request.args.get('tname')
    facebook_token = request.args.get('fname')
    if twitter_username is not "":
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
    fexec.map(total_scoring, obj_id)
    return str(fexec.get_result())

if __name__ == '__main__':
  app.run(debug=True) 