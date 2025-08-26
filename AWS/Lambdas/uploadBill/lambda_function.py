import json
import boto3
import base64

s3_client = boto3.client('s3')
BUCKET_NAME = '' #bill bucket name

def lambda_handler(event, context):
    try:
        # Determine if coming from API Gateway proxy
        if 'body' in event and 'user_id' not in event:
            # API Gateway: body is JSON string
            body = json.loads(event['body'])
        else:
            # Direct Lambda test: body is event dict
            body = event

        user_id = body['user_id']
        filename = body['filename']

        # Support both "file" (API) and "body" (older test)
        file_content_base64 = body.get('file') or body.get('body')
        if not file_content_base64:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing file content'})
            }

        file_content = base64.b64decode(file_content_base64)

        # Upload to S3
        s3_key = f"{user_id}/{filename}"
        s3_client.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=file_content)

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
