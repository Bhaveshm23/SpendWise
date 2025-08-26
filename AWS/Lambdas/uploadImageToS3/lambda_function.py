import boto3
import json
import base64
from botocore.exceptions import ClientError

def lambda_handler(event, context):
    s3_client = boto3.client('s3')
    bucket_name = ''

    print(f'Raw event: {event}')
    
    # Determine if event came from API Gateway or direct Lambda test
    if 'body' in event:
        try:
            body = json.loads(event['body'])
        except (TypeError, json.JSONDecodeError) as e:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': f'Invalid JSON in body: {str(e)}'})
            }
    else:
        # Direct Lambda test event
        body = event

    # Extract required fields
    user_id = body.get('user_id')
    image_data = body.get('image_data')
    content_type = body.get('content_type')

    if not all([user_id, image_data, content_type]):
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing required fields: user_id, image_data, or content_type'})
        }

    try:
        if ',' in image_data:
            image_data = image_data.split(',')[1]

        image_bytes = base64.b64decode(image_data)

        extension_map = {'image/jpeg': 'jpeg', 'image/png': 'png', 'image/jpg': 'jpg'}
        extension = extension_map.get(content_type)
        if not extension:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Unsupported file type'})
            }

        object_key = f'user_profiles/{user_id}.{extension}'
        print(f"Uploading image to S3 with key: {object_key}")

        s3_client.put_object(Bucket=bucket_name, Key=object_key, Body=image_bytes, ContentType=content_type)

        image_url = f'https://{bucket_name}.s3.amazonaws.com/{object_key}'
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'message': 'Image uploaded successfully', 'url': image_url})
        }

    except Exception as e:
        return {'statusCode': 500, 'body': json.dumps({'error': f'Error processing image: {str(e)}'})}
