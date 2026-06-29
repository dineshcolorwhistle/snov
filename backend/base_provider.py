from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseProvider(ABC):
    @abstractmethod
    def get_user_lists(self) -> List[Dict[str, Any]]:
        """
        Fetches all lead/prospect lists from the platform.
        Returns a list of dicts: [{"id": str, "name": str, "contacts": int}]
        """
        pass

    @abstractmethod
    def get_prospects_by_list(self, list_id: str, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """
        Fetches prospects in a specific list.
        Returns a dict: {"success": bool, "prospects": [...]}
        """
        pass

    @abstractmethod
    def create_user_list(self, name: str) -> str:
        """
        Creates a new lead list on the platform.
        Returns the ID of the newly created list.
        """
        pass

    @abstractmethod
    def find_email_by_name_and_domain(self, first_name: str, last_name: str, domain: str) -> Optional[str]:
        """
        Finds a business email for a prospect.
        Returns the email address or None.
        """
        pass

    @abstractmethod
    def verify_email(self, email: str) -> Dict[str, Any]:
        """
        Verifies the email address.
        Returns a dict: {"verified": bool, "status": str}
        """
        pass

    @abstractmethod
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
        Adds a verified prospect to the specified platform list.
        Returns True if successful, False otherwise.
        """
        pass
