'''
James Todd - toddjam - CS496_400 - 3/18/18
Final Project - My Recipes
Help from:
https://docs.python.org/2/ , https://cloud.google.com/appengine/docs/standard/python/ ,
https://webapp2.readthedocs.io/en/latest/index.html#guide , https://developers.google.com/people/api/rest/
https://stackoverflow.com/questions/247483/http-get-request-in-javascript#4033310, https://bootswatch.com/,
https://developer.mozilla.org/en-US/docs/Web , https://www.w3schools.com/
'''

import webapp2
import json
from google.appengine.ext import ndb
import urllib
from google.appengine.api import urlfetch
import os
from webapp2_extras import jinja2
import logging

#Load app settings from config file
config = json.loads(open('config.json').read())
client_id = config['client_id']
client_secret = config['client_secret']
redirect_uri = config['redirect_uri']
scopes = config['scopes']
#set a secure random state
state = os.urandom(25).decode('latin-1')

#URL to authenticate user with OAuth2
auth_url = 'https://accounts.google.com/o/oauth2/v2/auth?response_type=code&client_id=' + client_id + '&redirect_uri=' + redirect_uri + '&scope=' + scopes + '&state=' + state

#Allow patching
allowed_methods = webapp2.WSGIApplication.allowed_methods
new_allowed_methods = allowed_methods.union(('PATCH',))
webapp2.WSGIApplication.allowed_methods = new_allowed_methods

#Setup token for authenticated API requests and getter and setter methods for it
token = None
def setUserToken(t):
    global token
    token = t

def getUserToken():
    return token

#setup user info variables and getter and setter methods for them
person_id, display_name, user_photo = None, None, None
def setUserInfo(p_id, d_name, photo):
    global person_id, display_name, user_photo
    person_id = p_id
    display_name = d_name
    user_photo = photo

def getUserInfo():
    return [person_id, display_name, user_photo]

#Checks if the user is authorized to view/edit data for the given pid, test account 1 is authorized for any user
def authorized(pid):
        if pid:
            pid = str(pid)
            user_info = getUserInfo()
            user_pid = user_info[0]
            if user_pid and str(user_pid) == pid:
                return True
            #Set test user information for view if necessary
            if pid == '1':
                setUserInfo(1, "Test User", "")
                return True
        return False

#Setup Jinja2 template rendering
class TemplateHandler(webapp2.RequestHandler):
    @webapp2.cached_property
    def jinja2(self):
        return jinja2.get_jinja2(app=self.app)
    def render_response(self, _template, **context):
        rv = self.jinja2.render_template(_template, **context)
        self.response.write(rv)

#Index Page
class IndexHandler(TemplateHandler):
    def get(self):
        setUserInfo(None, None, None)
        context = {'auth_url': auth_url}
        return self.render_response('index.html', **context)


#Handle OAuth2 Callback
class AuthCallBackHandler(webapp2.RequestHandler):
    def get(self):
        #get the state and access code from url
        sent_state = self.request.GET['state']
        access_code = self.request.GET['code']
        #verify state and receive access code from server
        payload = {'code': access_code, 'client_id' : client_id, 'client_secret' : client_secret, 'redirect_uri' : redirect_uri, 'grant_type' : 'authorization_code' }
        payload = urllib.urlencode(payload)
        post_req = urlfetch.fetch(url = 'https://www.googleapis.com/oauth2/v4/token',
        payload = payload, method = urlfetch.POST)
        result = json.loads(post_req.content)
        #set token from result sent by server
        token = str(result['token_type']) + ' ' + str(result['access_token'])
        setUserToken(token)
        headers = {'Authorization' : token}
        user_req = urlfetch.fetch(url = 'https://people.googleapis.com/v1/people/me?personFields=names,photos', method = urlfetch.GET, headers = headers)
        result = json.loads(user_req.content)
        p_id = str(result['resourceName'])[8:]
        d_name = str(result['names'][0]['displayName'])
        photo = str(result['photos'][0]['url'])
        setUserInfo(p_id, d_name, photo)
        return self.redirect(p_id + '/view')

