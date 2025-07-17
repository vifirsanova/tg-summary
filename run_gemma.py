#!/usr/bin/env python3
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from pathlib import Path
import torch
import re
import tomli
from datetime import datetime, timezone
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class GemmaSummarizer:
    """Corrected Gemma summarizer with proper model loading and error handling."""
    
    def __init__(self):
        """Initialize with proper model type and CUDA settings."""
        os.environ['TOKENIZERS_PARALLELISM'] = 'false'
        self._load_config()
        self._load_prompts()
        self._initialize_model()

    def _load_config(self):
        """Load model configuration from TOML."""
        with open("config.toml", "rb") as f:
            config = tomli.load(f)
        self.model_name = config["model"]["name"]

    def _load_prompts(self):
        """Load prompts from text files."""
        prompts_dir = Path("prompts")
        self.system_prompt = (prompts_dir / "system_prompt.txt").read_text(encoding="utf-8").strip()
        self.summary_prompt = (prompts_dir / "summary_prompt.txt").read_text(encoding="utf-8").strip()

    def _initialize_model(self):
        """Load model with correct class and improved error handling."""
        try:
            # Use AutoModelForCausalLM instead of specific class
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                device_map="auto",
                torch_dtype=torch.float16,
                quantization_config=BitsAndBytesConfig(load_in_8bit=True),
                attn_implementation="sdpa"
            ).eval()
            
            if not torch.cuda.is_available():
                raise RuntimeError("CUDA is not available")
                
            logger.info(f"Model loaded on {self.model.device}")
            
        except Exception as e:
            logger.error(f"Model initialization failed: {e}")
            raise

    def generate_summary(self, chat_history: str) -> str:
        """Generate summary with proper error handling."""
        try:
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": self.summary_prompt.format(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    chat_history=chat_history
                )}
            ]
            
            inputs = self.tokenizer.apply_chat_template(
                messages,
                add_generation_prompt=True,
                return_tensors="pt",
                truncation=True,
                max_length=2048  # Added reasonable limit
            ).to(self.model.device)

            with torch.inference_mode():
                outputs = self.model.generate(
                    inputs,
                    temperature=0.7,
                    top_k=50,
                    top_p=0.9,
                    max_new_tokens=512,
                    do_sample=True,
                    pad_token_id=self.tokenizer.pad_token_id or self.tokenizer.eos_token_id
                )

            full_response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            return self._clean_response(full_response)
            
        except RuntimeError as e:
            logger.error(f"Generation failed: {e}")
            if "probability tensor" in str(e):
                return "Error: Invalid probabilities in model output"
            return "Error: Failed to generate summary"
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return "Error: Unexpected error occurred"

    def _clean_response(self, response: str) -> str:
        """Extract the model's response with proper timestamp."""
        try:
            clean_response = response.split("assistant")[-1].strip()
            return f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}] {clean_response}"
        except Exception as e:
            logger.error(f"Response cleaning failed: {e}")
            return "Error: Could not process response"

if __name__ == "__main__":
    try:
        summarizer = GemmaSummarizer()
        test_history = "[2023-01-01 12:00] User1: Привет\n[2023-01-01 12:05] User2: Как дела?"
        print(summarizer.generate_summary(test_history))
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
