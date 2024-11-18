import boto3
from boto3.dynamodb.conditions import Key
import json
from decimal import Decimal

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)

def lambda_handler(event, context):
    print("Received event:", event)
    print("Full Event Object: ", json.dumps(event))

    
    # Initialize DynamoDB resource
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('UserBills')  # Your DynamoDB table name

    # Extract user_id from query parameters
    if 'queryStringParameters' in event and event['queryStringParameters']:
        user_id = event['queryStringParameters'].get('user_id')
        if not user_id:
            return {
                'statusCode': 400,
                'body': json.dumps('user_id is missing in the query string')
            }
    else:
        return {
            'statusCode': 400,
            'body': json.dumps('Query parameters missing')
        }

    # Query DynamoDB to get the last 10 items for the user
    try:
        response = table.query(
            KeyConditionExpression=Key('user_id').eq(user_id),
            ScanIndexForward=False,  # Set to False for descending order (to get the latest first)
        )

        # Extract the last 10 items
        last_10_items = response.get('Items', [])

        # Prepare the response using the custom encoder
        response_body = {
            'statusCode': 200,
            'body': json.dumps(last_10_items, cls=DecimalEncoder)
        }

        return response_body

    except Exception as e:
        print(f"Error querying DynamoDB: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps('Internal Server Error')
        }
