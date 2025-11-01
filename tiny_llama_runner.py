from llama_cpp import Llama

# Load your TinyLlama GGUF model
MODEL_PATH = "/opt/oss-migrate/llm-planner/models/tiny-llama.Q4_K_M.gguf"

# Instantiate the LLM once at startup
llm = Llama(
    model_path=MODEL_PATH,
    n_ctx=2048,         # context length — adjust if needed
    n_threads=4         # adjust for your VM's CPU
)

def run_tiny_llama(prompt: str) -> str:
    """Run prompt through TinyLlama and return trimmed response text."""
    response = llm(prompt, max_tokens=512, stop=["</s>"])
    return response["choices"][0]["text"].strip()
