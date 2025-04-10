# EPAM Code Review Guidelines

## General Guidelines

1. **Be Respectful and Constructive**: Focus on the code, not the person. Provide constructive feedback that helps improve the code quality.

2. **Be Specific**: Point to specific sections of code when providing feedback. Use line numbers and file names to make your comments clear.

3. **Ask Questions**: Instead of making demands, ask questions that lead the developer to discover issues themselves.

4. **Explain Why**: Always explain why you're suggesting a change, not just what should be changed.

5. **Prioritize Feedback**: Focus on architectural and design issues first, then functional correctness, and finally style and formatting.

## Code Quality Guidelines

### Readability
- Is the code easy to understand?
- Are variable and function names descriptive and consistent?
- Is the code well-formatted according to team standards?
- Are there appropriate comments for complex logic?

### Maintainability
- Is the code modular and follows single responsibility principle?
- Is there any duplicate code that should be refactored?
- Are magic numbers and strings avoided in favor of constants?
- Is the code extensible for future requirements?

### Performance
- Are there any obvious performance issues?
- Are there any unnecessary computations or memory allocations?
- Are appropriate data structures being used?
- Are database queries optimized?

### Security
- Are inputs properly validated?
- Is authentication and authorization properly implemented?
- Are there any SQL injection, XSS, or CSRF vulnerabilities?
- Is sensitive information properly protected?

### Testing
- Are there appropriate unit tests for the code?
- Do the tests cover edge cases?
- Are mock objects used appropriately?
- Is the code testable?

## Language-Specific Guidelines

### Java
- Avoid unnecessary object creation
- Use appropriate collection types
- Handle exceptions properly
- Follow standard coding conventions

### JavaScript/TypeScript
- Use modern ES6+ features appropriately
- Avoid callback hell with promises or async/await
- Minimize DOM manipulation in UI code
- Handle asynchronous operations properly

### Python
- Follow PEP 8 style guide
- Use list comprehensions when appropriate
- Use virtual environments for dependencies
- Properly handle exceptions

### Kotlin
- Use Kotlin's concise syntax appropriately
- Leverage nullable types and safe calls
- Use extension functions to enhance existing classes
- Make appropriate use of coroutines for asynchronous code

## Pull Request Guidelines

1. **Keep Changes Small**: Limit PRs to a single feature or bug fix
2. **Provide Context**: Explain what the changes do and why they're needed
3. **Link to Requirements**: Reference related tickets or requirements
4. **Self-Review**: Review your own code before submitting for review
5. **Testing**: Ensure all tests pass and add new tests for new functionality

## Final Review Checklist

Before approving a PR, consider:
- Does the code meet all requirements?
- Are all edge cases handled?
- Is there technical debt being introduced?
- Is documentation updated?
- Are all tests passing?
- Does the code follow team standards?
