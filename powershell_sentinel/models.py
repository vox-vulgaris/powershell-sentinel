# powershell_sentinel/models.py

import json
from enum import Enum
from pydantic import BaseModel, Field, ValidationError, ConfigDict
from typing import List, Dict, Any, Optional

with open('data/source/mitre_ttp_library.json', 'r', encoding='utf-8') as f:
    mitre_data = json.load(f)
MitreTTPEnum = Enum('MitreTTPEnum', {k.replace('.', '_'): k for k in mitre_data.keys()})

class IntentEnum(str, Enum):
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
    # --- NEW INTENTS FOR V2 DATASET ---
    # Execution Tactic
    COMMAND_AND_SCRIPTING_INTERPRETER = "Execution: Command and Scripting Interpreter"
    WINDOWS_MANAGEMENT_INSTRUMENTATION = "Execution: Windows Management Instrumentation (WMI)"
    # Command & Control Tactic
    INGRESS_TOOL_TRANSFER = "Command and Control: Ingress Tool Transfer"
    # Defense Evasion Tactic
    MASQUERADING = "Defense Evasion: Masquerading"
    MODIFY_REGISTRY = "Defense Evasion: Modify Registry"
    # --- Final V2 Additions ---
    COMMAND_AND_CONTROL_WEB_PROTOCOLS = "Command and Control: Web Protocols"
    COMMAND_AND_CONTROL_DNS = "Command and Control: DNS"

class CommandOutput(BaseModel):
    stdout: str = Field(..., alias='Stdout')
    stderr: str = Field(..., alias='Stderr')
    return_code: int = Field(..., alias='ReturnCode')

class SplunkLogEvent(BaseModel):
    raw: str = Field(..., alias='_raw')
    time: str = Field(..., alias='_time')
    source: str
    sourcetype: str
    model_config = ConfigDict(extra='ignore')

class ExtractionMethodEnum(str, Enum):
    REGEX = "regex"
    KEY_VALUE = "key_value"
    
class ParsingRule(BaseModel):
    rule_name: str = Field(..., description="A unique, human-readable name for the rule.")
    event_id: int = Field(..., description="The Event ID this rule applies to.")
    source_match: Optional[str] = Field(None, description="A substring that must exist in the log's source field.")
    extraction_method: ExtractionMethodEnum
    detail_key_or_pattern: str

class TelemetryRule(BaseModel):
    source: str
    event_id: int
    details: str

class Primitive(BaseModel):
    primitive_id: str = Field(..., pattern=r'^PS-\d{3}$')
    primitive_command: str
    intent: List[IntentEnum]
    mitre_ttps: List[MitreTTPEnum]
    telemetry_rules: List[TelemetryRule]

# --- MODIFICATION START: Flattening the LLMResponse Structure ---

# The nested `Analysis` class is now removed.
# class Analysis(BaseModel):
#     intent: List[IntentEnum]
#     mitre_ttps: List[MitreTTPEnum]
#     telemetry_signature: List[TelemetryRule]

# The `LLMResponse` class is updated to be flat, containing all necessary fields at the top level.
# This creates a clearer, more robust data contract for the fine-tuning and evaluation process.
class LLMResponse(BaseModel):
    deobfuscated_command: str
    intent: List[IntentEnum]
    mitre_ttps: List[MitreTTPEnum]
    telemetry_signature: List[TelemetryRule]

# --- MODIFICATION END ---

class TrainingPair(BaseModel):
    prompt: str
    response: LLMResponse