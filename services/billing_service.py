import os
import requests
from services.db_service import db_service

class BillingService:
    def __init__(self):
        self.api_key = os.getenv("INSTAMOJO_API_KEY")
        self.auth_token = os.getenv("INSTAMOJO_AUTH_TOKEN")
        env = os.getenv("INSTAMOJO_ENV", "test").lower()
        if env == "production":
            self.base_url = "https://www.instamojo.com/api/1.1"
        else:
            self.base_url = "https://test.instamojo.com/api/1.1"

    def create_checkout_session(self, user_id, email, success_url, cancel_url):
        try:
            headers = {
                "X-Api-Key": self.api_key,
                "X-Auth-Token": self.auth_token
            }
            
            payload = {
                "purpose": "KiraakStudy Premium (Monthly)",
                "amount": "49", # ₹49
                "buyer_name": user_id,
                "email": email,
                "redirect_url": success_url,
                "send_email": True,
                "allow_repeated_payments": False
            }
            
            response = requests.post(f"{self.base_url}/payment-requests/", data=payload, headers=headers)
            response_data = response.json()
            
            if response_data.get("success"):
                # Return the longurl for the user to visit and pay
                return response_data["payment_request"]["longurl"]
            else:
                print(f"Instamojo Error: {response_data}")
                return None
        except Exception as e:
            print(f"Error creating Instamojo payment request: {e}")
            return None

    def verify_payment(self, payment_request_id, payment_id):
        """Verifies the payment with Instamojo API and upgrades the user if successful."""
        try:
            headers = {
                "X-Api-Key": self.api_key,
                "X-Auth-Token": self.auth_token
            }
            # Verify the payment details
            response = requests.get(f"{self.base_url}/payment-requests/{payment_request_id}/{payment_id}/", headers=headers)
            data = response.json()
            
            if data.get("success") and data.get("payment_request", {}).get("payment", {}).get("status") == "Credit":
                return True
            return False
        except Exception as e:
            print(f"Error verifying Instamojo payment: {e}")
            return False

    def upgrade_user_to_premium(self, user_id):
        try:
            # Update the user's tier to premium in the database
            db_service.execute("UPDATE user_usage SET subscription_tier = 'premium' WHERE user_id = ?", (user_id,))
            print(f"Successfully upgraded user {user_id} to Premium!")
            return True
        except Exception as e:
            print(f"Error upgrading user to premium: {e}")
            return False

billing_service = BillingService()
