from flask import Flask, redirect, request, render_template, url_for, session, jsonify
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




app = Flask(__name__)
app.secret_key = 'spendwise_secret_key'  # Replace with a secure secret key



# AWS Cognito Configuration
COGNITO_USER_POOL_ID = ''
COGNITO_APP_CLIENT_ID = ''
COGNITO_APP_CLIENT_SECRET = ''
COGNITO_REGION = ''
COGNITO_DOMAIN = ''

REDIRECT_URI = 'http://localhost:5001/home'




#API Gateway Endpoints
API_GATEWAY_BASE_URL = ''
API_GATEWAY_UPLOAD_ENDPOINT = API_GATEWAY_BASE_URL + '/upload'
API_GATEWAY_AUTOFILL_ENDPOINT = API_GATEWAY_BASE_URL + '/autofill'
API_GATEWAY_SAVEBILL_ENDPOINT = API_GATEWAY_BASE_URL + '/savebill'
API_GATEWAY_UPLOADIMAGE_ENDPOINT = API_GATEWAY_BASE_URL+'/uploadImage'

API_GATEWAY_UPDATE_USER_PREF_ENDPOINT = API_GATEWAY_BASE_URL + '/updateUserPref'
API_GATEWAY_GET_PROFILE_PIC_URL_ENDPOINT = API_GATEWAY_BASE_URL + '/getProfilePicUrl'

#S3 Configurations
BUCKET_NAME = 'bill-data-bucket-2024'

cognito_client = boto3.client('cognito-idp', region_name=COGNITO_REGION)

def is_authenticated():
    return 'user_id' in session and 'user_name' in session and 'user_email' in session

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signin')
def signin():
    print(f"Inside SignIn")
    return redirect(f"{COGNITO_DOMAIN}/login?response_type=code&client_id={COGNITO_APP_CLIENT_ID}&redirect_uri={REDIRECT_URI}")


def get_authenticated_user(access_token):
    try:
        # Get user information using the access token
        user_info = cognito_client.get_user(AccessToken=access_token)
        print(user_info)
        print(f"User Attributes: {user_info['UserAttributes']}")

        # Attempt to fetch 'given_name' or use a fallback
        user_name = next((attr['Value'] for attr in user_info['UserAttributes'] if attr['Name'] == 'given_name'), None)
        if not user_name:
            user_name = user_info.get('Username', 'User')  # Fallback to Username or 'User'
        
        user_id = user_info['Username']  # or another unique identifier
        user_email = next((attribute['Value'] for attribute in user_info['UserAttributes'] if attribute['Name'] == 'email'), None)

        return {'user_id': user_id, 'user_name': user_name, 'user_email' : user_email}

    except Exception as e:
        print(f"Error getting user information: {e}")
        # Log the error for further analysis
        app.logger.error(f"Error getting user information: {e}")
        return None


def is_token_expired(access_token):
    try:
        # Decode the token (without verifying, as we just want the expiry time)
        decoded_token = jwt.decode(access_token, options={"verify_signature": False})
        expiration_time = decoded_token['exp']
        expiration_datetime = datetime.utcfromtimestamp(expiration_time)

        return expiration_datetime < datetime.utcnow()

    except Exception as e:
        app.logger.error(f"Error checking token expiration: {e}")
        return False  

