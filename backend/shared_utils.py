import os
import re
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

def is_valid_domain(domain: str) -> bool:
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

def find_domain_via_custom_api(company_name: str) -> Optional[str]:
    """
    Calls the custom Domain Finder API to retrieve the company's domain.
    """
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

def find_linkedin_via_custom_api(first_name: str, last_name: str, company_name: str) -> Optional[str]:
    """
    Calls the custom LinkedIn Profile API to retrieve the prospect's LinkedIn URL.
    """
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
