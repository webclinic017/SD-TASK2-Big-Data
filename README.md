# SocialAuth


## About
This distributed application is designed to analayze the social media security of our users. They can analyze which is the personal information that they make public in their social media accounts. Specifically, they can analyze their Facebook and Twitter accounts. The objective is raise awareness among users that they can put a lot of personal information public, and this can be a risk because the hackers can use social engineering to condition their ideologies or decisions. Even thieves can take advantage of this information to find out where you live and rob your home if you are on holidays.

This software implements serverless architecture and use IBM Cloud Functions to execute this app. Also, we used Lithops API to execute IBM Cloud Functions and store user's data in IBM Object Storage. Therefore, we use an object-oriented storage architecture.
## Installation


The prerequisites for this project are listed below:

* PIP (Python Package Manager)
* Flask
* Lithops
* Facebook-sdk
* Tweepy
* A facebook account





## Installation

Use the package manager to install the packages.

```bash
pip install flask lithops tweepy facebook-sdk
```

## Usage

Start the webserver using:

```bash
python internet_security_crawling.py
```

Once the webserver has started, you have access to the frontend.

You will be greeted with this screen: 

![alt text](https://i.imgur.com/L0yq7Qx.png)

Here is where it gets tricky:

Here you will need to insert a twitter username (For example, USA President's username for twitter is POTUS ) without the @ sign.

And also you will need to insert a facebook token, which only can be your facebook token, this is because Facebook doesn't let you scrap profiles without their consent.


For Logging in with facebook:




Go to the [facebook graph explorer](https://developers.facebook.com/tools/explorer/) and generate a new token. Then log in with this account:

```bash
Name	
Jayden Alfihdhcgeajg Shepardson
User ID	100069848375107
Login email	hwerbzi_shepardson_1624193783@tfbnw.net
Login password	yhynscexiip
```


![alt text](https://i.imgur.com/xJ1Dat5.png)

Insert the facebook token into the Facebook Token input.



Then you are ready to submit.

Once you submit, you will get the resoults in this format:

![alt text](https://i.imgur.com/rU2gzFk.png)



## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License
[MIT](https://choosealicense.com/licenses/mit/)
