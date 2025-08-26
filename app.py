from flask import Flask, redirect, request, render_template, url_for, session, jsonify
from authlib.integrations.flask_client import OAuth
import boto3, requests
import base64
import json
import jwt
from jinja2 import Environment, FileSystemLoader
from collections import defaultdict
from flask import flash
from datetime import datetime, timedelta
from botocore.exceptions import ClientError
from dateutil.relativedelta import relativedelta 
import os
from decouple import config  

app = Flask(__name__)
app.secret_key = os.urandom(24)  
oauth = OAuth(app)

COGNITO_USER_POOL_ID = config('COGNITO_USER_POOL_ID')
COGNITO_APP_CLIENT_ID = config('COGNITO_APP_CLIENT_ID')
COGNITO_APP_CLIENT_SECRET = config('COGNITO_APP_CLIENT_SECRET')
COGNITO_REGION = config('COGNITO_REGION')
COGNITO_DOMAIN = config('COGNITO_DOMAIN')
REDIRECT_URI = config('REDIRECT_URI')
API_GATEWAY_BASE_URL = config('API_GATEWAY_BASE_URL')
BUCKET_NAME = config('BUCKET_NAME')

# API Gateway Endpoints (derived from BASE_URL)
API_GATEWAY_UPLOAD_ENDPOINT = f"{API_GATEWAY_BASE_URL}/upload"
API_GATEWAY_AUTOFILL_ENDPOINT = f"{API_GATEWAY_BASE_URL}/autofill"
API_GATEWAY_SAVEBILL_ENDPOINT = f"{API_GATEWAY_BASE_URL}/savebill"
API_GATEWAY_UPLOADIMAGE_ENDPOINT = f"{API_GATEWAY_BASE_URL}/uploadImage"
API_GATEWAY_UPDATE_USER_PREF_ENDPOINT = f"{API_GATEWAY_BASE_URL}/updateUserPref"
API_GATEWAY_GET_PROFILE_PIC_URL_ENDPOINT = f"{API_GATEWAY_BASE_URL}/getProfilePicUrl"

# Configure authlib OAuth client
oauth.register(
    name='cognito',
    authority=f'https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}',
    client_id=COGNITO_APP_CLIENT_ID,
    client_secret=COGNITO_APP_CLIENT_SECRET,
    server_metadata_url=f'https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}/.well-known/openid-configuration',
    client_kwargs={'scope': 'email openid phone'}
)

def is_authenticated():
    return 'user' in session

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signin')
def signin():
    print(f"Inside SignIn")
    return oauth.cognito.authorize_redirect(REDIRECT_URI)

@app.route('/authorize')
def authorize():
    print("Entering /authorize route")
    try:
        token = oauth.cognito.authorize_access_token()
        user = token['userinfo']
        session['user'] = user
        session['access_token'] = token['access_token']
        session['refresh_token'] = token['refresh_token']
        print(f"User: {user}")
        return redirect(url_for('home'))
    except Exception as e:
        print(f"Authentication error: {e}")
        app.logger.error(f"Authentication error: {e}")
        return render_template('error.html', error_message="Authentication failed. Please try again.")

def parse_api_response(response):
    """Parse API response, expecting {"statusCode": <code>, "body": "<json_string>"}, with fallback for lists."""
    print(f"API response: {response.text}")  # Debug
    if response.status_code == 200:
        try:
            api_data = response.json()
            if isinstance(api_data, list):
                print("Warning: Received unexpected list response, treating as body")
                return api_data  # Fallback for list
            return json.loads(api_data.get('body', '[]'))
        except (json.JSONDecodeError, TypeError) as e:
            print(f"Error parsing API response: {e}")
            return []
    else:
        print(f"API error: {response.status_code} - {response.text}")
        return []

@app.route('/home')
def home():
    if not is_authenticated():
        return redirect(url_for('signin'))

    user = session['user']
    print(f"User in home route:{user}")
    api_url = f"{API_GATEWAY_BASE_URL}/home/lasttendays"
    response = requests.get(api_url, params={'user_id': user['sub']})
    transactions = parse_api_response(response)
    total_amount = sum(float(entry.get('totalAmount', 0)) for entry in transactions)
    return render_template('home.html', user_id=user['sub'], user_name=user.get('cognito:username', 'User'), user_email=user['email'], transactions=transactions, total_amount=total_amount)
    

@app.route('/uploadbill')
def uploadbill():
    if not is_authenticated():
        return redirect(url_for('signin'))
    user = session['user']
    return render_template('uploadbill.html', user_id=user['sub'])

