#!/usr/bin/env python3
import tomli
from pathlib import Path
from typing import Optional
import logging
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
        """Initialize the summarizer with configurable paths.
        
        Args:
            config_path: Path to the TOML configuration file
            system_prompt_path: Path to the system prompt file
            summary_prompt_path: Path to the summary prompt file
        """
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

    def generate_summary(self, chat_history: str) -> str:
        """Generate a summary of the chat history using Groq API style.
        
        Args:
            chat_history: The chat history to summarize
            
        Returns:
            The generated summary text
        """
        try:
            model_config = self.config["model"]
            
            # Prepare the user prompt with chat history
            user_prompt = self.summary_prompt.format(
                chat_history=chat_history
            )
            
            # Make the API call in Groq style
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=model_config["name"],
                temperature=model_config.get("temperature", 0.7),
                top_p=0.2,  # Added top_p parameter as per Groq example
                max_tokens=model_config.get("max_tokens", 500)
            )
            
            # Return just the content of the first choice
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise
"""
**Example usage**

if __name__ == "__main__":
    try:
        summarizer = GemmaSummarizer()
        test_history = "[2023-01-01 12:00] User1: Привет\n[2023-01-01 12:05] User2: Как дела?"
        print(summarizer.generate_summary(test_history))
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
"""
