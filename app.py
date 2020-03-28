from flask import Flask, render_template, request, redirect
import urllib.request
from flask import send_file
from flask import g
import tweepy
from tweepy import API 
from tweepy import Cursor
from tweepy.streaming import StreamListener
from tweepy import OAuthHandler
from tweepy import Stream 
import numpy as np
import pandas as pd
from textblob import TextBlob 
import re

ACCESS_TOKEN = "1097318551101132800-621b0FHfBhRgf3YkHiJIRpBjoIxM4G"
ACCESS_TOKEN_SECRET = "YCmdPRveixN7uh5iZ0sWSsT90ym4IifWiagT77KGGaAqL"
CONSUMER_KEY = "XvH06SXnp1jYeubyt3Z7hvpb4"
CONSUMER_SECRET = "d9XFuysqX4Ab4Dr2y5bYN0e9nqbSypfM2AxRTdWTFeW2PdkhGn"

app=Flask(__name__)

class TwitterClient():
    def __init__(self, twitter_user=None):
        self.auth = TwitterAuthenticator().authenticate_twitter_app()
        self.twitter_client = API(self.auth)

        self.twitter_user = twitter_user

    def get_twitter_client_api(self):
        return self.twitter_client

    def get_user_timeline_tweets(self, num_tweets):
        tweets = []
        for tweet in Cursor(self.twitter_client.user_timeline, id=self.twitter_user).items(num_tweets):
            tweets.append(tweet)
        return tweets

    def get_friend_list(self, num_friends):
        friend_list = []
        for friend in Cursor(self.twitter_client.friends, id=self.twitter_user).items(num_friends):
            friend_list.append(friend)
        return friend_list

    def get_home_timeline_tweets(self, num_tweets):
        home_timeline_tweets = []
        for tweet in Cursor(self.twitter_client.home_timeline, id=self.twitter_user).items(num_tweets):
            home_timeline_tweets.append(tweet)
        return home_timeline_tweets


# # # # TWITTER AUTHENTICATER # # # #
class TwitterAuthenticator():

    def authenticate_twitter_app(self):
        auth = OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
        auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
        return auth

# # # # TWITTER STREAMER # # # #
class TwitterStreamer():
    """
    Class for streaming and processing live tweets.
    """
    def __init__(self):
        self.twitter_autenticator = TwitterAuthenticator()    

    def stream_tweets(self, fetched_tweets_filename, hash_tag_list):
        # This handles Twitter authetification and the connection to Twitter Streaming API
        listener = TwitterListener(fetched_tweets_filename)
        auth = self.twitter_autenticator.authenticate_twitter_app() 
        stream = Stream(auth, listener)

        # This line filter Twitter Streams to capture data by the keywords: 
        stream.filter(track=hash_tag_list)


# # # # TWITTER STREAM LISTENER # # # #
class TwitterListener(StreamListener):
    """
    This is a basic listener that just prints received tweets to stdout.
    """
    def __init__(self, fetched_tweets_filename):
        self.fetched_tweets_filename = fetched_tweets_filename

    def on_data(self, data):
        try:
            print(data)
            with open(self.fetched_tweets_filename, 'a') as tf:
                tf.write(data)
            return True
        except BaseException as e:
            print("Error on_data %s" % str(e))
        return True
          
    def on_error(self, status):
        if status == 420:
            # Returning False on_data method in case rate limit occurs.
            return False
        print(status)


class TweetAnalyzer():
    """
    Functionality for analyzing and categorizing content from tweets.
    """

    def clean_tweet(self, tweet):
        return ' '.join(re.sub("(@[A-Za-z0-9]+)|([^0-9A-Za-z \t])|(\w+:\/\/\S+)", " ", tweet).split())

    def analyze_sentiment(self, tweet):
        analysis = TextBlob(self.clean_tweet(tweet))
        
        if analysis.sentiment.polarity > 0:
            return 1
        elif analysis.sentiment.polarity == 0:
            return 0
        else:
            return -1

    def tweets_to_data_frame(self, tweets):
        df = pd.DataFrame(data=[tweet.text for tweet in tweets], columns=['Tweets'])

        df['id'] = np.array([tweet.id for tweet in tweets])
        df['len'] = np.array([len(tweet.text) for tweet in tweets])
        df['date'] = np.array([tweet.created_at for tweet in tweets])
        df['source'] = np.array([tweet.source for tweet in tweets])
        df['likes'] = np.array([tweet.favorite_count for tweet in tweets])
        df['retweets'] = np.array([tweet.retweet_count for tweet in tweets])

        return df