@app.route('/analytics')
def analytics():
    if not is_authenticated():
        return redirect(url_for('signin'))
    
    user = session['user']
    api_url = f"{API_GATEWAY_BASE_URL}/home/UserFullDetailsApi"
    response = requests.get(api_url, params={'user_id': user['sub']})
    transactions = parse_api_response(response)

    #fetch recommendations from AI-advisor
    advisor_url = f"{API_GATEWAY_BASE_URL}/home/advisor"
    advisor_response = requests.post(advisor_url, json={'user_id': user['sub']})
    advisor_data = parse_api_response(advisor_response)
    recommendations = advisor_data.get('recommendations', [])

    total_amount_sum = sum(float(entry.get('totalAmount', 0)) for entry in transactions)
    category_totals = defaultdict(float)
    for entry in transactions:
        category_totals[entry.get('category', 'Unknown')] += float(entry.get('totalAmount', 0))
    pie_chart_data = [{'category': category, 'totalAmount': total} for category, total in category_totals.items()]
    pie_chart_data = sorted(pie_chart_data, key=lambda x: x['category'].lower())

    sorted_transactions = sorted(transactions, key=lambda x: x.get('date', ''))
    last_30_days_data = [
        entry for entry in sorted_transactions
        if 'date' in entry and datetime.now() - datetime.strptime(entry['date'], '%Y-%m-%d') <= timedelta(days=30)
    ]
    date_totals = defaultdict(float)
    for entry in last_30_days_data:
        date_totals[entry['date']] += float(entry.get('totalAmount', 0))
    line_chart_data_30_days = {
        'labels': list(date_totals.keys()),
        'data': list(date_totals.values())
    }

    last_12_months_data = [
        entry for entry in sorted_transactions
        if 'date' in entry and datetime.now() - datetime.strptime(entry['date'], '%Y-%m-%d') <= timedelta(days=365)
    ]
    month_totals = defaultdict(float)
    for entry in last_12_months_data:
        try:
            year_month = entry['date'][:7]
            month_totals[year_month] += float(entry.get('totalAmount', 0))
        except Exception as e:
            print(f"Error processing entry {entry}: {e}")

    current_month = datetime.now().replace(day=1)
    for i in range(12):
        month_key = (current_month - relativedelta(months=i)).strftime('%Y-%m')
        if month_key not in month_totals:
            month_totals[month_key] = 0

    line_chart_data_12_months = {
        'labels': [datetime.strptime(date, '%Y-%m').strftime('%b %Y') for date in sorted(month_totals.keys())],
        'data': [month_totals[date] for date in sorted(month_totals.keys())]
    }

    current_month = datetime.now().strftime('%Y-%m')
    current_month_data = [entry for entry in sorted_transactions if entry.get('date', '')[:7] == current_month]
    total_amount_current_month = sum(float(entry.get('totalAmount', 0)) for entry in current_month_data)

    if len(line_chart_data_12_months['data']) >= 2:
        total_amount_last_month = line_chart_data_12_months['data'][-2]
        total_amount_last_last_month = line_chart_data_12_months['data'][-3] if len(line_chart_data_12_months['data']) > 2 else 0
        percentage_increase = (
            (total_amount_last_month - total_amount_last_last_month) / total_amount_last_last_month * 100
        ) if total_amount_last_last_month > 0 else 0
    else:
        total_amount_last_month = 0
        percentage_increase = 0

    frontend_data = {
        'user_id': user['sub'],
        'user_name': user.get('cognito:username', user.get('cognito:username', 'User')),
        'user_email': user['email'],
        'total_amount_sum': total_amount_sum,
        'total_amount_current_month': total_amount_current_month,
        'percentage_increase_last_month': percentage_increase,
        'pie_chart_data': pie_chart_data,
        'line_chart_data_30_days': line_chart_data_30_days,
        'line_chart_data_12_months': line_chart_data_12_months,
        'recommendations': recommendations
    }
    return render_template('analytics.html', **frontend_data)

@app.route('/exportdata', methods=['GET', 'POST'])
def exportdata():
    if not is_authenticated():
        return redirect(url_for('signin'))
    user = session['user']
    if request.method == 'POST':
        date_range = request.form.get('dateRange')
        payload = {
            'date_range': date_range,
            'user_id': user['sub'],
            'user_email': user['email'],
            'user_name': user.get('cognito:username', user.get('cognito:username', 'User'))
        }
        if date_range == 'custom':
            start_date = request.form.get('startDate')
            end_date = request.form.get('endDate')
            payload['start_date'] = start_date
            payload['end_date'] = end_date
        else:
            end_date = datetime.now().strftime('%Y-%m-%d')
            if date_range == '1_week':
                start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            elif date_range == '1_month':
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            elif date_range == '1_year':
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            else:
                start_date = end_date
            payload['start_date'] = start_date
            payload['end_date'] = end_date

        print(f"Payload export email: {payload}")
        api_url = f"{API_GATEWAY_BASE_URL}/export/daterange"
        response = requests.post(api_url, json=payload)

        if response.status_code == 200:
            print(f"Response of export email: {response.json()}")
            flash('Check your mail in some time for the exported data.', 'success')
        else:
            flash('Error exporting data. Please try again later.', 'error')

    return render_template('exportdata.html', user_id=user['sub'])


