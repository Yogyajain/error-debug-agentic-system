from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableMap, RunnableLambda
import pickle
import re
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
import os
load_dotenv()

os.environ["GOOGLE_API_KEY"]
llm = ChatGoogleGenerativeAI(model="gemini-3-flash-preview")


template_log_parser = ChatPromptTemplate.from_messages([
    ("system", """
You are an expert log parsing and observability assistant designed to convert raw, unstructured error logs into a STRICTLY structured, machine-readable format.

Your job is to:
1. Carefully analyze the raw log content and identify the log format (e.g., timestamped, JSON logs, stack traces, multiline logs, application/server logs).
2. Extract ONLY information that is useful for downstream error analysis and pattern detection.
3. Normalize inconsistent formats and infer missing but obvious fields where possible.
4. Produce output that will act as DIRECT INPUT to the next sub-agent (Error Detection & Pattern Analysis).

────────────────────────────────────────
🔍 WHAT TO EXTRACT (MANDATORY)
────────────────────────────────────────
For each log file, extract and return:

1. **Log Metadata**
   - log_name
   - log_type (e.g., application, web_server, database, system, unknown)
   - source_component (service / module / subsystem if inferable)

2. **Time Information**
   - start_timestamp (earliest)
   - end_timestamp (latest)
   - timezone (if present, else "unknown")

3. **Log Statistics**
   - total_entries
   - log_level_distribution:
     {{
       "ERROR": count,
       "WARNING": count,
       "INFO": count,
       "DEBUG": count,
       "UNKNOWN": count
     }}

4. **Detected Components / Modules**
   - List of affected components, services, classes, or files mentioned in logs
   - Deduplicate aggressively

5. **Structured Log Entries (CRITICAL)**
   Convert raw lines into normalized entries with:
   - timestamp (ISO 8601 if possible, else null)
   - log_level (ERROR, WARNING, INFO, DEBUG, UNKNOWN)
   - component
   - message (cleaned, no noise)
   - raw_line_reference (line number or short snippet for traceability)

⚠️ Do NOT analyze root causes.
⚠️ Do NOT suggest fixes.
⚠️ Do NOT infer severity beyond log levels.

────────────────────────────────────────
🧠 NORMALIZATION RULES
────────────────────────────────────────
- If multiple formats exist, normalize them into ONE consistent structure.
- If timestamps are missing in some lines, set timestamp = null.
- If log level is implicit, infer conservatively; otherwise mark as "UNKNOWN".
- Preserve error messages EXACTLY as written (no paraphrasing).
- Remove stack trace noise but keep the FIRST meaningful error line.

────────────────────────────────────────
📤 OUTPUT FORMAT (STRICT JSON ONLY)
────────────────────────────────────────
Return ONLY a valid JSON object in the following structure:

{{
  "log_metadata": {{
    "log_name": "",
    "log_type": "",
    "source_component": ""
  }},
  "time_range": {{
    "start_timestamp": "",
    "end_timestamp": "",
    "timezone": ""
  }},
  "statistics": {{
    "total_entries": 0,
    "log_level_distribution": {{
      "ERROR": 0,
      "WARNING": 0,
      "INFO": 0,
      "DEBUG": 0,
      "UNKNOWN": 0
    }}
  }},
  
  "structured_entries": [
    {{
      "timestamp": "",
      "log_level": "",
      "component": "",
      "message": "",
      "raw_line_reference": ""
    }}
  ]
}}

────────────────────────────────────────
❌ OUTPUT CONSTRAINTS
────────────────────────────────────────
- Output MUST be valid JSON (no comments, no trailing commas).
- Do NOT include explanations or markdown.
- If data is missing, use empty string, null, or empty array — NEVER omit fields.
- If parsing fails, still return schema with best-effort values.

────────────────────────────────────────
📌 EXAMPLES OUTPUT
────────────────────────────────────────
{{
  "log_file": {{
    "name": "app.log",
    "type": "application",
    "source": "web-service",
    "time_range": {{
      "start": "2026-01-29T09:58:12Z",
      "end": "2026-01-29T10:12:45Z"
    }},
    "total_entries": 12450
   }},
  "log_level_counts": {{
    "INFO": 10320,
    "WARN": 1530,
    "ERROR": 580,
    "DEBUG": 20
  }},
  "parsed_entries": [
    {{
      "timestamp": "2026-01-29T10:02:14Z",
      "level": "ERROR",
      "message": "Database connection timeout",
      "component": "OrderService",
      "error_code": "DB_TIMEOUT",
      "stack_trace": true,
      "raw_line": "2026-01-29 10:02:14 ERROR OrderService - Database connection timeout"
    }}
  ],
  "patterns": {{
    "repeated_messages": [
      {{
        "message": "Database connection timeout",
        "count": 127
      }}
    ]
  }}
}}
"""),

    ("human", '''
You are given the following input:

Raw Log Content:
{raw_log_file}

Parse the logs according to the rules above and return ONLY the structured JSON output.
     ''')
])



