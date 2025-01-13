"""
chatbot.py: A module for implementing a versatile chatbot for restaurant booking and administration.

This module contains the core functionalities of a chatbot that handles user interactions for various purposes.
It includes a system for user dialogue management, handling administrative tasks (like viewing and clearing
reservations), processing booking requests, and responding to general user queries. The chatbot leverages
a trained machine learning model for intent recognition and uses a randomized set of  associated responses for user communication.

"""
# Import necessary libraries

import pandas as pd
import random
import nltk
from nltk.stem import WordNetLemmatizer
#nltk.download('wordnet')
#nltk.download('omw-1.4')
from utils import train_intent_model, extract_all_entities, get_intent, load_intent_model
import csv
from sklearn.ensemble import RandomForestClassifier
import os

# Get the directory of the current script
script_dir = os.path.dirname(__file__)
#file paths
RESPONSES_FILE_PATH = ('responses.csv')
BOOKINGS_FILE_PATH = ('bookings.csv')
MENU_FILE_PATH = ('menu.csv')

#Train or Load  the intent model and vectorizer
vectorizer, model = train_intent_model()
# Train or Load  the intent model and vectorizer
vectorizer, model = load_intent_model()

def lemmatize_text(text):
    """
    Lemmatize the given text using NLTK's WordNetLemmatizer.

    Parameters:
    text (str): The text to be lemmatized.

    Returns:
    str: Lemmatized text.
    """
    lemmatizer = WordNetLemmatizer()
    lemmatized_output = ' '.join([lemmatizer.lemmatize(w) for w in nltk.word_tokenize(text)])
    return lemmatized_output

def handle_admin_login(user_input, user_dict):
    """
    Handle the admin login process, including username and password input.

    Parameters:
    user_input (str): The current user input.
    user_dict (dict): The current state dictionary of the user.

    Returns:
    tuple: A response message and the updated user_dict.
    """
    if user_dict['admin_login']['awaiting_username']:
        user_dict['admin_login']['username'] = user_input
        user_dict['admin_login']['awaiting_username'] = False
        user_dict['admin_login']['awaiting_password'] = True
        return "Please enter your password:", user_dict

    elif user_dict['admin_login']['awaiting_password']:
        if user_input == "adminpass":  # Replace with password 
            user_dict['admin_login']['is_admin'] = True
            user_dict['admin_login']['awaiting_password'] = False
            return "Admin login successful.", user_dict
        else:
            user_dict['admin_login'] = {"is_admin": False, "username": None, "awaiting_username": False, "awaiting_password": False}
            return "Incorrect password. Admin login failed.", user_dict

    return None, user_dict

def handle_admin_actions(intent, user_dict):
    """
    Handle admin-specific actions such as viewing and clearing reservations.

    Parameters:
    intent (str): The recognized intent of the user's input.
    user_dict (dict): The current state dictionary of the user.

    Returns:
    tuple: A response message and the updated user_dict.
    """
    if intent == 'view_reservations':
        if user_dict['admin_login']['is_admin']:
            try:
                bookings_df = pd.read_csv(BOOKINGS_FILE_PATH, delimiter='|')
                bookings_list = bookings_df.to_string(index=False)
                return f"Current List of Bookings:\n{bookings_list}", user_dict
            except Exception as e:
                return "Error reading the bookings file.", user_dict
        else:
            return "Sorry, you need to log in as an administrator first.", user_dict

    if intent == 'clear_reservations':
        if user_dict['admin_login']['is_admin']:
            try:
                open(BOOKINGS_FILE_PATH, 'w').close()
                return "All reservations have been cleared.", user_dict
            except Exception as e:
                return "Error clearing the bookings file.", user_dict
        else:
            return "Sorry, you need to log in as an administrator to perform this action.", user_dict

    return None, user_dict




