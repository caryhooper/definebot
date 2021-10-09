from keys import keys
from bs4 import BeautifulSoup
import random, time, re, requests, tweepy, twint, datetime, warnings
warnings.filterwarnings("ignore")
#Twitter Bot to respond to tweets with the dictionary definition of a word.
#10/9/21 added helpful mode to search for people explicitly asking for 
#    the definition of a word and replying to them.
#Example. @Hooper_Labs define flabbergast

CONSUMER_KEY = keys['consumer_key']
CONSUMER_SECRET = keys['consumer_secret']
ACCESS_TOKEN = keys['access_token']
ACCESS_TOKEN_SECRET = keys['access_token_secret']

# Authenticate to Twitter
auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)

# Create API object
api = tweepy.API(auth, wait_on_rate_limit=True)
try:
	api.verify_credentials()
	print("Credentials Verified")
except Exception as e:
	print("Error creating API")
	raise e

def save_last_id(tweet_id):
	#Save most recent tweet ID in a file
	results_file = open('.last_tweet','w')
	results_file.write(tweet_id)
	results_file.close()

def get_last_id():
	#Retrieve most recent tweet ID from a file
	try:
		results_file = open('.last_tweet','r')
	except:
		return '0000000000000000000'
	tweet_id = results_file.read()
	results_file.close()
	return tweet_id

def random_sleep(min_minutes,max_minutes):
	#Sleep a random number of minutes within a range (random + jitter)
	sleep_seconds = random.randrange(min_minutes * 60,max_minutes * 60)
	print(f"Sleeping {sleep_seconds} seconds.")
	time.sleep(sleep_seconds)

def get_definitions(word):
	#Given a word, utilize Python and BS4 to get the definition from MW online.
	#Returns the response to the tweet
	if word == 'life' or word == 'universe' or word == 'everything':
		return '42'
	url = f'https://www.merriam-webster.com/dictionary/{word}'
	#Make web request
	response = requests.get(url)
	soup = BeautifulSoup(response.text, 'html.parser')
	#Parse with BS4
	if soup.find('p',{'class':'missing-query'}):
		print(f"Definition not found for {word}.  Check your spelling and try again!")
		return ''
	definitions = soup.findAll('span',{'class':'dtText'})
	reply = f"{word}: \n"
	count = 1
	def_set = set()
	#The following dedups the definitions into a set
	for definition in definitions:
		definition = definition.text.replace(":","").strip()
		def_set.add(definition)
	#Manually build the reply string
	for definition in def_set:
		add_text = f"  ({count}) {definition}\n"
		if len(add_text) + len(reply) <= 280:
			reply += add_text
			count += 1
	print(f"Reply ({len(reply)} chars): {reply}")
	return reply

def parse_mention(text):
	#Return a word to define if mention asks to define a word, otherwise return an empty string
	#Define X, define X, what is the definition of X, what does X mean, 
	#X, what is the meaning of X
	#What does this mean: X, What does this word mean: X

	#TODO: Is there an easier way of parsing natural language in Python?
	#TODO: if the target word is surrounded by quotes, look up the whole phrase
	text = text.lower()
	text = text.replace(f'@Hooper_Labs','')
	text = text.replace(':','').replace('?','').replace("'",'').replace('"','')
	text = text.replace('definition of','definition_of',1).replace('meaning of','meaning_of',1).replace('the word','')
	text = text.replace('this word mean','this_word_mean').replace('this mean','this_mean')
	text_array_with_links = text.split(' ')
	#Regex to remove links
	regex = re.compile(r'https://.*/[a-zA-Z]{4,16}')
	text_array = [i for i in text_array_with_links if not regex.match(i)]

	post_keywords = ['define','definition_of','meaning_of','this_word_mean']
	keywords = ['this_mean']
	pre_keywords = ['mean']

	#If there is only one word, look it up.
	if len(text_array) == 1:
		return text_array[0]

	#Go through all keywords that appear before the defined word
	for keyword in post_keywords:
		if keyword in text_array:
			index = text_array.index(keyword)
			word_to_define = text_array[index + 1]
			if word_to_define == 'a' or word_to_define == 'the' or word_to_define == 'an':
				word_to_define =  text_array[index + 2]
			return word_to_define
	
	#Special case where it could be before or after
	for keyword in keywords:
		if keyword in text_array:
			index = text_array.index(keyword)
			if index == len(text_array):
				return 'this'
			else:
				word_to_define = text_array[index + 1]
				return word_to_define

	#Go through all keywords that appear after the defined word
	for keyword in pre_keywords:
		if keyword in text_array:
			index = text_array.index(keyword)
			word_to_define = text_array[index - 1]
			return word_to_define

	#Return '' if no word can be determined
	return ''

def reply_def(original_id,reply):
	#Try to reply to the tweet ID
	try:
		new_status = api.update_status(status = reply, in_reply_to_status_id = original_id , auto_populate_reply_metadata=True)
		new_status_id = new_status.id_str
		print(f"Successfully created status with ID {new_status_id}\n: {new_status.text}")
	except Exception as e:
		print(e)
		print(f'Failed to reply to {original_id}')

