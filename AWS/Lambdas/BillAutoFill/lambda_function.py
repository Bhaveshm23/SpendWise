import boto3
import json
import re
from urllib.parse import urlparse

textract = boto3.client('textract')

def lambda_handler(event, context):
    try:
        print(f"Full event: {json.dumps(event)}")

        # Find if coming from API Gateway proxy
        if 'body' in event and 'user_id' not in event:
            # API Gateway: body is JSON string
            body = json.loads(event['body'])
        else:
            # Direct Lambda test: body is event dict
            body = event

        s3_url = body['s3_url']
        user_id = body['user_id']
        
        if not s3_url or not user_id:
            return {"statusCode": 400, "body": json.dumps({"success": False, "error": "Missing parameters"})}
        
        # Extract bucket & key from S3 URL
        parsed_url = urlparse(s3_url)
        bucket = parsed_url.netloc.split('.')[0]
        key = parsed_url.path.lstrip('/')
        
        # Call Textract
        response = textract.detect_document_text(
            Document={'S3Object': {'Bucket': bucket, 'Name': key}}
        )
        
        lines = [block['Text'] for block in response['Blocks'] if block['BlockType'] == 'LINE']
        
        # Extract date - multiple formats
        date = None
        date_patterns = [
            r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',     # YYYY-MM-DD or YYYY/M/D
            r'(\d{1,2}[-/]\d{1,2}[-/]\d{4})',     # MM-DD-YYYY or M/D/YYYY  
            r'(\d{1,2}[-/]\d{1,2}[-/]\d{2})',     # MM-DD-YY or M/D/YY
        ]
        
        for line in lines:
            for pattern in date_patterns:
                match = re.search(pattern, line)
                if match:
                    date_str = match.group(1).replace('/', '-')
                    parts = date_str.split('-')
                    if len(parts[0]) == 4:  # YYYY-MM-DD format
                        date = f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
                    elif len(parts[2]) == 2:  # MM-DD-YY format
                        date = f"20{parts[2]}-{parts[0].zfill(2)}-{parts[1].zfill(2)}"
                    else:  # MM-DD-YYYY format
                        date = f"{parts[2]}-{parts[0].zfill(2)}-{parts[1].zfill(2)}"
                    break
            if date:
                break

        amount = None
        total_words = ['total', 'subtotal', 'amount due', 'balance', 'grand total', 'amount payable']
        money_pattern = r'\b\d{1,3}(?:,\d{3})*(?:\.\d{2})\b'  

        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(word in line_lower for word in total_words):
                # Check current line
                money_matches = re.findall(money_pattern, line_lower)
                print(money_matches)
                if money_matches:
                    clean_amounts = [float(m.replace(',', '')) for m in money_matches]
                    amount = max(clean_amounts)
                    print(amount)
                    break
                # Check next line
                if (i + 1) < len(lines):
                    next_line = lines[i + 1].lower()
                    money_matches = re.findall(money_pattern, next_line)
                    if money_matches:
                        clean_amounts = [float(m.replace(',', '')) for m in money_matches]
                        amount = max(clean_amounts)
                        break

        #  If amount is not found Look for largest reasonable amount in last 10 lines
        if amount is None:
            money_matches = []
            for line in reversed(lines[-10:]):
                money_matches.extend(re.findall(money_pattern, line.lower()))
            if money_matches:
                clean_amounts = [float(m.replace(',', '')) for m in money_matches]
                valid_amounts = [amt for amt in clean_amounts if 10 <= amt <= 10000]  
                amount = max(valid_amounts) if valid_amounts else None

        amount = str(amount) if amount is not None else None

        all_text = ' '.join(lines).lower()
        print(all_text)
        category = "miscellaneous"
        grocery_keywords = ['produce', 'deli', 'grocery', 'market', 'food', 'fruits', 'vegetables']
        if any(word in all_text for word in grocery_keywords):
            category = "groceries/food"
        elif any(word in all_text for word in ['restaurant', 'cafe', 'dining']):
            category = "dining"
        elif any(word in all_text for word in ['gas', 'fuel', 'shell', 'exxon']):
            category = "transportation"
        elif any(word in all_text for word in ['pharmacy', 'shoppers drug mart', 'lawtons']):
            category = "healthcare"
        elif any(word in all_text for word in ['clothing', 'shoes', 'jewelry', 'accessories']):
            category = "clothing"
        elif any(word in all_text for word in ['electronics', 'computer', 'software', 'hardware']):
            category = "electronics"
        elif any(word in all_text for word in ['entertainment', 'movie', 'music', 'game', 'streaming']):
            category = "entertainment"
        elif any(word in all_text for word in ['home', 'furniture', 'appliances', 'tools']):
            category = "home"
        elif any(word in all_text for word in ['travel', 'airline', 'hotel', 'rental']):
            category = "travel"
        elif any(word in all_text for word in ['education', 'school', 'tuition']):
            category = "education"
        elif any(word in all_text for word in ['utilities', 'water', 'gas', 'electricity']):
            category = "utilities"
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "success": True,
                "date": date,
                "totalAmount": amount,
                "category": category
            })
        }
        
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"success": False, "error": str(e)})}