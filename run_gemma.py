#!/usr/bin/env python3
import tomli
from pathlib import Path
from typing import Optional
import logging
import json
import sys
from groq import Groq

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class GemmaSummarizer:
    """A streamlined Gemma summarizer following Groq API style."""
    
    def __init__(
        self,
        config_path: str = "config.toml",
        system_prompt_path: str = "prompts/system_prompt.txt",
        summary_prompt_path: str = "prompts/summary_prompt.txt"
    ):
        """Initialize the summarizer with configurable paths."""
        self.config = self._load_config(config_path)
        self.system_prompt = self._load_prompt_file(system_prompt_path)
        self.summary_prompt = self._load_prompt_file(summary_prompt_path)
        self.client = Groq(api_key=self.config["model"].get("api_key"))

    def _load_config(self, config_path: str) -> dict:
        """Load and validate configuration from TOML file."""
        try:
            with open(config_path, "rb") as f:
                config = tomli.load(f)
            
            required_keys = {"name", "temperature", "max_tokens", "api_key"}
            if not required_keys.issubset(config.get("model", {})):
                raise ValueError(f"Config missing required keys: {required_keys}")
                
            return config
            
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            raise

    def _load_prompt_file(self, path: str) -> str:
        """Load a prompt from a text file."""
        try:
            return Path(path).read_text(encoding="utf-8").strip()
        except Exception as e:
            logger.error(f"Failed to load prompt file {path}: {e}")
            raise

    def generate_summary(self, chat_history: str, output_file: str) -> None:
        """Generate and save summary of the chat history."""
        try:
            model_config = self.config["model"]
            
            user_prompt = self.summary_prompt.format(
                chat_history=chat_history
            )
            
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=model_config["name"],
                temperature=model_config.get("temperature", 0.7),
                top_p=0.2,
                max_tokens=model_config.get("max_tokens", 500)
            )
            
            summary = response.choices[0].message.content
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(summary)
            logger.info(f"Summary successfully saved to {output_file}")
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise

def main():
    """Command line interface for the summarizer."""
    if len(sys.argv) != 3:
        print("Usage: python3 run_gemma.py <input_file> <output_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    try:
        # Read the formatted chat history
        with open(input_file, 'r', encoding='utf-8') as f:
            chat_history = f.read()
        
        summarizer = GemmaSummarizer()
        summarizer.generate_summary(chat_history, output_file)
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