@app.route('/home')
def home():
    print("Entering /home route")
    
    if is_authenticated():
        print("User is authenticated")
        access_token = session['access_token']

        if is_token_expired(access_token):
            print("Access token expired")
            return render_template('error.html', error_message="Access token expired. Please reauthenticate.")

        user_info = get_authenticated_user(access_token)
        if user_info:
            print(f"....inside user info in home....")
            print(f"User info: {user_info}")
            print(f"Access token: {session.get('access_token')}")
            print(f"Session user ID: {session.get('user_id')}")

            # Retrieve last 10 transactions data (similar to the /analytics route)
            api_url = ''
            #payload = {'body': json.dumps({'user_id': session['user_id']})}
            #response = requests.get(api_url, data=json.dumps(payload))


            response = requests.get(api_url, params={'user_id': session['user_id']})

            print(f"API response of home last 10 days: ", response)

            if response.status_code == 200:
                api_data = response.json()
                #print(f"API data", api_data)

                body_data = json.loads(api_data.get('body', '[]'))
                transactions = body_data[:]  

                # Calculate total amount
                total_amount = sum(float(entry.get('totalAmount', 0)) for entry in transactions)

                # Render home.html with user information, last 10 transactions, and total amount
                return render_template('home.html', user_id=user_info['user_id'],
                                           user_name=user_info['user_name'],
                                           user_email=user_info['user_email'],
                                           transactions=transactions,
                                           total_amount=total_amount)
        else:
            print("Error retrieving user information")
            # Handle error retrieving user information
            return render_template('error.html', error_message="Error retrieving user information.")

    code = request.args.get('code')
    if code:
        try:
            print(f"Received code: {code}")

            # Exchange authorization code for tokens using Authorization Code Grant
            token_url = f'{COGNITO_DOMAIN}/oauth2/token'
            redirect_uri = REDIRECT_URI
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
            }
            data = {
                'grant_type': 'authorization_code',
                'client_id': COGNITO_APP_CLIENT_ID,
                'client_secret': COGNITO_APP_CLIENT_SECRET,
                'redirect_uri': redirect_uri,
                'code': code # Include the necessary scopes here
            }

            response = requests.post(token_url,headers=headers, data=data)

            tokens = response.json()
            access_token = tokens['access_token']
            refresh_token = tokens['refresh_token']
            id_token = tokens['id_token']

            # Store access token and refresh token in the session
            session['access_token'] = access_token
            session['refresh_token'] = refresh_token
            user_info = get_authenticated_user(access_token)
            session['user_id'] = user_info['user_id']
            session['user_name'] = user_info['user_name']
            session['user_email']= user_info['user_email']
            print(session)
            if user_info:
                api_url = ''
                payload = {'body': json.dumps({'user_id': session['user_id']})}
                response = requests.get(api_url, data=json.dumps(payload))

                if response.status_code == 200:
                    api_data = response.json()
                    body_data = json.loads(api_data.get('body', '[]'))
                    transactions = body_data[:10]  # Take the first 10 transactions

                    # Calculate total amount
                    total_amount = sum(float(entry.get('totalAmount', 0)) for entry in transactions)

                    # Render home.html with user information, last 10 transactions, and total amount
                    return render_template('home.html', user_id=user_info['user_id'],
                                            user_name=user_info['user_name'],
                                            user_email=user_info['user_email'],
                                            transactions=transactions,
                                            total_amount=total_amount)    
            else:
                print("Error retrieving user information")
                # Handle error retrieving user information
                return render_template('error.html', error_message="Error retrieving user information.")

        except Exception as e:
            print(f"Authentication error: {e}")
            # Log the error for further analysis
            app.logger.error(f"Authentication error: {e}")
            print("Rendering error.html")
            # Handle authentication failure gracefully, e.g., redirect to a specific error page
            return render_template('error.html', error_message="Authentication failed. Please try again.")

    print("Redirecting to /signin")
    return redirect(url_for('signin'))

@app.route('/uploadbill')
def uploadbill():
    if not is_authenticated():
        return redirect(url_for('signin'))
    return render_template('uploadbill.html', user_id=session['user_id'])

