# utils.py
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
import pandas as pd
import nltk
from nltk import word_tokenize, pos_tag, ne_chunk
from nltk.tree import Tree
import numpy as np 
from sklearn.feature_extraction.text import TfidfVectorizer
import pickle
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')
nltk.download('maxent_ne_chunker')
nltk.download('words')
import re
INTENT_FILE_PATH =  'intents.csv'

def train_intent_model():
    """
    Train the intent classification model using RandomForestClassifier on the intents dataset.

    Returns:
    tuple: The trained TfidfVectorizer and RandomForestClassifier model.
    """
    df = pd.read_csv(INTENT_FILE_PATH, delimiter='|')

    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(df['User Input'])
    y = df['Intent']

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, y)
    # Save the model and vectorizer
    with open('model.pkl', 'wb') as model_file:
        pickle.dump(model, model_file)
    with open('vectorizer.pkl', 'wb') as vectorizer_file:
        pickle.dump(vectorizer, vectorizer_file)

    return vectorizer, model

def extract_date_entities(text):
    # Regex patterns for date
    date_patterns = [
        r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',  # Matches dates like 01/01/2023, 01-01-23
        r'\b\d{1,2}\s(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\b',  # Matches dates like 13 January, 01 Feb
        r'\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s\d{1,2}(?:st|nd|rd|th)?\b',  # Matches dates like January 13, Dec 12th
        r'\b(?:tomorrow|yesterday|today|next week|next month|next year)\b', r'\b\d{1,2}[./ ]\d{1,2}[./ ]\d{4}\b', 
r'\bthe\s\d{1,2}(?:st|nd|rd|th)?\sof\s(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?),?\s\d{4}\b',
r'\b\d{1,2}(?:st|nd|rd|th)?\s(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\b',
r'\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s\d{1,2}(?:st|nd|rd|th)?\b'


# Add more patterns as needed
    ]
    dates = []
    for pattern in date_patterns:
        matches = re.findall(pattern, text)
        dates.extend([(match, 'DATE') for match in matches])
    return dates

import re

def extract_time_entities(text):
    # Regex patterns for time
    time_patterns = [
        r'\b\d{1,2}(?::\d{2})?\s?(AM|PM|am|pm)?\b',  # Matches times like 3pm, 12:30, 3:45 PM, 3 PM
        r'\b(?:morning|afternoon|evening|night|noon)\b'   # Matches words like morning, afternoon, evening, night
    ]
    
    times = []
    for pattern in time_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        times.extend([(match.group(), 'TIME') for match in matches])
    
    return times



def extract_cardinal_entities(text):
    # Regex pattern for cardinal numbers (both numeric and word forms)
    cardinal_pattern = r'\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b'
    cardinals = [(match.group(), 'CARDINAL') for match in re.finditer(cardinal_pattern, text, re.IGNORECASE)]
    return cardinals


def extract_nltk_entities(text):
    """
    Extract named entities using NLTK's NER capabilities, focusing on 'PERSON'.

    Parameters:
    text (str): The text from which to extract entities.

    Returns:
    list of tuples: A list of 'PERSON' entities found in the text, each represented as a tuple of (text, label).
    """
    entities = []
    for chunk in ne_chunk(pos_tag(word_tokenize(text))):
        if isinstance(chunk, Tree) and chunk.label() == 'PERSON':
            entities.append((' '.join(c[0] for c in chunk), 'PERSON'))
    return entities

def extract_all_entities(text):
    """
    Extract various named entities (including PERSON, DATE, TIME, CARDINAL) from text using NLTK and regex.

    Parameters:
    text (str): The text from which to extract entities.

    Returns:
    list of tuples: A list of entities found in the text, each represented as a tuple of (text, label).
    """
    # Extract PERSON entities using NLTK
    nltk_entities = extract_nltk_entities(text)

    # Extract DATE, TIME, CARDINAL entities using regex
    date_entities = extract_date_entities(text)
    time_entities = extract_time_entities(text)
    cardinal_entities = extract_cardinal_entities(text)

    # Combine all extracted entities
    all_entities = nltk_entities + date_entities + time_entities + cardinal_entities
    return all_entities



def get_intent(user_input, vectorizer, model):
    """
    Predict the intent of the user input using the trained model and vectorizer.

    Parameters:
    user_input (str): The user's input text.
    vectorizer (TfidfVectorizer): The TfidfVectorizer used for transforming text data.
    model (RandomForestClassifier): The trained RandomForestClassifier model for intent prediction.

    Returns:
    str: The predicted intent of the user input.
    """
    # Vectorize user input
    vectorized_input = vectorizer.transform([user_input])
    # Predict the intent
    predicted_intent = model.predict(vectorized_input)
    return predicted_intent[0]

def load_intent_model():
    """
    Load the pre-trained intent classification model and vectorizer from disk.

    Returns:
    tuple: The loaded TfidfVectorizer and RandomForestClassifier model.
    """
    # Load the model and vectorizer
    with open(r'model.pkl', 'rb') as model_file:
        model = pickle.load(model_file)
    with open(r'vectorizer.pkl', 'rb') as vectorizer_file:
        vectorizer = pickle.load(vectorizer_file)

    return vectorizer, model


