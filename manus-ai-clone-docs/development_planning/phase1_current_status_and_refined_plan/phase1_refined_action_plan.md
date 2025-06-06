# Phase 1 Refined Action Plan - Manus AI Clone

**Plan Date:** 2025-06-02

This refined action plan addresses the current status and identified issues to guide the completion of Phase 1: "Foundation Repair & Basic Functionality."

---

## Overarching Goals for Phase 1 Completion:

1.  **Achieve Stability:** Ensure the system is runnable without critical errors.
2.  **Implement Core Missing Components:** Address critical gaps like configuration and essential methods.
3.  **Basic Functionality for Tools:** Move beyond stubs for key tools.
4.  **Standardize Critical Infrastructure:** Align Docker and web server with best practices and/or make conscious decisions on deviations.

## Strategic Decision: Flask vs. FastAPI

The current web server uses Flask, while FastAPI was planned.

*   **Option 1: Revert to FastAPI.**
    *   **Pros:** Aligns with original plan, benefits of FastAPI (async, Pydantic validation, auto-docs).
    *   **Cons:** Requires re-writing existing Flask endpoints, potentially more effort.
*   **Option 2: Accept Flask and Adjust Future Plans.**
    *   **Pros:** Leverages existing working code, potentially faster to get to a functional state.
    *   **Cons:** Deviates from plan, may need to find Flask equivalents for some FastAPI features if they become critical.

**Recommendation:**
Given Phase 1's goal is "basic functionality" and a working Flask implementation exists for status and messaging, **it is recommended to proceed with Flask for the remainder of Phase 1 to save time.** A task should be created for Phase 2 to re-evaluate this decision and potentially migrate to FastAPI if its advantages are deemed critical for future development. For now, ensure the Flask app is robust.

## Refined Action Items:

**Estimated Effort Key:**
*   **Small:** 1-4 hours
*   **Medium:** 4-8 hours (1 day)
*   **Large:** 8-16 hours (1-2 days)
*   **X-Large:** 16+ hours (2+ days)

---

### 1. Critical Infrastructure & Configuration

| Task ID | Task Description                                                                 | Affected Component(s)                                  | Estimated Effort | Priority | Notes                                                                                                |
| :------ | :------------------------------------------------------------------------------- | :----------------------------------------------------- | :--------------- | :------- | :--------------------------------------------------------------------------------------------------- |
| RAP-001 | **Implement Configuration System (`config/settings.py`)**                        | `config/settings.py`, All modules needing config       | Medium           | High     | Use Pydantic as planned. Include basic settings for app, debug, ports, DB/Redis URLs (even if not used yet). |
| RAP-002 | **Add Non-Root User to `Dockerfile`**                                            | `Dockerfile`                                           | Small            | High     | Implement standard non-root user creation and `USER` instruction.                                    |
| RAP-003 | **Review & Standardize `Dockerfile`**                                          | `Dockerfile`                                           | Small            | Medium   | Confirm Python version, justify extra dependencies (like Chrome), remove if not needed for Phase 1.    |
| RAP-004 | **Clarify/Address `code-sandbox` Service**                                       | `docker-compose.yml`                                   | Small            | Low      | Understand purpose. If not for Phase 1, comment out or remove.                                       |
| RAP-005 | **Fix/Enable Nginx Custom Configuration**                                        | `docker-compose.yml`, `nginx.conf` (if exists)         | Small            | Medium   | Uncomment volume mount for `nginx.conf`. Ensure a basic `nginx.conf` exists.                         |
| RAP-006 | **Decision: Flask vs. FastAPI (Formalize for Phase 1)**                          | Web server strategy, `web_interface/app.py`            | Small            | High     | Confirm decision to stick with Flask for Phase 1. Document rationale.                                |

---

### 2. Knowledge Module Enhancements

