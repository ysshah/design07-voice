import urllib2
import json
import boto3

def lambda_handler(event, context):
    # if (event["session"]["application"]["applicationId"] !=
    #         "amzn1.ask.skill.???"):
    #     raise ValueError("Invalid Application ID")
    if event["request"]["type"] == "LaunchRequest":
        return on_launch(event["request"], event["session"])
    elif event["request"]["type"] == "IntentRequest":
        return on_intent(event["request"], event["session"])


def on_launch(launch_request, session):
    card_title = "Welcome"
    speech_output = "Cook Smart here! What can I do for you?"
    return build_response(build_speechlet_response(speech_output, card_title))


def on_intent(intent_request, session):
    intent = intent_request["intent"]
    intent_name = intent_request["intent"]["name"]

    if "attributes" in session and session["attributes"].get("inRecipe", False):
        if intent_name == "HomeIntent":
            return go_to_home()
        elif intent_name == "StartIngredIntent":
            session["attributes"]["ingredientIndex"] = 0
            return read_ingredient(session)
        elif intent_name == "StartInstIntent":
            session["attributes"]["directionIndex"] = 0
            return read_direction(session)
        elif session["attributes"].get("readingIngredients", False):
            if intent_name == "GeneralQueryIntent":
                return ingredient_commands(session)
            elif intent_name == "PrevIngredIntent":
                session["attributes"]["ingredientIndex"] -= 1
            elif intent_name == "NextIngredIntent":
                session["attributes"]["ingredientIndex"] += 1
            elif intent_name == "RestartIntent":
                session["attributes"]["ingredientIndex"] = 0
            return read_ingredient(session)
        elif session["attributes"].get("readingDirections", False):
            if intent_name == "GeneralQueryIntent":
                return direction_commands(session)
            elif intent_name == "PrevInstIntent":
                session["attributes"]["directionIndex"] -= 1
            elif intent_name == "NextInstIntent":
                session["attributes"]["directionIndex"] += 1
            elif intent_name == "RestartIntent":
                session["attributes"]["directionIndex"] = 0
            return read_direction(session)
        elif intent_name == "GeneralQueryIntent":
            return recipe_commands(session)

    elif intent_name == "AddRecipeIntent":
        return add_recipe_to_calendar(intent)

    elif intent_name == "AddRecipeNoDateIntent":
        return start_add_recipe_to_calendar_no_date(intent)

    elif intent_name == "AddRecipeNoMealTypeIntent":
        return start_add_recipe_to_calendar_no_meal_type(intent)

    elif intent_name == "AddIngredIntent":
        return start_add_ingred_to_pantry(intent)

    elif intent_name == "AddIngredNoAmountNoUnitIntent":
        return start_add_ingred_to_pantry_no_amount_no_unit(intent)

    elif intent_name == "RecipeMealTypeSpecifierIntent":
        return finish_add_recipe_to_calendar_no_meal_type(intent, session)

    elif intent_name == "IngredAmountAndUnitSpecifierIntent":
        return middle_add_ingred_to_pantry_no_amount_no_unit(intent, session)

    elif intent_name == "DateSpecifierIntent":
        if "attributes" in session and session["attributes"].get("inCalendar",False):
            return finish_add_recipe_to_calendar_no_date(intent, session)
        elif "attributes" in session and session["attributes"].get("inPantry",False):
            return finish_add_ingred_to_pantry(intent, session)

    elif intent_name == "GeneralQueryIntent":
        return home_commands()

    elif intent_name == "FindIntent":
        return find_recipe(intent)

    elif intent_name == "HomeIntent":
        return go_to_home()

    else:
        raise ValueError("Invalid intent")


def recipeInTable(recipe_name):
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    cook_smart_recipes = dynamodb.Table("CookSmartRecipes")
    response = cook_smart_recipes.scan()
    for recipe in response["Items"]:
        if recipe_name.lower() == recipe["RecipeName"].lower():
            return recipe["RecipeName"]
    return False


