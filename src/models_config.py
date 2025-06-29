# Available LLM Models Configuration

AVAILABLE_MODELS = {
    "GPT-4.1-mini": "gpt-4.1-mini",
    "GPT-4.1-nano": "gpt-4.1-nano",
    "GPT-4.1": "gpt-4.1",
    "GPT-4o": "gpt-4o",
    "GPT-4o-mini": "gpt-4o-mini",
    "O3-mini": "o3-mini",
    "O3": "o3",
    "O4-mini-deep-research": "o4-mini-deep-research",
}

# Default model
DEFAULT_MODEL = "GPT-4.1-mini"

# Reasoning models that only support temperature=1.0
REASONING_MODELS = ["o3-mini", "o3", "o4-mini-deep-research"]

def get_model_options():
    """Get list of model display names for dropdown"""
    return list(AVAILABLE_MODELS.keys())

def get_model_id(display_name):
    """Get API model ID from display name"""
    return AVAILABLE_MODELS.get(display_name, AVAILABLE_MODELS[DEFAULT_MODEL])

def is_reasoning_model(model_id):
    """Check if a model is a reasoning model that requires temperature=1.0"""
    return model_id in REASONING_MODELS 