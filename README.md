# Gerrit AI Review

An AI-powered code review tool that integrates with Gerrit Code Review system. This tool automatically analyzes code changes and provides intelligent feedback through Gerrit's comment system.

## Features

- Automatic code review using AI
- Integration with Gerrit REST API
- Support for line-specific and global comments
- Configurable review criteria
- Draft comments management
- Code-Review label application (-1 or -2)

## Setup

1. Clone the repository:
```bash
git clone [your-repo-url]
cd gerrit_ai_review
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your Gerrit credentials:
```
GERRIT_URL=your_gerrit_url
GERRIT_USERNAME=your_username
GERRIT_API_TOKEN=your_api_token
```

## Usage

Run the server:
```bash
python src/server_direct.py
```

The server provides several tools for interacting with Gerrit:
- Get commit information
- Fetch change details
- Create draft comments
- Submit reviews with labels
- And more...

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.