import os
import logging
from fastapi import FastAPI, HTTPException, status
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
            
        # Basic domain format validation (contains a dot and valid chars)
        if "." not in domain or len(domain) < 4:
            raise ValueError("Invalid domain name format")
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

@app.post("/api/prospects")
async def add_prospect(request: ProspectRequest):
    """
    Attempts to find a business email for the prospect, and adds the
    prospect to the specified Snov.io list if found.
    """
    snov_client = get_client()
    
    # 1. Look up email using Snov.io Email Finder API
    try:
        resolved_email = snov_client.find_email_by_name_and_domain(
            first_name=request.first_name,
            last_name=request.last_name,
            domain=request.domain
        )
    except Exception as e:
        logger.error(f"Email Finder failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Snov.io Email Finder failed: {str(e)}"
        )

    # 2. Handle scenario where no email is found
    if not resolved_email:
        logger.info(f"No email address resolved for {request.first_name} {request.last_name} at {request.domain}.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No business email address found for this prospect. Prospect was not created."
        )

    # 3. Add prospect to the selected Snov.io list
    try:
        success = snov_client.add_prospect_to_list(
            list_id=request.list_id,
            email=resolved_email,
            first_name=request.first_name,
            last_name=request.last_name
        )
        if not success:
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
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Snov.io Prospect Management error: {str(e)}"
        )
