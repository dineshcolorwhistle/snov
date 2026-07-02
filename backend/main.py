import os
import logging
import csv
import io
import re
import concurrent.futures
from typing import Optional, List
from fastapi import FastAPI, HTTPException, status, File, UploadFile, Form, Depends, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv

import db
from auth_utils import verify_supabase_token
from base_provider import BaseProvider
from snov_client import SnovioClient
from hunter_client import HunterioClient
import shared_utils

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Dependency that validates the Supabase JWT token and returns the user payload.
    """
    token = credentials.credentials
    user = verify_supabase_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate Supabase credentials or session expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

app = FastAPI(title="Multi-Platform Lead Automation API")

# Enable CORS for React frontend local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    """Initialize database tables on startup."""
    db.init_db()

def get_provider_client(platform: str, user: dict) -> BaseProvider:
    """
    Resolves and instantiates the appropriate lead provider client.
    First checks the user's settings in Supabase, and falls back to backend .env variables.
    """
    user_settings = db.get_user_settings(user["id"])
    
    if platform == "snov":
        client_id = user_settings.get("snov_client_id") or os.getenv("SNOV_CLIENT_ID", "").strip()
        client_secret = user_settings.get("snov_client_secret") or os.getenv("SNOV_CLIENT_SECRET", "").strip()
        if not client_id or not client_secret:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Snov.io credentials are not configured. Please add them in the Settings modal."
            )
        return SnovioClient(client_id=client_id, client_secret=client_secret)
        
    elif platform == "hunter":
        api_key = user_settings.get("hunter_api_key") or os.getenv("HUNTER_API_KEY", "").strip()
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Hunter.io API key is not configured. Please add it in the Settings modal."
            )
        return HunterioClient(api_key=api_key)
        
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported platform: {platform}"
        )

# --- Pydantic Models ---

class CreateListRequest(BaseModel):
    name: str = Field(..., description="Name of the new prospect list")

    @field_validator("name")
    @classmethod
    def check_non_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("List name cannot be empty or blank")
        return stripped

class ProspectRequest(BaseModel):
    list_id: str = Field(..., description="ID of the platform list to add to")
    first_name: str = Field(..., description="First name of the prospect")
    last_name: str = Field(..., description="Last name of the prospect")
    company_name: str = Field(..., description="Company name of the prospect")
    location: Optional[str] = Field(None, description="Location of the prospect")
    title: Optional[str] = Field(None, description="Title of the prospect")
    verify_emails: bool = Field(False, description="Whether to verify email addresses")
    unverified_list_id: Optional[str] = Field(None, description="ID of the platform list for unverified emails")

    @field_validator("first_name", "last_name", "company_name", "list_id")
    @classmethod
    def check_non_empty(cls, v: str, info) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError(f"{info.field_name} cannot be empty or blank")
        return stripped

class UserSettingsRequest(BaseModel):
    snov_client_id: Optional[str] = None
    snov_client_secret: Optional[str] = None
    hunter_api_key: Optional[str] = None
    email_not_found_list_id: Optional[str] = None
    hunter_fallback_list_id: Optional[str] = None

# --- API Endpoints ---

@app.get("/api/settings")
async def get_settings(current_user: dict = Depends(get_current_user)):
    """Retrieves the current user's settings."""
    settings = db.get_user_settings(current_user["id"])
    return {"success": True, "settings": settings}

@app.post("/api/settings")
async def save_settings(request: UserSettingsRequest, current_user: dict = Depends(get_current_user)):
    """Saves the current user's settings."""
    success = db.save_user_settings(current_user["id"], request.dict())
    if success:
        return {"success": True, "message": "Settings saved successfully!"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save settings to the database."
        )

