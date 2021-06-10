import tweepy
import lithops
import urllib3
import csv
import os
import sys

twitter_consumer_key = "HULJLDcth2DlyCeQetSVImh0S"
twitter_consumer_secret = "UVPSLbfTudhGa4j1MlsmDA6KxXJUeY7mqGQkprdsHJD1rFcJH6"
twitter_access_token = "1313145032-gdwPOWniKGX9jbOwlUs1fqqJuDfLzue17FdNDUD"
twitter_access_token_secret = "s5YDPEylUR9hWuuNIXNIRmgTXoVkBKFwavxke2u8O49pi"
userID = "usama12_usama"
header = ['user_name', 'name', 'account_created_at', 'location', 'URL', 'sentiment_analysis', 'protected', 'geo_enabled ', 'description', 'post_id', 'post_created_at', 'post_text']

auth = tweepy.OAuthHandler(twitter_consumer_key, twitter_consumer_secret)
auth.set_access_token(twitter_access_token, twitter_access_token_secret)
api = tweepy.API(auth) 
user=api.get_user(userID)

if not os.path.exists(str(user.id)):
    os.makedirs(str(user.id))
f = open(str(user.id)+'/twitter.txt', 'a')
writer = csv.writer(f)
writer.writerow(header)

tweets = api.user_timeline(screen_name=userID, 
                           # 200 is the maximum allowed count
                           count=200,
                           include_rts = False,
                           # Necessary to keep full_text 
                           # otherwise only the first 140 words are extracted
                           tweet_mode = 'extended'
                           )

for info in tweets:
    status = api.get_status(info.id)
    row=[info.user.screen_name, info.user.name, info.user.created_at, info.user.location, 'https://twitter.com/'+info.user.screen_name, ' ', info.user.protected, info.user.geo_enabled, info.user.description, info.id, info.created_at, info.full_text]
    writer.writerow(row)
for favorite in tweepy.Cursor(api.favorites, id=userID).items(20):
    row=[info.user.screen_name, info.user.name, info.user.created_at, info.user.location, 'https://twitter.com/'+info.user.screen_name, ' ', info.user.protected, info.user.geo_enabled, info.user.description, favorite.id, favorite.created_at, favorite.text]
    writer.writerow(row)

f.close

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
    else:
        return "republican"