"""
Simple YAML configuration loading for skills.

Provides easy access to global and skill-specific configuration values.
"""

from pathlib import Path
from typing import Any, Dict
from openai import AsyncOpenAI
import yaml
from skill_library.cli.azure_openai import create_azure_openai_client

class SkillConfig(dict[str, Any]):
    """Configuration for a specific skill with additional methods."""

    def __init__(self, skill_name: str, config_data: Dict[str, Any]):
        super().__init__(config_data or {})
        self.skill_name = skill_name

    def azure_client(self, model: str) -> AsyncOpenAI:
        """Create an Azure OpenAI client from config."""
        model_config = self.get("models", {}).get(model, {})
        if not model_config:
            raise ValueError(f"Model '{model}' not configured for skill '{self.skill_name}'")

        endpoint = model_config.get("endpoint")
        deployment = model_config.get("deployment")
        if not endpoint or not deployment:
            raise ValueError(f"Azure OpenAI endpoint or deployment not configured for skill '{self.skill_name}'")

        return create_azure_openai_client(endpoint, deployment)

class SkillsConfig:
    """Configuration manager for skills with YAML loading."""

    def __init__(self, skills_home_dir: Path):
        """Initialize config from skills home directory."""
        self.skills_home_dir = skills_home_dir
        config_file = skills_home_dir / "config" / "config.yaml"

        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    self._config = yaml.safe_load(f) or {}
            except Exception:
                self._config = {}
        else:
            self._config = {}

        # Create SkillConfig objects for each skill
        self.skill_configs = {}
        for skill_name, skill_data in self._config.get("skills", {}).items():
            self.skill_configs[skill_name] = SkillConfig(skill_name, skill_data or {})

    def skill_config(self, skill_name: str) -> SkillConfig:
        """Get SkillConfig object for the specified skill."""
        if skill_name in self.skill_configs:
            return self.skill_configs[skill_name]
        raise ValueError(f"Skill '{skill_name}' not found in configuration.")

    def get(self, key: str, default: Any = None) -> Any:
        """Get global config value."""
        return self._config.get(key, default)

    def get_skills_list(self) -> list[str]:
        """Get list of configured skill names."""
        return list(self._config.get("skills", {}).keys())

    def has_skill(self, skill_name: str) -> bool:
        """Check if skill is configured."""
        return skill_name in self._config.get("skills", {})
