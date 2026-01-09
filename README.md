# SpendWise: Cloud-Powered Personal Finance Management Platform

SpendWise is a cloud-based personal finance management platform that empowers users to take control of their financial future. Leveraging the power of AWS services, SpendWise automates the process of expense tracking, spend analysis, and report generation. With advanced tools and intelligent automation, SpendWise provides real-time insights and personalized financial reports, helping users optimize their financial life with ease and confidence.


---

## Features

- **User Authentication**: Secure user login and management using AWS Cognito.
- **Bill Upload & Storage**: 
  - Effortlessly upload bills as images or input transaction details directly.
  - Files are securely stored in AWS S3.
- **Automatic Bill Data Extraction**:
  - Uses AWS Textract to analyze uploaded bill images, automatically extracting and filling details such as date, total amount, and category for seamless form population
- **Expense Analysis**: Provides insights such as:
  - Expenditure over the last 30 days.
  - Yearly spending trends.
  - Category-wise distribution of expenses
- **AI-Powered Spending Advisor**:
  - Leverages AWS Bedrock to generate personalized financial suggestions and recommendations based on aggregated spending patterns from user transactions.
- **Report Generation**: Receive detailed expense reports via email using Amazon SES.
- **Home Page Dashboard**: View all bill details and summaries on a user-friendly dashboard.
- **Scalability & Security**: Built using AWS Lambda, API Gateway, DynamoDB, and other serverless services for high availability, scalability, and robust security.

---

## Architecture
<img width="989" alt="Screenshot 2024-11-20 at 9 04 17 PM" src="https://github.com/user-attachments/assets/6c6d640a-8362-4212-9982-ff1aa0f6969e">

### High-Level Diagram


### Key Components:
1. **Frontend**: 
   - Developed in JavaScript for a seamless user experience.
2. **Backend**: 
   - Flask application that calls AWS API Gateway to trigger Lambda Functions interacting with DynamoDB and S3.
3. **Cloud Services**:
   - **AWS Cognito**: Handles authentication.
   - **AWS Lambda**: Contains core business logic.
   - **API Gateway**: Routes API requests securely.
   - **DynamoDB**: Stores user and bill data.
   - **S3**: Stores uploaded bill images and profile pictures.
   - **SES**: Sends financial reports to users.
   - **Amazon Textract**: Analyzes bill images to extract text and data for auto-filling.
   - **Amazon Bedrock**: Provides AI runtime for generating spending suggestions using large language models.

---

# Deployment Steps

### 1. Clone the Repository
```bash
git clone https://github.com/Bhaveshm23/SpendWise
cd SpendWise
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # Unix/macOS
# OR
venv\Scripts\activate    # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure AWS Services
- Set up AWS Cognito User Pool
- Configure API Gateway endpoints
- Create necessary IAM roles

### 5. Set Environment Variables
Create a `.env` file:
```
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
COGNITO_USER_POOL_ID=your_user_pool_id
API_GATEWAY_URL=your_api_gateway_endpoint
```

### 6. Run the Application
```bash
python app.py
```

### 7. Access Application
Open browser and navigate to:
```
http://localhost:5001
```
---

## Testing Procedures


### Integration Testing

## Lambda Function Testing

### Testing Tools
- AWS Lambda Test Events
- CloudWatch Logs

### Test Scenarios
1. **Bill Upload Lambda**
   - Verify file processing
   - Check data extraction accuracy
   - Test error handling

2. **User Authentication Lambda**
   - Validate token generation
   - Test user registration flow
   - Check permission handling
     
3. **BillAutoFill Lambda**
   - Test image upload to S3 and invocation.
   - Verify Textract text detection and extraction of date, amount, and category using sample bill images.

4. **AI-Advisor Lambda**
  - Test Bedrock model invocation with generated prompt.
  - Query DynamoDB for user transactions


### Sample Test Event
```json
{
  "user_id": "test_user",
  "file_content": "base64_encoded_bill_image",
  "file_type": "pdf"
}
```

## API Gateway Testing

### Testing Approach
- Postman/curl for API endpoint verification
- Manual API endpoint testing

### Key Endpoints to Test
- `/upload`
- `/savebill`
- `/home/`
- `/export/daterange`
- `/home/advisor (for AI suggestions)`
- `/upload/processBill (for bill auto-fill)`

### Test Cases
1. **Successful Requests**
   - Validate response structure
   - Check status codes
   - Verify data integrity

2. **Error Scenarios**
   - Invalid authentication
   - Malformed requests
   - Permission issues


## Monitoring and Logging
- Use CloudWatch for lambda function logs
- Monitor API Gateway request/response cycles


### Future Roadmap

- Implement machine learning for spending predictions
- Enhanced data visualization
