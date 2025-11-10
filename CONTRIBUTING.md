# Contributing to Orb

Thank you for your interest in contributing to Orb! We welcome contributions from the community.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally
   ```bash
   git clone https://github.com/your-username/Orb.git
   cd Orb
   ```
3. **Set up the development environment**
   ```bash
   # Create a virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements-dev.txt
   ```

## Development Workflow

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Follow the code style (PEP 8)
   - Write tests for new features
   - Update documentation as needed

3. **Run tests**
   ```bash
   pytest
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add your feature"
   ```

5. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request**
   - Go to the [Orb repository](https://github.com/your-username/Orb)
   - Click "New Pull Request"
   - Follow the PR template

## Code Style

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) for Python code
- Use type hints for all function signatures
- Keep lines under 100 characters
- Use docstrings for all public functions and classes

## Testing

- Write unit tests for new features
- Ensure all tests pass before submitting a PR
- Run `pytest --cov=src` to check test coverage

## Reporting Issues

When reporting issues, please include:
- Description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, etc.)

## Code of Conduct

Please note that this project is released with a [Contributor Code of Conduct](CODE_OF_CONDUCT.md). By participating in this project you agree to abide by its terms.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