@app.route('/analytics')
def analytics():
    # Check if the user is authenticated
    if not is_authenticated():
        return redirect(url_for('signin'))

    # Define the API URL
    api_url = ''

    try:
        # Make a request to the API
        response = requests.get(api_url, params={'user_id': session['user_id']})

        # Check if the request was successful
        if response.status_code == 200:
            # Parse the JSON response
            api_data = response.json()
            body_data = json.loads(api_data.get('body', '[]'))

            # Calculate the sum of totalAmount values
            total_amount_sum = sum(float(entry.get('totalAmount', 0)) for entry in body_data)

            # Combine values for the same category
            category_totals = defaultdict(float)
            for entry in body_data:
                category_totals[entry['category']] += float(entry.get('totalAmount', 0))

            # Prepare data for pie chart
            pie_chart_data = [{'category': category, 'totalAmount': total} for category, total in category_totals.items()]
            pie_chart_data = sorted(pie_chart_data, key=lambda x: x['category'].lower())

            ################## Line Graph for Last 30 Days ##################
            sorted_body_data = sorted(body_data, key=lambda x: x['date'])
            last_30_days_data = [
                entry for entry in sorted_body_data 
                if 'date' in entry and datetime.now() - datetime.strptime(entry['date'], '%Y-%m-%d') <= timedelta(days=30)
            ]

            date_totals = defaultdict(float)
            for entry in last_30_days_data:
                date_totals[entry['date']] += float(entry.get('totalAmount', 0))

            line_chart_data_30_days = {
                'labels': list(date_totals.keys()),
                'data': list(date_totals.values())
            }

            ################## Line Graph for Last 12 Months ##################
            last_12_months_data = [
                entry for entry in sorted_body_data 
                if 'date' in entry and datetime.now() - datetime.strptime(entry['date'], '%Y-%m-%d') <= timedelta(days=365)
            ]

            month_totals = defaultdict(float)
            for entry in last_12_months_data:
                try:
                    year_month = entry['date'][:7]  # Extract year and month
                    month_totals[year_month] += float(entry.get('totalAmount', 0))
                except Exception as e:
                    print(f"Error processing entry {entry}: {e}")

            # Fill in missing months with 0
            current_month = datetime.now().replace(day=1)
            for i in range(12):
                month_key = (current_month - relativedelta(months=i)).strftime('%Y-%m')
                if month_key not in month_totals:
                    month_totals[month_key] = 0

            line_chart_data_12_months = {
                'labels': [datetime.strptime(date, '%Y-%m').strftime('%b %Y') for date in sorted(month_totals.keys())],
                'data': [month_totals[date] for date in sorted(month_totals.keys())]
            }

            ################## Total Amount for Current Month ##################
            current_month = datetime.now().strftime('%Y-%m')
            current_month_data = [entry for entry in sorted_body_data if entry['date'][:7] == current_month]
            total_amount_current_month = sum(float(entry.get('totalAmount', 0)) for entry in current_month_data)

            ################## Percentage Increase from Last Month ##################
            if len(line_chart_data_12_months['data']) >= 2:
                total_amount_last_month = line_chart_data_12_months['data'][-2]
                total_amount_last_last_month = line_chart_data_12_months['data'][-3] if len(line_chart_data_12_months['data']) > 2 else 0
                percentage_increase = (
                    (total_amount_last_month - total_amount_last_last_month) / total_amount_last_last_month * 100
                ) if total_amount_last_last_month > 0 else 0
            else:
                total_amount_last_month = 0
                percentage_increase = 0

            # Prepare data for frontend
            frontend_data = {
                'user_id': session['user_id'],
                'total_amount_sum': total_amount_sum,
                'total_amount_current_month': total_amount_current_month,
                'percentage_increase_last_month': percentage_increase,
                'pie_chart_data': pie_chart_data,
                'line_chart_data_30_days': line_chart_data_30_days,
                'line_chart_data_12_months': line_chart_data_12_months
            }
            return render_template('analytics.html', **frontend_data)

        else:
            print(f"Error fetching API data. Status code: {response.status_code}")
            return render_template('analytics.html', user_id=session['user_id'], total_amount_sum=0, pie_chart_data="[]", transactions=[])

    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")




