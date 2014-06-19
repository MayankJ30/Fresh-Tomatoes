#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from google.appengine.ext import db
from apiclient.discovery import build
from apiclient.errors import HttpError

import os, re, string, urllib2, json, logging, webapp2, jinja2, cookielib

SECRET = "imsosecret"
DEVELOPER_KEY = "AIzaSyAgf7k0mQmxF12ywMq1_pxOxFi_OfOuuUs"
API_KEY = '49101d62654e71a2931722642ac07e5e'
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), autoescape=True)

def youtube_search(query, max_results=20):
    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=DEVELOPER_KEY)
 
    # Call the search.list method to retrieve results matching the specified
    # query term.
    search_response = youtube.search().list(
        q=query,
        part="id,snippet",
        maxResults=max_results,
        type="video"
    ).execute()
 
    #extract only a few 'interesting' fields from the data
    result_transform = lambda search_result: {
                    'id': search_result['id']['videoId'],
                    'title': search_result['snippet']['title'], 
                    'thumbnail': search_result['snippet']['thumbnails']['default']['url'],
                    'date': search_result['snippet']['publishedAt']
                }
    # Filter results to retaun only matching videos, and filter out channels and playlists.
    
    return map(result_transform, search_response.get("items", []))


class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)
    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

class Movie(db.Model):
    name = db.StringProperty(required = True)
    trailer_url = db.StringProperty(required = True)
    poster_url = db.StringProperty(required = True)
    plot = db.StringProperty(required = True)
    
class MainPage(Handler):
    def get(self):
        movies = db.GqlQuery("select * from Movie ")
        
        #self.write("hello")
        self.render('jumbotron.html', movies=movies)

class SubmitHandler(Handler):
    def get(self):
        self.render("signin.html" , movie_error = None)
    def post(self):
        movie = self.request.get("movie")
        search_results = youtube_search(movie+"Trailer")
        if len(search_results) != 0:
            trailer_url = "http://www.youtube.com/embed/"+search_results[0]['id']
        else: 
            trailer_url = None

        movie_split = movie.split(" ")
        encoded_movie_name = "%20".join(movie_split)
        #logging.error("url is http://www.omdbapi.com/?t=" + encoded_movie_name)
        connection = urllib2.urlopen(r"http://api.themoviedb.org/3/search/movie?query="+encoded_movie_name+"&api_key="+API_KEY)
        j = connection.read()
        search_results = json.loads(j)
        #logging.error(movie_attributes)
        if search_results["total_results"] == 0:
            #logging.error("Error route")
            self.render("signin.html",movie_error="Movie cannot be found/does not exist. Please check spelling.")
        else:
            #logging.error("Correct route")
            connection = urllib2.urlopen("http://api.themoviedb.org/3/movie/"+str(search_results["results"][0]["id"])+"?api_key="+API_KEY)
            j = connection.read()
            movie_attributes = json.loads(j)
            plot = movie_attributes["overview"]
            name = movie_attributes["title"]
            poster_url = r"http://image.tmdb.org/t/p/w500" + movie_attributes["poster_path"]
            
            
            check = db.GqlQuery('SELECT * FROM Movie WHERE name = :1', movie).get()
            if not check:
                # youtube_id_match = re.search(r'(?<=v=)[^&#]+', youtube)
                # youtube_id_match = youtube_id_match or re.search(r'(?<=be/)[^&#]+', youtube)
                # youtube = youtube_id_match.group(0) if youtube_id_match else None
                u = Movie(name = name, trailer_url = trailer_url,poster_url = poster_url, plot = plot )
                u.put()
                

            #     adding this movie to the users movie list
            #     my_movies = self.request.cookies.get("my_movies")
            #     if my_movies:
            #         my_movies = json.loads(my_movies)
            #         if movie not in my_movies:
            #             my_movies += [movie]
            #     else:
            #         my_movies = [movie]
            #     self.response.set_cookie("my_movies", json.dumps(my_movies), max_age=315360000)
            #     self.redirect('/')
            # else:
            #     self.render("signin.html",movie_error="Movie already exists")


class DetailsHandler(Handler):
    def get(self, movie_id):
        key = db.Key.from_path('Movie', int(movie_id))
        movie = db.get(key)
        if not movie:
            self.write("404 Error")
        else:
            self.render("details.html", movie = movie)


app = webapp2.WSGIApplication([('/', MainPage),
                               ('/submit' , SubmitHandler),
                               ('/([0-9]+)',DetailsHandler)], debug=True)
