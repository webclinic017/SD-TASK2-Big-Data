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
from nltk.corpus import stopwords
import gensim
from gensim.utils import simple_preprocess

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
    posts = do_predictions(posts)
    id = storage.put_cloudobject(write_csv_body([tprofile,fprofile,posts]), BUCKET_NAME, path+".csv")
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
    return str.encode(output.getvalue())

def write_csv_posts(texts):
    output = io.StringIO()
    w = csv.writer(output)
    i=0
    for row in texts:
        w.writerow(row)
    return output.getvalue()

#STATISTICS
def remove_hashtags(post, pattern1, pattern2):
    r = re.findall(pattern1, post)
    for i in r:
        tweet = re.sub(i, '', tweet)
    r = re.findall(pattern2, tweet)
    for i in r:
        tweet = re.sub(i, '', tweet)
    return tweet

def remove_links(post):
    tweet_no_link = re.sub(r"http\S+", "", post)
    return tweet_no_link

def remove_users(post, pattern1, pattern2):
    r = re.findall(pattern1, post)
    for i in r:
        post = re.sub(i, '', post)
    r = re.findall(pattern2, post)
    for i in r:
        post = re.sub(i, '', post)
    return post

def remove_stopwords(tweets):
    return [[word for word in simple_preprocess(str(tweet)) if word    not in stopwords] for tweet in tweets]

def tokenize(tweet):
    for word in tweet:
        yield(gensim.utils.simple_preprocess(str(word), deacc=True)) 

def clean_posts(df):
    df.drop_duplicates(subset=['posts_text'], keep='first', inplace=True)
    df['tidy_post'] = np.vectorize(remove_users)(df['posts_text'],     "@ [\w]*", "@[\w]*")
    df['tidy_post'] = df['tidy_post'].str.lower()
    df['tidy_post'] = np.vectorize(remove_hashtags)(df['tidy_post'], "# [\w]*", "#[\w]*")
    df['tidy_post'] = np.vectorize(remove_links)(df['tidy_post'])
    df['tidy_post'] = df['tidy_post'].str.replace("[^a-zA-Z#]", " ")
    df['tidy_no_stop'] = remove_stopwords(df['tidy_post'])
    return df

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
    posts = storage.get_cloudobject(obj_id).decode()
    posts=posts.split('\",\"')
    posts=write_csv_posts(posts)
    storage.put_cloudobject(str.encode(posts),BUCKET_NAME, "dades.csv")

    df = pd.read_csv(posts, index_col=[0], error_bad_lines=False)
    df.columns = ["posts_text"]
    df.head()

    show_basic_statistics(df)
    new_df = clean_posts(df)
    political_pred = political_analysis(new_df['tidy_no_stop'])
    religion_pred = religion_analysis(new_df['tidy_no_stop'])
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

def countFrequency(my_list, freq):
 
    # Creating an empty dictionary
    for item in my_list:
        if (item in freq):
            freq[item] += 1
        else:
            freq[item] = 1
 
 
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
        countFrequency(text.split(' '), democrat_dict)
        countFrequency(text.split(' '), republican_dict)
    for word in democrat_dict.keys():
        democrat_freq+=democrat_dict[word]
    for word in republican_dict.keys():
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
        countFrequency(text.split(' '), islam_dict)
        countFrequency(text.split(' '), catholic_dict)
        countFrequency(text.split(' '), jewish_dict)
        countFrequency(text.split(' '), budism_dict)

    for word in islam_dict.keys():
        results["islam"]+=islam_dict[word]
    for word in catholic_dict.keys():
        results["catholic"]+=catholic_dict[word]
    for word in jewish_dict.keys():
        results["jewish"]+=jewish_dict[word]
    for word in budism_dict.keys():
        results["budism"]+=budism_dict[word]

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
    fexec.map(total_scoring, obj_id)
    return str(score)

if __name__ == '__main__':
  app.run(debug=True)  