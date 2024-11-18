import json
import boto3
from boto3.dynamodb.conditions import Key
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime

def lambda_handler(event, context):
    print(event)
    # Extract values from the event
    date_range = event['date_range']
    user_id = event['user_id']
    user_email = event['user_email']
    user_name = event['user_name']
    start_date = event['start_date']
    end_date = event['end_date']
    print(user_id)
    print(start_date)
    print(end_date)
    
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('')  # Replace with your DynamoDB table name

    
    if start_date and end_date:
        response = table.scan(
            FilterExpression="user_id = :uid and #date between :start_date and :end_date",
            ExpressionAttributeValues={
                ":uid": user_id,
                ":start_date": start_date,
                ":end_date": end_date
            },
            ExpressionAttributeNames={
                "#date": "date"
            }
        )

        # Extract items from the response
        items = response.get('Items', [])
        
        # Prepare CSV data with headers
        headers = items[0].keys() if items else []
        csv_data = '\n'.join([','.join(headers)] + [','.join(map(str, item.values())) for item in items])
        

        print(csv_data)
        
        # Create a MIME multipart message
        msg = MIMEMultipart()
        msg['Subject'] = 'Your Spend Analysis '
        msg['From'] = 'bhaveshmotiramani97@gmail.com' 
        msg['To'] = user_email
        
        # Add a text part to the email body
        hi_message = f"Hi {user_name},\n"
        date_range_text = f"Your requested data from {start_date} to {end_date}  is attached as csv file in this mail. \n \n"
        text_part = MIMEText(hi_message + date_range_text)
        msg.attach(text_part)
        # msg.pep() -> commented 

        # Add CSV data as an attachment
        part = MIMEApplication(csv_data)
        part.add_header('Content-Disposition', 'attachment', filename=f"data_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv")
        msg.attach(part)

        # Send the email with SES
        ses_client = boto3.client('ses')
        ses_response = ses_client.send_raw_email(
            Source=msg['From'],
            Destinations=[msg['To']],
            RawMessage={'Data': msg.as_string()}
        )
        print(ses_response)
        
        # Prepare the response
        response_body = {
            'statusCode': 200,
            'body': json.dumps(items)
        }

        return response_body
    else:
        # Handle the case where start_date or end_date is missing
        return {
            'statusCode': 400,
            'body': json.dumps('Both start_date and end_date are required for date range queries.')
        }
        