#View all of the users recipes and ingredients
class RecipeViewHandler(TemplateHandler):
    def get(self, p_id = None):
        if p_id:
            if authorized(p_id):
                #get the user's recipes and ingredients
                base_url = 'https://myrecipes-194614.appspot.com/'
                recipe_req = urlfetch.fetch(url = base_url + p_id + '/recipes', method = urlfetch.GET)
                recipes = json.loads(recipe_req.content)
                ingredient_req = urlfetch.fetch(url = base_url + p_id + '/ingredients', method = urlfetch.GET)
                ingredients = json.loads(ingredient_req.content)
                #set up table rows with recipes and ingredients
                recipe_rows = ''
                if recipes:
                    for recipe in recipes:
                        if ingredients and recipe['ingredient_ids']:
                            recipe['ingredients'] = []
                            for i_id in recipe['ingredient_ids']:
                                for ing in ingredients:
                                    if ing['id'] == i_id:
                                        rec_ing = {'info': 'ID:(' + str(ing['id']) + ') ' + str(ing['quantity'])}
                                        units = recipe.get('units', False)
                                        if units:
                                            rec_ing['info'] = rec_ing['info'] + ' ' + units
                                        rec_ing['info'] = rec_ing['info'] + ' ' + ing['name']
                                        rec_ing['id'] = i_id
                                        recipe['ingredients'].append(rec_ing)
                user_info = getUserInfo()
                context = {'display_name': user_info[1], 'user_photo': user_info[2], 'recipes': recipes}
                return self.render_response('recipes.html', **context)
            else:
                return self.response.write('You have not been authorized to view this user\'s recipes.')
        else:
            return self.response.write('Please specify a pid of a user to view their recipes.')

#Recipe entity definition
class Recipe(ndb.Model):
    person_id = ndb.StringProperty(required=True)
    name = ndb.StringProperty(required=True)
    description = ndb.StringProperty()
    ingredient_ids = ndb.IntegerProperty(repeated=True)
    directions = ndb.StringProperty(required=True)
    prep_time = ndb.StringProperty(required=True)

#Ingredient entity definition
class Ingredient(ndb.Model):
    person_id = ndb.StringProperty(required=True)
    name = ndb.StringProperty(required=True)
    quantity = ndb.IntegerProperty(required=True)
    unit = ndb.StringProperty()
    recipe_id = ndb.IntegerProperty(required=True)

