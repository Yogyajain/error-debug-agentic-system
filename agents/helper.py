from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableMap, RunnableLambda
import pickle
import re
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
import os


os.environ["GOOGLE_API_KEY"]
llm = ChatGoogleGenerativeAI(model="gemini-3-flash-preview")


template_log_parser = ChatPromptTemplate.from_messages([
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
chain_log_parser = (
    RunnableMap({
        "question": lambda x: x["question"]
    })
    | template_log_parser
    | llm 
    | StrOutputParser()
)



template_error_detector = ChatPromptTemplate.from_messages([
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
chain_error_detector = (
    RunnableMap({
        "question": lambda x: x["question"]
    })
    | template_error_detector
    | llm 
    | StrOutputParser()
)

template_root_cause_analyzer = ChatPromptTemplate.from_messages([
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
chain_root_cause_analyzer = (
    RunnableMap({
        "question": lambda x: x["question"]
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
