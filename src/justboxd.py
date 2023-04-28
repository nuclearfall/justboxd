import os
import urllib.request
import ssl
import json
from json2html import *
from bs4 import BeautifulSoup
from justwatch import JustWatch
from collections import namedtuple
from pprint import pprint
from imdb import Cinemagoer
from imdb import Movie
import time

def isEmpty(value) -> bool:
	return True if len(value) == 0 or value in [None, '', {}, []] else False

def stringFromIndex(line: str, substr: str, end='"') -> str:
	if substr in line:
		start = line.index(substr) + len(substr)
		stop = line.index(end, start)
		return line[start: stop]
def check(key, val, alist, target=False):
	if target is False:
		return list(filter(lambda x: x[key] == val, alist))
	if target is True:
		return list(filter(lambda x: x[key] in val, alist))

JustboxdMovie 		= namedtuple('JustboxdMovie', 		
						['title', 'year', 'providers', 'cover', 'url'])
JustboxdDisplay		= namedtuple('NewJustboxdMovie', ['cover', 'title', 'year', 'providers'])
JustboxdList 		= namedtuple('JustboxdList', 		
						['listname', 'username', 'movie_urls', 'url'])
JustboxdProvider 	= namedtuple('JustboxdProvider',
						['short', 'clear', 'subscription', 'adsupported', 'free', 'purchase', 'rental'])
JustboxdRate 		= namedtuple('JustboxdProvider',
						['subscription', 'adsupported', 'free', 'purchase', 'rental'])


def loadProviders(path:str) -> list:
	if os.path.exists(path):
		with open(path) as fp:
			providers = json.load(fp)
			fp.close()
			return [JustboxdProvider (	short=p['short'],
										clear=p['clear'],
										subscription=p['subscription'],
										adsupported=p['adsupported'],
										free=p['free'],
										purchase=p['purchase'],
										rental=p['rental']) for p in providers]
	else:
		return []
def loadMovies(path:str) -> list:
	if os.path.exists(path):
		with open(path) as fp:
			movies = json.load(fp)
			fp.close()
			return [JustboxdMovie (	title=m['title'],
									year=m['year'],
									providers=m['providers'],
									cover=m['cover'],
									url=m['url']) for m in movies]
	else:
		return []
def loadLists(path:str) -> list:
	if os.path.exists(path):
		with open(path) as fp:
			lists = json.load(fp)
			fp.close()
			return [JustboxdList(	listname=ls['listname'],
									username=ls['username'],
									url=ls['url'],
									movie_urls=ls['movie_urls']) for ls in lists]
	else:
		return []
def saveJson(data, path):
	with open(path, 'w') as fp:
		json_data = json.dumps([ld._asdict() for ld in data], indent=4)
		fp.write(json_data)
		fp.close()
	return True
def saveHtml(data, path):
	with open(path, 'w') as fp:
		fp.write(data)
		fp.close()

