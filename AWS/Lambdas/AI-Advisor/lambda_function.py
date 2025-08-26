import boto3
import json
import re
from boto3.dynamodb.conditions import Key
from decimal import Decimal
from collections import defaultdict

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o) if o % 1 > 0 else int(o)
        return super().default(o)

def lambda_handler(event, context):
    print("Received event:", json.dumps(event))

    # Initialize DynamoDB and Bedrock clients
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('UserBills')
    bedrock = boto3.client('bedrock-runtime', region_name='us-east-2')

    user_id = event.get("user_id")
    if not user_id:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'user_id is missing'})
        }

    try:
        # Query all transactions for the user
        response = table.query(
            KeyConditionExpression=Key('user_id').eq(user_id),
            ScanIndexForward=True
        )
        transactions = response.get('Items', [])

        # Aggregate data
        category_totals = defaultdict(float)
        monthly_totals = defaultdict(float)
        for entry in transactions:
            category_totals[entry.get('category', 'Unknown')] += float(entry.get('totalAmount', 0))
            year_month = entry.get('date', '')[:7]
            monthly_totals[year_month] += float(entry.get('totalAmount', 0))

        # Prepare Bedrock prompt
        prompt = f"""
            You are a financial advisor. Analyze the following user spending data:
            - Categories: {json.dumps(dict(category_totals))}
            - Monthly totals (last 12 months): {json.dumps(dict(monthly_totals))}
            Provide 3-5 personalized financial recommendations in plain English, such as budgeting tips or savings goals. Return only a JSON array of strings.
            Example: ["Reduce dining out by 20% to save $50/month", "Set a savings goal of $200/month"]
            """

        
        
        bedrock_response = bedrock.invoke_model(
            modelId='arn:aws:bedrock:us-east-2:394691794226:inference-profile/us.meta.llama3-1-8b-instruct-v1:0',
            contentType='application/json',
            accept='application/json',
            body=json.dumps({
                'prompt': f"\n\nHuman: {prompt}\n\nAssistant: []",
                'max_gen_len': 500,
                'temperature': 0.7
            })
        )

        resp_body = json.loads(bedrock_response['body'].read())
        print("Bedrock raw response:", resp_body)  

        generated_text = resp_body.get("generation", "[]")  # every model has diff type of get
        json_match = re.search(r'\[\s*(".*?"\s*(?:,\s*".*?"\s*)*)\]', generated_text) # since it can't parse '# (markdown)'
        recommendations = json.loads(json_match.group(0)) if json_match else []
        print("Extracted recommendations:", recommendations)

        return {
            'statusCode': 200,
            'body': json.dumps({
                'transactions': transactions,
                'recommendations': recommendations
            }, cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Error processing request: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
