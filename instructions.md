# Snov.io Integration Project Instructions

## Project Overview

This application integrates with the **Snov.io API** to automate prospect discovery and management. The initial implementation focuses on retrieving existing prospect lists from the user's Snov.io account and allowing users to add prospects to a selected list.

**Technology Stack**

* Backend: Python
* Frontend: React
* API: Snov.io REST API

---

# Authentication

## Environment Variables

Store the following credentials in the `.env` file:

```env
SNOV_CLIENT_ID=
SNOV_CLIENT_SECRET=
```

### Access Token Management

* Generate an OAuth access token using the Client ID and Client Secret.
* Store the access token in memory (do not persist it in a database or file).
* Before making any Snov.io API request, verify that the access token is still valid.
* If the token has expired, automatically generate a new access token and update the in-memory cache.
* All API requests should use the latest valid access token.

---

# Phase 1 – Display Prospect Lists

## Objective

Retrieve and display all prospect lists available in the authenticated Snov.io account.

### Requirements

* Fetch all user prospect lists from Snov.io.
* Display the following information for each list:

  * List Name
  * Number of Prospects
* Each list should include an **"Add Prospect"** action.

---

# Add Prospect

When the user selects **Add Prospect**, present two options:

### Option 1 – Add Single Prospect

Allow the user to manually enter:

* First Name
* Last Name
* Company Domain

### Option 2 – Upload Multiple Prospects

This feature will be implemented in a later phase.

Expected input:

* CSV or Excel file containing prospect details.

---

# Current Scope

Only **Single Prospect** functionality is included in the current implementation.

---

# Single Prospect Workflow

## Step 1

User selects a prospect list.

## Step 2

User enters:

* First Name
* Last Name
* Company Domain

## Step 3

Validate that all required fields are provided.

## Step 4

Call the Snov.io **Email Finder API** using the supplied information.

## Step 5

If a valid business email address is found:

* Create the prospect.
* Add the prospect to the selected Snov.io list.
* Display a success message.

## Step 6

If no valid email address is found:

* Do not create the prospect.
* Display an appropriate error message to the user.

---

# Validation Rules

The following fields are mandatory:

* First Name
* Last Name
* Company Domain

The application should:

* Validate required fields before calling the API.
* Display validation errors immediately.
* Prevent duplicate submissions while the API request is in progress.

---

# Error Handling

Handle the following scenarios gracefully:

* Missing required fields
* Invalid domain
* No email address found
* Invalid or expired access token
* Snov.io API errors
* Network failures
* Rate limit responses

Display clear, user-friendly error messages.

---

# UI Requirements

## Prospect Lists Page

Display:

* List Name
* Total Prospects
* Add Prospect button

## Add Prospect Dialog

Fields:

* First Name
* Last Name
* Company Domain

Buttons:

* Find & Add Prospect
* Cancel

---

# Future Enhancements

The following features are out of scope for the current phase but should be considered during development:

* Bulk prospect upload (CSV/Excel)
* Bulk email discovery
* Email verification
* Campaign management
* Create new prospect lists
* Search and filter prospect lists
* Background processing for bulk imports
* Progress tracking for large uploads

---

# Development Guidelines

* Keep frontend and backend responsibilities separate.
* Centralize all Snov.io API communication in a dedicated service layer.
* Reuse the in-memory access token across all API requests.
* Automatically refresh expired tokens without user intervention.
* Use async operations for all API calls.
* Implement consistent error handling and logging.
* Design the codebase to support future Snov.io features with minimal refactoring.
