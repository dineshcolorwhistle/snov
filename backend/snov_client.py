import time
import logging
import requests
from typing import Dict, Any, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SnovioClient:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token: Optional[str] = None
        self.token_expires_at: float = 0.0
        self.base_url = "https://api.snov.io"

    def get_valid_token(self) -> str:
        """
        Retrieves a cached token or requests a new one if expired.
        Token is cached in-memory and refreshed 60 seconds before actual expiration.
        """
        current_time = time.time()
        if self.access_token and current_time < self.token_expires_at - 60:
            return self.access_token

        logger.info("Access token is missing or expired. Requesting a new one...")
        url = f"{self.base_url}/v1/oauth/access_token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        try:
            response = requests.post(url, data=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            self.access_token = data.get("access_token")
            expires_in = data.get("expires_in", 3600)
            self.token_expires_at = time.time() + expires_in
            
            if not self.access_token:
                raise ValueError("Response did not contain an 'access_token'")
                
            logger.info("Successfully obtained new access token.")
            return self.access_token
        except Exception as e:
            logger.error(f"Error fetching access token: {e}")
            raise Exception("Authentication with Snov.io failed. Check your client credentials.") from e

    def get_headers(self) -> Dict[str, str]:
        token = self.get_valid_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def get_user_lists(self) -> List[Dict[str, Any]]:
        """
        Fetches prospect lists. Tries POST first (with Bearer token),
        and falls back to GET if a method error occurs.
        """
        url = f"{self.base_url}/v1/get-user-lists"
        headers = self.get_headers()
        
        # Snov.io's documentation or legacy endpoints may expect POST, newer expect GET.
        # We run GET first as the primary method, and fall back to POST if GET is unsupported.
        try:
            logger.info("Attempting to fetch lists via GET...")
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code in [405, 404]:
                logger.warning(f"GET returned {response.status_code}. Retrying with POST...")
                response = requests.post(url, json={}, headers=headers, timeout=15)
            response.raise_for_status()
            raw_lists = response.json()
        except Exception as e:
            logger.error(f"Failed list retrieval: {e}")
            raise Exception(f"Failed to fetch lists from Snov.io: {e}")

        # Standardize the lists response to have id, name, and contacts keys
        standardized_lists = []
        
        # Ensure raw_lists is iterable
        if isinstance(raw_lists, dict):
            # Sometimes APIs return lists nested inside a dictionary key
            lists_data = raw_lists.get("lists") or raw_lists.get("data") or []
            if not lists_data and "id" in raw_lists:
                lists_data = [raw_lists]
        elif isinstance(raw_lists, list):
            lists_data = raw_lists
        else:
            lists_data = []

        logger.info(f"Raw lists data received: {lists_data}")

        for lst in lists_data:
            if not isinstance(lst, dict):
                continue
            
            # Match Snov list properties dynamically
            list_id = lst.get("id") or lst.get("listId")
            list_name = lst.get("name") or lst.get("listName") or "Unnamed List"
            contacts_count = (
                lst.get("contacts") or 
                lst.get("contactsCount") or 
                lst.get("count") or 
                lst.get("prospectsCount") or 
                0
            )
            
            if list_id is not None:
                standardized_lists.append({
                    "id": str(list_id),
                    "name": str(list_name),
                    "contacts": int(contacts_count)
                })

        return standardized_lists

    def find_email_by_name_and_domain(self, first_name: str, last_name: str, domain: str) -> Optional[str]:
        """
        Starts an email search task and polls the Snov.io result endpoint.
        Returns the resolved business email or None if no valid email is found.
        """
        start_url = f"{self.base_url}/v2/emails-by-domain-by-name/start"
        headers = self.get_headers()
        
        payload = {
            "rows": [
                {
                    "first_name": first_name,
                    "last_name": last_name,
                    "domain": domain
                }
            ]
        }
        
        logger.info(f"Initiating email search for {first_name} {last_name} @ {domain}...")
        try:
            response = requests.post(start_url, json=payload, headers=headers, timeout=15)
            response.raise_for_status()
            start_data = response.json()
        except Exception as e:
            logger.error(f"Failed to start email finder task: {e}")
            raise Exception(f"Snov.io Email Finder API failed to start: {e}")

        task_hash = start_data.get("task_hash")
        if not task_hash:
            logger.warning(f"No task_hash returned in Snov.io response: {start_data}")
            # Check if it directly returned the email (sometimes APIs return cached items immediately)
            if isinstance(start_data, list) and len(start_data) > 0:
                first_res = start_data[0]
                if isinstance(first_res, dict) and first_res.get("email"):
                    return first_res.get("email")
            raise Exception("Snov.io did not return a task hash for the email search.")

        # Polling result
        result_url = f"{self.base_url}/v2/emails-by-domain-by-name/result"
        max_attempts = 15
        poll_interval = 2.0
        
        logger.info(f"Task started. Hash: {task_hash}. Polling for results...")
        
        for attempt in range(max_attempts):
            time.sleep(poll_interval)
            try:
                # Snov.io expects task_hash as query parameter
                res = requests.get(result_url, params={"task_hash": task_hash}, headers=headers, timeout=10)
                res.raise_for_status()
                result_data = res.json()
            except Exception as e:
                logger.error(f"Error polling search results (attempt {attempt+1}): {e}")
                continue

            logger.info(f"Poll attempt {attempt+1} response: {result_data}")

            # Check if task is still processing
            # Snov.io result endpoint might return status: 'processing', or empty results, or list of results
            if isinstance(result_data, dict):
                status = result_data.get("status")
                if status in ["processing", "pending"]:
                    logger.info("Search task is still processing. Waiting...")
                    continue
                
                # Check for results list
                rows = result_data.get("results") or result_data.get("rows") or []
            elif isinstance(result_data, list):
                rows = result_data
            else:
                rows = []

            # If results are returned, extract email
            if rows:
                first_row = rows[0]
                if isinstance(first_row, dict):
                    email = first_row.get("email")
                    status = first_row.get("status")
                    
                    if email:
                        # Check verification status
                        if status == "not_valid":
                            logger.info(f"Email {email} found but verification status is 'not_valid'.")
                            return None
                        
                        logger.info(f"Found valid/unknown email: {email} (status: {status})")
                        return email
                
                # If we got rows but no email, it means search is complete and nothing was found
                logger.info("Search complete but no email address was found.")
                return None

        logger.warning("Polling timed out. No email address was resolved.")
        return None

    def add_prospect_to_list(self, list_id: str, email: str, first_name: str, last_name: str) -> bool:
        """
        Adds a prospect to a Snov.io list.
        """
        url = f"{self.base_url}/v1/add-prospect-to-list"
        headers = self.get_headers()
        
        payload = {
            "listId": list_id,
            "email": email,
            "firstName": first_name,
            "lastName": last_name,
            "updateContact": 1
        }
        
        logger.info(f"Adding prospect {first_name} {last_name} ({email}) to list {list_id}...")
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            # API returns success status. It may return success = True or status = 'added' etc.
            success = data.get("success") or data.get("status") == "added" or "id" in data
            if success:
                logger.info("Successfully added prospect to Snov.io list.")
                return True
            else:
                logger.error(f"Snov.io failed to add prospect. Response: {data}")
                return False
        except Exception as e:
            logger.error(f"Error adding prospect to list: {e}")
            raise Exception(f"Failed to add prospect to Snov.io list: {e}")