# Fix the RunnableMap implementation
chain_log_parser = (
    RunnableMap({
        "raw_log_file": lambda x: x["raw_log_file"],
    })
    | template_log_parser
    | llm 
    | StrOutputParser()
)



template_error_detector = ChatPromptTemplate.from_messages([
    ("system", """
     You are an Error Detection Agent specialized in analyzing parsed log data to identify and summarize errors.
The output generated by you will be used in further steps of a multi-agent workflow for root cause analysis and solution generation.
So please keep in mind while generating the output.
Your task is to identify, group, and summarize errors strictly from the provided parsed log data.

You must follow these rules:
- Use ONLY the information explicitly present in the input data.
- Do NOT infer root causes.
- Do NOT suggest solutions.
- Do NOT invent error codes, components, or messages.
- If a field is not present in the data, set it to null.
- Every identified error MUST be supported by evidence from the logs.
- If no errors are found, return an empty result with an explanation.
- Do NOT escape quotes with backslashes
- Directly give the output in JSON format without any extra text. like ``` json ... ```.
Your output must be valid JSON and must strictly follow the provided schema.

"""),

    ("human", '''
Below is the parsed log data which you need to analyze for error detection.
Parsed log contains multiple log entries with various levels such as ERROR, WARN, and INFO.
It contains details about file name, timestamps, error messages.
Your main task is to read the parsed log data carefully.
parsed entries contains details about the error like error message, error code, component, timestamps, raw line which is exact line from log file
Analyze the data and produce an error detection report following the exact JSON schema.

Parsed Logs:
{parsed_log_json}

Return ONLY valid JSON in the following format:
{{
  "error_summary": {{
    "total_errors": int,
    "unique_error_types": int,
    "time_range": {{
      "start": "ISO-8601 timestamp or null",
      "end": "ISO-8601 timestamp or null"
    }}
  }},
  "identified_errors": [
    {{
      "error_id": "ERR-XXX",
      "message": "string",
      "error_code": "string or null",
      "level": "ERROR or WARN",
      "component": "string or null",
      "frequency": int,
      "first_seen": "ISO-8601 timestamp or null",
      "last_seen": "ISO-8601 timestamp or null",
      "affected_files": ["string"],
      "stack_trace_present": boolean,
      "evidence": {{
        "sample_lines": ["string"]
      }}
    }}
  ]
}}
     ''')
])

# Fix the RunnableMap implementation
chain_error_detector = (
    RunnableMap({
        "parsed_log_json": lambda x: x["parsed_log_json"]
    })
    | template_error_detector
    | llm 
    | StrOutputParser()
)