#Handle Recipe Requests
class RecipeHandler(webapp2.RequestHandler):
    #create new recipes for a user with a given p_id or for a user passed in request body
    def post(self, p_id = None):
        recipe_data = json.loads(self.request.body)
        if p_id is None:
            p_id = recipe_data.get('person_id', None)
        #create a new ingredient iff person_id passed in body or in url
        if p_id is not None and authorized(p_id):
            p_id = str(p_id)
            i_ids = recipe_data.get('ingredient_ids', [])
            d = recipe_data.get('description', None)
            #Only add ingredients that exist in the datastore for the given person
            if i_ids:
                for i_id in i_ids:
                    ing = Ingredient.get_by_id(i_id)
                    if(not(ing and ing.person_id is p_id)):
                        i_ids.remove(i_id)
            new_recipe = Recipe(person_id = p_id, name = recipe_data['name'], ingredient_ids = i_ids, description = d, directions = recipe_data['directions'], prep_time = recipe_data['prep_time'])
            new_recipe.put()
            recipe_dict = new_recipe.to_dict()
            recipe_dict['id'] = new_recipe.key.id()
            self.response.write(json.dumps(recipe_dict))
        #Return 403 error if no p_id in url or post body, or user not authorized to make the request
        else:
            self.abort(403)
    #get recipes for a given p_id with a passed in r_id or all recipes with no r_id
    def get(self, p_id = None, r_id = None):
        if p_id and authorized(p_id):
            p_id = str(p_id)
            #get a specific recipe for a given p_id
            if r_id:
                recipe = Recipe.get_by_id(int(r_id));
                if(recipe):
                    recipe_dict = recipe.to_dict()
                    recipe_dict['id'] = recipe.key.id()
                    self.response.write(json.dumps(recipe_dict))
                #return 404 code if recipe not found
                else:
                    self.abort(404)
            #get all recipes for a given p_id
            else:
                recipes = Recipe.query(Recipe.person_id == p_id).order(Recipe.name)
                recipe_dicts = []
                if recipes:
                    for recipe in recipes:
                        recipe_dict = recipe.to_dict()
                        recipe_dict['id'] = recipe.key.id()
                        recipe_dicts.append(recipe_dict)
                self.response.write(json.dumps(recipe_dicts))
        #Return 403 error if no p_id passed or user not authorized
        else:
            self.abort(403)
    #update a recipe with a given r_id for a person with p_id to new values sent in request body
    def patch(self, p_id = None, r_id = None):
        if p_id and authorized(p_id):
            p_id = str(p_id)
            if r_id:
                recipe = Recipe.get_by_id(int(r_id))
                if(recipe):
                    recipe_data = json.loads(self.request.body)
                    recipe.name = recipe_data.get('name', recipe.name)
                    recipe.directions = recipe_data.get('directions', recipe.directions)
                    recipe.description = recipe_data.get('description', recipe.description)
                    recipe.prep_time = recipe_data.get('prep_time', recipe.prep_time)
                    recipe.put()
                    recipe_dict = recipe.to_dict()
                    recipe_dict['id'] = recipe.key.id()
                    self.response.write(json.dumps(recipe_dict))
                #Return 404 if recipe with r_id not in database
                else:
                    self.abort(404)
            #Return 403 if no recipe specified for patch
            else:
                self.abort(403)
        #Return 403 if no person specified for patching their recipe, or user not authorized
        else:
            self.abort(403)
    #remove recipes from datastore, removing their ingredients if they have any
    def delete(self, p_id = None, r_id = None):
        if p_id and authorized(p_id):
            p_id = str(p_id)
            if r_id:
                recipe = Recipe.get_by_id(int(r_id));
                if(recipe):
                    #Remove each ingredient assigned to the recipe
                    recipe_ingredients = Ingredient.query(Ingredient.recipe_id == int(r_id))
                    if recipe_ingredients:
                        for ingredient in recipe_ingredients:
                            ingredient.key.delete()
                    #remove the recipe
                    recipe.key.delete()
                #Return 404 if trying to delete a recipe not found in datastore
                else:
                    self.abort(404)
            #Return 403 if not passing a recipe id to delete
            else:
                self.abort(403)
        #Return 403 if not specifying which person's recipe to delete or user not authorized
        else:
            self.abort(403)