def add_recipe_to_calendar(intent):
    card_title = "Add Recipe to Calendar"

    input_recipe = intent["slots"]["RecipeName"]["value"]
    table_recipe = recipeInTable(input_recipe)

    if table_recipe:
        date = intent["slots"]["Date"]["value"]
        meal_type = intent["slots"]["MealType"]["value"].title()
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        cook_smart_calendar = dynamodb.Table("CookSmartCalendar")
        response = cook_smart_calendar.put_item(
            Item = {
                "Date": date,
                "MealType": meal_type,
                "RecipeName": table_recipe
            }
        )
        speech_output = table_recipe + " has been added to your calendar."
    else:
        speech_output = (input_recipe + " is not in the list of recipes. "
            "You can add this recipe using the web application.")

    return build_response(build_speechlet_response(speech_output, card_title))


def start_add_recipe_to_calendar_no_date(intent):
    session_attributes = None
    card_title = "Start Add Recipe to Calendar No Date"

    input_recipe = intent["slots"]["RecipeName"]["value"]
    table_recipe = recipeInTable(input_recipe)

    if table_recipe:
        meal_type = intent["slots"]["MealType"]["value"].title()
        session_attributes = {
            "inCalendar": True,
            "RecipeName": table_recipe,
            "MealType": meal_type,
        }
        speech_output = "What date would you like to eat " + table_recipe + "?"
    else:
        speech_output = (input_recipe + " is not in the list of recipes. "
            "You can add this recipe using the web application")

    return build_response(build_speechlet_response(speech_output, card_title),
        session_attributes)


def finish_add_recipe_to_calendar_no_date(intent, session):
    card_title = "Finish Add Recipe to Calendar No Date"

    session_attributes = session.get("attributes", {})
    recipe_name = session_attributes["RecipeName"]
    meal_type = session_attributes["MealType"]
    date = intent["slots"]["Date"]["value"]

    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    cook_smart_calendar = dynamodb.Table("CookSmartCalendar")
    response = cook_smart_calendar.put_item(
        Item={
            "Date": date,
            "MealType": meal_type,
            "RecipeName": recipe_name
        }
    )
    speech_output = recipe_name + " has been added to the calendar."
    return build_response(build_speechlet_response(speech_output, card_title))


def start_add_recipe_to_calendar_no_meal_type(intent):
    session_attributes = None
    card_title = "Start Add Recipe to Calendar No Meal Type"

    input_recipe = intent["slots"]["RecipeName"]["value"]
    table_recipe = recipeInTable(input_recipe)

    if table_recipe:
        date = intent["slots"]["Date"]["value"]
        session_attributes = {
            "inCalendar": True,
            "RecipeName": table_recipe,
            "Date": date,
        }
        speech_output = ("Would you like to eat " + table_recipe + " for "
            "breakfast, lunch, dinner, or dessert?")
    else:
        speech_output = (input_recipe + " is not in the list of recipes. "
            "You can add this recipe using the web application")

    return build_response(build_speechlet_response(speech_output, card_title), session_attributes)


def finish_add_recipe_to_calendar_no_meal_type(intent, session):
    card_title = "Finish Add Recipe to Calendar No Meal Type"

    session_attributes = session.get("attributes",{})
    recipe_name = session_attributes["RecipeName"]
    date = session_attributes["Date"]
    meal_type = intent["slots"]["MealType"]["value"].title()

    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    cook_smart_calendar = dynamodb.Table("CookSmartCalendar")
    response = cook_smart_calendar.put_item(
        Item={
            "Date": date,
            "MealType": meal_type,
            "RecipeName": recipe_name
        }
    )
    speech_output = (recipe_name + " has been added to the calendar.")
    return build_response(build_speechlet_response(speech_output, card_title))


