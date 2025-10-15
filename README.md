# Human Augmented Analytics Group - Research Projects

<div align="center">

![GitHub repo size](https://img.shields.io/github/repo-size/Human-Augment-Analytics/Progress-Tracker)
![GitHub last commit](https://img.shields.io/github/last-commit/Human-Augment-Analytics/Progress-Tracker)
![GitHub issues](https://img.shields.io/github/issues/Human-Augment-Analytics/Progress-Tracker)
![GitHub pull requests](https://img.shields.io/github/issues-pr/Human-Augment-Analytics/Progress-Tracker)


[View Project Tracker](https://human-augment-analytics.github.io/Progress-Tracker/)

</div>

---
## Quick Start

This repository contains two separate bots:

1. **Progress Bot** - Tracks GitHub milestones
2. **Qualtrics Bot** - Tracks survey response rates

### Prerequisites

**For Progress Bot:**
- Python 3.8+
- Slack Bot Token
- GitHub Personal Access Token

**For Qualtrics Bot:**
- Python 3.8+
- Slack Bot Token
- Qualtrics OAuth2 Client ID & Secret
- Qualtrics Datacenter ID

### Installation

```bash
# Clone the repository
git clone https://github.com/Human-Augment-Analytics/Progress-Tracker
cd Progress-Tracker

# Install dependencies
pip install -r requirements.txt
```

### Usage

#### Progress Bot (GitHub Milestones)

```bash
# Set environment variables
export GITHUB_TOKEN="your_github_token_here"
export SLACK_BOT_TOKEN="your_slack_bot_token_here"
export SLACK_CHANNEL_ID="C01234ABCDE"  # Channel ID or User ID

# Optional: Override default repository
export GITHUB_REPO_OWNER="your-org"
export GITHUB_REPO_NAME="your-repo"

# Run the bot
python progress_bot.py
```

#### Qualtrics Bot (Survey Tracking)

```bash
# Set environment variables
export SLACK_BOT_TOKEN="your_slack_bot_token_here"
export SLACK_CHANNEL_ID="C01234ABCDE"  # Channel ID or User ID

# Qualtrics OAuth2 credentials
export QUALTRICS_CLIENT_ID="your_client_id_here"
export QUALTRICS_CLIENT_SECRET="your_client_secret_here"
export QUALTRICS_DATACENTER="iad1"  # e.g., "fra1", "iad1", "sjc1"

# Run the bot
python qualtrics_bot.py
```

#### Combined Report (Legacy)

```bash
# To run both in one report (uses advanced_progress_bot.py)
export GITHUB_TOKEN="your_github_token_here"
export SLACK_BOT_TOKEN="your_slack_bot_token_here"
export SLACK_USER_ID="your_channel_id_here"
export QUALTRICS_CLIENT_ID="your_client_id_here"
export QUALTRICS_CLIENT_SECRET="your_client_secret_here"
export QUALTRICS_DATACENTER="your_datacenter_id"

python advanced_progress_bot.py --test
```

---

## Qualtrics Integration

The Progress Bot now supports tracking Qualtrics survey response rates alongside GitHub milestones, providing a unified view of both technical progress and research participant engagement.

### Features

- **Automatic Survey Discovery**: Automatically discovers and tracks all active surveys in your Qualtrics account
- **Response Rate Tracking**: Monitors survey responses against target goals
- **Completion Metrics**: Tracks completed vs. in-progress responses
- **Slack Integration**: Displays survey statistics in weekly Slack reports
- **Web Dashboard**: Shows survey progress cards on the web dashboard (requires backend API)

### Setup Qualtrics OAuth2 Authentication

**Using OAuth2 Client Credentials:**

1. **Create OAuth2 Client Application in Qualtrics**:
   - Log in to Qualtrics
   - Go to Account Settings → Qualtrics IDs
   - Navigate to the OAuth section
   - Click "Register a new application"
   - Save your `Client ID` and `Client Secret`

2. **Find your Datacenter ID**:
   - Look at your Qualtrics URL: `https://[DATACENTER].qualtrics.com`
   - Common datacenters: `fra1` (Frankfurt), `iad1` (Virginia), `sjc1` (San Jose), `ca1` (Canada), `au1` (Australia)

3. **Set environment variables**:
   ```bash
   export QUALTRICS_CLIENT_ID="your_client_id_here"
   export QUALTRICS_CLIENT_SECRET="your_client_secret_here"
   export QUALTRICS_DATACENTER="your_datacenter_id"
   ```

**How OAuth2 Works:**
- The bot uses **client credentials flow** with `grant_type=client_credentials`
- Requests a **bearer token** with `scope=manage:surveys` for survey API access
- Automatically refreshes the token before expiry
- More secure than API tokens as tokens are short-lived

### How It Works

When Qualtrics integration is enabled:

1. The bot automatically discovers all active surveys in your account
2. For each survey, it fetches:
   - Total response count
   - Completed responses
   - In-progress responses
   - Survey metadata (name, status, dates)
3. Calculates metrics:
   - Response rate (against target)
   - Completion rate
   - Average response rates across surveys
4. Displays in Slack reports with progress bars and action buttons

### Customizing Survey Targets

By default, each survey has a target of 100 responses. You can customize this in your code:

```python
# Manual survey configuration
bot.add_survey(
    name="User Research Study Q4",
    survey_id="SV_xxxxxxxxxxxxx",
    emoji="🔬",
    target_responses=250
)
```

### Web Dashboard Integration

The web dashboard (`docs/index.html`) includes survey tracking UI. To enable it, you need to:

1. Set up a backend API endpoint that proxies Qualtrics API calls (to avoid CORS issues)
2. Configure the endpoint in your HTML:
   ```javascript
   window.QUALTRICS_API_ENDPOINT = 'https://your-api.com/surveys';
   ```

The dashboard will display:
- Survey cards with response progress
- Completion rates and active status
- Links to take surveys
- Summary statistics

---


