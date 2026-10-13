"""Generic application entry point backed by the scenario package catalog."""


def main() -> int:
    from cognitive_sandbox.presentation.app import main as run_application

    return run_application()


if __name__ == "__main__":
    raise SystemExit(main())
