#!/usr/bin/env python3
"""
AWS Lambda handler for OrbitSpace FastAPI backend
"""

import json
import asyncio
from mangum import Mangum
from main import app

# Wrap FastAPI app with Mangum for Lambda compatibility
handler = Mangum(app)

def lambda_handler(event, context):
    """
    AWS Lambda handler function
    """
    try:
        # Mangum handles the event processing
        response = handler(event, context)
        return response
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }

# For local testing
if __name__ == "__main__":
    # Test event
    test_event = {
        'httpMethod': 'GET',
        'path': '/health',
        'headers': {},
        'body': None
    }
    
    class MockContext:
        aws_request_id = 'test-request-id'
    
    response = lambda_handler(test_event, MockContext())
    print(f"Response: {response}")
