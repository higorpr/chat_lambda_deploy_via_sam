from requests import Response
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.utilities.typing import LambdaContext

from functions import (
    import_data,
    message_cleanup,
    chat_classification,
    generate_weighted_df,
    calculate_chat_sentiment_coef,
    generate_sentiment_label,
)

app = APIGatewayRestResolver()


@app.get("/chat/<chat_id>")
def hello_name(chat_id):
    # Create messages dataframe:
    messages_df = import_data(chat_id)

    # Reorder messages by send date:
    messages_df.sort_values(by=["send_date"], inplace=True)

    ## Data Processing ##

    # Remove non-client data:
    client_messages_df = message_cleanup(messages_df)

    ## Model Application ##

    # Apply LeIA model:
    classified_messages_df = chat_classification(client_messages_df)

    ## Chat Sentiment Coefficient Calculation ##

    # Calculate messages' weights:
    weighted_df = generate_weighted_df(classified_messages_df)

    # Generate whole chat sentiment:
    coefficient = calculate_chat_sentiment_coef(weighted_df)

    sat_label = generate_sentiment_label(coefficient)

    return {
        'statusCode':200,
        'body': f'The satisfaction label for the calculated coefficient is "{sat_label}".'
    }

def lambda_handler(event:dict, context:LambdaContext) -> dict:
    return app.resolve(event, context)
