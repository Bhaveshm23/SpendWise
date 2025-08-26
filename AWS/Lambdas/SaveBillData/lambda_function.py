import boto3
import json
from datetime import datetime
from decimal import Decimal


def lambda_handler(event, context):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('UserBills')  # Your DynamoDB table name

    # Parse incoming data
    data = json.loads(event['body'],  parse_float=Decimal)
    user_id = data['user_id']
    # Generate a timestamp for sorting
    timestamp = datetime.now().isoformat()
    date = data['date']
    total_amount = data['totalAmount']
    category = data['category']
    s3_url = data['s3_url']

    print(user_id, timestamp, date, total_amount, category, s3_url)
    # Save data to DynamoDB
    table.put_item(Item={
        'user_id': user_id,
        'timestamp': timestamp,
        'date': date,
        'totalAmount': total_amount,
        'category': category,
        's3_url': s3_url
    })

    return {
        'statusCode': 200,
        'body': json.dumps('Data saved successfully')
    }
