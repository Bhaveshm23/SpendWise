import json
import boto3
import base64

# Initialize the S3 client
s3_client = boto3.client('s3')
BUCKET_NAME = ''  # Your S3 bucket name

def lambda_handler(event, context):
    try:
        # Extract data from the event
        user_id = event['user_id']
        filename = event['filename']
        file_content_base64 = event['body']
        
        # Decode the base64 content
        file_content = base64.b64decode(file_content_base64)
        
        # Define the S3 path
        s3_key = f"{user_id}/{filename}"
        
        # Upload to S3
        s3_client.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=file_content)
        
        # Return the S3 URL
        s3_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
        return {
            'statusCode': 200,
            'body': json.dumps({'s3_url': s3_url})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
