"""Compatibility defaults for scenario-driven runtime policies."""

DEFAULT_ACTION_ALIASES = {
    "observe": "observe", "observation": "observe", "look": "observe",
    "help": "help", "assist": "help", "protect": "protect", "guard": "protect",
    "观察": "observe", "看看": "observe", "查看": "observe",
    "帮助": "help", "救": "help", "救助": "help",
    "保护": "protect", "守护": "protect",
}

# Entity names are deliberately not supplied by the engine. A world package
# provides aliases through its runtime configuration.
LEGACY_ENTITY_ALIASES = {}

DEFAULT_ACTION_DURATIONS = {
    "wake": 5, "eat": 20, "work": 60, "go_home": 15,
    "move": 15, "find": 10, "inspect": 5, "explore": 20,
}

DEFAULT_ACTION_DECISION_RULES = ()