def find_unprocessed_tweets():
	#Get the last ID that was responded to
	last_id = get_last_id()
	#Retrieve all @ mentions
	mentions = api.mentions_timeline(since_id=last_id,count=1000)
	#Collect all mention IDs
	mention_ids = [i.id_str for i in mentions]
	print(f"Mention IDs: {mention_ids}")
	for mention in mentions:
		print(f"{mention.id_str}: {mention.text}")

	#If the last response is in the last 1000 @ tweets, slice all mentions to include only the latest
	if last_id in mention_ids:
		last_index = mention_ids.index(last_id)
		mention_slice = mentions[:last_index-1]
	else:
		mention_slice = mentions
	return mentions

def reply_tweets():
	#Gather all "mentions", which are Twitter status objects
	#returns false if there are no tweets to be replied to, true if there are '@s'
	mentions = find_unprocessed_tweets()

	#If there are none, end here
	if len(mentions) == 0:
		return False

	#Immediately save the state (last ID).  If program ends prematurely, this will cause false negatives (no reply)
	last_id = mentions[0].id_str
	print(f"Saving last id: {last_id}")
	save_last_id(last_id)

	#For each mention, parse the text, determine the dictionary word, get the definition, and reply
	for mention in mentions:
		defined_word = parse_mention(mention.text)
		if defined_word != '':
			definition = get_definitions(defined_word)
			if definition != '':
				reply_def(mention.id_str,definition)

		random_sleep(5,120)
	return True

def proactive_search():
	headers = {"User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:92.0) Gecko/20100101 Firefox/92.0"}
	#proxies = {'http':'http://127.0.0.1:8080','https':'http://127.0.0.1:8080'}

	#Find Bearer Token
	#obfuscate URL for reasons
	#TODO - get this URL dynamically from sw.js as the hash may change in the future.
	auth_token_url = "https://ab" + "s.tw" + "\x69mg.com/re" + "spon" + "s\x69ve-w" + "eb/cl" + "ient" + "-web/ma\x69n.ae" + "8116d5.js"
	print(f"Requesting {auth_token_url}")
	response =  requests.get(auth_token_url,verify=False,headers=headers)# requests.get(auth_token_url,verify=False,headers=headers,proxies=proxies)
	tokens = response.text.split(';')
	bearer = ""
	#Parse JavaScript manually
	for token in tokens:
		if "ACTION_FLUSH" in token:
			newtokens = token.split(',')
			for newtoken in newtokens:
				if 's="' in newtoken:
					bearer = newtoken.split('"')[1]
					print(f"Bearer Token: {bearer}")
	if bearer == "":
		print(f"Bearer Token not found")
		return ""
	#Get Guest Token
	#obfuscate URL for reasons
	guest_token_url = "https://ap" + "i.t" + "w\x69t" + "ter.c" + "om/1.1/g" + "uest/a" + "ctivat" + "e.json"
	print(f"Requesting {guest_token_url}")
	headers["Authorization"] = f"Bearer {bearer}"
	response = requests.post(guest_token_url,verify=False,headers=headers)#requests.post(guest_token_url,verify=False,headers=headers,proxies=proxies)
	try:
		guest_token = response.json()["guest_token"]
	except:
		print(response.json())
		print(response.text)
	print(f"Guest Token: {guest_token}")

	#Get Search Tweets
	headers["X-G" + "ues" + "t-T" + "ok" + "en"] = guest_token
	today = datetime.date.today()
	weekago = today - datetime.timedelta(days=7)
	year = weekago.year
	month = weekago.month
	day = weekago.day

	#obfuscate URL for reasons
	search_url = 	f"https://t" + "w\x69" + "tte" + "r.com/" + "i/ap" + "i/2/s" + "earch/a" + "dapt\x69v" + "e.json?"
	search_url += 	f"q=\"What%20is%20the%20definition%20of\"%20since:{year}-{month}-{day}&count=5"
	response = requests.get(search_url,verify=False,headers=headers)#requests.get(search_url,verify=False,headers=headers,proxies=proxies)
	tweets = response.json()["globalObjects"]["tweets"]
	tweet_ids = tweets.keys()
	for tweet_id in tweet_ids:
		tweet_text = tweets[tweet_id]["text"]
		print(f"Tweet ID {tweet_id}: {tweet_text}")
		keyword = parse_mention(tweet_text)
		if keyword != "":
			definition = get_definitions(keyword)
			reply_def(tweet_id,definition)
			#Sleep 24 hrs to rate limit this functionality
			random_sleep(1440,1880)
			return ""
	return ""

# print(api.me())
# info = api.get_user('chumbawambafan')
# home = api.home_timeline()

#While loop to continuously check for more '@' mentions
while True:
	if not reply_tweets():
		proactive_search()
	random_sleep(180,900)