@app.route("/")
def home() : 
	return render_template("index.html")

@app.route("/about")
def about() : 
	return render_template("about.html")

@app.route("/stats", methods=['GET','POST'])
def stats() : 
	if request.method == "POST":
		twitterHandle=request.form['twitterHandle']
		tweetCount=request.form['count']
		# message=twitterHandle+' '+tweetCount
		tweetCount=int(tweetCount)
		twitter_client=TwitterClient()
		tweet_analyzer=TweetAnalyzer()
		api=twitter_client.get_twitter_client_api()
		tweets=api.user_timeline(screen_name=twitterHandle,count=100)
		df=tweet_analyzer.tweets_to_data_frame(tweets)
		message=df.head(tweetCount)
		print(df.head(tweetCount))
		return render_template("showStats.html",confirm=message,handle=twitterHandle)
	return render_template("stats.html")

@app.route("/sentiment", methods=['GET','POST'])
def senti() : 
    if request.method=="POST":
        twitterHandle=request.form['twitterHandle']
        tweetCount=request.form['count']
        tweetCount=int(tweetCount)
        twitter_client = TwitterClient()
        tweet_analyzer = TweetAnalyzer()
        api = twitter_client.get_twitter_client_api()
        tweets = api.user_timeline(screen_name=twitterHandle, count=100)
        # print(tweets)
        df = tweet_analyzer.tweets_to_data_frame(tweets)
        df['sentiment'] = np.array([tweet_analyzer.analyze_sentiment(tweet) for tweet in df['Tweets']])
        print(df)
        message=df.head(tweetCount)
        return render_template("showSentiment.html",confirm=message,handle=twitterHandle)
    return render_template("senti.html")

@app.route("/covid19")
def covid19() : 
	return render_template("covid19Options.html")

@app.route("/covid19India")
def covid19India() :
    maxTweets=50
    auth = OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    api=tweepy.API(auth)
    df = pd.DataFrame(data=[tweet.text for tweet in tweepy.Cursor(api.search,q="#covid19",rpp=100).items(maxTweets)], columns=['text'])
    df['date'] = np.array([tweet.created_at for tweet in tweepy.Cursor(api.search,q="#covid19",rpp=100).items(maxTweets)])
    df['likes'] = np.array([tweet.favorite_count for tweet in tweepy.Cursor(api.search,q="#covid19",rpp=100).items(maxTweets)])
    df['retweets'] = np.array([tweet.retweet_count for tweet in tweepy.Cursor(api.search,q="#covid19",rpp=100).items(maxTweets)])
    df['retweets'] = np.array([tweet.retweet_count for tweet in tweepy.Cursor(api.search,q="#covid19",rpp=100).items(maxTweets)])
    df['url'] = np.array([tweet.source_url for tweet in tweepy.Cursor(api.search,q="#covid19",rpp=100).items(maxTweets)])
    print(df)
    message=df
    return render_template("covid19.html",confirm=message)

@app.route("/covid19World",methods=['GET','POST'])
def covid19World() : 
    maxTweets=50
    auth = OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    api=tweepy.API(auth)
    df = pd.DataFrame(data=[tweet.text for tweet in tweepy.Cursor(api.search,q="#covid19",rpp=100).items(maxTweets)],columns=['text'])
    df['date'] = np.array([tweet.created_at for tweet in tweepy.Cursor(api.search,q="#covid19",rpp=100).items(maxTweets)])
    df['likes'] = np.array([tweet.favorite_count for tweet in tweepy.Cursor(api.search,q="#covid19",rpp=100).items(maxTweets)])
    df['retweets'] = np.array([tweet.retweet_count for tweet in tweepy.Cursor(api.search,q="#covid19",rpp=100).items(maxTweets)])
    df['retweets'] = np.array([tweet.retweet_count for tweet in tweepy.Cursor(api.search,q="#covid19",rpp=100).items(maxTweets)])
    df['url'] = np.array([tweet.source_url for tweet in tweepy.Cursor(api.search,q="#covid19",rpp=100).items(maxTweets)])
    print(df)
    message=df
    return render_template("covid19.html",confirm=message)

if __name__ == "__main__":
	app.run(debug=True)