def generate_response(user_input, user_dict):
    """
    Handles all the general user actions/intents. 

    This function orchestrates the chatbot's response by handling different scenarios:
    - Admin login process: managing admin username and password inputs.
    - Focus handling during the booking process: managing queries related to booking details like date, time, and number of people.
    - Booking confirmation: confirming the booking details with the user.
    - Editing booking details: allows modification of existing booking details before confirmation.
    - Admin-specific actions: handling actions like viewing and clearing reservations if the user is logged in as an admin.
    - General user interactions: handling standard user queries such as asking for a name, viewing the menu, changing and checking current user name.

    Parameters:
    user_input (str): The user's input to the chatbot.
    user_dict (dict): The current state dictionary of the user, containing information 
                      like current focus, booking details, and admin status.

    Returns:
    tuple: A response message from the chatbot and the updated user_dict.
    """
    # Load all responses
    # Lemmatize the user input
    user_input = lemmatize_text(user_input)
    df = pd.read_csv(RESPONSES_FILE_PATH, delimiter='|')

    # Divert Admin login process
    if user_dict['admin_login']['awaiting_username'] or user_dict['admin_login']['awaiting_password']:
        response, user_dict = handle_admin_login(user_input, user_dict)
        if response:
            return response, user_dict
    #Handling name pending request

    if user_dict['pending_name']:
        user_dict['name'] = user_input
        user_dict['pending_name'] = False
        responses = df[df['Intent'] == 'change_name_specified']['Response'].tolist()
        chosen_response = random.choice(responses).format(name=user_dict['name'])
        return chosen_response, user_dict

    # Handling focus during booking process and awaiting confirmation logic
    if 'focus' in user_dict and user_dict['focus']:
        if user_dict['focus'] == 'ask_for_date':
            user_dict['booking']['date'] = user_input
        elif user_dict['focus'] == 'ask_for_time':
            user_dict['booking']['time'] = user_input
        elif user_dict['focus'] == 'ask_for_people':
            user_dict['booking']['people'] = user_input
        # Reset focus after handling
        user_dict['focus'] = None

        # Check for any remaining missing information
        missing_info = [info for info in ['date', 'time', 'people'] if not user_dict['booking'][info]]
        if missing_info:
            # Continue asking for the next missing detail
            next_missing_info = missing_info[0]
            user_dict['focus'] = f'ask_for_{next_missing_info}'
            response_query = df[df['Intent'] == f'ask_for_{next_missing_info}']['Response'].tolist()
            chosen_response = random.choice(response_query)
            return chosen_response, user_dict
        else:
            confirm_response = df[df['Intent'] == 'confirm']['Response'].tolist()
            chosen_response = random.choice(confirm_response).format(**user_dict['booking'])
            user_dict['awaiting_confirmation'] = True
            user_dict['pending_booking'] = user_dict['booking'].copy()
            return chosen_response + "\nIs this correct? Please confirm.", user_dict

    elif user_dict.get('awaiting_confirmation'):
        intent = get_intent(user_input, vectorizer, model)
        if intent == 'confirm':
            # Save booking details if confirmation intent is detected
            with open(BOOKINGS_FILE_PATH, 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([user_dict['name'], user_dict['pending_booking']['date'],
                                 user_dict['pending_booking']['time'], user_dict['pending_booking']['people']])
            user_dict['booking'] = {"date": None, "time": None, "people": None}
            user_dict['awaiting_confirmation'] = False
            user_dict['pending_booking'] = None
            return "Your booking has been confirmed and saved in our records. Please let me know what else I can do for you. ", user_dict

        elif intent in ['edit_date', 'edit_time', 'edit_people']:
            entities = extract_all_entities(user_input)
            entity_updated = False

            for entity_text, entity_type in entities:
                if intent == 'edit_date' and entity_type == 'DATE':
                    user_dict['pending_booking']['date'] = entity_text
                    entity_updated = True
                elif intent == 'edit_time' and entity_type == 'TIME':
                    user_dict['pending_booking']['time'] = entity_text
                    entity_updated = True
                elif intent == 'edit_people' and entity_type == 'CARDINAL':
                    user_dict['pending_booking']['people'] = entity_text 
                    entity_updated = True 
            if entity_updated:

                # Update the booking details in the user dictionary
                user_dict['booking'] = user_dict['pending_booking'].copy()
                # Set the chatbot back to awaiting confirmation state
                user_dict['awaiting_confirmation'] = True
                # Retrieve the confirmation response from the database
                confirm_response = df[df['Intent'] == 'confirm']['Response'].tolist()
                chosen_response = random.choice(confirm_response).format(**user_dict['booking'])
                return chosen_response + "\nIs this correct? Please confirm.", user_dict
            else:
                # If the entity wasn't extracted, ask the user to provide the specific information
                if intent == 'edit_date':
                    user_dict['focus'] = 'ask_for_date'
                elif intent == 'edit_time':
                    user_dict['focus'] = 'ask_for_time'
                elif intent == 'edit_people':
                    user_dict['focus'] = 'ask_for_people'

                response_query = df[df['Intent'] == user_dict['focus']]['Response'].tolist()
                chosen_response = random.choice(response_query)
                return chosen_response, user_dict
        else:
            # Handle non-confirmation responses
            user_dict['awaiting_confirmation'] = False
            user_dict['pending_booking'] = None
            return "Booking not confirmed. How can I assist you further?", user_dict

    # Vectorize the user input and predict the intent
    input_vectors = vectorizer.transform([user_input])
    
    intent = get_intent(user_input, vectorizer, model)
    #intent = get_intent(user_input, vectorizer, input_vector)
    #print("Intent: ", intent)
    
    if intent == 'login_admin':
        user_dict['admin_login']['awaiting_username'] = True
        return "Please enter your username:", user_dict

    # Handle admin-specific actions
    if intent in ['view_reservations', 'clear_reservations']:
        response, user_dict = handle_admin_actions(intent, user_dict)
        if response:
            return response, user_dict

    
    # Handle Name change request
    if intent == 'change_name_specified':
        entities = extract_all_entities(user_input)
        names = [entity[0] for entity in entities if entity[1] == 'PERSON']
        if names:
            user_dict['name'] = names[0]
        else:
            user_dict['pending_name'] = True
            intent= 'change_name'
        
        
    # Handle asking for name
    if intent == 'ask_name':
        responses = df[df['Intent'] == intent]['Response'].tolist()
        chosen_response = random.choice(responses).format(name=user_dict['name'])
        return chosen_response, user_dict

    # Handle menu display request
    if intent == 'view_menu':
        responses = df[df['Intent'] == intent]['Response'].tolist()
        chosen_response = random.choice(responses)
        menu_df = pd.read_csv(MENU_FILE_PATH, delimiter='|')
        menu_response = "\n Here's our menu:\n" + menu_df.to_string(index=False)
        return chosen_response + menu_response, user_dict

    # Handle table booking
    if intent == 'reserve_table':
        entities = extract_all_entities(user_input)
        print(entities)
        for entity_text, entity_type in entities:
            if entity_type == 'DATE':
                user_dict['booking']['date'] = entity_text
            elif entity_type == 'TIME':
                user_dict['booking']['time'] = entity_text
            elif entity_type == 'CARDINAL':
                user_dict['booking']['people'] = entity_text

        missing_info = [info for info in ['date', 'time', 'people'] if not user_dict['booking'][info]]

        if missing_info:
            user_dict['focus'] = f'ask_for_{missing_info[0]}'
            response_query = df[df['Intent'] == user_dict['focus']]['Response'].tolist()
            chosen_response = random.choice(response_query)

        elif not missing_info:
            confirm_response = df[df['Intent'] == 'confirm']['Response'].tolist()
            chosen_response = random.choice(confirm_response).format(**user_dict['booking'])
            
        
            user_dict['pending_booking'] = user_dict['booking'].copy()
            user_dict['awaiting_confirmation'] = True
            return chosen_response + "\nIs this correct? Please confirm.", user_dict

    # Handle other intents
    responses = df[df['Intent'] == intent]['Response'].tolist()
    if responses:
        chosen_response = random.choice(responses)
        return chosen_response, user_dict
    else:
        return "Sorry, I didn't understand that.", user_dict




# Main loop for the chatbot interaction
if __name__ == "__main__":
    user_dict = {
    "name": "Guest",
    "booking": {
        "date": None,
        "time": None,
        "people": None
    },
    "awaiting_confirmation": False,
    "pending_booking": None,
    "pending_name": False,

    "admin_login": {
        "is_admin": False,
        "username": None,
        "awaiting_username": False,
        "awaiting_password": False
    }

}

    
 # Initialize context for conversatione
    while True:
        # Take user input    
        user_input = input(f"{user_dict['name']}: ")

        # Check if the user wants to exit
        if user_input.strip().lower() == 'exit':
            print("Exiting conversation. Goodbye!")
            break
        
        # Generate response based on user input
        response, user_dict = generate_response(user_input, user_dict)
        # Print the bot's response
        print("Restaurant Bot:", response)
        #print(user_dict)