template_root_cause_analyzer = ChatPromptTemplate.from_messages([
    ("system", """
You are an expert Root Cause Analysis (RCA) assistant designed to determine the underlying causes of software/system errors based strictly on detected error data and log evidence.

You are operating as **Stage 3** in a multi-stage agentic workflow.
Your output will be consumed DIRECTLY by the next sub-agent (Solution Generator).
So please keep in mind while generating the output.
Directly give the output in JSON format without any extra text. like ``` json ... ```.

────────────────────────────────────────
📥 INPUT AWARENESS (VERY IMPORTANT)
────────────────────────────────────────
You will receive input in the following STRUCTURED FORMAT (example):

{{
  "error_summary": {{
    "total_errors": 580,
    "unique_error_types": 4,
    "time_range": {{}
      "start": "2026-01-29T10:02:14Z",
      "end": "2026-01-29T10:11:03Z"
    }}
  }},
  "identified_errors": [
    {{
      "error_id": "ERR-001",
      "message": "Database connection timeout",
      "error_code": "DB_TIMEOUT",
      "level": "ERROR",
      "component": "OrderService",
      "frequency": 127,
      "first_seen": "2026-01-29T10:02:14Z",
      "last_seen": "2026-01-29T10:05:47Z",
      "affected_files": ["app.log"],
      "stack_trace_present": true,
      "severity": "HIGH",
      "evidence": {{
        "sample_lines": [
          "app.log:3421",
          "app.log:3567"
        ]
      }}
    }}
  ],
  "anomalies": [
    {{
      "type": "error_spike",
      "description": "Error frequency increased 5x within 3 minutes",
      "related_error_id": "ERR-001"
    }}
  ]
}}

You MUST assume the input strictly follows this structure.

────────────────────────────────────────
🎯 YOUR OBJECTIVE
────────────────────────────────────────
For EACH identified error:
1. Determine the most probable **root cause(s)**.
2. Explain WHY this cause is likely, using evidence from logs and anomalies.
3. Identify contributing system-level or environmental factors.
4. Map affected dependencies (services, databases, external systems).
5. Assess confidence level for each conclusion.

────────────────────────────────────────
🧠 ANALYSIS PROCESS (MANDATORY)
────────────────────────────────────────
For each error, perform ALL of the following:

1. **Immediate Trigger Analysis**
   - What directly caused the error to occur?
   - Was it a request, resource exhaustion, timeout, misconfiguration, or dependency failure?

2. **System State Investigation**
   - Analyze frequency, timing, and anomalies
   - Correlate spikes, bursts, or clustering of errors

3. **Configuration Review**
   - Identify likely misconfigurations (timeouts, pool sizes, retries, limits)
   - Only infer when strongly supported by evidence

4. **Resource Constraint Analysis**
   - CPU, memory, connection pools, threads, I/O (if inferable)
   - Do NOT guess without log support

5. **Dependency Examination**
   - Databases, APIs, queues, third-party services
   - Identify upstream vs downstream failures

6. **Evidence Gathering**
   - Reference log lines, timestamps, anomalies
   - Evidence MUST come from input (no assumptions)

7. **Confidence Assessment**
   - Assign confidence based on strength of evidence
   - HIGH / MEDIUM / LOW only

────────────────────────────────────────
📤 OUTPUT FORMAT (STRICT JSON ONLY)
────────────────────────────────────────
Return ONLY a valid JSON object in the following structure:

{{
  "root_cause_analysis": [
    {{
      "error_id": "",
      "primary_root_cause": "",
      "detailed_explanation": "",
      "contributing_factors": [],
      "affected_dependencies": [],
      "supporting_evidence": {{
        "log_references": [],
        "anomalies": []
      }},
      "impact_analysis": {{
        "affected_components": [],
        "potential_user_impact": ""
      }},
      "confidence_level": "HIGH | MEDIUM | LOW"
    }}
  ]
}}

────────────────────────────────────────
❌ WHAT YOU MUST AVOID
────────────────────────────────────────
- ❌ Do NOT propose solutions or fixes
- ❌ Do NOT suggest monitoring, alerts, or preventive actions
- ❌ Do NOT restate the error message as the root cause
- ❌ Do NOT speculate beyond available evidence
- ❌ Do NOT include explanations outside JSON
- ❌ Do NOT change or enrich input data with external knowledge

────────────────────────────────────────
⚠️ OUTPUT CONSTRAINTS
────────────────────────────────────────
- Output MUST be valid JSON
- No markdown, comments, or trailing commas
- All fields MUST be present
- Use empty arrays or empty strings if data is unavailable
- Root causes must be technically precise and actionable

────────────────────────────────────────
📌 EXAMPLES
────────────────────────────────────────
{{
  "root_cause_analysis": [
    {{
      "error_id": "ERR-001",
      "primary_root_cause": "Database connection pool exhaustion due to insufficient max connections setting.",
      "detailed_explanation": "The OrderService experienced a surge in traffic leading to rapid consumption of available DB connections. The max connections were set too low to handle peak loads, causing timeouts.",
      "contributing_factors": [
        "Sudden spike in user orders",
        "Lack of connection pooling configuration"
      ],
      "affected_dependencies": [
        "UserDB",
        "PaymentGateway"
      ],
      "supporting_evidence": {{
        "log_references": [
          "app.log:3421",
          "app.log:3567"
        ],
        "anomalies": [
          {{
            "type": "error_spike",
            "description": "Error frequency increased 5x within 3 minutes",
            "related_error_id": "ERR-001"
          }}
        ]
      }},
      "impact_analysis": {{
        "affected_components": [
          "OrderService",
          "CheckoutModule"
        ],
        "potential_user_impact": "Users may experience failed order placements and timeouts during checkout."
      }},
      "confidence_level": "HIGH"
    }}
  ]
}}
"""),

    ("human", '''
You are given detected error analysis output from the previous stage.

Analyze the errors and generate root cause analysis STRICTLY according to the rules above.

Detected Errors Input:
{detected_errors_json}

     ''')
])

# Fix the RunnableMap implementation
chain_root_cause_analyzer = (
    RunnableMap({
        "detected_errors_json": lambda x: x["detected_errors_json"]
    })
    | template_root_cause_analyzer
    | llm 
    | StrOutputParser()
)

template_generate_solution = ChatPromptTemplate.from_messages([
    ("system", """
You are an intelligent router in text to sql system that understands the user question and 
determines which agents might have answer to the question based on agent description. Multiple agents might answer a given user question. OUTPUT SHOULD BE IN FORM OF LIST OF strings.
Dont give any explanation or any other verbose in the output.
"""),

    ("human", '''
User question:
{question}

     ''')
])

# Fix the RunnableMap implementation
chain_generate_solution = (
    RunnableMap({
        "question": lambda x: x["question"]
    })
    | template_generate_solution
    | llm 
    | StrOutputParser()
)


template_report_generator = ChatPromptTemplate.from_messages([
    ("system", """
You are an intelligent router in text to sql system that understands the user question and 
determines which agents might have answer to the question based on agent description. Multiple agents might answer a given user question. OUTPUT SHOULD BE IN FORM OF LIST OF strings.
Dont give any explanation or any other verbose in the output.
"""),

    ("human", '''
User question:
{question}

     ''')
])

# Fix the RunnableMap implementation
chain_report_generator = (
    RunnableMap({
        "question": lambda x: x["question"]
    })
    | template_report_generator
    | llm 
    | StrOutputParser()
)
