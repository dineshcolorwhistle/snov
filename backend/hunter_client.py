import logging
import requests
from typing import Dict, Any, List, Optional
from base_provider import BaseProvider

logger = logging.getLogger(__name__)

class HunterioClient(BaseProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.hunter.io/v2"

    def get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def get_user_lists(self) -> List[Dict[str, Any]]:
        """
        Fetches lead lists from Hunter.io.
        Endpoint: GET /v2/leads_lists
        """
        url = f"{self.base_url}/leads_lists"
        headers = self.get_headers()
        try:
            logger.info("Fetching lead lists from Hunter.io...")
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            raw_lists = data.get("data", {}).get("leads_lists", [])
            standardized_lists = []
            
            for lst in raw_lists:
                standardized_lists.append({
                    "id": str(lst.get("id")),
                    "name": lst.get("name", "Unnamed List"),
                    "contacts": int(lst.get("leads_count", 0))
                })
            return standardized_lists
        except Exception as e:
            logger.error(f"Failed to fetch lists from Hunter.io: {e}")
            raise Exception(f"Failed to fetch lists from Hunter.io: {e}")

    def get_prospects_by_list(self, list_id: str, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """
        Fetches leads in a specific list.
        Endpoint: GET /v2/leads
        """
        url = f"{self.base_url}/leads"
        headers = self.get_headers()
        
        # Hunter uses limit and offset for pagination
        offset = (page - 1) * per_page
        params = {
            "leads_list_id": list_id,
            "limit": per_page,
            "offset": offset
        }
        
        try:
            logger.info(f"Fetching leads for list {list_id} from Hunter.io...")
            response = requests.get(url, headers=headers, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            raw_leads = data.get("data", {}).get("leads", [])
            prospects = []
            
            for lead in raw_leads:
                prospects.append({
                    "id": str(lead.get("id")),
                    "firstName": lead.get("first_name") or "",
                    "lastName": lead.get("last_name") or "",
                    "companyName": lead.get("company") or "",
                    "companySite": lead.get("website") or "",
                    "emails": [{"email": lead.get("email")}] if lead.get("email") else [],
                    "linkedinUrl": lead.get("linkedin_url") or ""
                })
            
            total_count = data.get("meta", {}).get("total", len(prospects))
            
            return {
                "success": True,
                "prospects": prospects,
                "list": {
                    "contacts": total_count
                }
            }
        except Exception as e:
            logger.error(f"Failed to fetch leads for list {list_id} from Hunter.io: {e}")
            raise Exception(f"Failed to fetch leads from Hunter.io: {e}")

    def create_user_list(self, name: str) -> str:
        """
        Creates a new lead list on Hunter.io.
        Endpoint: POST /v2/leads_lists
        """
        url = f"{self.base_url}/leads_lists"
        headers = self.get_headers()
        payload = {
            "name": name
        }
        try:
            logger.info(f"Creating Hunter.io lead list with name '{name}'...")
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            list_id = data.get("data", {}).get("id")
            if list_id:
                return str(list_id)
            else:
                raise Exception(f"Hunter.io did not return list ID: {data}")
        except Exception as e:
            logger.error(f"Failed to create lead list on Hunter.io: {e}")
            raise Exception(f"Failed to create lead list on Hunter.io: {e}")

    def find_email_by_name_and_domain(self, first_name: str, last_name: str, domain: str) -> Optional[str]:
        """
        Finds a business email on Hunter.io.
        Endpoint: GET /v2/email-finder
        """
        url = f"{self.base_url}/email-finder"
        headers = self.get_headers()
        params = {
            "domain": domain,
            "first_name": first_name,
            "last_name": last_name
        }
        try:
            logger.info(f"Searching email for {first_name} {last_name} @ {domain} via Hunter.io...")
            response = requests.get(url, headers=headers, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            email = data.get("data", {}).get("email")
            if email:
                logger.info(f"Hunter.io Email Finder found email: {email}")
                return email
            return None
        except Exception as e:
            logger.error(f"Hunter.io Email Finder failed: {e}")
            raise Exception(f"Hunter.io Email Finder failed: {e}")

    def verify_email(self, email: str) -> Dict[str, Any]:
        """
        Verifies an email address using Hunter.io's email-verifier.
        Endpoint: GET /v2/email-verifier
        """
        url = f"{self.base_url}/email-verifier"
        headers = self.get_headers()
        params = {
            "email": email
        }
        try:
            logger.info(f"Verifying email {email} via Hunter.io...")
            response = requests.get(url, headers=headers, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            result = data.get("data", {}).get("result")
            logger.info(f"Hunter.io verification result for {email}: {result}")
            
            # Hunter.io results: deliverable, undeliverable, risky, unknown
            if result == "deliverable":
                return {"verified": True, "status": result}
            else:
                return {"verified": False, "status": result or "unknown"}
        except Exception as e:
            logger.error(f"Hunter.io Email Verifier failed: {e}")
            return {"verified": False, "status": "verification_error"}

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
        Adds a lead to a Hunter.io list.
        Endpoint: POST /v2/leads
        """
        url = f"{self.base_url}/leads"
        headers = self.get_headers()
        
        payload = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "leads_list_id": int(list_id)
        }
        if company_name:
            payload["company"] = company_name
        if company_domain:
            payload["website"] = company_domain
        if linkedin_url:
            payload["linkedin_url"] = linkedin_url
            
        try:
            logger.info(f"Adding lead {first_name} {last_name} ({email}) to Hunter.io list {list_id}...")
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            lead_id = data.get("data", {}).get("id")
            if lead_id:
                logger.info("Successfully added lead to Hunter.io list.")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to add lead to Hunter.io list: {e}")
            raise Exception(f"Failed to add lead to Hunter.io list: {e}")
