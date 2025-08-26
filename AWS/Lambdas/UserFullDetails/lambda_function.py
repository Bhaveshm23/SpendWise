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

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('UserBills')

    if 'queryStringParameters' not in event or not event['queryStringParameters']:
        return {
            'statusCode': 400,
            'body': json.dumps('Query parameters missing'),
            'headers': {'Content-Type': 'application/json'}
        }

    user_id = event['queryStringParameters'].get('user_id')
    if not user_id:
        return {
            'statusCode': 400,
            'body': json.dumps('user_id is missing in the query string'),
            'headers': {'Content-Type': 'application/json'}
        }

    try:
        response = table.query(
            KeyConditionExpression=Key('user_id').eq(user_id),
            ScanIndexForward=False,
            Limit=10
        )

        last_10_items = response.get('Items', [])

        return {
            'statusCode': 200,
            'body': json.dumps(last_10_items, cls=DecimalEncoder),
            'headers': {'Content-Type': 'application/json'}
        }

    except Exception as e:
        print(f"Error querying DynamoDB: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps('Internal Server Error'),
            'headers': {'Content-Type': 'application/json'}
        }