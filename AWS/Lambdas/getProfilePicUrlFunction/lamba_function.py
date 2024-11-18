import boto3
import json
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    s3_client = boto3.client('s3')
    bucket_name = ''

    # Extract `user_id` from pathParameters
    user_id = event.get('pathParameters', {}).get('user_id')
    if not user_id:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing user_id in path parameters'})
        }

    file_extensions = ['jpeg', 'jpg', 'png']
    for ext in file_extensions:
        object_key = f'user_profiles/{user_id}.{ext}'
        try:
            s3_client.head_object(Bucket=bucket_name, Key=object_key)
            image_url = f'https://{bucket_name}.s3.us-east-1.amazonaws.com/{object_key}'
            return {
                'statusCode': 200,
                'body': json.dumps({'exists': True, 'url': image_url})
            }
        except ClientError:
            continue

    # No image found
    return {
        'statusCode': 404,
        'body': json.dumps({'exists': False, 'url': ''})
    }