| Task ID | Task Description                                                              | Affected Component(s)           | Estimated Effort | Priority | Notes                                                                 |
| :------ | :---------------------------------------------------------------------------- | :------------------------------ | :--------------- | :------- | :-------------------------------------------------------------------- |
| RAP-007 | **Implement `KnowledgeBase.get_prompt_template()`**                           | `knowledge/knowledge_base.py`   | Small            | Medium   | Implement the missing method as per original plan.                    |
| RAP-008 | **Basic Review of `KnowledgeBase` & `MemorySystem` Functionality**          | `knowledge/` module             | Medium           | Medium   | Ensure methods needed for basic tool operation are present and functional. |

---

### 3. Tool Implementation (Moving Beyond Stubs)

| Task ID | Task Description                                                              | Affected Component(s)        | Estimated Effort | Priority | Notes                                                                                                |
| :------ | :---------------------------------------------------------------------------- | :--------------------------- | :--------------- | :------- | :--------------------------------------------------------------------------------------------------- |
| RAP-009 | **`BrowserTool`: Implement Basic `httpx` GET Requests**                       | `tools/browser_tool.py`      | Medium           | High     | Replace stub with actual `httpx.get()` calls. Basic content return. No complex parsing needed for Phase 1. |
| RAP-010 | **`FileTool`: Implement Basic Read & List Operations**                        | `tools/file_tool.py`         | Medium           | Medium   | Implement actual `read_file` and `list_directory` functionality. Maintain security concepts.           |
| RAP-011 | **`ShellTool`: Implement Basic `echo` or `ls` Command Execution**             | `tools/shell_tool.py`        | Medium           | Medium   | Implement execution for a very limited set of safe commands (e.g., `echo`, `ls`). Maintain security. |
| RAP-012 | **`MessageTool`: Align with Plan or Document Deviations**                     | `tools/message_tool.py`      | Medium           | Medium   | Review current `MessageTool` against plan. Either align key functionalities or clearly document deviations. |

---

### 4. Testing & Validation

| Task ID | Task Description                                                              | Affected Component(s)        | Estimated Effort | Priority | Notes                                                                                                   |
| :------ | :---------------------------------------------------------------------------- | :--------------------------- | :--------------- | :------- | :------------------------------------------------------------------------------------------------------ |
| RAP-013 | **Basic End-to-End Test: Web UI -> Flask -> Engine -> (Stubbed/Basic) Tool**  | Full system (high level)     | Medium           | Medium   | Test a simple message flow to ensure basic connectivity once critical gaps are filled.                  |
| RAP-014 | **Test Docker Environment with Changes**                                      | `Dockerfile`, `docker-compose.yml` | Small            | High     | Ensure `docker-compose up --build` works and services run after `Dockerfile` and config changes.        |

---

## Timeline & Effort Consideration:

The original Phase 1 was estimated at 2-3 weeks. Given the number of critical gaps and deviations:

*   **Missing `config/settings.py`:** High impact, blocks proper initialization.
*   **Flask vs. FastAPI:** Decision made to stick with Flask for P1, reducing immediate rework.
*   **Tool Stubs:** Moving tools to basic functionality will take time.
*   **Docker Security:** Non-root user is a quick but critical fix.

**Revised Outlook for Phase 1 Completion:**
Addressing the items in this refined plan will likely still fit within the **upper end of the original 2-3 week estimate, possibly extending slightly into a 4th week**, depending on the complexity encountered when moving tools beyond stubs and integrating the configuration system. The key is to prioritize ruthlessly to achieve a *stable and basically functional* system.

**Key Priorities for "Runnable" Status:**
1.  `config/settings.py` (RAP-001)
2.  Non-root user in Docker (RAP-002)
3.  Basic `BrowserTool` with `httpx` (RAP-009)
4.  Ensure `KnowledgeBase.get_prompt_template()` is present (RAP-007)
5.  Confirm Flask decision and basic API functionality (RAP-006)

Addressing these high-priority items will significantly move the project towards the Phase 1 goal of being "runnable with basic functionality."

---