@app.get("/api/logs/{log_type}")
async def get_tracking_logs(
    log_type: str,
    platform: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """Retrieves paginated tracking logs by type."""
    try:
        logs, total = db.get_logs(log_type, current_user["id"], platform, page, limit)
        return {
            "success": True,
            "logs": logs,
            "total": total,
            "page": page,
            "limit": limit
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching logs: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database retrieval error")

@app.get("/api/lists")
async def get_lists(platform: str = "snov", current_user: dict = Depends(get_current_user)):
    """Fetches prospect lists for the selected platform."""
    client = get_provider_client(platform, current_user)
    try:
        lists = client.get_user_lists()
        return {"success": True, "lists": lists}
    except Exception as e:
        logger.error(f"Error fetching lists for {platform}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e)
        )

@app.get("/api/lists/{list_id}/prospects")
async def get_list_prospects(
    list_id: str,
    platform: str = "snov",
    page: int = 1,
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """Retrieves prospects in a specific list, with pagination."""
    if page < 1:
        raise HTTPException(status_code=400, detail="Page must be 1 or greater.")
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 100.")

    client = get_provider_client(platform, current_user)
    try:
        data = client.get_prospects_by_list(list_id=list_id, page=page, per_page=limit)
        
        # Snov.io requires separate enrichment for detailed fields
        if platform == "snov" and isinstance(client, SnovioClient):
            prospects = data.get("prospects") or []
            
            def enrich_prospect(prospect):
                pid = prospect.get("id")
                if not pid:
                    return prospect
                
                details = client.get_prospect_details(pid)
                
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
                    data["prospects"] = list(executor.map(enrich_prospect, prospects))
                    
        return data
    except Exception as e:
        logger.error(f"Error fetching prospects for list {list_id} ({platform}): {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e)
        )

@app.post("/api/lists")
async def create_list(
    request: CreateListRequest,
    platform: str = "snov",
    current_user: dict = Depends(get_current_user)
):
    """Creates a new list on the selected platform."""
    client = get_provider_client(platform, current_user)
    
    # Check for duplicates first (case-insensitive)
    try:
        existing_lists = client.get_user_lists()
    except Exception as e:
        logger.error(f"Failed to fetch lists: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to check existing lists: {str(e)}")
        
    name_lower = request.name.lower()
    for lst in existing_lists:
        if lst.get("name", "").lower() == name_lower:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A list named '{request.name}' already exists."
            )
            
    try:
        new_list_id = client.create_user_list(request.name)
        return {
            "success": True,
            "list": {
                "id": new_list_id,
                "name": request.name,
                "contacts": 0
            },
            "message": f"Successfully created list '{request.name}' on {platform.capitalize()}!"
        }
    except Exception as e:
        logger.error(f"Failed to create list: {e}")
        raise HTTPException(status_code=502, detail=f"API error: {str(e)}")

@app.post("/api/prospects")
async def add_prospect(
    request: ProspectRequest,
    platform: str = "snov",
    current_user: dict = Depends(get_current_user)
):
    """
    Processes a single prospect search: resolves domain, finds LinkedIn, 
    finds email, verifies email, and adds to list. Logs failures to Supabase.
    """
    client = get_provider_client(platform, current_user)
    uid = current_user["id"]
    input_val = request.company_name.strip()
    prospect_location = (request.location or "").strip() or None
    prospect_title = (request.title or "").strip() or None

    # 1. Resolve Company Name & Domain
    if shared_utils.is_valid_domain(input_val):
        resolved_domain = input_val
        parts = input_val.split('.')
        company_name = parts[0].capitalize() if len(parts) > 1 else input_val.capitalize()
    else:
        company_name = input_val
        resolved_domain = shared_utils.find_domain_via_custom_api(company_name)
        if not resolved_domain:
            logger.info(f"Could not resolve domain for '{company_name}'. Logging to DB.")
            db.log_domain_not_found(uid, request.first_name, request.last_name, company_name, None, platform, location=prospect_location, title=prospect_title)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not resolve company domain for '{company_name}'. Logged to database."
            )

    # 2. Find LinkedIn Profile (non-blocking, logged if not found)
    linkedin_url = shared_utils.find_linkedin_via_custom_api(
        first_name=request.first_name,
        last_name=request.last_name,
        company_name=company_name
    )
    if not linkedin_url:
        logger.info("LinkedIn URL not found. Logging to DB.")
        db.log_linkedin_not_found(uid, request.first_name, request.last_name, company_name, platform, location=prospect_location, title=prospect_title)

    # 3. Find Business Email
    resolved_email = None
    try:
        resolved_email = client.find_email_by_name_and_domain(
            first_name=request.first_name,
            last_name=request.last_name,
            domain=resolved_domain
        )
    except Exception as e:
        logger.error(f"Email Finder failed: {e}")
        db.log_email_not_found(uid, request.first_name, request.last_name, company_name, resolved_domain, linkedin_url, platform, location=prospect_location, title=prospect_title)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Email Finder API failed: {str(e)}. Logged to database."
        )

    if not resolved_email:
        logger.info("No email address resolved. Logging to DB.")
        db.log_email_not_found(uid, request.first_name, request.last_name, company_name, resolved_domain, linkedin_url, platform, location=prospect_location, title=prospect_title)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No business email address found. Logged to database."
        )

    # 4. Verify Business Email
    if request.verify_emails:
        if not request.unverified_list_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An unverified list must be specified when email verification is enabled."
            )
        verification = client.verify_email(resolved_email)
        if not verification.get("verified"):
            status_str = verification.get("status", "unverified")
            logger.info(f"Email found but failed verification: {resolved_email} (status: {status_str}). Logging to DB.")
            db.log_email_unverified(
                uid, request.first_name, request.last_name, company_name, 
                resolved_domain, resolved_email, linkedin_url, status_str, platform,
                location=prospect_location, title=prospect_title
            )
            # Add to unverified list
            try:
                success = client.add_prospect_to_list(
                    list_id=request.unverified_list_id,
                    email=resolved_email,
                    first_name=request.first_name,
                    last_name=request.last_name,
                    company_name=company_name,
                    company_domain=resolved_domain,
                    linkedin_url=linkedin_url,
                    location=prospect_location,
                    title=prospect_title
                )
                if not success:
                    raise Exception("Platform unverified list addition returned False.")
                return {
                    "success": True,
                    "email": resolved_email,
                    "message": f"Successfully resolved ({resolved_email}) and added unverified lead to list!"
                }
            except Exception as e:
                logger.error(f"Failed to add unverified lead to list: {e}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Failed to add unverified lead to list: {str(e)}"
                )

    # 5. Add Prospect/Lead to the selected list
    try:
        success = client.add_prospect_to_list(
            list_id=request.list_id,
            email=resolved_email,
            first_name=request.first_name,
            last_name=request.last_name,
            company_name=company_name,
            company_domain=resolved_domain,
            linkedin_url=linkedin_url,
            location=prospect_location,
            title=prospect_title
        )
        if not success:
            raise Exception("Platform list addition returned False.")
            
        return {
            "success": True,
            "email": resolved_email,
            "message": f"Successfully resolved ({resolved_email}) and added lead to list!"
        }
    except Exception as e:
        logger.error(f"Failed to add lead to list: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to add lead to list: {str(e)}"
        )

