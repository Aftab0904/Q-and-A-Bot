import os
from openai import OpenAI
import json
import re

# Initialize Groq for evaluation
groq_client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

def evaluate_response(question, context, answer):
    """
    Uses an LLM as a judge to evaluate the Faithfulness and Relevancy of the answer.
    Returns a dictionary with scores (0-100).
    """
    
    prompt = f"""
    You are an expert AI Auditor. Your task is to evaluate the quality of an AI-generated response based on the provided context and the user's question.
    
    [CONTEXT]
    {context}
    
    [USER QUESTION]
    {question}
    
    [AI ANSWER]
    {answer}
    
    Evaluate the following two metrics on a scale of 0 to 100:
    
    1. Faithfulness: Is the answer strictly derived from the context? Does it contain any information NOT present in the context (hallucinations)? 100 means perfectly faithful, 0 means entirely hallucinated.
    2. Relevancy: Does the answer directly address the user's question? Is it concise and helpful? 100 means perfectly relevant, 0 means completely irrelevant.
    
    Return your response ONLY in the following JSON format:
    {{
        "faithfulness": <score>,
        "relevancy": <score>,
        "reasoning": "<brief explanation for the scores>"
    }}
    """
    
    try:
        res = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        evaluation = json.loads(res.choices[0].message.content)
        return evaluation
    except Exception as e:
        print(f"Evaluation failed: {e}")
        return {
            "faithfulness": 0,
            "relevancy": 0,
            "reasoning": "Evaluation engine encountered an error."
        }
