from keys import keys
from bs4 import BeautifulSoup
import random, time, re, requests, tweepy
#Twitter Bot to respond to tweets with the dictionary definition of a word.
#Example. @Hooper_Labs define flabbergast

CONSUMER_KEY = keys['consumer_key']
CONSUMER_SECRET = keys['consumer_secret']
ACCESS_TOKEN = keys['access_token']
ACCESS_TOKEN_SECRET = keys['access_token_secret']

# Authenticate to Twitter
auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)

# Create API object
api = tweepy.API(auth, wait_on_rate_limit=True,wait_on_rate_limit_notify=True)
try:
	api.verify_credentials()
	print("Credentials Verified")
except Exception as e:
	print("Error creating API")
	raise e
my_handle = api.me().screen_name

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
		return f"Definition not found for {word}.  Check your spelling and try again!"
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

def parse_mention(text):
	#Return a word to define if mention asks to define a word
	#Define X, define X, what is the definition of X, what does X mean, 
	#X, what is the meaning of X
	#What does this mean: X, What does this word mean: X

	#TODO: Is there an easier way of parsing natural language in Python?
	text = text.lower()
	text = text.replace(f'@{my_handle}','')
	text = text.replace(':','').replace('?','')
	text = text.replace('definition of','definition_of',1).replace('meaning of','meaning_of',1)
	text = text.replace('this word mean','this_word_mean').replace('this mean','this_mean')
	text_array_with_links = text.split(' ')
	#Regex to remove links
	regex = re.compile(r'https://.*/[a-zA-Z]{4,16}')
	text_array = [i for i in text_array_with_links if not regex.match(i)]

	post_keywords = ['define','definition_of','meaning_of','this_word_mean']
	keywords = ['this_mean']
	pre_keywords = ['mean']
	for keyword in post_keywords:
		if keyword in text_array:
			index = text_array.index(keyword)
			word_to_define = text_array[index + 1]
			return word_to_define
	
	for keyword in keywords:
		if keyword in text_array:
			index = text_array.index(keyword)
			if index == len(text_array):
				return 'this'
			else:
				word_to_define = text_array[index + 1]
				return word_to_define

	for keyword in pre_keywords:
		if keyword in text_array:
			index = text_array.index(keyword)
			word_to_define = text_array[index - 1]
			return word_to_define

	#Return '' if this cannot be determined
	return ''


def reply_def(original_id,reply):
	try:
		new_status = api.update_status(status = reply, in_reply_to_status_id = original_id , auto_populate_reply_metadata=True)
		new_status_id = new_status.id_str
		print(f"Successfully created status with ID {new_status_id}\n: {new_status.text}")
	except Exception as e:
		print(e)
		print(f'Failed to reply to {original_id}')


def find_unprocessed_tweets():
	last_id = get_last_id()
	mentions = api.mentions_timeline(since_id=last_id,count=1000)
	mention_ids = [i.id_str for i in mentions]
	print(f"Mention IDs: {mention_ids}")
	for mention in mentions:
		print(f"{mention.id_str}: {mention.text}")

	if last_id in mention_ids:
		last_index = mention_ids.index(last_id)
		mention_slice = mentions[:last_index-1]
	else:
		mention_slice = mentions
	return mentions

def reply_tweets():
	mentions = find_unprocessed_tweets()

	if len(mentions) == 0:
		return True
	last_id = mentions[0].id_str
	print(f"Saving last id: {last_id}")
	save_last_id(last_id)

	for mention in mentions:
		defined_word = parse_mention(mention.text)
		if defined_word != '':
			definition = get_definitions(defined_word)
			reply_def(mention.id_str,definition)

		random_sleep(0,1)

# print(api.me())
# info = api.get_user('chumbawambafan')
# home = api.home_timeline()

while True:
	reply_tweets()
	random_sleep(180,900)