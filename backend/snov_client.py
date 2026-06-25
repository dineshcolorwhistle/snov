import time
import re
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

    def is_valid_domain(self, domain: str) -> bool:
        """
        Validates if the input looks like a valid domain format.
        """
        val = domain.strip().lower()
        if " " in val:
            return False
        if val.startswith("http://"):
            val = val[7:]
        elif val.startswith("https://"):
            val = val[8:]
        if val.startswith("www."):
            val = val[4:]
            
        # Basic domain format validation (contains a dot and valid characters)
        pattern = r"^[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9]?\.[a-zA-Z]{2,10}$"
        return bool(re.match(pattern, val))

    def find_domain_via_custom_api(self, company_name: str) -> Optional[str]:
        """
        Calls the custom Domain Finder API to retrieve the company's domain.
        """
        import os
        url = "https://domainfinder.agentwhistle.com/api/domain"
        api_key = os.getenv("DOMAIN_FINDER_API_KEY", "33879b4f44c668474d12bfb93af204183c26813dcdde463a68ee024ace9f3859").strip()
        serper_api_key = os.getenv("DOMAIN_FINDER_SERPER_API_KEY", "ce3db86bd10626443ff95fe94e400b8057b5fafc").strip()
        
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": api_key
        }
        payload = {
            "companyName": company_name,
            "serperApiKey": serper_api_key
        }
        
        logger.info(f"Calling custom Domain Finder API for company: '{company_name}'...")
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=20)
            response.raise_for_status()
            data = response.json()
            if data.get("success") and data.get("domain"):
                domain = data["domain"].strip().lower()
                logger.info(f"Custom Domain Finder API resolved '{company_name}' to domain '{domain}'")
                return domain
            else:
                logger.warning(f"Custom Domain Finder API failed to find domain for '{company_name}': {data}")
                return None
        except Exception as e:
            logger.error(f"Error calling custom Domain Finder API for '{company_name}': {e}")
            return None

    def find_linkedin_via_custom_api(self, first_name: str, last_name: str, company_name: str) -> Optional[str]:
        """
        Calls the custom LinkedIn Profile API to retrieve the prospect's LinkedIn URL.
        """
        import os
        url = "https://linkedinurl.agentwhistle.com/api/profile"
        api_key = os.getenv("LINKEDIN_API_KEY", "a30e41404071653c993cfcba98287f42a2c152a7f07f5d5d644e4b0ffeaa604c").strip()
        serper_api_key = os.getenv("LINKEDIN_SERPER_API_KEY", "64d5bd586e19b19010f4ac64c257fe4510e6adde").strip()
        try:
            credits_balance = int(os.getenv("LINKEDIN_SERPER_CREDITS_BALANCE", "2497").strip())
        except Exception:
            credits_balance = 2497
            
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": api_key
        }
        payload = {
            "firstName": first_name,
            "lastName": last_name,
            "companyName": company_name,
            "serperApiKey": serper_api_key,
            "serperCreditsBalance": credits_balance
        }
        
        logger.info(f"Calling custom LinkedIn API for '{first_name} {last_name}' at '{company_name}'...")
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=20)
            response.raise_for_status()
            data = response.json()
            if data.get("success") and data.get("linkedinUrl"):
                linkedin_url = data["linkedinUrl"].strip()
                logger.info(f"Custom LinkedIn API resolved profile: '{linkedin_url}'")
                return linkedin_url
            else:
                logger.warning(f"Custom LinkedIn API failed to find profile: {data}")
                return None
        except Exception as e:
            logger.error(f"Error calling custom LinkedIn API: {e}")
            return None

    def find_domain_by_company_name(self, company_name: str) -> Optional[str]:
        """
        Searches Snov.io for a company's website domain by name.
        """
        start_url = f"{self.base_url}/v2/company-domain-by-name/start"
        headers = self.get_headers().copy()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        
        # Snov.io expects names[] array parameter in application/x-www-form-urlencoded
        payload = [("names[]", company_name)]
        
        logger.info(f"Initiating domain search for company: '{company_name}'...")
        try:
            response = requests.post(start_url, data=payload, headers=headers, timeout=15)
            response.raise_for_status()
            start_data = response.json()
        except Exception as e:
            logger.error(f"Failed to start company domain search task: {e}")
            raise Exception(f"Snov.io Company Domain API failed to start: {e}")

        task_hash = start_data.get("task_hash")
        if not task_hash and isinstance(start_data.get("data"), dict):
            task_hash = start_data["data"].get("task_hash")
            
        if not task_hash:
            logger.warning(f"No task_hash returned in domain search: {start_data}")
            raise Exception("Snov.io did not return a task hash for the domain search.")

        result_url = f"{self.base_url}/v2/company-domain-by-name/result"
        max_attempts = 12
        poll_interval = 4.0
        
        logger.info(f"Domain search task started. Hash: {task_hash}. Polling...")
        for attempt in range(max_attempts):
            time.sleep(poll_interval)
            try:
                res = requests.get(result_url, params={"task_hash": task_hash}, headers=headers, timeout=10)
                res.raise_for_status()
                result_data = res.json()
            except Exception as e:
                logger.error(f"Error polling domain search results (attempt {attempt+1}): {e}")
                continue

            logger.info(f"Domain search poll attempt {attempt+1} response: {result_data}")

            status = result_data.get("status")
            if status in ["in progress", "processing", "pending"]:
                logger.info("Domain search task is still processing. Waiting...")
                continue
                
            if status == "completed":
                data = result_data.get("data") or []
                if data:
                    first_res = data[0]
                    result_dict = first_res.get("result") or {}
                    domain = result_dict.get("domain") or first_res.get("domain")
                    if domain:
                        logger.info(f"Successfully resolved company '{company_name}' to domain '{domain}'")
                        return domain
                logger.warning(f"Domain search completed but no domain found for company '{company_name}'")
                return None

        logger.warning("Polling timed out. No domain was resolved.")
        return None

    def find_email_by_name_and_domain(self, first_name: str, last_name: str, domain: str) -> Optional[str]:
        """
        Starts an email search task and polls the Snov.io result endpoint.
        Returns the resolved business email or None if no valid email is found.
        """
        if not self.is_valid_domain(domain):
            raise Exception(f"Invalid domain '{domain}' provided for email search.")

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
        if not task_hash and isinstance(start_data.get("data"), dict):
            task_hash = start_data["data"].get("task_hash")

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
        max_attempts = 12
        poll_interval = 4.0
        
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
            status = "completed"
            if isinstance(result_data, dict):
                status = result_data.get("status") or "completed"
                if status in ["processing", "pending"]:
                    logger.info("Search task is still processing. Waiting...")
                    continue
                
                # Check for results list
                rows = result_data.get("results") or result_data.get("rows") or result_data.get("data") or []
            elif isinstance(result_data, list):
                rows = result_data
            else:
                rows = []

            # If results are returned, extract email
            if rows:
                first_row = rows[0]
                if isinstance(first_row, dict):
                    email = first_row.get("email")
                    email_status = first_row.get("status")
                    
                    # Support v2 nested format
                    if not email and isinstance(first_row.get("result"), list) and len(first_row["result"]) > 0:
                        res_item = first_row["result"][0]
                        if isinstance(res_item, dict):
                            email = res_item.get("email")
                            email_status = res_item.get("status")
                    elif not email and isinstance(first_row.get("result"), dict):
                        res_item = first_row["result"]
                        email = res_item.get("email")
                        email_status = res_item.get("status")
                    
                    if email:
                        # Check verification status
                        if email_status == "not_valid":
                            logger.info(f"Email {email} found but verification status is 'not_valid'.")
                            return None
                        
                        logger.info(f"Found valid/unknown email: {email} (status: {email_status})")
                        return email
                
                # If we got rows but no email, it means search is complete and nothing was found
                if status == "completed":
                    logger.info("Search complete but no email address was found.")
                    return None
            
            if status == "completed":
                logger.info("Search complete but no results were returned.")
                return None

        logger.warning("Polling timed out. No email address was resolved.")
        return None

    def add_prospect_to_list(
        self, 
        list_id: str, 
        email: str, 
        first_name: str, 
        last_name: str,
        company_name: Optional[str] = None,
        company_domain: Optional[str] = None,
        linkedin_url: Optional[str] = None
    ) -> bool:
        """
        Adds a prospect to a Snov.io list with rate-limit retry handling.
        """
        url = f"{self.base_url}/v1/add-prospect-to-list"
        
        payload = {
            "listId": list_id,
            "email": email,
            "firstName": first_name,
            "lastName": last_name,
            "updateContact": 1
        }
        
        if company_name:
            payload["companyName"] = company_name
        if company_domain:
            if not company_domain.startswith("http://") and not company_domain.startswith("https://"):
                payload["companySite"] = f"https://{company_domain}"
            else:
                payload["companySite"] = company_domain
        if linkedin_url:
            formatted_linkedin = linkedin_url.strip()
            if not formatted_linkedin.endswith("&social"):
                if formatted_linkedin.endswith("/"):
                    formatted_linkedin += "&social"
                else:
                    formatted_linkedin += "/&social"
            payload["socialLinks[linkedIn]"] = formatted_linkedin
            
        logger.info(f"Adding prospect {first_name} {last_name} ({email}) to list {list_id}...")
        
        max_retries = 4
        backoff = 3.0
        
        for attempt in range(max_retries):
            token = self.get_valid_token()
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            payload_with_token = payload.copy()
            payload_with_token["access_token"] = token
            try:
                response = requests.post(url, data=payload_with_token, headers=headers, timeout=15)
                if response.status_code == 429:
                    logger.warning(f"Snov.io rate limit (429) hit during list addition. Retrying in {backoff} seconds...")
                    time.sleep(backoff)
                    backoff *= 2.0
                    continue
                response.raise_for_status()
                data = response.json()
                
                success = data.get("success") or data.get("status") == "added" or "id" in data
                if success:
                    logger.info("Successfully added prospect to Snov.io list.")
                    return True
                else:
                    logger.error(f"Snov.io failed to add prospect. Response: {data}")
                    return False
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Error adding prospect to list: {e}")
                    raise Exception(f"Failed to add prospect to Snov.io list: {e}") from e
                time.sleep(backoff)
                backoff *= 2.0

    def create_user_list(self, name: str) -> str:
        """
        Creates a new prospect list in Snov.io.
        """
        url = f"{self.base_url}/v1/lists"
        headers = self.get_headers()
        payload = {"name": name}
        
        logger.info(f"Creating prospect list with name '{name}'...")
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            success = data.get("success")
            list_data = data.get("data") or {}
            list_id = list_data.get("id")
            
            if success and list_id:
                logger.info(f"Successfully created prospect list. ID: {list_id}")
                return str(list_id)
            else:
                logger.error(f"Snov.io failed to create list. Response: {data}")
                raise Exception(f"Snov.io API returned unexpected response: {data}")
        except Exception as e:
            logger.error(f"Error creating prospect list: {e}")
            raise Exception(f"Failed to create prospect list in Snov.io: {e}")

    def get_prospects_by_list(self, list_id: str, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """
        Fetches prospects in a specific list.
        Uses POST /v1/prospect-list with JSON payload.
        """
        url = f"{self.base_url}/v1/prospect-list"
        
        payload = {
            "listId": list_id,
            "page": page,
            "perPage": per_page
        }
        
        logger.info(f"Fetching prospects for list {list_id} (page {page}, perPage {per_page})...")
        
        max_retries = 4
        backoff = 3.0
        
        for attempt in range(max_retries):
            headers = self.get_headers()
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=15)
                if response.status_code == 429:
                    logger.warning(f"Snov.io rate limit (429) hit during list prospects retrieval. Retrying in {backoff} seconds...")
                    time.sleep(backoff)
                    backoff *= 2.0
                    continue
                response.raise_for_status()
                return response.json()
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Error fetching prospects from list: {e}")
                    raise Exception(f"Failed to fetch prospects from Snov.io list: {e}") from e
                time.sleep(backoff)
                backoff *= 2.0

    def get_prospect_details(self, prospect_id: str) -> Dict[str, Any]:
        """
        Fetches full details of a prospect by ID.
        """
        url = f"{self.base_url}/v1/get-prospect-by-id"
        headers = self.get_headers()
        payload = {"id": prospect_id}
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get("success") and "data" in data:
                return data["data"]
            return {}
        except Exception as e:
            logger.error(f"Error fetching prospect details for ID {prospect_id}: {e}")
            return {}