#Handle Ingredient Requests
class IngredientHandler(webapp2.RequestHandler):
    #create new ingredients for a user with a given p_id or for a user passed in request body
    def post(self, p_id = None):
        ing_data = json.loads(self.request.body)
        if not p_id:
            p_id = ing_data.get('person_id', False)
        #create a new ingredient iff person_id passed in body or in url and recipe_id corresponds to recipe in database
        if p_id and authorized(p_id):
            p_id = str(p_id)
            u = ing_data.get('unit', None)
            r_id = ing_data['recipe_id']
            recipe = Recipe.get_by_id(int(r_id))
            if recipe and recipe.person_id == p_id:
                new_ing = Ingredient(person_id = p_id, name = ing_data['name'], quantity = ing_data['quantity'], unit = u, recipe_id = ing_data['recipe_id'])
                new_ing.put()
                ing_dict = new_ing.to_dict()
                ing_dict['id'] = new_ing.key.id()
                #add the new ingredient to the recipe's ingredient ids
                recipe.ingredient_ids.append(ing_dict['id'])
                recipe.put()
                self.response.write(json.dumps(ing_dict))
            #Return 403 error if adding an ingredient for a recipe that doesn't exist in datastore or doesn't correspond to the passed in p_id
            else:
                self.abort(403)
        #Return 403 error if no p_id in url or post body or user not authorized
        else:
            self.abort(403)
    #get ingredients for a given p_id with a passed in i_id or all ingredients with no i_id
    def get(self, p_id = None, i_id = None):
        if p_id and authorized(p_id):
            p_id = str(p_id)
            #get a specific ingredient for a given p_id
            if i_id:
                ing = Ingredient.get_by_id(int(i_id));
                if ing:
                    ing_dict = ing.to_dict()
                    ing_dict['id'] = ing.key.id()
                    self.response.write(json.dumps(ing_dict))
                #return 404 code if ingredient not found
                else:
                    self.abort(404)
            #get all ingredients for a given p_id
            else:
                ings = Ingredient.query(Ingredient.person_id == p_id).order(Ingredient.name)
                ing_dicts = []
                if ings:
                    for ing in ings:
                        ing_dict = ing.to_dict()
                        ing_dict['id'] = ing.key.id()
                        ing_dicts.append(ing_dict)
                self.response.write(json.dumps(ing_dicts))
        #Return 403 error if no p_id passed or user not authorized
        else:
            self.abort(403)
    #update an ingredient with a given i_id for a person with p_id to new values sent in request body
    def patch(self, p_id = None, i_id = None):
        if p_id and authorized(p_id):
            p_id = str(p_id)
            if i_id:
                ing = Ingredient.get_by_id(int(i_id))
                if ing:
                    ing_data = json.loads(self.request.body)
                    ing.name = ing_data.get('name', ing.name)
                    ing.unit = ing_data.get('unit', ing.unit)
                    ing.quantity = ing_data.get('quantity', ing.quantity)
                    #If changing the recipe_id only do so if the recipe belongs to this p_id and exists in datastore
                    r_id = ing_data.get('recipe_id', None)
                    if(r_id):
                        recipe = Recipe.get_by_id(int(r_id))
                        #Remove the ingredient id from the old recipe and add it to the new one
                        if recipe and recipe.person_id == p_id:
                            old_recipe = Recipe.get_by_id(ing.recipe_id)
                            old_recipe.ingredient_ids.remove(ing.key.id())
                            old_recipe.put()
                            ing.recipe_id = r_id
                            recipe.ingredient_ids.append(ing.key.id())
                            recipe.put()
                        #Return a 403 if assigning ingredient to another user's recipe or for a recipe that doesn't exist
                        else:
                            self.abort(403)
                    ing.put()
                    ing_dict = ing.to_dict()
                    ing_dict['id'] = ing.key.id()
                    self.response.write(json.dumps(ing_dict))
                #Return 404 if ingredient with i_id not in database
                else:
                    self.abort(404)
            #Return 403 if no ingredient specified for patch
            else:
                self.abort(403)
        #Return 403 if no person specified for patching their ingredient, or user not authorized
        else:
            self.abort(403)
    #remove a person with p_id's ingredient with i_id
    def delete(self, p_id = None, i_id = None):
        if p_id and authorized(p_id):
            p_id = str(p_id)
            if i_id:
                ing = Ingredient.get_by_id(int(i_id))
                if(ing):
                    #Remove the ingredient id from the recipe which contains the ingredient
                    recipe = Recipe.get_by_id(ing.recipe_id)
                    recipe.ingredient_ids.remove(ing.key.id())
                    recipe.put()
                    #remove the ingredient
                    ing.key.delete()
                #Return 404 if trying to delete an ingredient not found in datastore
                else:
                    self.abort(404)
            #Return 403 if not passing a i_id to delete
            else:
                self.abort(403)
        #Return 403 if not specifying which person's ingredient to delete or user not authorized
        else:
            self.abort(403)

#Define app routes
app = webapp2.WSGIApplication([
    ('/', IndexHandler),
    ('/authcallback', AuthCallBackHandler),
    ('/(.*)/view', RecipeViewHandler),
    ('/recipes', RecipeHandler),
    ('/(.*)/recipes', RecipeHandler),
    ('/(.*)/recipes/(.*)', RecipeHandler),
    ('/ingredients', IngredientHandler),
    ('/(.*)/ingredients', IngredientHandler),
    ('/(.*)/ingredients/(.*)', IngredientHandler)
], debug=True)
