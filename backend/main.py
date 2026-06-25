import os
import logging
import csv
import io
import re
import concurrent.futures
from fastapi import FastAPI, HTTPException, status, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv
from snov_client import SnovioClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = FastAPI(title="Snov.io Integration API")

# Enable CORS for React frontend local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instantiate Snov.io Client
SNOV_CLIENT_ID = os.getenv("SNOV_CLIENT_ID", "")
SNOV_CLIENT_SECRET = os.getenv("SNOV_CLIENT_SECRET", "")

client = None
if SNOV_CLIENT_ID and SNOV_CLIENT_SECRET:
    client = SnovioClient(client_id=SNOV_CLIENT_ID, client_secret=SNOV_CLIENT_SECRET)
else:
    logger.warning("SNOV_CLIENT_ID or SNOV_CLIENT_SECRET are not set in the environment variables.")

def get_client() -> SnovioClient:
    """ Helper to ensure SnovioClient is configured before proceeding. """
    global client
    # Re-read if it was updated dynamically via .env
    if not client:
        client_id = os.getenv("SNOV_CLIENT_ID", "")
        client_secret = os.getenv("SNOV_CLIENT_SECRET", "")
        if client_id and client_secret:
            client = SnovioClient(client_id=client_id, client_secret=client_secret)
            
    if not client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Snov.io credentials are not configured. Please add SNOV_CLIENT_ID and SNOV_CLIENT_SECRET in backend/.env file."
        )
    return client

class ProspectRequest(BaseModel):
    list_id: str = Field(..., description="ID of the Snov.io prospect list to add to")
    first_name: str = Field(..., description="First name of the prospect")
    last_name: str = Field(..., description="Last name of the prospect")
    domain: str = Field(..., description="Company domain of the prospect")

    @field_validator("first_name", "last_name", "domain", "list_id")
    @classmethod
    def check_non_empty(cls, v: str, info) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError(f"{info.field_name} cannot be empty or blank")
        return stripped

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        domain = v.strip().lower()
        # Clean basic prepended URLs
        if domain.startswith("http://"):
            domain = domain[7:]
        elif domain.startswith("https://"):
            domain = domain[8:]
        if domain.startswith("www."):
            domain = domain[4:]
            
        # Allow either a valid domain or a company name (at least 2 characters)
        if len(domain) < 2:
            raise ValueError("Company domain or name must be at least 2 characters")
        return domain

@app.get("/api/lists")
async def get_lists():
    """
    Exposes Snov.io prospect lists to the React frontend.
    """
    snov_client = get_client()
    try:
        lists = snov_client.get_user_lists()
        return {"success": True, "lists": lists}
    except Exception as e:
        logger.error(f"Error fetching lists: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e)
        )

@app.get("/api/lists/{list_id}/prospects")
async def get_list_prospects(list_id: str, page: int = 1, limit: int = 20):
    """
    Retrieves prospects in a specific list, with pagination support.
    Enriches prospect lists with custom fields (firstName, lastName, companyName, companySite, linkedinUrl).
    """
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page number must be 1 or greater."
        )
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit must be between 1 and 100."
        )

    snov_client = get_client()
    try:
        data = snov_client.get_prospects_by_list(list_id=list_id, page=page, per_page=limit)
        prospects = data.get("prospects") or []
        
        def enrich_prospect(prospect):
            pid = prospect.get("id")
            if not pid:
                return prospect
            
            details = snov_client.get_prospect_details(pid)
            
            company_name = None
            company_site = None
            current_jobs = details.get("currentJob") or []
            if current_jobs and isinstance(current_jobs, list):
                job = current_jobs[0]
                if isinstance(job, dict):
                    company_name = job.get("companyName")
                    company_site = job.get("site")
            
            linkedin_url = None
            social_links = details.get("socialLinks") or details.get("social") or []
            if social_links and isinstance(social_links, list):
                for link_obj in social_links:
                    if isinstance(link_obj, dict):
                        link = link_obj.get("link")
                        source = link_obj.get("source") or link_obj.get("type") or ""
                        if "linkedin" in source.lower() or "linkedin" in (link or "").lower():
                            if not linkedin_url or (link and "&social" not in link and "&amp;social" not in link):
                                linkedin_url = link
            
            prospect["companyName"] = company_name
            prospect["companySite"] = company_site
            prospect["linkedinUrl"] = linkedin_url
            return prospect

        if prospects:
            max_workers = min(10, len(prospects))
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                enriched_prospects = list(executor.map(enrich_prospect, prospects))
                data["prospects"] = enriched_prospects
                
        return data
    except Exception as e:
        logger.error(f"Error fetching prospects for list {list_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e)
        )