class Justboxd():
	def __init__(self):

		self.services 		= loadProviders('../data/services.json')
		self.providers 		= loadProviders('../data/providers.json')
		self.movies 		= loadMovies('../data/movies.json')
		self.lists 			= loadLists('../data/lists.json')
		self.free_services 	= list(filter(lambda x: x.free == True or x.adsupported == True, self.services))
		self.subscriptions  = list(filter(lambda x: x.subscription == True, self.services))
		self.country_code   = 'US'

	def scrapeMovie(self, url):
			tags 			= list(map(lambda x: str(x).replace('&amp;','&'), self.makeMovieSoup(url, 'meta')))
			#gets, title, year, and director for verification of movie if necessary
			content 		= list(filter(lambda x: 'content="' in x, tags))
			title_year 		= list(filter(lambda x: 'og:title' in x, content))
			title_year 		= stringFromIndex(title_year[0], 'content="', end='"')
			title 			= title_year[0:-7]
			year 			= title_year[len(title_year)-5:len(title_year)-1]
			if year.isnumeric() is False:
				title 		= title_year
				year 		= -1
			movie_tuple 	= (title, year)
			cover 			= self.getCover(movie_tuple)
			providers 		= self.getProviders(movie_tuple)
			movie 			= JustboxdMovie(title=title, 
											year=year, 
											providers=providers,
											cover=cover,
											url=url)
			return movie

	def getCover(self, movie):
		title, year 	= movie
		cover 	 		= ''
		year 			= int(year)
		year_range		= range(year-1, year+2)
		cine 			= Cinemagoer()
		try:
			search 		= cine.search_movie_advanced(title, results=15)
		except:
			try:
				time.sleep(3)
				search 		= cine.search_movie_advanced(title, results=1)
			except:
				return cover
		results 		= [dict(r) for r in search]
		results 		= [r for r in results if 'kind' in r.keys() and 'year' in r.keys()]
		if len(results) > 0:
			exact_title 	= check('title', title, results)
			title_year 		= [r for r in results if 'year' == year]
			exact_year		= check('year', year, results)
			approx_year 	= [r for r in results if year in year_range]

			if len(title_year) == 1:
				cover = title_year[0]['cover url']
			elif len(exact_title) == 1:
				cover = exact_title[0]['cover url']
			elif len(exact_year) == 1:
				cover = exact_year[0]['cover url']
			elif len(approx_year) > 0:
				cover = approx_year[0]['cover url']
			elif len(results) > 0:
				cover = results[0]['cover url']
			else:
				cover = ''
		return cover

	# def updateMovie(self, movie):
	# 		return			= JustboxdMovie(title=movie.title, 
	# 										year=movie.year, 
	# 										providers=self.getProviders(movie.title, movie.year),
	# 										cover=self.getCover(movie.title, movie.year),
	# 										url=url)
	# takes a Movie namedtuple and returns a Movie namedtuple
	def getProviders(self, movie, exclude=['buy', 'rent']):
		title, year 		 	= movie
		just_watch				= JustWatch(country=self.country_code)
		found_movies 			= just_watch.search_for_item(query=title)
		all_user_providers 		= self.providers + self.free_services
		short_keys 				= [s.short for s in all_user_providers]
		if isEmpty(found_movies) or 'items' not in found_movies.keys():
			return []
		found = found_movies['items']
		try:	
			match = [m for m in found if m['title'] == title and m['original_release_year'] == int(year)]
			if isEmpty(match) or isEmpty(match[0]) or 'offers' not in match[0].keys():
				return []
			offers = match[0]['offers']
			offers = [o['package_short_name'] for o in offers]
			offers = [*set(offers)]
			offers = [p.clear for p in all_user_providers for o in offers if o == p.short] 
			return offers
		except:
			return []


	# takes a url and returns a soup
	def makeMovieSoup(self, url:str, tag_name:str) -> object:
		html_str = ''
		ssl._create_default_https_context = ssl._create_unverified_context
		with urllib.request.urlopen(url) as fp:
			return BeautifulSoup(fp.read(), 'html.parser').findAll(tag_name)

	def findMovie(self, url):
		for m in self.movies:
			if m.url == url:
				return self.movies.index(m)
		return None

	def addMovie(self, movie):
		index = self.findMovie(movie.url)
		if not index:
			self.movies.append(movie)
			saveJson(self.movies, '../data/movies.json')
		return None

	def delMovie(self, index):
		try:
			self.movies.pop(index)
			return None 
		except:
			return None

	def getMovie(self, url, update_all=False, add_new=True):
		index = self.findMovie(url)
		if add_new is True and index is None:
			movie = self.scrapeMovie(url)
			self.addMovie(movie)
		if update_all is not True and index is not None:
			movie = self.movies[index]
		else:
			self.delMovie(index)
			movie = self.scrapeMovie(url)
			self.addMovie(movie)
		return movie

	def findList(self, url):
		for ln in self.lists:
			if ln.url == url:
				return self.lists.index(ln)
		return None

	def addList(self, mlist):
		index = self.findList(mlist)
		if not index:
			self.lists.append(mlist)
			saveJson(self.lists, '../data/lists.json')
		return None		

	def delList(self, index):
		try:
			return self.lists.pop(index)
		except:
			return None

	def getList(self, url):
		index = self.findList(url)
		try:
			mlist = self.scrapeList(url)
			self.delList(index)
			self.addList(mlist)
		except:
			mlist = self.lists[index]
		return mlist

	def addNewMovies(self, mlist):
		all_movie_urls = [m.url for m in self.movies]
		self.movies += [self.scrapeMovie(murl) for murl in mlist.movie_urls if murl not in all_movie_urls]

	def quickFetchMovies(self, mlist_url):
		index = self.findList(mlist_url)
		mlist = self.lists[index]
		return [m for m in self.movies if m.url in mlist.movie_urls]

	# def parseLetterboxdUrl(self, url):
	# 	excluder 		= ['https://', ':', '']
	# 	isLetterboxd	= lambda x: 'letterboxd.com' in x.split('/') 
	# 	splitUrl 		= [x for x in split.x('/') if x not in []
	# 	isWatchlist = lambda x: x.startswith("https://") and split.x('/')

	# def parseLetterboxdSlug(self, url):
	# 	kinds 			= ['diary', 'review', 'personal', ]
	def scrapeList(self, url, pages=50):
		split 			= url.split('/')[3:]
		username 		= split[0]
		listname 		= split[1] if split[1] == 'watchlist' else split[2]
		postfix 		= 'page/' if url.endswith('/') else '/page/'
		complete_url 	= url + postfix
		ssl._create_default_https_context = ssl._create_unverified_context
		html_str = ''
		for i in range(pages):
			fp = urllib.request.urlopen(complete_url + str(i+1))
			html_str += fp.read().decode('utf-8')
			fp.close()
		soup = BeautifulSoup(html_str, 'html.parser')
		tags = soup.findAll('li', {'class':'poster-container'})
		tags = map(lambda x: str(x).replace('&amp;','&'), tags)
		tags = filter(lambda x : 'data-film-slug="' in x, tags)
		movie_urls = list(map(lambda x:'https://letterboxd.com' + (stringFromIndex(x, 'data-film-slug="')), tags))
		justboxd_list = JustboxdList(listname=listname, username=username, movie_urls=movie_urls, url=url)
		return justboxd_list 

	def moviesFromList(self, url, update_all=False, add_new=True):
		mlist = self.getList(url)
		mlist_movies = [self.getMovie(url, update_all=update_all, add_new=add_new) for url in mlist.movie_urls]
		return mlist_movies

	def searchMovies(self, **kwargs):

	def displayFields(self, *values):
		return [v for v in values]

	def getYear(self, title):
		just_watch				= JustWatch(country=self.country_code)
		found_movies 			= just_watch.search_for_item(query=title)
		if isEmpty(found_movies) or 'items' not in found_movies.keys():
			return ''
		try:
			found = found_movies['items'][0]
			year = str(found['original_release_year'])
			return year
		except:
			return ''


	def toHtml(self, data, path='../data/results.html'):
		path = os.path.realpath(path)
		display = [JustboxdDisplay(
						cover=m.cover, 
						title=m.title, 
						year=m.year, 
						providers=m.providers) for m in data]
		display = [item._asdict() for item in display]

		unavailable = []
		for d in display:
			index = display.index(d)
			d['cover'] = '<img src="' + d['cover'] + '" + " title="' + d['title'] + '"></img>'
			if d['year'] == -1:
				d['year'] = ''
				
		for d in display:

			del(d['title'])
		pprint(display)

		html = json2html.convert(json=display)
		html = html.replace('&quot;', '"')
		html = html.replace('&lt;', '<')
		html = html.replace('&gt;', '>')
		styleline =  '<html><head><meta charset="utf-8"><style> html, body {width: 90%;height: 10%; margin: 0;padding: 0; background-color: grey7;}'
		container = '#container {width: inherit; height: inherit; margin: 0; padding: 0;} </style></head>'
		div = '<body><div id="container">'
		html = styleline + container + div + html + '</div></body></html>'
		saveHtml(html, path)
		return path

	def delProvider(self, text):
		self.providers = list(filter(lambda x: x.clear != text, self.providers))
		saveJson(self.providers, '../data/providers.json')
		return True

	def addProvider(self, text):
		self.providers += list(filter(lambda x: x.clear == text and x not in self.providers, self.services))
		saveJson(self.providers, '../data/providers.json')
		return True


if __name__ == '__main__':
	mlist_url = "https://letterboxd.com/grryboy/watchlist/"
	jb = Justboxd()
	providers = ["Netflix", "Apple TV Plus", "Shudder", "Hulu", "Disney Plus", "HBO Max", "Hoopla", "Kanopy"]

	[jb.addProvider(p) for p in providers]
	# movies = jb.moviesFromList(mlist_url, update_all=False)
	# jb.toHtml(movies, path='../data/watchlist.html')


