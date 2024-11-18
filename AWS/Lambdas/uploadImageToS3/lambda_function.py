# Lambda Function (lambda_function.py)
import boto3
import json
import base64
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    s3_client = boto3.client('s3')
    bucket_name = ''
    
    print(f'Raw event: {event}')
    
    # Handle both direct JSON and API Gateway event formats
    if isinstance(event, str):
        try:
            body = json.loads(event)
        except json.JSONDecodeError:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid JSON in request body'})
            }
    else:
        # API Gateway format
        try:
            if isinstance(event.get('body'), str):
                body = json.loads(event['body'])
            else:
                body = event.get('body', {})
        except (AttributeError, json.JSONDecodeError):
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid request format'})
            }
    
    print(f'Parsed body: {body}')
    
    # Extract required fields
    user_name = body.get('user_name')
    image_data = body.get('image_data')
    content_type = body.get('content_type')
    
    print(f'User name: {user_name}')
    print(f'Content type: {content_type}')
    
    if not all([user_name, image_data, content_type]):
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing required fields: user_name, image_data, or content_type'})
        }

    try:
        # Handle base64 data with or without data URI prefix
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        # Decode base64 string to bytes
        image_bytes = base64.b64decode(image_data)
        
        # Determine file extension
        extension_map = {
            'image/jpeg': 'jpeg',
            'image/png': 'png',
            'image/jpg': 'jpg'
        }
        
        extension = extension_map.get(content_type)
        if not extension:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Unsupported file type'})
            }

        object_key = f'user_profiles/{user_name}.{extension}'
        print(f"Uploading image to S3 with key: {object_key}")

        # Check if object exists (optional)
        try:
            s3_client.head_object(Bucket=bucket_name, Key=object_key)
            print(f"Image for {user_name} already exists, replacing it.")
        except ClientError:
            print(f"Image for {user_name} does not exist, uploading new image.")
        
        # Upload to S3
        s3_client.put_object(
            Bucket=bucket_name,
            Key=object_key,
            Body=image_bytes,  #
            ContentType=content_type
        )
        
        image_url = f'https://{bucket_name}.s3.amazonaws.com/{object_key}'
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',  # Configure as needed
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'message': 'Image uploaded successfully',
                'url': image_url
            })
        }
    except Exception as e:
        print(f"Error processing image: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Error processing image: {str(e)}'})
        }