class CreateListRequest(BaseModel):
    name: str = Field(..., description="Name of the new prospect list")

    @field_validator("name")
    @classmethod
    def check_non_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("List name cannot be empty or blank")
        return stripped

@app.post("/api/lists")
async def create_list(request: CreateListRequest):
    """
    Creates a new prospect list in Snov.io after validating it doesn't already exist.
    """
    snov_client = get_client()
    
    # 1. Fetch existing lists to check for duplicates (case-insensitive)
    try:
        existing_lists = snov_client.get_user_lists()
    except Exception as e:
        logger.error(f"Failed to fetch existing lists for validation: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to check existing lists: {str(e)}"
        )
        
    name_lower = request.name.lower()
    for lst in existing_lists:
        if lst.get("name", "").lower() == name_lower:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A prospect list named '{request.name}' already exists."
            )
            
    # 2. Create the list on Snov.io
    try:
        new_list_id = snov_client.create_user_list(request.name)
        return {
            "success": True,
            "list": {
                "id": new_list_id,
                "name": request.name,
                "contacts": 0
            },
            "message": f"Successfully created prospect list '{request.name}'!"
        }
    except Exception as e:
        logger.error(f"Failed to create prospect list: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Snov.io API error: {str(e)}"
        )

@app.post("/api/prospects")
async def add_prospect(request: ProspectRequest):
    """
    Attempts to find a business email for the prospect, and adds the
    prospect to the specified Snov.io list if found.
    If lookup or insertion fails, the prospect is routed to the fallback list.
    """
    snov_client = get_client()
    fallback_list_id = os.getenv("EMAIL_NOT_FOUND_LIST_ID", "").strip()

    # 1. Determine company name and resolve company domain
    input_val = request.domain.strip()
    
    if snov_client.is_valid_domain(input_val):
        resolved_domain = input_val
        parts = input_val.split('.')
        company_name = parts[0].capitalize() if len(parts) > 1 else input_val.capitalize()
    else:
        company_name = input_val
        try:
            resolved_domain = snov_client.find_domain_via_custom_api(company_name)
        except Exception as e:
            logger.error(f"Error resolving domain via custom API: {e}")
            resolved_domain = None

    # 2. Find LinkedIn Profile URL using Custom API (non-blocking)
    linkedin_url = None
    try:
        linkedin_url = snov_client.find_linkedin_via_custom_api(
            first_name=request.first_name,
            last_name=request.last_name,
            company_name=company_name
        )
    except Exception as e:
        logger.error(f"Error fetching LinkedIn URL: {e}")

    # Fallback helper inside endpoint
    def add_to_fallback(domain_to_use: str, reason: str):
        if fallback_list_id:
            dummy_email = make_dummy_email(request.first_name, request.last_name, domain_to_use or company_name)
            try:
                logger.info(f"Adding failed single prospect to fallback list: {request.first_name} {request.last_name} ({dummy_email})")
                snov_client.add_prospect_to_list(
                    list_id=fallback_list_id,
                    email=dummy_email,
                    first_name=request.first_name,
                    last_name=request.last_name,
                    company_name=company_name,
                    company_domain=domain_to_use,
                    linkedin_url=linkedin_url
                )
            except Exception as e:
                logger.error(f"Failed to add failed single prospect to fallback list: {e}")

    # 3. If domain is not resolved, route to fallback immediately
    if not resolved_domain:
        logger.info(f"Could not resolve domain for '{company_name}'. Routing to fallback list.")
        add_to_fallback(None, "Could not resolve company domain")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not resolve company domain for '{company_name}'. Prospect routed to Email Not Found list."
        )

    # 4. Search for business email using Snov.io Email Finder API
    resolved_email = None
    try:
        resolved_email = snov_client.find_email_by_name_and_domain(
            first_name=request.first_name,
            last_name=request.last_name,
            domain=resolved_domain
        )
    except Exception as e:
        logger.error(f"Email Finder failed: {e}")
        add_to_fallback(resolved_domain, f"Email Finder failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Snov.io Email Finder failed: {str(e)}"
        )

    # 5. Handle scenario where no email is found
    if not resolved_email:
        logger.info(f"No email address resolved for {request.first_name} {request.last_name} at {resolved_domain}.")
        add_to_fallback(resolved_domain, "No business email address found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No business email address found for this prospect. Prospect was routed to Email Not Found list."
        )

    # 6. Add prospect to the selected Snov.io list
    try:
        success = snov_client.add_prospect_to_list(
            list_id=request.list_id,
            email=resolved_email,
            first_name=request.first_name,
            last_name=request.last_name,
            company_name=company_name,
            company_domain=resolved_domain,
            linkedin_url=linkedin_url
        )
        if not success:
            add_to_fallback(resolved_domain, "Failed to add prospect to main list")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add the prospect to the Snov.io list."
            )
            
        return {
            "success": True,
            "email": resolved_email,
            "message": f"Successfully resolved email ({resolved_email}) and added prospect to the list!"
        }
    except Exception as e:
        logger.error(f"Failed to add prospect to list: {e}")
        if not isinstance(e, HTTPException):
            add_to_fallback(resolved_domain, f"Snov.io API error adding prospect: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Snov.io Prospect Management error: {str(e)}"
            )
        raise e


