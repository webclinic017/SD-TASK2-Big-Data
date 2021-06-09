import tweepy
import lithops
import urllib3
import facebook
import csv

twitter_consumer_key = "HULJLDcth2DlyCeQetSVImh0S"
twitter_consumer_secret = "UVPSLbfTudhGa4j1MlsmDA6KxXJUeY7mqGQkprdsHJD1rFcJH6"
twitter_access_token = "1313145032-gdwPOWniKGX9jbOwlUs1fqqJuDfLzue17FdNDUD"
twitter_access_token_secret = "s5YDPEylUR9hWuuNIXNIRmgTXoVkBKFwavxke2u8O49pi"
facebook_token= "EAACTYqyk4wIBAIhxzIDEUiX8OZC1ffRaZCrn746Jvr0hdYOoAwwfOcZAltKy1WKJMS61fRLC00xagyykwcU8ttVYyUTsk9fZBgIq7NrECwAKaidtVK3Uk1vkU0HjfZCfkTSNAnnjlljWxPQTFi11gz9ZA0qTwYYGXIjZA8QVqAjDqOwhZAkm8jpISxXBD0BYSPGC9VT9ZCtASeuXX2pzvNRuz"
userID = "usama12_usama"
header = ['user_name', 'name', 'account_created_at', 'location', 'URL', 'sentiment_analysis', 'protected', 'geo_enabled ', 'description', 'post_id', 'post_created_at', 'post_text']

auth = tweepy.OAuthHandler(twitter_consumer_key, twitter_consumer_secret)
auth.set_access_token(twitter_access_token, twitter_access_token_secret)
api = tweepy.API(auth) 

graph = facebook.GraphAPI (access_token = facebook_token, version = 8.0) 

f = open('csv_file', 'w+')
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
    retweets = api.retweets()
    row=[info.user.screen_name, info.user.name, info.user.created_at, info.user.location, 'https://twitter.com/'+info.user.screen_name, ' ', info.user.protected, info.user.geo_enabled, info.user.description, info.id, info.created_at, info.full_text]
    writer.writerow(row)

f.close