@app.route('/exportdata', methods=['GET', 'POST'])
def exportdata():
    if not is_authenticated():
        return redirect(url_for('signin'))
    
    print(f"Request Method:", request.method)
    if request.method == 'POST':
        # Get the selected date range from the form
        date_range = request.form.get('dateRange')

        # Initialize payload with date_range
        payload = {'date_range': date_range, 'user_id': session['user_id'], 'user_email' : session['user_email'], 'user_name' : session['user_name']}

        
        # If the selected date range is 'custom', add start and end dates to the payload
        if date_range == 'custom':
            start_date = request.form.get('startDate')
            end_date = request.form.get('endDate')
            payload['start_date'] = start_date
            payload['end_date'] = end_date
        else:
            # Calculate start and end dates based on the selected option
            end_date = datetime.now().strftime('%Y-%m-%d')  # End date is always today

            if date_range == '1_week':
                start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            elif date_range == '1_month':
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            elif date_range == '1_year':
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            else:
                # Handle additional date range options if needed
                start_date = end_date

            payload['start_date'] = start_date
            payload['end_date'] = end_date

        print(f"Payload export email:", payload)


        # Make a POST request to your API with the payload
        api_url = ''
        response = requests.post(api_url, json=payload)

        if response.status_code == 200:
            # Display a success message on the frontend
            flash('Check your mail in some time for the exported data.', 'success')
        else:
            # Display an error message on the frontend
            flash('Error exporting data. Please try again later.', 'error')

    return render_template('exportdata.html', user_id=session['user_id'])

@app.route('/settings')
def settings():
    if not is_authenticated():
        return redirect(url_for('signin'))

    return render_template('settings.html', user_id=session['user_id'], user_name=session['user_name'], user_email=session['user_email'])

@app.route('/signout')
def signout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/upload', methods=['POST'])
def upload_file():
    data = request.get_json()  # Use .get_json() to handle JSON data
    print(f"user_id", data['user_id'])
    print(f"file", data['filename'])
    if 'filename' not in data or 'user_id' not in data:
        return jsonify({'error': 'Missing file or user_id'}), 400

    file_content_base64 = data['body']
    user_id = data['user_id']
    filename = data['filename']
    bucket_name = data['bucket_name']

    # Send the request to API Gateway
    payload = json.dumps({
        'user_id': user_id,
        'filename': filename,
        'body': file_content_base64,
        'bucket_name': bucket_name
    })

    # Make the request to API Gateway
    response = requests.post(API_GATEWAY_UPLOAD_ENDPOINT, data=payload, headers={'Content-Type': 'application/json'})
    print(f"response from API gateway in upload", response)
    # Handle the response from API Gateway
    if response.status_code == 200:
        data = response.json()
        s3_url = BUCKET_NAME+"/"+user_id+"/"+filename
        return jsonify({'message': 'File uploaded successfully', 's3_url': s3_url}), 200
    else:
        return jsonify(response.json()), response.status_code


@app.route('/saveBillData', methods=['POST'])
def save_bill_data():
    # Get the data from the request
    data = request.json
    print(f"data in save bill route", data)
    # Send the request to the Lambda function via API Gateway
    response = requests.post(API_GATEWAY_SAVEBILL_ENDPOINT, json=data)

    # Forward the response from the Lambda function
    if response.status_code == 200:
        return jsonify(response.json()), 200
    else:
        return jsonify(response.json()), response.status_code
    
    
@app.route('/getUserProfilePic/<user_id>', methods=['GET'])
def get_user_profile_pic(user_id):
    try:
        print(user_id)
        # Pass `user_id` in the path to API Gateway
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
    try:
        # Get the data from the request
        data = request.get_json()
        print(f"Received data: {data}")
        
        # Validate required fields
        required_fields = ['user_name', 'image_data', 'content_type']
        if not all(field in data for field in required_fields):
            return jsonify({
                'error': 'Missing required fields'
            }), 400
        
        # Prepare the payload for Lambda
        payload = {
            'body': {
                'user_name': data['user_name'],
                'image_data': data['image_data'],
                'content_type': data['content_type']
            }
        }
        
        # Send request to API Gateway
        response = requests.post(
            API_GATEWAY_UPLOADIMAGE_ENDPOINT,
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        # Handle the response
        if response.ok:
            return jsonify(response.json()), response.status_code
        else:
            print(f"API Gateway error: {response.text}")
            return jsonify({
                'error': 'Failed to upload image',
                'details': response.json()
            }), response.status_code
            
    except Exception as e:
        print(f"Error in upload_user_image: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
        }), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port = 5001)