@app.route('/settings')
def settings():
    if not is_authenticated():
        return redirect(url_for('signin'))
    user = session['user']
    return render_template('settings.html',
                          user_id=user['sub'],
                          user_name=user.get('cognito:username', user.get('cognito:username', 'User')),
                          user_email=user['email'])


@app.route('/upload', methods=['POST'])
def upload_file():
    if not is_authenticated():
        return redirect(url_for('signin'))
    user = session['user']
    data = request.get_json()
    print(f"user_id: {data['user_id']}")
    print(f"file: {data['filename']}")
    if 'filename' not in data or 'user_id' not in data:
        return jsonify({'error': 'Missing file or user_id'}), 400
    if data['user_id'] != user['sub']:
        return jsonify({'error': 'Unauthorized user'}), 403
    file_content_base64 = data['body']
    user_id = data['user_id']
    filename = data['filename']
    bucket_name = data['bucket_name']
    payload = json.dumps({
        'user_id': user_id,
        'filename': filename,
        'body': file_content_base64,
        'bucket_name': bucket_name
    })
    response = requests.post(API_GATEWAY_UPLOAD_ENDPOINT, data=payload, headers={'Content-Type': 'application/json'})
    print(f"response from API gateway in upload: {response}")
    if response.status_code == 200:
        data = response.json()
        s3_url = f"https://{BUCKET_NAME}/{user_id}/{filename}"
        print(f"S3 upload bill url:{s3_url}")
        return jsonify({'message': 'File uploaded successfully', 's3_url': s3_url}), 200
    else:
        return jsonify(response.json()), response.status_code
    

@app.route('/processBill', methods=['POST'])
def process_bill():
    if not is_authenticated():
        return {'error': 'Unauthorized'}, 401
    user = session['user']
    data = request.get_json()

    
    # Forward to API Gateway endpoint for BillProcessorLambda
    api_url = f"{API_GATEWAY_BASE_URL}/upload/processBill"
    response = requests.post(api_url, json=data)
    
    return response.json(), response.status_code

@app.route('/saveBillData', methods=['POST'])
def save_bill_data():
    if not is_authenticated():
        return redirect(url_for('signin'))
    user = session['user']
    data = request.json
    print(f"data in save bill route: {data}")
    if data.get('user_id') != user['sub']:
        return jsonify({'error': 'Unauthorized user'}), 403
    response = requests.post(API_GATEWAY_SAVEBILL_ENDPOINT, json=data)
    if response.status_code == 200:
        return jsonify(response.json()), 200
    else:
        return jsonify(response.json()), response.status_code    
    

@app.route('/getUserProfilePic/<user_id>', methods=['GET'])
def get_user_profile_pic(user_id):
    if not is_authenticated():
        return redirect(url_for('signin'))
    user = session['user']
    if user_id != user['sub']:
        return jsonify({'error': 'Unauthorized user'}), 403
    try:
        print(user_id)
        response = requests.get(f"{API_GATEWAY_GET_PROFILE_PIC_URL_ENDPOINT}/{user_id}")
        print(f"Profile Pic response: {response.json()}")
        if response.status_code == 200:
            return response.json()
        else:
            return {'exists': False, 'url': ''}, response.status_code
    except requests.exceptions.RequestException as e:
        return {'message': str(e), 'exists': False, 'url': ''}, 500


@app.route('/uploadImage', methods=['POST'])
def upload_user_image():
    if not is_authenticated():
        return redirect(url_for('signin'))
    user = session['user']
    try:
        data = request.get_json()
        print(f"Received data: {data}")
        if data.get('user_id') != user['sub']:
            return jsonify({'error': 'Unauthorized user'}), 403
        required_fields = ['user_id', 'image_data', 'content_type']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
        payload = {
            'user_id': data['user_id'],
            'image_data': data['image_data'],
            'content_type': data['content_type']
        }
        response = requests.post(
            API_GATEWAY_UPLOADIMAGE_ENDPOINT,
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        if response.ok:
            return jsonify(response.json()), response.status_code
        else:
            print(f"API Gateway error: {response.text}")
            return jsonify({'error': 'Failed to upload image', 'details': response.json()}), response.status_code
    except Exception as e:
        print(f"Error in upload_user_image: {str(e)}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500
    

@app.route('/signout')
def signout():
    session.pop('user', None)
    session.pop('access_token', None)
    session.pop('refresh_token', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5001)