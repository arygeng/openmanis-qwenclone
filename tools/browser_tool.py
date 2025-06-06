"""
Browser tool adapter for Manus AI Clone
Implements standardized interface for browser operations
"""

import re
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
import httpx
from bs4 import BeautifulSoup
from core.logging import get_logger # Added for logging

from tools.tool_interface import ToolAdapter, ToolType, ToolMetadata, ExecutionResult, SecurityContext, PermissionLevel

class BrowserTool(ToolAdapter):
    """
    Adapter for secure web browsing operations
    """
    def __init__(self):
        self.logger = get_logger(__name__) # Added for logging
        self.logger.info("Initializing BrowserTool") # Added for logging
        # Create tool metadata
        metadata = ToolMetadata(
            name="browser_tool",
            description="Secure web browsing with content filtering and real HTTP requests",
            version="1.1.0", # Updated version
            author="Manus AI Clone Team",
            license_type="MIT"
        )
        
        # Initialize base class
        super().__init__(
            tool_type=ToolType.BROWSER,
            metadata=metadata,
            permission_level=PermissionLevel.WRITE
        )
        
        # Browser-specific configuration
        self.sandbox_config = {
            "memory_limit": 512 * 1024 * 1024,  # bytes (512MB)
            "timeout": 30.0,  # seconds
            "max_redirects": 5,
            "allowed_domains": ["example.com", "trusted.org"], # Example, should be configurable
            "content_types_allowed": ["text/html", "application/json", "text/plain"] # Added text/plain
        }
        
        # Prohibited patterns
        self.prohibited_patterns = [
            r"login.*password",
            r"account.*details",
            r"credit-card.*information"
        ]
        
        # Blocked domains
        self.blocked_domains = [
            "malicious.com",
            "phishing.net"
        ]

        # Initialize httpx client
        self.client = httpx.AsyncClient(
            timeout=self.sandbox_config["timeout"],
            follow_redirects=True, # httpx handles max_redirects internally if needed, but we can also check response history
            # max_redirects parameter is not directly available in AsyncClient constructor in this way.
            # We can check response.history for number of redirects if needed.
            # For now, relying on httpx's default redirect handling (usually around 20)
            # or we can manually handle redirects if more control is needed.
            # The 'max_redirects' in sandbox_config is more of a policy limit.
        )


    async def close(self):
        """
        Properly close the httpx client.
        """
        self.logger.info("Closing BrowserTool httpx client.")
        await self.client.aclose()
        self.logger.info("BrowserTool httpx client closed.")

    def _validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """
        Validate browser command parameters
        
        Args:
            parameters: Parameters to validate
            
        Returns:
            True if valid, False otherwise
        """
        self.logger.debug(f"Validating parameters: {parameters}")
        # Check required parameter
        if "url" not in parameters:
            self.logger.warning("Parameter validation failed: 'url' not in parameters.")
            return False
            
        # Validate URL format
        if not isinstance(parameters["url"], str):
            self.logger.warning("Parameter validation failed: 'url' is not a string.")
            return False
            
        # Additional validation could be added here (e.g., method, headers format)
        method = parameters.get("method", "GET").upper()
        if method not in ["GET", "POST"]: # Add other supported methods if necessary
            self.logger.warning(f"Parameter validation failed: Unsupported HTTP method '{method}'.")
            return False

        self.logger.debug("Parameters validated successfully.")
        return True

    def _validate_url(self, url: str, parameters: Dict[str, Any]) -> bool: # Added parameters for context if needed later
        """
        Validate URL against security rules
        
        Args:
            url: URL to validate
            parameters: Original request parameters (for potential future use in validation)
            
        Returns:
            True if URL is allowed
        """
        self.logger.debug(f"Validating URL: {url}")
        # Basic URL pattern validation
        url_pattern = r"^https?://[a-zA-Z0-9.-]+.[a-zA-Z]{2,}(:[0-9]+)?(/.*)?$" # Consider using a more robust library for URL parsing if complex URLs are expected
        if not re.match(url_pattern, url):
            self.logger.warning(f"URL validation failed: Invalid URL format for '{url}'.")
            return False
            
        # Extract domain from URL
        domain = self._extract_domain(url)
        if not domain: # Should not happen if re.match passed, but as a safeguard
            self.logger.warning(f"URL validation failed: Could not extract domain from '{url}'.")
            return False
        self.logger.debug(f"Extracted domain '{domain}' from URL '{url}'.")
        
        # Check blocked domains
        if any(blocked_domain in domain for blocked_domain in self.blocked_domains):
            self.logger.warning(f"URL validation failed: Domain '{domain}' (from URL '{url}') is in blocked_domains list.")
            return False
            
        # Check allowed domains (if the list is not empty and has entries)
        if self.sandbox_config.get("allowed_domains") and \
           not any(allowed_domain in domain for allowed_domain in self.sandbox_config["allowed_domains"]):
            self.logger.warning(f"URL validation failed: Domain '{domain}' (from URL '{url}') is not in allowed_domains list: {self.sandbox_config['allowed_domains']}.")
            return False
            
        # Content type validation is moved to after fetching the response
        # as we don't know the content type before the request.
        
        self.logger.debug(f"URL '{url}' validated successfully.")
        return True

    def _extract_domain(self, url: str) -> str:
        """
        Extract domain from a URL
        
        Args:
            url: Full URL string
            
        Returns:
            Extracted domain
        """
        # Simple domain extraction
        start = url.find("//") + 2
        end = url.find("/", start)
        if end == -1:
            end = len(url)
            
        return url[start:end].lower()
        
    def _create_error_response(self, message: str) -> Dict[str, Any]:
        """
        Create standardized error response
        
        Args:
            message: Error message
            
        Returns:
            Error response dictionary
        """
        return {
            "status": "error",
            "message": message,
            "timestamp": datetime.now().isoformat()
        }

    async def _execute_in_sandbox(self, parameters: Dict[str, Any]) -> ExecutionResult:
        """
        Execute browser operation using httpx.
        
        Args:
            parameters: Dictionary containing operation details:
                        'url': str,
                        'method': str (GET, POST),
                        'headers': Optional[Dict],
                        'data': Optional[Dict] (for POST)
            
        Returns:
            Execution result
        """
        self.logger.info(f"Executing browser operation: Method='{parameters.get('method', 'GET')}', URL='{parameters.get('url')}'")
        url = parameters.get("url")
        method = parameters.get("method", "GET").upper()
        headers = parameters.get("headers", {})
        data = parameters.get("data", None) # For POST requests

        if not self._validate_url(url, parameters): # _validate_url logs its own reasons
            return ExecutionResult(
                tool_name=self.metadata.name,
                success=False,
                output=None,
                error=f"Invalid or disallowed URL: {url}" # Generic error, specific logged by _validate_url
            )
        self.logger.debug(f"URL '{url}' passed initial validation for execution.")

        try:
            self.logger.info(f"Attempting {method} request to {url}")
            if method == "GET":
                response = await self.client.get(url, headers=headers)
            elif method == "POST":
                response = await self.client.post(url, headers=headers, data=data)
            else:
                # This case should ideally be caught by _validate_parameters
                self.logger.error(f"Unsupported HTTP method '{method}' encountered during execution.")
                return ExecutionResult(
                    tool_name=self.metadata.name,
                    success=False,
                    output=None,
                    error=f"Unsupported HTTP method: {method}"
                )
            self.logger.info(f"Received response for {url}: Status {response.status_code}, Final URL: {response.url}")

            # Check number of redirects against policy
            if len(response.history) > self.sandbox_config["max_redirects"]:
                self.logger.warning(f"Exceeded max redirects ({self.sandbox_config['max_redirects']}) for URL {url}. Final URL: {response.url}, History: {len(response.history)} redirects.")
                return ExecutionResult(
                    tool_name=self.metadata.name,
                    success=False,
                    output={"status_code": response.status_code, "url": str(response.url), "redirect_history_count": len(response.history)},
                    error=f"Exceeded max redirects ({self.sandbox_config['max_redirects']}). Final URL: {response.url}"
                )
            
            response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
            self.logger.debug(f"HTTP request to {url} successful with status {response.status_code}.")

            content_type = response.headers.get("Content-Type", "").split(";")[0].strip()
            self.logger.debug(f"Response Content-Type: '{content_type}' for URL {url}.")
            if self.sandbox_config.get("content_types_allowed") and \
               content_type not in self.sandbox_config["content_types_allowed"]:
                self.logger.warning(f"Content type '{content_type}' for URL {url} is not in allowed list: {self.sandbox_config['content_types_allowed']}.")
                return ExecutionResult(
                    tool_name=self.metadata.name,
                    success=False,
                    output={"status_code": response.status_code, "url": str(response.url), "content_type": content_type},
                    error=f"Content type '{content_type}' not allowed for URL: {url}"
                )

            extracted_content = {
                "status_code": response.status_code,
                "url": str(response.url), # Final URL after redirects
                "headers": dict(response.headers),
                "content_length": len(response.content),
                "content_type": content_type,
                "html_analysis": None,
                "text_preview": None,
                "json_payload": None # Ensure key exists
            }
            
            self.logger.debug(f"Extracting content from response for {url}. Content length: {len(response.content)} bytes.")
            if "text/html" in content_type:
                self.logger.debug(f"Parsing HTML content for {url}.")
                soup = BeautifulSoup(response.content, 'html.parser')
                title = soup.title.string if soup.title else "N/A"
                headings = [h.get_text(strip=True) for h_level in ['h1', 'h2', 'h3'] for h in soup.find_all(h_level)]
                links = [{"text": a.get_text(strip=True)[:100], "href": a.get('href')} for a in soup.find_all('a', href=True)]
                
                raw_text = soup.get_text(separator=' ', strip=True)
                text_preview = (raw_text[:500] + '...') if len(raw_text) > 500 else raw_text
                self.logger.debug(f"HTML analysis for {url}: Title='{title}', Headings found={len(headings)}, Links found={len(links)}")

                extracted_content["html_analysis"] = {
                    "title": title,
                    "headings": headings[:10],
                    "links": links[:20]
                }
                extracted_content["text_preview"] = text_preview
            elif "application/json" in content_type:
                self.logger.debug(f"Parsing JSON content for {url}.")
                try:
                    extracted_content["json_payload"] = response.json()
                    self.logger.debug(f"Successfully parsed JSON payload for {url}.")
                except ValueError as json_err:
                    self.logger.warning(f"Failed to parse JSON for {url}, falling back to text preview. Error: {json_err}", exc_info=True)
                    extracted_content["text_preview"] = response.text[:500] + ('...' if len(response.text) > 500 else '')
            else:
                 self.logger.debug(f"Content type for {url} is '{content_type}', providing text preview.")
                 extracted_content["text_preview"] = response.text[:500] + ('...' if len(response.text) > 500 else '')

            self.logger.info(f"Browser operation for {url} completed successfully.")
            return ExecutionResult(
                tool_name=self.metadata.name,
                success=True,
                output=extracted_content
            )
            
        except httpx.HTTPStatusError as e:
            self.logger.warning(f"HTTP error {e.response.status_code} for {e.request.url}: {e}", exc_info=True)
            return ExecutionResult(
                tool_name=self.metadata.name,
                success=False,
                output={"status_code": e.response.status_code, "url": str(e.request.url), "response_text": e.response.text[:200]},
                error=f"HTTP error {e.response.status_code} for {e.request.url}: {e}"
            )
        except httpx.RequestError as e:
            self.logger.error(f"Request failed for {str(e.request.url) if e.request else url}: {e}", exc_info=True)
            return ExecutionResult(
                tool_name=self.metadata.name,
                success=False,
                output={"url": str(e.request.url) if e.request else url},
                error=f"Request failed for {str(e.request.url) if e.request else url}: {e}"
            )
        except Exception as e:
            self.logger.error(f"An unexpected error occurred while processing {url}: {e}", exc_info=True)
            return ExecutionResult(
                tool_name=self.metadata.name,
                success=False,
                output={"url": url},
                error=f"An unexpected error occurred while processing {url}: {str(e)}"
            )

    async def browse_url(self,
                  url: str,
                  method: str = "GET",
                  headers: Optional[Dict[str, Any]] = None,
                  data: Optional[Dict[str, Any]] = None, # Added data for POST
                  context: Optional[SecurityContext] = None) -> ExecutionResult:
        """
        Direct API for browsing URLs.
        
        Args:
            url: URL to access
            method: HTTP method (GET, POST, etc.)
            headers: Optional request headers
            data: Optional data for POST requests
            context: Security context for operation validation
            
        Returns:
            Execution result
        """
        self.logger.info(f"browse_url API called: URL='{url}', Method='{method}'")
        parameters = {
            "url": url,
            "method": method.upper()
        }
        
        if headers:
            parameters["headers"] = headers
            self.logger.debug(f"Custom headers provided for {url}: {list(headers.keys())}")
        if data and method.upper() == "POST":
            parameters["data"] = data
            self.logger.debug(f"POST data provided for {url}.")
            
        # Execute through main execution path
        # Assuming self.execute in ToolAdapter can handle async _execute_in_sandbox
        # If not, ToolAdapter.execute would need to be made async or use asyncio.run/create_task
        result = await self.execute(parameters, context) # Made async
        if result.success:
            self.logger.info(f"browse_url for '{url}' succeeded. Status: {result.output.get('status_code')}")
        else:
            self.logger.error(f"browse_url for '{url}' failed. Error: {result.error}")
        return result


    def set_sandbox_config(self,
                         memory_limit: int = 512 * 1024 * 1024,
                         timeout: float = 30.0,
                         max_redirects: int = 5,
                         allowed_domains: Optional[List[str]] = None,
                         content_types_allowed: Optional[List[str]] = None) -> None:
        """
        Configure sandbox settings
        
        Args:
            memory_limit: Maximum memory usage in bytes
            timeout: Maximum execution time in seconds
            max_redirects: Maximum number of allowed redirects
            allowed_domains: List of allowed domains
            content_types_allowed: List of allowed content types
        """
        self.logger.info(f"Updating BrowserTool sandbox configuration: timeout={timeout}, max_redirects={max_redirects}, etc.")
        config_update = {
            "memory_limit": memory_limit, # Note: memory_limit is not directly used by httpx
            "timeout": timeout,
            "max_redirects": max_redirects
        }
        self.logger.debug(f"Base config update: {config_update}")
        
        if allowed_domains is not None:
            config_update["allowed_domains"] = [d.lower() for d in allowed_domains]
            self.logger.debug(f"allowed_domains set to: {config_update['allowed_domains']}")
            
        if content_types_allowed is not None:
            config_update["content_types_allowed"] = content_types_allowed
            self.logger.debug(f"content_types_allowed set to: {config_update['content_types_allowed']}")
            
        self.sandbox_config.update(config_update)
        
        # Update httpx client timeout if it changed
        if self.client.timeout.connect != timeout or self.client.timeout.read != timeout : # Basic check, httpx.Timeout can be more complex
            self.logger.info(f"Reconfiguring httpx client timeout to {timeout}s.")
            # Need to re-initialize or update client; httpx client timeout is not easily mutable after creation.
            # For simplicity, we'll log a warning. A robust solution might involve recreating the client.
            # await self.close() # Close old client
            # self.client = httpx.AsyncClient(timeout=timeout, follow_redirects=True) # Create new
            self.logger.warning("httpx client timeout was changed; consider restarting the tool or application for the new timeout to fully apply if client is not recreated.")
            # For now, we'll just update the config value. The existing client instance will retain its original timeout.
            self.sandbox_config["timeout"] = timeout # Ensure our config reflects the desired state

        self.logger.info("BrowserTool sandbox configuration updated.")

    def add_blocked_domain(self, domain: str) -> None:
        """
        Add a new domain to block
        
        Args:
            domain: Domain to block
        """
        domain_lower = domain.lower()
        if domain_lower not in self.blocked_domains:
            self.blocked_domains.append(domain_lower)
            self.logger.info(f"Domain '{domain_lower}' added to blocked_domains list.")
        else:
            self.logger.debug(f"Domain '{domain_lower}' is already in blocked_domains list.")


    def remove_blocked_domain(self, domain: str) -> None:
        """
        Remove a domain from the block list
        
        Args:
            domain: Domain to unblock
        """
        domain_lower = domain.lower()
        if domain_lower in self.blocked_domains:
            self.blocked_domains = [d for d in self.blocked_domains if d != domain_lower]
            self.logger.info(f"Domain '{domain_lower}' removed from blocked_domains list.")
        else:
            self.logger.debug(f"Domain '{domain_lower}' not found in blocked_domains list for removal.")

    def add_allowed_domain(self, domain: str) -> None:
        """
        Add a new domain to allow
        
        Args:
            domain: Domain to allow
        """
        domain_lower = domain.lower()
        if "allowed_domains" not in self.sandbox_config or self.sandbox_config["allowed_domains"] is None:
            self.sandbox_config["allowed_domains"] = []
        
        if domain_lower not in self.sandbox_config["allowed_domains"]:
            self.sandbox_config["allowed_domains"].append(domain_lower)
            self.logger.info(f"Domain '{domain_lower}' added to allowed_domains list.")
        else:
            self.logger.debug(f"Domain '{domain_lower}' is already in allowed_domains list.")


    def remove_allowed_domain(self, domain: str) -> None:
        """
        Remove a domain from allowed list
        
        Args:
            domain: Domain to remove
        """
        domain_lower = domain.lower()
        if "allowed_domains" in self.sandbox_config and self.sandbox_config["allowed_domains"] is not None:
            if domain_lower in self.sandbox_config["allowed_domains"]:
                self.sandbox_config["allowed_domains"] = [
                    d for d in self.sandbox_config["allowed_domains"] if d != domain_lower
                ]
                self.logger.info(f"Domain '{domain_lower}' removed from allowed_domains list.")
            else:
                self.logger.debug(f"Domain '{domain_lower}' not found in allowed_domains list for removal.")
        else:
            self.logger.debug("allowed_domains list is not configured; cannot remove domain.")