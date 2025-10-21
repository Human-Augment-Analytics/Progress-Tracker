#!/usr/bin/env python3
"""
Qualtrics Survey Bot

Tracks Qualtrics survey response rates and sends reports to Slack.
Uses OAuth2 client credentials flow with manage:surveys scope.
"""

import os
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@dataclass
class SurveyConfig:
    """Configuration for a Qualtrics survey."""
    name: str
    survey_id: str
    emoji: str = ""


class QualtricsBot:
    """Slack bot for Qualtrics survey tracking."""
    
    def __init__(self, slack_token: str, channel_id: str,
                 qualtrics_client_id: str, qualtrics_client_secret: str,
                 qualtrics_datacenter: str):
        """
        Initialize the Qualtrics bot.
        
        Args:
            slack_token: Slack bot OAuth token
            channel_id: Slack channel ID or user ID to send updates to
            qualtrics_client_id: Qualtrics OAuth2 client ID
            qualtrics_client_secret: Qualtrics OAuth2 client secret
            qualtrics_datacenter: Qualtrics datacenter (e.g., 'fra1', 'iad1')
        """
        self.slack_token = slack_token
        self.channel_id = channel_id
        self.qualtrics_datacenter = qualtrics_datacenter
        self.qualtrics_client_id = qualtrics_client_id
        self.qualtrics_client_secret = qualtrics_client_secret
        self.qualtrics_oauth_token = None
        self.qualtrics_token_expiry = None
        
        self.slack_headers = {
            'Authorization': f'Bearer {slack_token}',
            'Content-Type': 'application/json'
        }
        
        self.qualtrics_headers = {}
        self.surveys = []
        
        # Get OAuth token
        print("Using Qualtrics OAuth2 authentication...")
        self._get_qualtrics_oauth_token()
    
    def _get_qualtrics_oauth_token(self) -> bool:
        """Obtain OAuth2 token from Qualtrics using client credentials flow."""
        if not self.qualtrics_client_id or not self.qualtrics_client_secret or not self.qualtrics_datacenter:
            print("Missing Qualtrics OAuth2 credentials")
            return False
        
        token_url = f'https://{self.qualtrics_datacenter}.qualtrics.com/oauth2/token'
        
        # Using client credentials flow with survey and response reading scopes
        auth_data = {
            'grant_type': 'client_credentials',
            'scope': 'read:surveys read:survey_responses',
            'client_id': self.qualtrics_client_id,
            'client_secret': self.qualtrics_client_secret
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        try:
            response = requests.post(token_url, data=auth_data, headers=headers)
            response.raise_for_status()
            
            token_data = response.json()
            self.qualtrics_oauth_token = token_data['access_token']
            expires_in = token_data.get('expires_in', 3600)
            
            self.qualtrics_token_expiry = datetime.now() + timedelta(seconds=expires_in - 60)
            
            self.qualtrics_headers = {
                'Authorization': f'Bearer {self.qualtrics_oauth_token}',
                'Content-Type': 'application/json'
            }
            
            print(f"Successfully obtained Qualtrics OAuth2 token (expires in {expires_in}s)")
            print(f"Bearer Token: {self.qualtrics_oauth_token}")
            return True
            
        except requests.RequestException as e:
            print(f"Error obtaining Qualtrics OAuth2 token: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Response: {e.response.text}")
            return False
    
    def _refresh_qualtrics_token_if_needed(self) -> None:
        """Refresh Qualtrics OAuth2 token if it's about to expire."""
        if self.qualtrics_oauth_token and self.qualtrics_token_expiry:
            if datetime.now() >= self.qualtrics_token_expiry:
                print("Refreshing Qualtrics OAuth2 token...")
                self._get_qualtrics_oauth_token()
    
    def discover_all_surveys(self) -> List[SurveyConfig]:
        """Auto-discover all surveys in Qualtrics account."""
        if not self.qualtrics_headers or not self.qualtrics_datacenter:
            print("Qualtrics API credentials not configured. Skipping survey discovery.")
            return []
        
        self._refresh_qualtrics_token_if_needed()
        
        base_url = f'https://{self.qualtrics_datacenter}.qualtrics.com/API/v3'
        url = f'{base_url}/surveys'
        
        try:
            response = requests.get(url, headers=self.qualtrics_headers)
            response.raise_for_status()
            
            surveys_data = response.json()['result']['elements']
            discovered_surveys = []
            
            for survey in surveys_data:
                if survey.get('isActive', False):
                    config = SurveyConfig(
                        name=survey.get('name', f"Survey {survey['id']}"),
                        survey_id=survey['id'],
                        emoji=""
                    )
                    discovered_surveys.append(config)
            
            print(f"Discovered {len(discovered_surveys)} active surveys in Qualtrics")
            return discovered_surveys
            
        except requests.RequestException as e:
            print(f"Error discovering surveys: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Status: {e.response.status_code}")
                print(f"   Response: {e.response.text}")
            return []
    
    def _export_survey_responses(self, survey_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Export survey responses using Qualtrics 3-step export API.

        Steps:
        1. Create export request
        2. Poll for export completion
        3. Download and parse export file

        Args:
            survey_id: The survey ID
            start_date: Optional start date filter (ISO format: YYYY-MM-DDTHH:MM:SSZ)
            end_date: Optional end date filter (ISO format: YYYY-MM-DDTHH:MM:SSZ)
        """
        base_url = f'https://{self.qualtrics_datacenter}.qualtrics.com/API/v3'

        # Step 1: Create export
        export_url = f'{base_url}/surveys/{survey_id}/export-responses'
        export_payload = {
            'format': 'json',
            'compress': False
        }

        # Add date filters if provided
        if start_date or end_date:
            export_payload['startDate'] = start_date
            export_payload['endDate'] = end_date
            print(f"DEBUG: Filtering responses from {start_date} to {end_date}")

        try:
            print(f"DEBUG: Creating export for survey {survey_id}...")
            create_response = requests.post(export_url, headers=self.qualtrics_headers, json=export_payload)
            create_response.raise_for_status()

            progress_id = create_response.json()['result']['progressId']
            print(f"DEBUG: Export created with progressId: {progress_id}")

            # Step 2: Poll for completion
            check_url = f'{base_url}/surveys/{survey_id}/export-responses/{progress_id}'
            max_attempts = 30
            attempt = 0

            import time
            while attempt < max_attempts:
                time.sleep(1)
                check_response = requests.get(check_url, headers=self.qualtrics_headers)
                check_response.raise_for_status()

                status_data = check_response.json()['result']
                status = status_data.get('status')
                percent_complete = status_data.get('percentComplete', 0)

                print(f"DEBUG: Export status: {status} ({percent_complete}%)")

                if status == 'complete':
                    file_id = status_data.get('fileId')
                    print(f"DEBUG: Export complete, fileId: {file_id}")

                    # Step 3: Download file
                    download_url = f'{base_url}/surveys/{survey_id}/export-responses/{file_id}/file'
                    download_response = requests.get(download_url, headers=self.qualtrics_headers)
                    download_response.raise_for_status()

                    import json
                    export_data = download_response.json()
                    responses = export_data.get('responses', [])
                    print(f"DEBUG: Downloaded {len(responses)} responses")

                    return responses
                elif status == 'failed':
                    print(f"DEBUG: Export failed")
                    return None

                attempt += 1

            print(f"DEBUG: Export timed out after {max_attempts} attempts")
            return None

        except requests.RequestException as e:
            print(f"DEBUG: Export API error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"DEBUG: Status: {e.response.status_code}")
                print(f"DEBUG: Response: {e.response.text}")
            return None

    def get_survey_data(self, survey: SurveyConfig) -> Optional[Dict[str, Any]]:
        """Fetch survey data from Qualtrics API."""
        if not self.qualtrics_headers or not self.qualtrics_datacenter:
            print("Qualtrics API credentials not configured. Skipping survey data.")
            return None

        self._refresh_qualtrics_token_if_needed()

        base_url = f'https://{self.qualtrics_datacenter}.qualtrics.com/API/v3'

        try:
            # Get survey metadata
            survey_url = f'{base_url}/surveys/{survey.survey_id}'
            survey_response = requests.get(survey_url, headers=self.qualtrics_headers)
            survey_response.raise_for_status()
            survey_info = survey_response.json()['result']

            # Calculate this week's date range (Monday to Sunday)
            from datetime import datetime, timedelta
            today = datetime.now()
            # Find Monday of current week (weekday 0 = Monday)
            days_since_monday = today.weekday()
            monday = today - timedelta(days=days_since_monday)
            monday_start = monday.replace(hour=0, minute=0, second=0, microsecond=0)

            # Find Sunday end of week
            sunday_end = monday_start + timedelta(days=7) - timedelta(seconds=1)

            # Format for Qualtrics API
            start_date = monday_start.strftime('%Y-%m-%dT%H:%M:%SZ')
            end_date = sunday_end.strftime('%Y-%m-%dT%H:%M:%SZ')

            # Get all responses
            print(f"Fetching all responses...")
            all_responses = self._export_survey_responses(survey.survey_id)

            # Get this week's responses
            print(f"Fetching this week's responses (since {monday_start.strftime('%Y-%m-%d')})...")
            weekly_responses = self._export_survey_responses(survey.survey_id, start_date, end_date)

            total_responses = 0
            completed_responses = 0
            in_progress = 0
            weekly_total = 0
            weekly_completed = 0

            if all_responses is not None:
                total_responses = len(all_responses)

                # Count completed responses - check in the 'values' dict
                completed_responses = sum(1 for r in all_responses if
                                        r.get('values', {}).get('finished') == 1 or
                                        r.get('values', {}).get('finished') == '1' or
                                        r.get('values', {}).get('finished') == True or
                                        str(r.get('values', {}).get('finished', '')).lower() == 'true' or
                                        r.get('values', {}).get('progress') == 100 or
                                        r.get('values', {}).get('progress') == '100' or
                                        r.get('values', {}).get('endDate'))

                in_progress = max(0, total_responses - completed_responses)
                print(f"DEBUG: Total: {total_responses}, Completed: {completed_responses}, In Progress: {in_progress}")
            else:
                print("Could not fetch response data via export API")

            if weekly_responses is not None:
                weekly_total = len(weekly_responses)
                weekly_completed = sum(1 for r in weekly_responses if
                                     r.get('values', {}).get('finished') == 1 or
                                     r.get('values', {}).get('finished') == '1' or
                                     r.get('values', {}).get('finished') == True or
                                     str(r.get('values', {}).get('finished', '')).lower() == 'true' or
                                     r.get('values', {}).get('progress') == 100 or
                                     r.get('values', {}).get('progress') == '100' or
                                     r.get('values', {}).get('endDate'))
                print(f"DEBUG: This week - Total: {weekly_total}, Completed: {weekly_completed}")

            completion_rate = (completed_responses / total_responses * 100) if total_responses > 0 else 0

            return {
                'name': survey_info.get('name', survey.name),
                'survey_id': survey.survey_id,
                'total_responses': total_responses,
                'completed_responses': completed_responses,
                'in_progress': in_progress,
                'weekly_total': weekly_total,
                'weekly_completed': weekly_completed,
                'completion_rate': completion_rate,
                'is_active': survey_info.get('isActive', False),
                'created_date': survey_info.get('creationDate'),
                'modified_date': survey_info.get('lastModified'),
                'survey_url': f'https://{self.qualtrics_datacenter}.qualtrics.com/jfe/form/{survey.survey_id}'
            }

        except requests.RequestException as e:
            print(f"Error fetching survey data for {survey.name}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Status: {e.response.status_code}")
                print(f"   Response: {e.response.text}")
            return None
    
    def create_progress_bar(self, percentage: float, width: int = 20) -> str:
        """Create a visual progress bar using Unicode characters."""
        filled = int(percentage / 100 * width)
        empty = width - filled
        
        filled_char = "█"
        empty_char = "░"
        
        return f"{filled_char * filled}{empty_char * empty}"
    
    def get_status_emoji(self, percentage: float) -> str:
        """Get status emoji based on progress percentage."""
        if percentage >= 100:
            return "✅"
        elif percentage >= 75:
            return "🟢"
        elif percentage >= 50:
            return "🟡"
        elif percentage >= 25:
            return "🟠"
        else:
            return "🔴"
    
    def create_survey_block(self, survey: SurveyConfig, survey_data: Dict[str, Any]) -> List[Dict]:
        """Create Slack blocks for a single survey."""
        completion_rate = survey_data['completion_rate']

        header_block = {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{survey_data['name']}",
                "emoji": True
            }
        }

        active_text = "Active" if survey_data.get('is_active') else "Inactive"

        stats_section = {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Survey ID:* `{survey_data['survey_id']}`"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Status:* {active_text}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Total Responses:* {survey_data['total_responses']}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Completion Rate:* {completion_rate:.1f}%"
                }
            ]
        }

        metrics_text = f"*All Time:*\n"
        metrics_text += f"  • Completed: {survey_data['completed_responses']}\n"
        metrics_text += f"  • In Progress: {survey_data['in_progress']}\n\n"
        metrics_text += f"*This Week:*\n"
        metrics_text += f"  • Total: {survey_data['weekly_total']}\n"
        metrics_text += f"  • Completed: {survey_data['weekly_completed']}\n"

        if survey_data.get('modified_date'):
            modified_date = datetime.fromisoformat(survey_data['modified_date'].replace('Z', '+00:00'))
            metrics_text += f"\n*Last Modified:* {modified_date.strftime('%B %d, %Y at %I:%M %p')}"

        metrics_section = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": metrics_text
            }
        }
        
        actions_block = {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Take Survey",
                        "emoji": True
                    },
                    "url": survey_data['survey_url'],
                    "style": "primary"
                }
            ]
        }
        
        return [
            header_block,
            stats_section,
            metrics_section,
            actions_block,
            {"type": "divider"}
        ]
    
    def send_slack_message(self, blocks: List[Dict]) -> bool:
        """Send formatted message to Slack using Blocks API."""
        url = "https://slack.com/api/chat.postMessage"
        
        payload = {
            "channel": self.channel_id,
            "blocks": blocks,
            "text": "Qualtrics Survey Report"
        }
        
        try:
            response = requests.post(url, headers=self.slack_headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            if result.get('ok'):
                print("Successfully sent survey report to Slack!")
                return True
            else:
                print(f"Slack API error: {result.get('error', 'Unknown error')}")
                return False
                
        except requests.RequestException as e:
            print(f"Error sending Slack message: {e}")
            return False
    
    def generate_report(self) -> None:
        """Generate and send survey report."""
        print("Generating Qualtrics survey report...")
        
        print("Auto-discovering surveys...")
        self.surveys = self.discover_all_surveys()
        
        if not self.surveys:
            print("No active surveys found")
            return
        
        surveys_data = []
        for survey in self.surveys:
            print(f"Fetching data for {survey.name}...")
            survey_data = self.get_survey_data(survey)
            if survey_data:
                surveys_data.append((survey, survey_data))
        
        if not surveys_data:
            print("No survey data could be retrieved")
            return
        
        all_blocks = []
        
        survey_header = {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Qualtrics Survey Tracking",
                "emoji": True
            }
        }
        all_blocks.append(survey_header)
        
        # Add survey summary
        total_surveys = len(surveys_data)
        total_responses = sum(data['total_responses'] for _, data in surveys_data)
        weekly_responses = sum(data['weekly_total'] for _, data in surveys_data)

        survey_summary = {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Active Surveys:* {total_surveys}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Total Responses (All Time):* {total_responses}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*This Week's Responses:* {weekly_responses}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Report Date:* {datetime.now().strftime('%B %d, %Y')}"
                }
            ]
        }
        all_blocks.extend([survey_summary, {"type": "divider"}])
        
        # Add individual survey blocks
        for survey, survey_data in surveys_data:
            all_blocks.extend(self.create_survey_block(survey, survey_data))
        
        if all_blocks and all_blocks[-1].get("type") == "divider":
            all_blocks.pop()
        
        footer_block = {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
                }
            ]
        }
        all_blocks.append(footer_block)
        
        success = self.send_slack_message(all_blocks)
        
        if success:
            print(f"Report sent! Tracked {len(surveys_data)} surveys successfully.")
        else:
            print("Failed to send report.")


def main():
    """Main function to run the Qualtrics bot."""
    
    slack_token = os.getenv('SLACK_BOT_TOKEN')
    channel_id = os.getenv('SLACK_CHANNEL_ID')
    
    qualtrics_client_id = os.getenv('QUALTRICS_CLIENT_ID')
    qualtrics_client_secret = os.getenv('QUALTRICS_CLIENT_SECRET')
    qualtrics_datacenter = os.getenv('QUALTRICS_DATACENTER')
    
    if not slack_token:
        print("Missing SLACK_BOT_TOKEN environment variable")
        print("Please set: export SLACK_BOT_TOKEN='your_slack_bot_token_here'")
        return
    
    if not channel_id:
        print("Missing SLACK_CHANNEL_ID environment variable")
        print("Please set: export SLACK_CHANNEL_ID='your_channel_id_here'")
        return
    
    if not qualtrics_client_id or not qualtrics_client_secret or not qualtrics_datacenter:
        print("Missing Qualtrics OAuth2 credentials")
        print("Please set:")
        print("  export QUALTRICS_CLIENT_ID='your_client_id'")
        print("  export QUALTRICS_CLIENT_SECRET='your_client_secret'")
        print("  export QUALTRICS_DATACENTER='your_datacenter'")
        return
    
    bot = QualtricsBot(
        slack_token=slack_token,
        channel_id=channel_id,
        qualtrics_client_id=qualtrics_client_id,
        qualtrics_client_secret=qualtrics_client_secret,
        qualtrics_datacenter=qualtrics_datacenter
    )
    
    bot.generate_report()


if __name__ == '__main__':
    main()



