"""
Locust Stress Test Script for Login API
Tests: POST /api/v1/auth/login endpoint under high concurrent load
Uses a predefined pool of test accounts for realistic login stress testing
"""

from locust import HttpUser, task, between
import random
import json


# Configuration: Number of test accounts in the pool
# Adjust this based on how many test accounts you have created
TEST_ACCOUNT_POOL_SIZE = 100

# Password used for all test accounts
TEST_PASSWORD = "TestPass123!"


class LoginStressUser(HttpUser):
    """
    Simulates a user attempting to login to the platform.
    Each user randomly selects from a predefined pool of test accounts.
    """
    
    # Wait 0.5-2 seconds between requests (login is faster than registration)
    wait_time = between(0.5, 2)
    
    def on_start(self):
        """
        Called when a simulated user starts.
        Initialize the test account pool if not already created.
        """
        # Create the test account pool (shared across all users)
        if not hasattr(LoginStressUser, 'test_accounts'):
            LoginStressUser.test_accounts = [
                f"loadtest{i}@gignut.com"
                for i in range(1, TEST_ACCOUNT_POOL_SIZE + 1)
            ]
        
        # Track login attempts for this user
        self.login_count = 0
    
    def get_random_account(self):
        """
        Randomly selects a test account from the pool.
        Returns a tuple of (email, password).
        """
        email = random.choice(LoginStressUser.test_accounts)
        return email, TEST_PASSWORD
    
    @task(1)
    def login_user(self):
        """
        Main task: Attempt to login with a random test account.
        Uses catch_response=True for accurate success/failure tracking.
        """
        email, password = self.get_random_account()
        self.login_count += 1
        
        payload = {
            "email": email,
            "password": password
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        # Use catch_response=True to manually mark success/failure
        with self.client.post(
            "/api/v1/auth/login",
            json=payload,
            headers=headers,
            catch_response=True,
            name="Login User"
        ) as response:
            # Check if login was successful (200 = OK)
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    # Verify we got expected response structure with session tokens
                    if "user" in response_data and "session" in response_data:
                        # Verify session has access_token
                        if "access_token" in response_data.get("session", {}):
                            response.success()
                        else:
                            response.failure(f"Missing access_token in session: {response_data}")
                    else:
                        response.failure(f"Unexpected response structure: {response_data}")
                except json.JSONDecodeError:
                    response.failure(f"Invalid JSON response: {response.text[:100]}")
                except Exception as e:
                    response.failure(f"Error parsing response: {str(e)}")
            
            # Handle different error status codes
            elif response.status_code == 400:
                # Bad Request - usually invalid email/password format
                response.failure(f"Bad Request (400): Invalid credentials or format - {response.text[:200]}")
            
            elif response.status_code == 401:
                # Unauthorized - wrong password or account doesn't exist
                response.failure(f"Unauthorized (401): Invalid email or password - {email}")
            
            elif response.status_code == 429:
                # Too Many Requests - rate limiting (Supabase or backend)
                response.failure(f"Rate Limited (429): Too many requests - server is throttling")
            
            elif response.status_code >= 500:
                # Server errors (500, 502, 503, 504, etc.)
                response.failure(f"Server Error ({response.status_code}): Backend failure - {response.text[:200]}")
            
            elif response.status_code == 0:
                # Connection error, timeout, or connection reset
                response.failure(f"Connection Error (0): Request failed - timeout or connection reset")
            
            else:
                # Any other unexpected status code
                response.failure(f"Unexpected status ({response.status_code}): {response.text[:200]}")

