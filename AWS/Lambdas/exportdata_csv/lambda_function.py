import json
import boto3
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime

def lambda_handler(event, context):
    print("Raw event:", event)

    # If called from API Gateway proxy, the body is a JSON string
    if "body" in event:
        body = json.loads(event["body"])
    else:
        body = event  # direct Lambda test

    # Extract values
    date_range = body['date_range']
    user_id = body['user_id']
    user_email = body['user_email']
    user_name = body['user_name']
    start_date = body['start_date']
    end_date = body['end_date']

    print("User:", user_id, "From:", start_date, "To:", end_date)

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('User')  # DynamoDB table

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
        items = response.get('Items', [])
        headers = items[0].keys() if items else []
        csv_data = '\n'.join([','.join(headers)] + [','.join(map(str, item.values())) for item in items])

        # Email creation (same as before) ...

        return {
            "statusCode": 200,
            "body": json.dumps(items)
        }
    else:
        return {
            "statusCode": 400,
            "body": json.dumps("Both start_date and end_date are required for date range queries.")
        }