def start_add_ingred_to_pantry(intent):
    card_title = "Start Add Ingred To Pantry"

    ingredient_name = intent["slots"]["IngredName"]["value"]
    ingredient_amount = intent["slots"]["IngredAmount"]["value"]
    ingredient_unit = intent["slots"]["IngredUnit"]["value"]

    session_attributes = {
        "inPantry": True,
        "IngredientName": ingredient_name,
        "IngredientAmount": ingredient_amount,
        "IngredientUnit": ingredient_unit
    }
    speech_output = ("What is the expiration date?")
    return build_response(build_speechlet_response(speech_output, card_title), session_attributes)


def finish_add_ingred_to_pantry(intent, session):
    card_title = "Finish Add Ingred to Pantry"

    session_attributes = session.get("attributes",{})
    ingredient_name = session_attributes["IngredientName"]
    ingredient_amount = session_attributes["IngredientAmount"]
    ingredient_unit = session_attributes["IngredientUnit"]
    date = intent["slots"]["Date"]["value"]

    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    cook_smart_pantry = dynamodb.Table("CookSmartPantry")
    response = cook_smart_pantry.put_item(
        Item={
            "IngredientName": ingredient_name,
            "IngredientAmount": ingredient_amount,
            "IngredientUnit": ingredient_unit,
            "ExpirationDate": date
        }
    )
    speech_output = (ingredient_amount + " " + ingredient_unit + " of " + ingredient_name + " has been added to the pantry")
    return build_response(build_speechlet_response(speech_output, card_title))


def start_add_ingred_to_pantry_no_amount_no_unit(intent):
    card_title = "Start Add Ingred to Pantry No Amount No Unit"

    ingredient_name = intent["slots"]["IngredName"]["value"]

    session_attributes = {
        "inPantry": True,
        "IngredientName": ingredient_name
    }
    speech_output = ("How much " + ingredient_name + " did you buy?")
    return build_response(build_speechlet_response(speech_output, card_title), session_attributes)


def middle_add_ingred_to_pantry_no_amount_no_unit(intent, session):
    card_title = "Middle Add Ingred To Pantry No Amount No Unit"

    session_attributes = session.get("attributes",{})
    ingredient_name = session_attributes["IngredientName"]
    ingredient_amount = intent["slots"]["IngredAmount"]["value"]
    ingredient_unit = intent["slots"]["IngredUnit"]["value"]
    session_attributes = {
        "inPantry": True,
        "IngredientName": ingredient_name,
        "IngredientAmount": ingredient_amount,
        "IngredientUnit": ingredient_unit
    }
    speech_output = ("What is the expiration date?")
    return build_response(build_speechlet_response(speech_output, card_title), session_attributes)


def home_commands():
    card_title = "List of Commands"
    speech_output = (
        "You can ask me to find any recipes that are on the website. When I "
        'find the recipe, you can say "ingredients" or "recipe" to have me '
        'read the list of ingredients or directions, one by one.'
    )
    return build_response(build_speechlet_response(speech_output, card_title))


def recipe_commands(session):
    session_attributes = session.get("attributes", {})
    card_title = "Recipe Commands"
    speech_output = ('You can say "ingredients" or "recipe" to have me '
        'read the list of ingredients or directions, one by one.')
    return build_response(build_speechlet_response(speech_output, card_title),
        session_attributes)


def ingredient_commands(session):
    session_attributes = session.get("attributes", {})
    card_title = "Ingredient List Commands"
    speech_output = ('You can say "next ingredient", "last ingredient", '
        '"start again" to restart the ingredients list, or "read recipe" '
        'to move on to the recipe directions.')
    return build_response(build_speechlet_response(speech_output, card_title),
        session_attributes)


def direction_commands(session):
    session_attributes = session.get("attributes", {})
    card_title = "Direction List Commands"
    speech_output = ('You can say "next step", "last step", or '
        '"start again" to restart the directions list.')
    return build_response(build_speechlet_response(speech_output, card_title),
        session_attributes)


