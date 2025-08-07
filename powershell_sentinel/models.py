# This is a new file: powershell_sentinel/models.py
#
# This file defines the Pydantic models that serve as the single source of truth
# for all data structures used throughout the PowerShell-Sentinel project.
# Using these models instead of generic dictionaries provides type safety,
# automatic validation, and self-documenting code.

# VERSION 3: This version adds the ParsingRule model to support the new
# interactive, deterministic parsing engine.

import json
from enum import Enum
from pydantic import BaseModel, Field, ValidationError, ConfigDict
from typing import List, Dict, Any, Optional

# --- Enums for Strict Validation ---
# By defining these, Pydantic will ensure that only these exact string values
# are allowed in the corresponding model fields, preventing typos and
# ensuring data consistency.

# Dynamically create MitreTTP Enum from the keys of the library file
# This is an advanced but very robust way to ensure our TTPs are always valid.
with open('data/source/mitre_ttp_library.json', 'r', encoding='utf-8') as f:
    mitre_data = json.load(f)
MitreTTPEnum = Enum('MitreTTPEnum', {k.replace('.', '_'): k for k in mitre_data.keys()})

class IntentEnum(str, Enum):
    """Enumeration for the high-level intent of a primitive command."""
    SYSTEM_INFO_DISCOVERY = "System Information Discovery"
    SOFTWARE_DISCOVERY = "Software Discovery"
    USER_DISCOVERY = "System Owner/User Discovery"
    FILE_DIRECTORY_DISCOVERY = "File and Directory Discovery"
    NETWORK_CONFIG_DISCOVERY = "System Network Configuration Discovery"
    PERMISSION_GROUP_DISCOVERY = "Permission Groups Discovery"
    LOCAL_GROUPS = "Local Groups"
    ACCOUNT_DISCOVERY = "Account Discovery"
    LOCAL_ACCOUNT_DISCOVERY = "Account Discovery: Local Account"
    REMOTE_SYSTEM_DISCOVERY = "Remote System Discovery"
    NETWORK_CONNECTIONS_DISCOVERY = "System Network Connections Discovery"
    NETWORK_SERVICE_DISCOVERY = "Network Service Discovery"
    INTERNET_CONNECTION_DISCOVERY = "Internet Connection Discovery"
    NETWORK_SHARE_DISCOVERY = "Network Share Discovery"
    SYSTEM_SERVICE_DISCOVERY = "System Service Discovery"
    PROCESS_DISCOVERY = "Process Discovery"
    SCHEDULED_TASK = "Scheduled Task/Job: Scheduled Task"
    QUERY_REGISTRY = "Query Registry"
    LOCAL_DATA_STAGING = "Local Data Staging"
    SECURITY_SOFTWARE_DISCOVERY = "Security Software Discovery"
    WIFI_DISCOVERY = "Wi-Fi Discovery"
    OS_CREDENTIAL_DUMPING_SAM = "OS Credential Dumping: Security Account Manager"
    OS_CREDENTIAL_DUMPING_LSA = "OS Credential Dumping: LSA Secrets"
    UNSECURED_CREDENTIALS_FILES = "Unsecured Credentials: Credentials In Files"
    BOOT_OR_LOGON_AUTOSTART_REGISTRY = "Boot or Logon Autostart Execution: Registry Run Keys / Startup Folder"
    CREATE_OR_MODIFY_SYSTEM_PROCESS_SERVICE = "Create or Modify System Process: Windows Service"

# --- Lab Connector & Raw Data Models ---

class CommandOutput(BaseModel):
    """Represents the standardized output of a remotely executed command."""
    # [DEFINITIVE FIX] Add aliases to bridge the gap between PowerShell's
    # PascalCase JSON and Python's snake_case attributes.
    stdout: str = Field(..., alias='Stdout')
    stderr: str = Field(..., alias='Stderr')
    return_code: int = Field(..., alias='ReturnCode')

class SplunkLogEvent(BaseModel):
    """Represents a single log event retrieved from Splunk."""
    raw: str = Field(..., alias='_raw')
    time: str = Field(..., alias='_time')
    source: str
    sourcetype: str
    
    model_config = ConfigDict(extra='ignore')


# --- Primitive & Curation Models ---

class ExtractionMethodEnum(str, Enum):
    """Defines the method to extract details from a raw log."""
    REGEX = "regex"
    KEY_VALUE = "key_value"
    
class ParsingRule(BaseModel):
    """
    A user-defined rule for parsing a specific type of raw log event.
    """
    rule_name: str = Field(..., description="A unique, human-readable name for the rule.")
    event_id: int = Field(..., description="The Event ID this rule applies to.")
    source_match: Optional[str] = Field(None, description="A substring that must exist in the log's source field.")
    extraction_method: ExtractionMethodEnum
    detail_key_or_pattern: str

class TelemetryRule(BaseModel):
    """A clean, curated, human-readable rule representing a key telemetry signal."""
    source: str
    event_id: int
    details: str

class Primitive(BaseModel):
    """Represents a single entry in the master primitives_library.json."""
    primitive_id: str = Field(..., pattern=r'^PS-\d{3}$')
    primitive_command: str
    intent: List[IntentEnum]
    mitre_ttps: List[MitreTTPEnum]
    telemetry_rules: List[TelemetryRule]


# --- MLOps & Training Data Models ---

class Analysis(BaseModel):
    """Represents the structured analysis portion of an LLM's response."""
    intent: List[IntentEnum]
    mitre_ttps: List[MitreTTPEnum]
    telemetry_signature: List[TelemetryRule]

class LLMResponse(BaseModel):
    """Represents the complete, structured JSON response expected from the LLM."""
    deobfuscated_command: str
    analysis: Analysis

class TrainingPair(BaseModel):
    """Represents a single prompt-response pair in the final generated dataset."""
    prompt: str # The obfuscated command
    response: LLMResponse