def make_dummy_email(first_name: str, last_name: str, company: str) -> str:
    # Clean names and company to contain only alphanumeric characters
    fn = re.sub(r'[^a-zA-Z0-9]', '', first_name).lower() if first_name else "prospect"
    ln = re.sub(r'[^a-zA-Z0-9]', '', last_name).lower() if last_name else "prospect"
    comp = re.sub(r'[^a-zA-Z0-9.]', '', company).lower() if company else "unknown"
    comp = comp.replace('..', '.').strip('.')
    if not fn: fn = "prospect"
    if not ln: ln = "prospect"
    if not comp: comp = "unknown"
    return f"{fn}.{ln}@{comp}.no-email-found-cw1.com"

@app.post("/api/prospects/bulk")
async def bulk_add_prospects(list_id: str = Form(...), file: UploadFile = File(...)):
    """
    Accepts a CSV file of prospects, parses and validates headers,
    and concurrently resolves emails and adds them to Snov.io.
    """
    # 1. Read file content
    contents = await file.read()
    
    # 2. Check if file is CSV
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only CSV files are supported.")
        
    # 3. Parse CSV
    try:
        decoded = contents.decode('utf-8-sig') # handle UTF-8 with BOM if present
        csv_file = io.StringIO(decoded)
        reader = csv.DictReader(csv_file)
        
        if not reader.fieldnames:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV file is empty.")
            
        # Clean and normalize field names
        normalized_headers = []
        for h in reader.fieldnames:
            h_clean = h.strip().lower()
            if h_clean == "first name":
                normalized_headers.append("First Name")
            elif h_clean in ["last name", "last-name"]:
                normalized_headers.append("Last Name")
            elif h_clean in [
                "company domain/name",
                "company name / domain",
                "company name/domain",
                "company domain or name",
                "company name or domain",
                "company name",
                "company domain",
                "domain"
            ]:
                normalized_headers.append("Company Domain/Name")
            else:
                normalized_headers.append(h.strip())
                
        # Enforce that only these three normalized headers exist
        expected_headers = ["First Name", "Last Name", "Company Domain/Name"]
        if set(normalized_headers) != set(expected_headers) or len(normalized_headers) != 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The CSV file must contain only these three headers: 'First Name', 'Last Name', and 'Company Domain/Name'."
            )
            
        # Re-assign normalized headers so row.get() matches the expected keys
        reader.fieldnames = normalized_headers

            
        rows = list(reader)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to parse CSV: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to parse CSV file: {str(e)}")
        
    if not rows:
        return {
            "total": 0,
            "successCount": 0,
            "failedCount": 0,
            "failedRecords": []
        }
        
    snov_client = get_client()
    fallback_list_id = os.getenv("EMAIL_NOT_FOUND_LIST_ID", "").strip()
    
    def add_failed_prospect_to_fallback(
        first_name: str, 
        last_name: str, 
        company_name: str, 
        company_domain: Optional[str], 
        linkedin_url: Optional[str], 
        reason: str
    ):
        if not fallback_list_id:
            logger.warning("EMAIL_NOT_FOUND_LIST_ID is not configured in env. Skipping fallback list routing.")
            return
            
        dummy_email = make_dummy_email(first_name, last_name, company_domain or company_name)
        try:
            logger.info(f"Adding failed prospect to fallback list: {first_name} {last_name} ({dummy_email})")
            snov_client.add_prospect_to_list(
                list_id=fallback_list_id,
                email=dummy_email,
                first_name=first_name or "Unknown",
                last_name=last_name or "Prospect",
                company_name=company_name,
                company_domain=company_domain,
                linkedin_url=linkedin_url
            )
        except Exception as e:
            logger.error(f"Failed to add prospect to fallback list: {e}")

    def process_row(row):
        first_name = row.get("First Name", "").strip()
        last_name = row.get("Last Name", "").strip()
        domain_or_name = row.get("Company Domain/Name", "").strip()
        
        # Validation checks
        if not first_name or not last_name or not domain_or_name:
            reason = "Missing required fields"
            add_failed_prospect_to_fallback(first_name, last_name, domain_or_name, None, None, reason)
            return {
                "success": False,
                "first_name": first_name or "[Blank]",
                "last_name": last_name or "[Blank]",
                "company": domain_or_name or "[Blank]",
                "reason": reason
            }
            
        # Determine company name and resolve company domain
        if snov_client.is_valid_domain(domain_or_name):
            target_domain = domain_or_name
            parts = domain_or_name.split('.')
            company_name = parts[0].capitalize() if len(parts) > 1 else domain_or_name.capitalize()
        else:
            company_name = domain_or_name
            try:
                target_domain = snov_client.find_domain_via_custom_api(company_name)
            except Exception as e:
                logger.error(f"Error resolving domain via custom API in bulk: {e}")
                target_domain = None

        # Call LinkedIn Profile Finder API (non-blocking)
        linkedin_url = None
        try:
            linkedin_url = snov_client.find_linkedin_via_custom_api(
                first_name=first_name,
                last_name=last_name,
                company_name=company_name
            )
        except Exception as e:
            logger.error(f"Error fetching LinkedIn URL in bulk: {e}")

        # If domain was not resolved, route to fallback immediately
        if not target_domain:
            reason = "Could not resolve company domain"
            add_failed_prospect_to_fallback(first_name, last_name, company_name, None, linkedin_url, reason)
            return {
                "success": False,
                "first_name": first_name,
                "last_name": last_name,
                "company": domain_or_name,
                "reason": reason
            }
                
        # Find email using domain
        email = None
        try:
            email = snov_client.find_email_by_name_and_domain(first_name, last_name, target_domain)
        except Exception as e:
            reason = f"Email Finder failed: {str(e)}"
            add_failed_prospect_to_fallback(first_name, last_name, company_name, target_domain, linkedin_url, reason)
            return {
                "success": False,
                "first_name": first_name,
                "last_name": last_name,
                "company": domain_or_name,
                "reason": reason
            }
            
        if not email:
            reason = "No business email address found"
            add_failed_prospect_to_fallback(first_name, last_name, company_name, target_domain, linkedin_url, reason)
            return {
                "success": False,
                "first_name": first_name,
                "last_name": last_name,
                "company": domain_or_name,
                "reason": reason
            }
            
        # Add to prospect list
        try:
            added = snov_client.add_prospect_to_list(
                list_id=list_id,
                email=email,
                first_name=first_name,
                last_name=last_name,
                company_name=company_name,
                company_domain=target_domain,
                linkedin_url=linkedin_url
            )
            if added:
                return {"success": True}
            else:
                reason = "Failed to add prospect to list"
                add_failed_prospect_to_fallback(first_name, last_name, company_name, target_domain, linkedin_url, reason)
                return {
                    "success": False,
                    "first_name": first_name,
                    "last_name": last_name,
                    "company": domain_or_name,
                    "reason": reason
                }
        except Exception as e:
            reason = f"Snov.io API error adding prospect: {str(e)}"
            add_failed_prospect_to_fallback(first_name, last_name, company_name, target_domain, linkedin_url, reason)
            return {
                "success": False,
                "first_name": first_name,
                "last_name": last_name,
                "company": domain_or_name,
                "reason": reason
            }

    # Run processing concurrently with ThreadPoolExecutor (max 5 parallel threads)
    max_workers = min(5, len(rows))
    results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_row = {executor.submit(process_row, row): row for row in rows}
        for future in concurrent.futures.as_completed(future_to_row):
            try:
                res = future.result()
                results.append(res)
            except Exception as e:
                row = future_to_row[future]
                logger.error(f"Worker thread exception for row {row}: {e}")
                results.append({
                    "success": False,
                    "first_name": row.get("First Name", ""),
                    "last_name": row.get("Last Name", ""),
                    "company": row.get("Company Domain/Name", ""),
                    "reason": f"System error during processing: {str(e)}"
                })

    success_count = sum(1 for r in results if r["success"])
    failed_records = [r for r in results if not r["success"]]
    failed_count = len(failed_records)
    
    return {
        "total": len(rows),
        "successCount": success_count,
        "failedCount": failed_count,
        "failedRecords": failed_records
    }