@app.post("/api/prospects/bulk")
async def bulk_add_prospects(
    list_id: str = Form(...),
    unverified_list_id: str = Form(None),
    file: UploadFile = File(...),
    platform: str = Form("snov"),
    verify_emails: bool = Form(False),
    current_user: dict = Depends(get_current_user)
):
    """
    Accepts a CSV file of prospects, processes them concurrently,
    verifies emails, and logs any failures to Supabase.
    """
    if verify_emails and not unverified_list_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An unverified list must be specified when email verification is enabled."
        )
        
    contents = await file.read()
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only CSV files are supported.")
        
    try:
        decoded = contents.decode('utf-8-sig')
        csv_file = io.StringIO(decoded)
        reader = csv.DictReader(csv_file)
        
        if not reader.fieldnames:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV file is empty.")
            
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
                normalized_headers.append("Company Name")
            elif h_clean == "location":
                normalized_headers.append("Location")
            elif h_clean == "title":
                normalized_headers.append("Title")
            else:
                normalized_headers.append(h.strip())
                
        expected_headers = {"First Name", "Last Name", "Company Name", "Location", "Title"}
        present_headers = set(normalized_headers)
        missing = expected_headers - present_headers
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"The CSV file is missing required headers: {', '.join(sorted(missing))}. Required: First Name, Last Name, Company Name, Location, Title."
            )
        
        # If more than 10 columns, filter to only required headers
        if len(normalized_headers) > 10:
            normalized_headers = [h if h in expected_headers else None for h in normalized_headers]
            
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
        
    client = get_provider_client(platform, current_user)
    uid = current_user["id"]
    
    def process_row(row):
        first_name = row.get("First Name", "").strip()
        last_name = row.get("Last Name", "").strip()
        domain_or_name = row.get("Company Name", "").strip()
        row_location = (row.get("Location") or "").strip() or None
        row_title = (row.get("Title") or "").strip() or None
        
        if not first_name or not last_name or not domain_or_name:
            reason = "Missing required fields"
            db.log_domain_not_found(uid, first_name, last_name, domain_or_name or "[Blank]", None, platform, location=row_location, title=row_title)
            return {
                "success": False,
                "first_name": first_name or "[Blank]",
                "last_name": last_name or "[Blank]",
                "company": domain_or_name or "[Blank]",
                "reason": reason
            }
            
        # 1. Resolve Company Name & Domain
        if shared_utils.is_valid_domain(domain_or_name):
            target_domain = domain_or_name
            parts = domain_or_name.split('.')
            company_name = parts[0].capitalize() if len(parts) > 1 else domain_or_name.capitalize()
        else:
            company_name = domain_or_name
            target_domain = shared_utils.find_domain_via_custom_api(company_name)
            if not target_domain:
                reason = "Could not resolve company domain"
                db.log_domain_not_found(uid, first_name, last_name, company_name, None, platform, location=row_location, title=row_title)
                return {
                    "success": False,
                    "first_name": first_name,
                    "last_name": last_name,
                    "company": domain_or_name,
                    "reason": reason
                }

        # 2. Find LinkedIn Profile (non-blocking)
        linkedin_url = shared_utils.find_linkedin_via_custom_api(
            first_name=first_name,
            last_name=last_name,
            company_name=company_name
        )
        if not linkedin_url:
            db.log_linkedin_not_found(uid, first_name, last_name, company_name, platform, location=row_location, title=row_title)

        # 3. Find Business Email
        email = None
        try:
            email = client.find_email_by_name_and_domain(first_name, last_name, target_domain)
        except Exception as e:
            reason = f"Email Finder failed: {str(e)}"
            db.log_email_not_found(uid, first_name, last_name, company_name, target_domain, linkedin_url, platform, location=row_location, title=row_title)
            return {
                "success": False,
                "first_name": first_name,
                "last_name": last_name,
                "company": domain_or_name,
                "reason": reason
            }
            
        if not email:
            reason = "No business email address found"
            db.log_email_not_found(uid, first_name, last_name, company_name, target_domain, linkedin_url, platform, location=row_location, title=row_title)
            return {
                "success": False,
                "first_name": first_name,
                "last_name": last_name,
                "company": domain_or_name,
                "reason": reason
            }
            
        # 4. Verify Business Email
        if verify_emails:
            verification = client.verify_email(email)
            if not verification.get("verified"):
                status_str = verification.get("status", "unverified")
                try:
                    added = client.add_prospect_to_list(
                        list_id=unverified_list_id,
                        email=email,
                        first_name=first_name,
                        last_name=last_name,
                        company_name=company_name,
                        company_domain=target_domain,
                        linkedin_url=linkedin_url,
                        location=row_location,
                        title=row_title
                    )
                    if added:
                        return {"success": True}
                    else:
                        return {
                            "success": False,
                            "first_name": first_name,
                            "last_name": last_name,
                            "company": domain_or_name,
                            "reason": f"Failed to add unverified lead to unverified list"
                        }
                except Exception as e:
                    return {
                        "success": False,
                        "first_name": first_name,
                        "last_name": last_name,
                        "company": domain_or_name,
                        "reason": f"API error adding unverified lead: {str(e)}"
                    }

        # 5. Add to List
        try:
            added = client.add_prospect_to_list(
                list_id=list_id,
                email=email,
                first_name=first_name,
                last_name=last_name,
                company_name=company_name,
                company_domain=target_domain,
                linkedin_url=linkedin_url,
                location=row_location,
                title=row_title
            )
            if added:
                return {"success": True}
            else:
                reason = "Failed to add lead to platform list"
                db.log_email_unverified(uid, first_name, last_name, company_name, target_domain, email, linkedin_url, "list_addition_failed", platform, location=row_location, title=row_title)
                return {
                    "success": False,
                    "first_name": first_name,
                    "last_name": last_name,
                    "company": domain_or_name,
                    "reason": reason
                }
        except Exception as e:
            reason = f"API error adding lead: {str(e)}"
            db.log_email_unverified(uid, first_name, last_name, company_name, target_domain, email, linkedin_url, "api_error_on_addition", platform, location=row_location, title=row_title)
            return {
                "success": False,
                "first_name": first_name,
                "last_name": last_name,
                "company": domain_or_name,
                "reason": reason
            }

    # Run processing concurrently
    max_workers = min(15, len(rows))
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
                    "company": row.get("Company Name", ""),
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
