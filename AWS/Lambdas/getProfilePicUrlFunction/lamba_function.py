
import boto3
import json
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    s3_client = boto3.client('s3')
    bucket_name = 'finance-user-image-2024'

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
            # Check if the object exists
            s3_client.head_object(Bucket=bucket_name, Key=object_key)

            # Generate a pre-signed URL
            url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket_name, 'Key': object_key},
                ExpiresIn=3600  # URL expires in 1 hour
            )

            return {
                'statusCode': 200,
                'body': json.dumps({'exists': True, 'url': url})
            }
        except ClientError:
            continue

    # No image found
    return {
        'statusCode': 404,
        'body': json.dumps({'exists': False, 'url': ''})
    }
