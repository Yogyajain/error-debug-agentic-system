from langgraph.graph import StateGraph, START, END
from typing import Dict, Any, TypedDict, Annotated
from operator import add
import pickle
from IPython.display import Image
import json
from agents.helper import agent_2
from langgraph.constants import Send
import os
from agents.helper import chain_log_parser, chain_error_detector, chain_root_cause_analyzer, chain_solution_generator, chain_report_generator
from datetime import datetime
import json

class finalstate(TypedDict):
    """State for the error log analysis workflow"""
    log_files: list[Dict[str, str]]  # List of {name, content, type}
    parsed_logs: list[Dict]  # Parsed and summarized logs
    identified_errors: list[Dict]  # Errors with patterns identified
    root_causes: list[Dict]  # Root cause analysis for each error
    solutions: list[Dict]  # Proposed solutions
    final_report: str  # Comprehensive report

def log_parser(finalstate):
    log_files = finalstate['log_files']
    log_files = []
    for log_file in log_files:
        response = chain_log_parser.invoke(log_file['content'])
    if isinstance(response, str):
        response = json.loads(response)
        response['name'] = log_file['name']
        response['type'] = log_file['type']
        log_files.append(response)
    print("Parsed Logs from log parser:", log_files)
    return {finalstate['parsed_logs'] : log_files} 

def error_detector(finalstate):
    parsed_logs = finalstate['parsed_logs']
    error_summary = []
    for parsed_log in parsed_logs:
        response = chain_error_detector.invoke(json.dumps(parsed_log))
    if isinstance(response, str):
        response = json.loads(response)
        response['name'] = parsed_log['name']
        response['type'] = parsed_log['type']
        error_summary.append(response)
    print("Identified Errors from error detector:", error_summary)
    return {finalstate['identified_errors'] : error_summary}

def analyze_root_cause(finalstate):
    identified_errors = finalstate['identified_errors']
    for error in identified_errors:
        response = chain_root_cause_analyzer.invoke(json.dumps(error))
    if isinstance(response, str):
        response = json.loads(response)
    print("Root Causes from root cause analyzer:", response)
    return {finalstate['root_causes'] : response}

def generate_solutions(finalstate):
    root_causes = finalstate['root_causes']
    for cause in root_causes:
        response = chain_solution_generator.invoke(json.dumps(cause))
    if isinstance(response, str):
        response = json.loads(response)
    print("Proposed Solutions from solution generator:", response)
    return {finalstate['solutions'] : response}

def generate_report(finalstate):
    parsed_logs = finalstate['parsed_logs']
    identified_errors = finalstate['identified_errors']
    root_causes = finalstate['root_causes']
    solutions = finalstate['solutions']
    
    response = chain_report_generator.invoke(json.dumps({
        "parsed_logs": parsed_logs,
        "identified_errors": identified_errors,
        "root_causes": root_causes,
        "solutions": solutions
    }))
    
    print("Final Report from report generator:", response)
    return {finalstate['final_report'] : response}

builder_final = StateGraph(finalstate)
builder_final.add_state(START)
builder_final.add_state(log_parser, name="log_parser")
builder_final.add_state(error_detector, name="error_detector")
builder_final.add_state(analyze_root_cause, name="analyze_root_cause")
builder_final.add_state(generate_solutions, name="generate_solutions")
builder_final.add_state(generate_report, name="generate_report")
builder_final.add_state(END)
builder_final.add_node(START, "log_parser")
builder_final.add_edge("log_parser", "error_detector")
builder_final.add_edge("error_detector", "analyze_root_cause")
builder_final.add_edge("analyze_root_cause", "generate_solutions")
builder_final.add_edge("generate_solutions", "generate_report")
builder_final.add_edge("generate_report", END)
graph_final = builder_final.compile()