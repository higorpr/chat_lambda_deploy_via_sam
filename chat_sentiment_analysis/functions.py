import pandas as pd
import emoji

from errors import CustomException
from bson.objectid import ObjectId
from LeIA import SentimentIntensityAnalyzer as LeiaAnalyzer
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer as EmojiAnalyzer
from connection import messages_db, chats_db

def chat_id_verification(chat_id:str):
    inexistant_chat_exception = CustomException('Inexistant chat_id')

    try:
        chat_check = chats_db.find_one({
            "_id": ObjectId(chat_id)
        })
        
        if chat_check == None:
            raise inexistant_chat_exception
    except Exception as e:
        print(e)
        raise inexistant_chat_exception

def get_chat_messages(chat_id:str):
    messages = []
    query = {
        "chat":ObjectId(chat_id),
        "type":"chat",
        "text":{"$exists":"true"},
    }
    try:
        messages = messages_db.find(query).sort("send_date",1)
        messages = list(messages)
        
        if len(messages) == 0:
            raise CustomException('Void chat history')

    except Exception as e:
        raise e

    return messages

def import_data(chat_id:str):
    order = 1

    chat_id_verification(chat_id)

    messages = get_chat_messages(chat_id)

    messages_dict = {'id':[],'text':[],'source':[], 'send_date':[],"order_in_chat":[]}

    for m in messages:
        # Get message id
        messages_dict['id'].append(m['_id'])

        # Get message source
        if m['is_out']:
            messages_dict['source'].append('A')
            # Add order in chat sequence for Attendant:
            messages_dict['order_in_chat'].append('NA')
        else:
            messages_dict['source'].append('C')
            # Add order in chat sequence for Client:
            messages_dict['order_in_chat'].append(order)
            order += 1
        
        # Get message text
        messages_dict['text'].append(m['text'])

        # Get message datetime
        messages_dict['send_date'].append(m['timestamp'])

    
    messages_df = pd.DataFrame(data=messages_dict)

    return messages_df

def message_cleanup(messages_df):
    cleaned_messages_df = messages_df[messages_df['source'] == 'C']
    cleaned_messages_df.reset_index(drop=True,inplace=True)

    return cleaned_messages_df

# Function to normalize LeIA compounds:
def extract_leia_sentiment(compound):
    sent_output = {'label':'', 'new_score':0}    
    
    sent_output['new_score'] = (compound + 1) / 2
    
    if compound == 0:
        sent_output['label'] = 0
    elif compound > 0.2:
        sent_output['label'] = 2
    elif compound > 0:
        sent_output['label'] = 1
    elif compound >= -0.2 :
        sent_output['label'] = -1
    else:
        sent_output['label'] = -2
        
    return sent_output

def split_message_sections(message:str):
    emoji_list = emoji.emoji_list(message)
    emojis = ''
    text = message
    
    # Case where the message does not have emojis
    if len(emoji_list) == 0:
        return {"text":text, "emojis":emojis}
        

    for e in emoji_list:
        # Add emoji to emoji list
        emojis += e['emoji']

        # Remove emoji from text
        text = text.replace(e['emoji'], '')
    
    return {"text":text, "emojis":emojis}

def get_message_compound(message:str) -> float:
    leia = LeiaAnalyzer()
    vader = EmojiAnalyzer()

    split_message = split_message_sections(message)
    
    # Get text message compound
    text_compound = leia.polarity_scores(split_message["text"])['compound']
    
    # Get emojis compound
    emoji_compound = vader.polarity_scores(split_message["emojis"])['compound']

    message_compound = round((text_compound + 2*emoji_compound)/3,4)

    return message_compound

# LeIA Method Function
def chat_classification(messages_df):
    
    # Verificação de emojis
    
    # Apply leia classifier
    classified_df = messages_df.assign(
    score=messages_df['text'].apply(lambda x: get_message_compound(x)))
    
    # Generate labels and normalized classification score
    classified_df = classified_df.assign(
        classification_score = classified_df['score'].apply(lambda x: extract_leia_sentiment(x)['new_score']),
        classification_label = classified_df['score'].apply(lambda x: extract_leia_sentiment(x)['label']),
    )
    
    # Remove unecessary columns
    classified_df.drop(columns=['score', 'source'],inplace=True)
    
    return classified_df

# Function to calculate individual message weight:
def calculate_weight(order:int, n_messages:int):
    if n_messages < 1 :
        raise Exception('There should be at least one message to be analyzed')
    den = 0
    for i in range(1, n_messages + 1):
        den += i**2
    w = (order**2) / den
    
    return w

# Function to generate a dataframe with weighted messages:
def generate_weighted_df(df:pd.DataFrame):
    n_messages = df.shape[0]
    df = df.assign(
        message_weight = df.apply(lambda x: calculate_weight(x['order_in_chat'],n_messages), axis=1)
    )
    
    return df

# Function to calculate chat sentiment based on message weights and classification score
def calculate_chat_sentiment_coef(df):
    num = 0
    den = 0
    for idx, row in df.iterrows():
        num += row['classification_label'] * row['message_weight']
        den += row['message_weight']
    coef = num / den
    return coef

# Function to generate the satisfaction label of the chat:
def generate_sentiment_label(coef:float):
    label = ''
    if coef > 2 or coef <-2:
        return 'Houve um erro, por favor entre em contato com o suporte da ChatGuru'
    
    if coef <= -1:
        label = 'Insatisfeito'        
    elif coef < -0.2:
        label = 'Levemente Insatisfeito'
    elif coef <= 0.2:
        label = 'Neutro'
    elif coef < 1:
        label = 'Levemente Satisfeito'
    else:
        label = 'Satisfeito'
    
    return label