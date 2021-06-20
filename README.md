# SocialAuth


## About
The focus of this project is to predict two topics from a Facebook/Twitter profile; religion and political opinion.

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

For the facebook token, we have the blue Log In button. 


For Logging in with facebook:

Creating a new facebook app and adding your appId to our facebook index.html
Or going to the [facebook graph explorer](https://developers.facebook.com/tools/explorer/) and generate a new token.



```python
import foobar

foobar.pluralize('word') # returns 'words'
foobar.pluralize('goose') # returns 'geese'
foobar.singularize('phenomena') # returns 'phenomenon'
```

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License
[MIT](https://choosealicense.com/licenses/mit/)
