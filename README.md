# Wine EC Email Composer

A Streamlit-based web application for generating marketing emails for a Japanese wine e-commerce business. The app uses OpenAI's language models to create compelling email content in Japanese for both individual wines and curated 6-bottle packages.

## Streamlit Cloud

https://wine-email-composer.streamlit.app

## Features

- **Single Wine Email Generator** - Create marketing emails for individual wine products
- **6-Bottle Package Email Generator** - Generate emails for monthly wine bundle sets (Monthly curated 6-bottle wine packages)
- **PDF Wine List Import** - Extract wine information from Japanese PDF menus with AI
- **Wine Library Management** - Session-based storage with intelligent deduplication
- **Multi-Model Support** - Various OpenAI models including GPT-4o, O3, and O4
- **Secure Authentication** - Session-based login system for production deployment

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/wine-ec_email-composer.git
cd wine-ec_email-composer

# Install dependencies using uv
uv sync

# Set up OpenAI API key
export OPENAI_API_KEY="your-api-key-here"
```

## Authentication Setup

The app includes secure authentication for production deployment on Streamlit Cloud. For detailed setup instructions, see [AUTHENTICATION_SETUP.md](AUTHENTICATION_SETUP.md).

**Quick Setup:**

- **Local Development**: Uses demo credentials (admin/password123)
- **Production**: Configure credentials in Streamlit Cloud secrets
- **Security**: Session-based authentication protects all pages

## Usage

```bash
# Run the application
uv run streamlit run single_wine.py
```

The application will open in your web browser. Navigate between pages using the sidebar:

- **Single Wine**: Generate emails for individual wines
- **6 bottles bundle monthly set**: Create emails for wine packages
- **Import Wine List from PDF**: Extract wine data from PDF menus
- **Wine Library**: View and manage imported wines

## Project Structure

```
wine-ec_email-composer/
├── single_wine.py              # Main entry - Single wine emails
├── auth.py                     # Authentication module
├── pages/
│   ├── packages_6bottles.py    # 6-bottle package emails
│   ├── pdf_import.py           # PDF import functionality
│   └── wine_library.py         # Wine library management
├── src/
│   ├── models_config.py        # OpenAI model configurations
│   ├── pdf_processor.py        # PDF parsing & deduplication
│   ├── type_schema.py          # Data models (Pydantic)
│   ├── wine-list-pdf/          # Sample PDF files
│   └── *.csv                   # Historical email templates
├── .streamlit/
│   └── secrets.toml            # Authentication credentials template
├── AUTHENTICATION_SETUP.md     # Authentication setup guide
├── CLAUDE.md                   # Project documentation
└── README.md                   # This file
```

## Key Workflows

### Generating Single Wine Emails

1. Navigate to the main page
2. Enter wine details (name, producer, region, etc.)
3. Select AI model and temperature settings
4. Click "Generate Email Content"
5. Review generated title, preview text, and body

### Creating 6-Bottle Package Emails

1. Go to "6 bottles bundle monthly set" page
2. Enter monthly concept and key sommelier comments
3. Add wine names (manually or select from imported library)
4. Generate complete email campaign

### Importing Wine Lists from PDF

1. Navigate to "Import Wine List from PDF"
2. Upload Japanese wine menu PDFs
3. AI extracts wine information automatically
4. Review and manually merge similar wines
5. Import to session wine library

### Managing Wine Library

1. View all imported wines in "Wine Library" page
2. Search and filter wines
3. Export wine data as needed

## Development

```bash
# Lint the code
ruff check .

# Format the code
ruff format .

# Run tests (if available)
# Add test command here
```

## Configuration

### OpenAI Models

The app supports multiple models with different capabilities:

- **GPT-4o mini** (default): Fast and cost-effective
- **GPT-4o**: More capable for complex tasks
- **O3/O3-mini**: Reasoning models (fixed temperature)
- **O4-mini-deep-research**: Deep research capabilities

### Temperature Settings

- **0.0-0.3**: More consistent, predictable outputs
- **0.7-1.0**: More creative and varied (default: 0.7)
- **1.0-2.0**: Highly creative outputs

## Business Context

This tool is designed for:

- **Business**: Backstreet Wine Shop（路地裏ワインショップ）
- **Service**: プレミアム - Monthly curated 6-bottle wine packages
- **Target**: Japanese wine consumers
- **Language**: All content generated in Japanese

## License

[Add your license here]

## Contributing

[Add contributing guidelines here]

## Support

For issues or questions, please [open an issue](https://github.com/yourusername/wine-ec_email-composer/issues).
