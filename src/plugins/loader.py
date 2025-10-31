"""
Plugin Loader
Loads and parses agent, command, and skill definitions from markdown files
"""
from typing import Dict, List, Any, Optional
import os
import yaml
import re


class AgentDefinition:
    """Represents an agent definition from a plugin"""

    def __init__(
        self,
        name: str,
        description: str,
        model: str,
        tools: List[str],
        triggers: List[str],
        instructions: str
    ):
        self.name = name
        self.description = description
        self.model = model
        self.tools = tools
        self.triggers = triggers
        self.instructions = instructions


class PluginLoader:
    """Loads plugins from system-plugins and workspace plugin directories"""

    def __init__(self, system_plugins_dir: str = "system-plugins"):
        self.system_plugins_dir = system_plugins_dir
        self.agents: Dict[str, AgentDefinition] = {}

    def load_all_plugins(self):
        """Load all plugins from system-plugins directory"""
        if not os.path.exists(self.system_plugins_dir):
            return

        plugins_dir = os.path.join(self.system_plugins_dir, "plugins")
        if not os.path.exists(plugins_dir):
            return

        # Iterate through plugin directories
        for plugin_name in os.listdir(plugins_dir):
            plugin_path = os.path.join(plugins_dir, plugin_name)
            if os.path.isdir(plugin_path):
                self._load_plugin(plugin_path)

    def _load_plugin(self, plugin_path: str):
        """Load a single plugin"""
        # Load agents
        agents_dir = os.path.join(plugin_path, "agents")
        if os.path.exists(agents_dir):
            for agent_file in os.listdir(agents_dir):
                if agent_file.endswith(".md"):
                    agent_path = os.path.join(agents_dir, agent_file)
                    agent = self._parse_agent_definition(agent_path)
                    if agent:
                        self.agents[agent.name] = agent

    def _parse_agent_definition(self, file_path: str) -> Optional[AgentDefinition]:
        """
        Parse agent definition from markdown file with YAML frontmatter

        Format:
        ---
        name: research-agent
        description: Gathers codebase context
        model: claude-sonnet-4
        tools: [Grep, Glob, Read, Bash, TodoWrite]
        triggers: [phase:research, command:/research]
        ---

        # Agent Instructions
        ...
        """
        with open(file_path, "r") as f:
            content = f.read()

        # Extract YAML frontmatter
        frontmatter_match = re.match(r'^---\n(.*?)\n---\n(.*)$', content, re.DOTALL)
        if not frontmatter_match:
            return None

        frontmatter_str = frontmatter_match.group(1)
        instructions = frontmatter_match.group(2).strip()

        try:
            frontmatter = yaml.safe_load(frontmatter_str)
        except yaml.YAMLError:
            return None

        return AgentDefinition(
            name=frontmatter.get("name", ""),
            description=frontmatter.get("description", ""),
            model=frontmatter.get("model", "claude-sonnet-4"),
            tools=frontmatter.get("tools", []),
            triggers=frontmatter.get("triggers", []),
            instructions=instructions
        )

    def get_agent(self, name: str) -> Optional[AgentDefinition]:
        """Get agent definition by name"""
        return self.agents.get(name)

    def list_agents(self) -> List[str]:
        """List all loaded agent names"""
        return list(self.agents.keys())