def find_recipe(intent):
    recipes = json.loads(urllib2.urlopen("https://ffgh18ctp9.execute-api."
        "us-east-1.amazonaws.com/prod/RecipeUpdate?TableName=RecipesDB").read())
    query = intent["slots"]["SearchTerms"]["value"].lower()
    for recipe in recipes["Items"]:
        if recipe["RecipeName"].lower() == query:
            return begin_recipe(recipe)

    card_title = "Recipe not found"
    speech_output = ('Sorry, I could not find "' + query
        + '" in your list of recipes.')
    return build_response(build_speechlet_response(speech_output, card_title))


def begin_recipe(recipe):
    card_title = "Found recipe!"
    speech_output = "I found your recipe for {}.".format(recipe["RecipeName"])
    session_attributes = {
        "inRecipe": True,
        "name": recipe["RecipeName"],
        "ingredients": recipe["IngredientsList"].split("\n"),
        "directions": recipe["PrepDirections"].split("\n"),
        "ingredientIndex": 0,
        "directionIndex": 0
    }
    return build_response(build_speechlet_response(speech_output, card_title),
        session_attributes)


def read_ingredient(session):
    session_attributes = session.get("attributes", {})
    session_attributes["readingIngredients"] = True
    session_attributes["readingDirections"] = False
    session_attributes["directionIndex"] = 0
    card_title = session_attributes["name"] + " Ingredients"
    i = session_attributes["ingredientIndex"]
    if i <= 0:
        session_attributes["ingredientIndex"] = 0
        speech_output = "The first ingredient is {}.".format(
            session_attributes["ingredients"][0])
    elif i >= len(session_attributes["ingredients"]) - 1:
        session_attributes["ingredientIndex"] = len(
            session_attributes["ingredients"]) - 1
        speech_output = ('The last ingredient is {}. To start recipe '
            'directions, please say "read recipe."'.format(
            session_attributes["ingredients"][-1]))
    else:
        speech_output = session_attributes["ingredients"][i]
    return build_response(build_speechlet_response(speech_output, card_title),
        session_attributes)


def read_direction(session):
    session_attributes = session.get("attributes", {})
    session_attributes["readingDirections"] = True
    session_attributes["readingIngredients"] = False
    session_attributes["ingredientIndex"] = 0
    card_title = session_attributes["name"] + " Directions"
    i = session_attributes["directionIndex"]
    if i <= 0:
        session_attributes["directionIndex"] = 0
        speech_output = "First, " + session_attributes["directions"][0]
    elif i >= len(session_attributes["directions"]) - 1:
        session_attributes["directionIndex"] = len(
            session_attributes["directions"]) - 1
        speech_output = "Finally, " + session_attributes["directions"][-1]
    else:
        speech_output = "Next, " + session_attributes["directions"][i]
    return build_response(build_speechlet_response(speech_output, card_title),
        session_attributes)


def go_to_home():
    card_title = "Recipe Assistant Home"
    speech_output = "What recipe would you like to make?"
    return build_response(build_speechlet_response(speech_output, card_title))


def handle_session_end_request():
    card_title = "Thank you!"
    speech_output = "Thank you for using Recipe Assistant."
    return build_response(build_speechlet_response(speech_output, card_title,
        should_end_session=True))


def build_speechlet_response(speech_output, card_title=None,
    card_output=None, reprompt_text=None, should_end_session=False):

    if card_output is None:
        card_output = speech_output

    return {
        "outputSpeech": {
            "type": "PlainText",
            "text": speech_output
        },
        "card": {
            "type": "Simple",
            "title": card_title,
            "subtitle": "Recipe Assistant",
            "content": card_output
        },
        "reprompt": {
            "outputSpeech": {
                "type": "PlainText",
                "text": reprompt_text
            }
        },
        "shouldEndSession": should_end_session
    }


def build_response(speechlet_response, session_attributes={}):
    return {
        "version": "1.0",
        "response": speechlet_response,
        "sessionAttributes": session_attributes
    }
