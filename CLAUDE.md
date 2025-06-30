# Wine EC Email Composer - Project Documentation

## Overview
This is a Streamlit-based web application for generating Japanese marketing emails for a wine e-commerce business. The app uses OpenAI's language models to create compelling email content for both individual wines and curated 6-bottle packages.

## Project Context
- **Business**: Backstreet Wine Shop (ペアリングワインショップ バックストリート / ビストロ路地裏)
- **Service**: 佐々布セレクション - Monthly curated 6-bottle wine packages by sommelier 佐々布
- **Target**: Japanese wine consumers
- **Language**: All email content is generated in Japanese

## Key Features
1. **Single Wine Email Generator** - Create marketing emails for individual wine products
2. **6-Bottle Package Email Generator** - Generate emails for monthly wine bundle sets
3. **PDF Wine List Import** - Extract wine information from Japanese PDF menus
4. **Wine Library Management** - Session-based storage with deduplication
5. **Multi-Model Support** - Various OpenAI models including GPT-4.1, O3, and O4

## Technical Stack
- **Framework**: Streamlit (>=1.40.1)
- **AI**: OpenAI API (>=1.61.0)
- **Data Processing**: Pandas, PDFPlumber
- **Validation**: Pydantic
- **Package Manager**: uv
- **Linting**: Ruff

## Project Structure
```
wine-ec_email-composer/
├── single_wine.py              # Main entry - Single wine emails
├── pages/
│   ├── packages_6bottles.py    # 6-bottle package emails
│   └── pdf_import.py           # PDF import functionality
├── src/
│   ├── models_config.py        # OpenAI model configurations
│   ├── pdf_processor.py        # PDF parsing & deduplication
│   ├── type_schema.py          # Data models (Pydantic)
│   ├── wine-list-pdf/          # Sample PDF files
│   └── *.csv                   # Historical email templates
```

## Running the Application
```bash
# Install dependencies
uv sync

# Run the application
streamlit run single_wine.py
```

## Development Commands
```bash
# Lint the code
ruff check .

# Format the code
ruff format .

# Type checking (if configured)
# Add type checking command if available
```

## Key Workflows

### 1. Generating Single Wine Emails
- Navigate to the main page
- Enter wine details (name, producer, region, etc.)
- Select AI model and temperature
- Generate email with title, preview text, and body

### 2. Creating 6-Bottle Package Emails
- Go to "6 bottles bundle monthly set" page
- Enter monthly concept and key sommelier comments
- Add wine names (manually or from imported library)
- Generate complete email campaign

### 3. Importing Wine Lists from PDF
- Navigate to "Import Wine List from PDF"
- Upload Japanese wine menu PDFs
- AI extracts and deduplicates wine information
- Save to session wine library for reuse

## Important Business Rules
1. **佐々布セレクション** packages are always:
   - 6 bottles per set
   - Free shipping (送料無料)
   - Curated by sommelier 佐々布

2. **Email Content Requirements**:
   - Written in Japanese
   - Uses appropriate emojis (but not excessively)
   - References seasonal themes
   - Includes tasting notes from sommelier

3. **Wine Information Processing**:
   - Japanese names take priority over romanized versions
   - Duplicate wines are merged intelligently
   - Non-wine content is filtered from PDFs

## Data Files
- `src/*-mail-contents_*.csv` - Historical email templates for reference
- `src/wine-list-pdf/*.pdf` - Sample wine list PDFs for testing

## Model Configuration
The app supports multiple OpenAI models with special handling:
- **Reasoning models** (O3, O3-mini, O4-mini-deep-research) - Fixed temperature of 1.0
- **Standard models** - Adjustable temperature (0.0-2.0)
- Default model: GPT-4o mini

## Session State Management
The app uses Streamlit session state to maintain:
- `imported_wines`: Library of wines from PDFs
- `selected_wines`: Currently selected wines for email generation
- Wine data persists across page navigation within a session

## Notes for Future Development
1. Consider adding email preview functionality
2. Implement email template saving/loading
3. Add batch processing for multiple wines
4. Consider integration with email service providers
5. Add analytics for email performance tracking

## Troubleshooting
- If PDF import fails, check that the PDF contains Japanese text
- For model errors, verify OpenAI API key is set in environment
- Session state resets on app restart - consider persistent storage