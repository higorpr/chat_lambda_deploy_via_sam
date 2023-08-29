# import os
import os
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.utilities.typing import LambdaContext

from functions import (
    chat_id_verification,
    get_chat_messages,
    import_data,
    message_cleanup,
    chat_classification,
    generate_weighted_df,
    calculate_chat_sentiment_coef,
    generate_sentiment_label,
    format_chat,
    create_report,
    update_file_to_s3
)

app = APIGatewayRestResolver()


@app.get("/chat/<chat_id>")
def hello_name(chat_id):
    # Check chat id:
    chat_id_verification(chat_id)
    
    #Retrieve messages:
    messages = get_chat_messages(chat_id)
    
    # Create messages dataframe:
    messages_df = import_data(messages)

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
    
    try:
        # Format Chat Messages
        formated_chat = format_chat(messages)
        # Create pdf byte file
        pdf_buffer = create_report(formated_chat,coefficient)
        
        # # S3 Variables    
        s3_bucket = os.environ['BucketName']
        s3_path = f'report/sentiment_analysis_report-{chat_id}.pdf'
        
        # # Upload data to S3
        update_file_to_s3(pdf_buffer,s3_bucket,s3_path)
    except Exception as e:
        raise e

    return {
        'statusCode':200,
        'body': f'The satisfaction label for the calculated coefficient is "{sat_label}".'
    }

def lambda_handler(event:dict, context:LambdaContext) -> dict:
    return app.resolve(event, context)
