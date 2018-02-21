A recipe tracker built on a REST API with Google OAuth 2.0 configured to access Google acccount information.
Available at  
https://myrecipes-194614.appspot.com
Service
I used the Google People API to allow a user to login to their Google Account to access their display name, photo, and people resource id. The people resource id is used in the routes below to access recipes and ingredients tied to their account as the value p_id. Any requests made to create/edit/delete/view recipes or ingredients requires the user to be authenticated for the requested pid or for the pid to equal 1, the hard-coded testing account.
Routes
POST /{p_id}/recipes
Result: creates a new recipe with the fields sent in the body for the user with the given p_id and puts it in the datastore
Required Data: name- string, directions- string, prep_time- string
Format: application/json, sent in request body
POST /recipes
Result: creates a new recipe with the fields sent in the body for the user with the body's person_id field value and puts it in the datastore
Required Data: name- string, person_id- integer, directions- string, prep_time- string
Format: application/json, sent in request body
GET /{p_id}/recipes
Result: returns all of the recipes for the person with the given p_id, ordered by name.
Format: Python list of JSON strings
GET /{p_id}/recipes/{r_id}
Result: returns the recipe with the given r_id attached to the person with the given p_id or a 404 error if not found.
Format: Python String
PATCH /{p_id}/recipes/{r_id}
Result: Modifies the recipe for the person with the given p_id and recipe with the given r_id or returns a 404 error code if not in the datastore. If changing the ingredients assigned to a recipe you can change the ingredient's recipe_id or delete the ingredient.
Required Data: One or more of the following, name- string, directions- string, prep_time- string
Format: application/json, sent in request body
DELETE /{p_id}/recipes/{r_id}
Result: Deletes a recipe for a person with the given p_id and a recipe id of r_id or returns a 404 if the recipe is not found. If the recipe is assigned any ingredients, all of the ingredients are deleted also.
POST /{p_id}/ingredients
Result: creates a new ingredient with the fields sent in the body for the user with the given p_id and puts it in the datastore
Required Data: name- string, quantity- integer, recipe_id- integer
Format: application/json, sent in request body
POST /ingredients
Result: creates a new ingredient with the fields sent in the body for the user with the body's person_id field value and puts it in the datastore
Required Data: name- string, quantity- integer, recipe_id- integer, person_id- string
Format: application/json, sent in request body
GET /{p_id}/ingredients
Result: returns all of the ingredients for the person with the given p_id, ordered by name.
Format: Python list of JSON strings
GET /{p_id}/ingredients/{i_id}
Result: returns the ingredient with the given i_id attached to the person with the given p_id or a 404 error if not found.
Format: Python String
PATCH /{p_id}/ingredients/{i_id}
Result: Modifies the ingredient for the person with the given p_id and ingredient with the given i_id or returns a 404 error code if not in the datastore. If changing the recipe_id for an ingredient, the new recipe_id must be in the datastore and belong to the given p_id or a 403 error is returned. 
Required Data: One or more of the following, name- string, quantity- integer, unit- string, recipe_id- integer
Format: application/json, sent in request body
DELETE /{p_id}/ingredients/{i_id}
Result: Deletes an ingredient for a person with the given p_id and an ingredient id of i_id or returns a 404 if the given ingredient is not found in the datastore. If the ingredient is assigned to any recipe i_id is removed from that recipe's ingredient_ids list.
GET /{p_id}/view
Result: use with a web browser to view a table of all of the user with the given p_id's recipes and ingredients assigned to them and forms and buttons for adding, editing, and deleting recipes and ingredients. One must be authenticated with OAuth2 from the site's Base URL page to view the recipes of any user other than a hard-coded test user with a p_id of 1.
