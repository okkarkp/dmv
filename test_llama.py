from tiny_llama_runner import run_tiny_llama

prompt = """
You are a data planner. Given the DDL diff below, generate a JSON plan that includes:
- field mappings
- transformation SQL snippet
- data quality checks

source schema: id, name, dob
target schema: id, full_name, birth_date
"""

output = run_tiny_llama(prompt)
print("TinyLlama JSON Output:\n", output)
