#!/usr/bin/env python3
"""
Human Augmented Analytics Group -  Progress Bot

A sophisticated bot that tracks multiple research projects and sends
beautifully formatted progress updates using Slack's Blocks API.
"""

import os
import json
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not installed, skip loading .env file
    pass


@dataclass
class ProjectConfig:
    """Configuration for a single project."""
    name: str
    repo_owner: str
    repo_name: str
    milestone_number: int
    emoji: str = ""
    color: str = "#36a64f"  # Green


@dataclass
class SurveyConfig:
    """Configuration for a Qualtrics survey."""
    name: str
    survey_id: str
    emoji: str = ""
    target_responses: int = 100


class ProgressBot:
    """ Slack bot for multi-project progress tracking."""
    
    def __init__(self, slack_token: str, github_token: str, user_id: str, 
                 qualtrics_client_id: str = None, qualtrics_client_secret: str = None,
                 qualtrics_datacenter: str = None):
        """
        Initialize the  progress bot.
        
        Args:
            slack_token: Slack bot OAuth token
            github_token: GitHub personal access token
            user_id: Slack user ID or channel ID/name to send updates to
                     (User ID: U01234ABCDE, Channel ID: C01234ABCDE, Channel name: #general)
            qualtrics_client_id: Qualtrics OAuth2 client ID (optional)
            qualtrics_client_secret: Qualtrics OAuth2 client secret (optional)
            qualtrics_datacenter: Qualtrics datacenter (e.g., 'fra1', 'iad1') (optional)
        """
        self.slack_token = slack_token
        self.github_token = github_token
        self.user_id = user_id
        self.qualtrics_datacenter = qualtrics_datacenter
        self.qualtrics_client_id = qualtrics_client_id
        self.qualtrics_client_secret = qualtrics_client_secret
        self.qualtrics_oauth_token = None
        self.qualtrics_token_expiry = None
        
        self.slack_headers = {
            'Authorization': f'Bearer {slack_token}',
            'Content-Type': 'application/json'
        }
        
        self.github_headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        # Initialize Qualtrics authentication with OAuth2 only
        self.qualtrics_headers = {}
        if qualtrics_client_id and qualtrics_client_secret and qualtrics_datacenter:
            print("Using Qualtrics OAuth2 authentication...")
            self._get_qualtrics_oauth_token()
        
        # Repository configuration
        self.repo_owner = "Human-Augment-Analytics"
        self.repo_name = "Progress-Tracker"
        
        # Milestones will be auto-discovered from GitHub
        self.milestones = []
        
        # Surveys to track
        self.surveys = []
    
    def _get_qualtrics_oauth_token(self) -> bool:
        """
        Obtain OAuth2 token from Qualtrics using client credentials flow.
        
        Returns:
            True if token obtained successfully, False otherwise
        """
        if not self.qualtrics_client_id or not self.qualtrics_client_secret or not self.qualtrics_datacenter:
            print("Missing Qualtrics OAuth2 credentials")
            return False
        
        token_url = f'https://{self.qualtrics_datacenter}.qualtrics.com/oauth2/token'
        
        # Prepare the request
        # Using client credentials flow with specific survey management scope
        auth_data = {
            'grant_type': 'client_credentials',
            'scope': 'manage:surveys',  # Specific scope for survey API access
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
            expires_in = token_data.get('expires_in', 3600)  # Default to 1 hour
            
            # Calculate expiry time
            from datetime import datetime, timedelta
            self.qualtrics_token_expiry = datetime.now() + timedelta(seconds=expires_in - 60)  # Refresh 1 min early
            
            # Set up headers with Bearer token
            self.qualtrics_headers = {
                'Authorization': f'Bearer {self.qualtrics_oauth_token}',
                'Content-Type': 'application/json'
            }
            
            print(f"Successfully obtained Qualtrics OAuth2 token (expires in {expires_in}s)")
            print(f"Bearer Token: {self.qualtrics_oauth_token}")
            return True
            
        except requests.RequestException as e:
            print(f"Error obtaining Qualtrics OAuth2 token: {e}")
            if hasattr(e.response, 'text'):
                print(f"   Response: {e.response.text}")
            return False
    
    def _refresh_qualtrics_token_if_needed(self) -> None:
        """Refresh Qualtrics OAuth2 token if it's about to expire."""
        if self.qualtrics_oauth_token and self.qualtrics_token_expiry:
            from datetime import datetime
            if datetime.now() >= self.qualtrics_token_expiry:
                print("Refreshing Qualtrics OAuth2 token...")
                self._get_qualtrics_oauth_token()
    
    def discover_all_milestones(self) -> List[ProjectConfig]:
        """
        Auto-discover all milestones in the repository.
        
        Returns:
            List of ProjectConfig objects for all milestones
        """
        url = f'https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/milestones'
        
        try:
            response = requests.get(url, headers=self.github_headers, params={'state': 'all'})
            response.raise_for_status()
            
            milestones = response.json()
            discovered_milestones = []
            
            # Emoji mapping for different milestone types
            emoji_map = {
                0: "",  # First milestone
                1: "",  # Research/testing
                2: "",  # Analysis/data
                3: "",  # Goals/targets
                4: "",  # Achievements
                5: "",  # Features
            }
            
            for i, milestone in enumerate(milestones):
                # Get appropriate emoji
                emoji = emoji_map.get(i % len(emoji_map), "")
                
                # Assign colors based on state
                if milestone['state'] == 'closed':
                    color = "#28a745"  # Green for completed
                elif milestone['open_issues'] == 0:
                    color = "#ffc107"  # Yellow for no issues
                else:
                    color = "#007bff"  # Blue for active
                
                config = ProjectConfig(
                    name=milestone['title'],
                    repo_owner=self.repo_owner,
                    repo_name=self.repo_name,
                    milestone_number=milestone['number'],
                    emoji=emoji,
                    color=color
                )
                discovered_milestones.append(config)
            
            print(f"Discovered {len(discovered_milestones)} milestones in {self.repo_owner}/{self.repo_name}")
            return discovered_milestones
            
        except requests.RequestException as e:
            print(f"Error discovering milestones: {e}")
            return []

    def get_milestone_data(self, project: ProjectConfig) -> Optional[Dict[str, Any]]:
        """
        Fetch milestone data from GitHub API.
        
        Args:
            project: Project configuration
            
        Returns:
            Milestone data dictionary or None if failed
        """
        url = f'https://api.github.com/repos/{project.repo_owner}/{project.repo_name}/milestones/{project.milestone_number}'
        
        try:
            response = requests.get(url, headers=self.github_headers)
            response.raise_for_status()
            
            milestone = response.json()
            
            total_issues = milestone['open_issues'] + milestone['closed_issues']
            closed_issues = milestone['closed_issues']
            progress_percentage = (closed_issues / total_issues * 100) if total_issues > 0 else 0
            
            return {
                'title': milestone['title'],
                'description': milestone.get('description', ''),
                'total_issues': total_issues,
                'closed_issues': closed_issues,
                'open_issues': milestone['open_issues'],
                'progress_percentage': progress_percentage,
                'due_date': milestone.get('due_on'),
                'html_url': milestone['html_url'],
                'created_at': milestone['created_at'],
                'updated_at': milestone['updated_at'],
                'state': milestone['state']
            }
            
        except requests.RequestException as e:
            print(f"Error fetching milestone data for {project.name}: {e}")
            return None
    
    def get_survey_data(self, survey: SurveyConfig) -> Optional[Dict[str, Any]]:
        """
        Fetch survey data from Qualtrics API.
        
        Args:
            survey: Survey configuration
            
        Returns:
            Survey data dictionary or None if failed
        """
        if not self.qualtrics_headers or not self.qualtrics_datacenter:
            print("Qualtrics API credentials not configured. Skipping survey data.")
            return None
        
        # Refresh OAuth token if needed
        self._refresh_qualtrics_token_if_needed()
        
        base_url = f'https://{self.qualtrics_datacenter}.qualtrics.com/API/v3'
        
        try:
            # Get survey metadata
            survey_url = f'{base_url}/surveys/{survey.survey_id}'
            survey_response = requests.get(survey_url, headers=self.qualtrics_headers)
            survey_response.raise_for_status()
            survey_info = survey_response.json()['result']
            
            # Try to get response count using the responses export summary
            # This is more reliable than response-counts endpoint
            total_responses = 0
            completed_responses = 0
            in_progress = 0
            
            try:
                # Try the response-counts endpoint first
                responses_url = f'{base_url}/surveys/{survey.survey_id}/response-counts'
                print(f"DEBUG: Requesting response counts from: {responses_url}")
                print(f"DEBUG: Using headers: {list(self.qualtrics_headers.keys())}")
                responses_response = requests.get(responses_url, headers=self.qualtrics_headers)
                responses_response.raise_for_status()
                response_counts = responses_response.json()['result']
                
                print(f"DEBUG: Response counts data: {response_counts}")
                
                # Correct mapping of Qualtrics response-counts fields:
                # - auditable: Completed responses (fully finished)
                # - generated: Total responses started (complete + incomplete)
                # - deleted: Responses that were deleted (not tracked)
                completed_responses = response_counts.get('auditable', 0)
                started_responses = response_counts.get('generated', 0)
                total_responses = started_responses
                in_progress = max(0, started_responses - completed_responses)
                
                print(f"DEBUG: Calculated - Total: {total_responses}, Completed: {completed_responses}, In Progress: {in_progress}")
                
            except requests.RequestException as count_error:
                # Fallback: Try to get response count from the responses endpoint
                print(f"DEBUG: Response-counts endpoint failed with error: {count_error}")
                if hasattr(count_error, 'response') and count_error.response is not None:
                    print(f"DEBUG: Status code: {count_error.response.status_code}")
                    print(f"DEBUG: Response text: {count_error.response.text}")
                print(f"Response-counts endpoint not available, trying alternative method...")
                try:
                    # Get list of responses to count completed vs in-progress
                    responses_list_url = f'{base_url}/surveys/{survey.survey_id}/responses'
                    params = {'pageSize': 100}  # Get sample to analyze completion
                    print(f"DEBUG: Trying fallback - requesting responses from: {responses_list_url}")
                    list_response = requests.get(responses_list_url, headers=self.qualtrics_headers, params=params)
                    list_response.raise_for_status()
                    result = list_response.json()['result']
                    
                    # Get total count from pagination metadata
                    total_responses = result.get('totalResponseCount', 0)
                    print(f"DEBUG: Fallback method - Total response count: {total_responses}")
                    
                    # Try to count completed vs in-progress from response data
                    responses = result.get('responses', [])
                    if responses:
                        # Count responses with 'finished' status or 'progress' = 100
                        completed_count = sum(1 for r in responses if 
                                             r.get('finished') == 1 or 
                                             r.get('progress') == 100 or
                                             r.get('responseCompletedDate') is not None)
                        
                        # Estimate completed percentage based on sample
                        if len(responses) > 0:
                            completion_ratio = completed_count / len(responses)
                            completed_responses = int(total_responses * completion_ratio)
                        else:
                            completed_responses = total_responses  # Assume all completed if no data
                    else:
                        completed_responses = total_responses  # Assume all completed if no response details
                    
                    in_progress = max(0, total_responses - completed_responses)
                    
                except requests.RequestException as list_error:
                    # If both methods fail, use 0 for counts
                    print(f"DEBUG: Fallback method also failed: {list_error}")
                    if hasattr(list_error, 'response') and list_error.response is not None:
                        print(f"DEBUG: Status code: {list_error.response.status_code}")
                        print(f"DEBUG: Response text: {list_error.response.text}")
                    print(f"Could not fetch response counts: {list_error}")
                    total_responses = 0
                    completed_responses = 0
                    in_progress = 0
            
            response_rate = (total_responses / survey.target_responses * 100) if survey.target_responses > 0 else 0
            completion_rate = (completed_responses / total_responses * 100) if total_responses > 0 else 0
            
            return {
                'name': survey_info.get('name', survey.name),
                'survey_id': survey.survey_id,
                'total_responses': total_responses,
                'completed_responses': completed_responses,
                'in_progress': in_progress,
                'target_responses': survey.target_responses,
                'response_rate': response_rate,
                'completion_rate': completion_rate,
                'is_active': survey_info.get('isActive', False),
                'created_date': survey_info.get('creationDate'),
                'modified_date': survey_info.get('lastModified'),
                'survey_url': f'https://{self.qualtrics_datacenter}.qualtrics.com/jfe/form/{survey.survey_id}'
            }
            
        except requests.RequestException as e:
            print(f"Error fetching survey data for {survey.name}: {e}")
            return None
    
    def discover_all_surveys(self) -> List[SurveyConfig]:
        """
        Auto-discover all surveys in Qualtrics account.
        
        Returns:
            List of SurveyConfig objects for all surveys
        """
        if not self.qualtrics_headers or not self.qualtrics_datacenter:
            print("Qualtrics API credentials not configured. Skipping survey discovery.")
            return []
        
        # Refresh OAuth token if needed
        self._refresh_qualtrics_token_if_needed()
        
        base_url = f'https://{self.qualtrics_datacenter}.qualtrics.com/API/v3'
        url = f'{base_url}/surveys'
        
        try:
            response = requests.get(url, headers=self.qualtrics_headers)
            response.raise_for_status()
            
            surveys_data = response.json()['result']['elements']
            discovered_surveys = []
            
            # Emoji mapping for surveys
            emoji_map = ["", "", "", "", "", "", "", ""]
            
            for i, survey in enumerate(surveys_data):
                if survey.get('isActive', False):  # Only track active surveys
                    emoji = emoji_map[i % len(emoji_map)]
                    
                    config = SurveyConfig(
                        name=survey.get('name', f"Survey {survey['id']}"),
                        survey_id=survey['id'],
                        emoji=emoji,
                        target_responses=100  # Default, can be configured per survey
                    )
                    discovered_surveys.append(config)
            
            print(f"Discovered {len(discovered_surveys)} active surveys in Qualtrics")
            return discovered_surveys
            
        except requests.RequestException as e:
            print(f"Error discovering surveys: {e}")
            return []
    
    def create_progress_bar(self, percentage: float, width: int = 20) -> str:
        """
        Create a visual progress bar using Unicode characters.
        
        Args:
            percentage: Progress percentage (0-100)
            width: Width of the progress bar in characters
            
        Returns:
            Unicode progress bar string
        """
        filled = int(percentage / 100 * width)
        empty = width - filled
        
        # Using block characters for better visual appeal
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
    
    def get_trend_indicator(self, current: float, previous: float = None) -> str:
        """Get trend indicator emoji."""
        if previous is None:
            return "📊"
        
        if current > previous:
            return "📈"
        elif current < previous:
            return "📉"
        else:
            return "➡️"
    
    def create_project_block(self, project: ProjectConfig, milestone_data: Dict[str, Any]) -> List[Dict]:
        """
        Create Slack blocks for a single project.
        
        Args:
            project: Project configuration
            milestone_data: Milestone data from GitHub
            
        Returns:
            List of Slack block elements
        """
        progress_percentage = milestone_data['progress_percentage']
        progress_bar = self.create_progress_bar(progress_percentage)
        status_emoji = self.get_status_emoji(progress_percentage)
        
        # Header block
        header_block = {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{project.name}",
                "emoji": True
            }
        }
        
        # Progress section
        state_text = "Closed" if milestone_data.get('state') == 'closed' else "Open"
        
        progress_section = {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Milestone:* <{milestone_data['html_url']}|{milestone_data['title']}>"
                },
                {
                    "type": "mrkdwn", 
                    "text": f"*Status:* {progress_percentage:.1f}% Complete"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Progress:* {milestone_data['closed_issues']}/{milestone_data['total_issues']} issues"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*State:* {state_text}"
                }
            ]
        }
        
        # Visual progress bar
        progress_bar_section = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"```{progress_bar}``` {progress_percentage:.1f}%"
            }
        }
        
        # Additional info
        info_text = ""
        if milestone_data.get('description'):
            info_text += f"📝 *Description:* {milestone_data['description']}\n"
        
        if milestone_data.get('due_date'):
            due_date = datetime.fromisoformat(milestone_data['due_date'].replace('Z', '+00:00'))
            info_text += f"📅 *Due Date:* {due_date.strftime('%B %d, %Y')}\n"
        
        updated_at = datetime.fromisoformat(milestone_data['updated_at'].replace('Z', '+00:00'))
        info_text += f"*Last Updated:* {updated_at.strftime('%B %d, %Y at %I:%M %p')}"
        
        info_section = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": info_text
            }
        }
        
        # Action buttons
        actions_block = {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View Milestone",
                        "emoji": True
                    },
                    "url": milestone_data['html_url'],
                    "style": "primary"
                },
            ]
        }
        
        return [
            header_block,
            progress_section,
            progress_bar_section,
            info_section,
            actions_block,
            {"type": "divider"}  # Separator between projects
        ]
    
    def create_survey_block(self, survey: SurveyConfig, survey_data: Dict[str, Any]) -> List[Dict]:
        """
        Create Slack blocks for a single survey.
        
        Args:
            survey: Survey configuration
            survey_data: Survey data from Qualtrics
            
        Returns:
            List of Slack block elements
        """
        response_rate = survey_data['response_rate']
        completion_rate = survey_data['completion_rate']
        progress_bar = self.create_progress_bar(response_rate)
        status_emoji = self.get_status_emoji(response_rate)
        
        # Header block
        header_block = {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{survey.emoji} {survey_data['name']}",
                "emoji": True
            }
        }
        
        # Survey stats section
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
                    "text": f"*Status:* {active_text} {status_emoji}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Responses:* {survey_data['total_responses']}/{survey_data['target_responses']}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Completion Rate:* {completion_rate:.1f}%"
                }
            ]
        }
        
        # Visual progress bar for response rate
        progress_bar_section = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Response Progress:*\n```{progress_bar}``` {response_rate:.1f}%"
            }
        }
        
        # Detailed metrics
        metrics_text = f"*Completed Responses:* {survey_data['completed_responses']}\n"
        metrics_text += f"*In Progress:* {survey_data['in_progress']}\n"
        
        if survey_data.get('modified_date'):
            modified_date = datetime.fromisoformat(survey_data['modified_date'].replace('Z', '+00:00'))
            metrics_text += f"*Last Modified:* {modified_date.strftime('%B %d, %Y at %I:%M %p')}"
        
        metrics_section = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": metrics_text
            }
        }
        
        # Action buttons
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
                },
            ]
        }
        
        return [
            header_block,
            stats_section,
            progress_bar_section,
            metrics_section,
            actions_block,
            {"type": "divider"}  # Separator between surveys
        ]
    
    def create_summary_blocks(self, milestones_data: List[tuple]) -> List[Dict]:
        """
        Create summary blocks for all milestones.
        
        Args:
            milestones_data: List of (milestone, milestone_data) tuples
            
        Returns:
            List of Slack block elements for summary
        """
        total_milestones = len(milestones_data)
        completed_milestones = sum(1 for _, data in milestones_data if data and data['progress_percentage'] >= 100)
        avg_progress = sum(data['progress_percentage'] for _, data in milestones_data if data) / total_milestones if total_milestones > 0 else 0
        
        summary_header = {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Milestone Summary",
                "emoji": True
            }
        }
        
        summary_section = {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Total Milestones:* {total_milestones}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Completed:* {completed_milestones}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Average Progress:* {avg_progress:.1f}%"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Report Date:* {datetime.now().strftime('%B %d, %Y')}"
                }
            ]
        }
        
        return [summary_header, summary_section, {"type": "divider"}]
    
    def send_slack_message(self, blocks: List[Dict]) -> bool:
        """
        Send formatted message to Slack using Blocks API.
        
        Args:
            blocks: List of Slack block elements
            
        Returns:
            True if successful, False otherwise
        """
        url = "https://slack.com/api/chat.postMessage"
        
        payload = {
            "channel": self.user_id,
            "blocks": blocks,
            "text": "Weekly Progress Report"  # Fallback text
        }
        
        try:
            response = requests.post(url, headers=self.slack_headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            if result.get('ok'):
                print("Successfully sent progress report to Slack!")
                return True
            else:
                print(f"Slack API error: {result.get('error', 'Unknown error')}")
                return False
                
        except requests.RequestException as e:
            print(f"Error sending Slack message: {e}")
            return False
    
    def generate_weekly_report(self) -> None:
        """Generate and send weekly progress report."""
        print("Generating weekly progress report...")
        
        # Auto-discover all milestones
        print("Auto-discovering milestones...")
        self.milestones = self.discover_all_milestones()
        
        if not self.milestones:
            print("No milestones found in the repository")
            return
        
        # Collect data for all milestones
        milestones_data = []
        for milestone in self.milestones:
            print(f"Fetching data for {milestone.name}...")
            milestone_data = self.get_milestone_data(milestone)
            milestones_data.append((milestone, milestone_data))
        
        # Auto-discover surveys if Qualtrics is configured
        surveys_data = []
        if self.qualtrics_oauth_token and self.qualtrics_datacenter:
            print("Auto-discovering surveys...")
            self.surveys = self.discover_all_surveys()
            
            # Collect data for all surveys
            for survey in self.surveys:
                print(f"Fetching data for {survey.name}...")
                survey_data = self.get_survey_data(survey)
                if survey_data:
                    surveys_data.append((survey, survey_data))
        
        # Build Slack blocks
        all_blocks = []
        
        # Add project header
        project_header = {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🚀 {self.repo_owner}/{self.repo_name} - Weekly Progress",
                "emoji": True
            }
        }
        all_blocks.append(project_header)
        
        # Add summary
        all_blocks.extend(self.create_summary_blocks(milestones_data))
        
        # Add individual milestone blocks
        for milestone, milestone_data in milestones_data:
            if milestone_data:
                all_blocks.extend(self.create_project_block(milestone, milestone_data))
            else:
                # Error block for failed milestones
                error_block = {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"❌ *{milestone.name}*\nFailed to fetch milestone data"
                    }
                }
                all_blocks.extend([error_block, {"type": "divider"}])
        
        # Add survey section if surveys exist
        if surveys_data:
            survey_header = {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📋 Qualtrics Survey Tracking",
                    "emoji": True
                }
            }
            all_blocks.append(survey_header)
            
            # Add survey summary
            total_surveys = len(surveys_data)
            total_responses = sum(data['total_responses'] for _, data in surveys_data)
            avg_response_rate = sum(data['response_rate'] for _, data in surveys_data) / total_surveys if total_surveys > 0 else 0
            
            survey_summary = {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Active Surveys:* {total_surveys}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Total Responses:* {total_responses}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Avg Response Rate:* {avg_response_rate:.1f}%"
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
        
        # Remove last divider
        if all_blocks and all_blocks[-1].get("type") == "divider":
            all_blocks.pop()
        
        # Add footer
        footer_block = {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"📅 Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
                }
            ]
        }
        all_blocks.append(footer_block)
        
        # Send to Slack
        success = self.send_slack_message(all_blocks)
        
        if success:
            milestone_count = len([d for _, d in milestones_data if d])
            survey_count = len(surveys_data)
            print(f"Report sent! Tracked {milestone_count} milestones and {survey_count} surveys successfully.")
        else:
            print("Failed to send report.")
    
    def add_milestone(self, name: str, milestone_number: int, 
                     emoji: str = "📊", color: str = "#36a64f") -> None:
        """Add a new milestone to track."""
        milestone = ProjectConfig(name, self.repo_owner, self.repo_name, milestone_number, emoji, color)
        self.milestones.append(milestone)
        print(f"Added milestone: {name}")
    
    def add_survey(self, name: str, survey_id: str, emoji: str = "📋", 
                   target_responses: int = 100) -> None:
        """Add a new survey to track."""
        survey = SurveyConfig(name, survey_id, emoji, target_responses)
        self.surveys.append(survey)
        print(f"Added survey: {name}")
    
    def run_test(self) -> None:
        """Run a test report to verify everything works."""
        print("Running test report...")
        self.generate_weekly_report()


def main():
    """Main function to run the progress bot."""
    
    # Get tokens from environment variables
    BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')
    SLACK_USER_ID = os.getenv('SLACK_USER_ID')
    
    # Qualtrics OAuth2 credentials
    QUALTRICS_CLIENT_ID = os.getenv('QUALTRICS_CLIENT_ID')
    QUALTRICS_CLIENT_SECRET = os.getenv('QUALTRICS_CLIENT_SECRET')
    QUALTRICS_DATACENTER = os.getenv('QUALTRICS_DATACENTER')
    
    # Validate all required environment variables
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        print("Missing GITHUB_TOKEN environment variable")
        print("Please set: export GITHUB_TOKEN='your_github_token_here'")
        return
    
    if not BOT_TOKEN:
        print("Missing SLACK_BOT_TOKEN environment variable")
        print("Please set: export SLACK_BOT_TOKEN='your_slack_bot_token_here'")
        return
    
    if not SLACK_USER_ID:
        print("Missing SLACK_USER_ID environment variable")
        print("Please set: export SLACK_USER_ID='your_SLACK_USER_ID_here'")
        return
    
    # Qualtrics credentials are optional
    if QUALTRICS_CLIENT_ID and QUALTRICS_CLIENT_SECRET and QUALTRICS_DATACENTER:
        print("Qualtrics integration enabled (OAuth2)")
    else:
        print("Qualtrics integration disabled")
        print("   To enable: set QUALTRICS_CLIENT_ID, QUALTRICS_CLIENT_SECRET, and QUALTRICS_DATACENTER")
    
    # Initialize the bot
    bot = ProgressBot(
        slack_token=BOT_TOKEN,
        github_token=github_token,
        user_id=SLACK_USER_ID,
        qualtrics_client_id=QUALTRICS_CLIENT_ID,
        qualtrics_client_secret=QUALTRICS_CLIENT_SECRET,
        qualtrics_datacenter=QUALTRICS_DATACENTER
    )
    
    # Check command line arguments or run test
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        bot.run_test()
    else:
        # Generate weekly report
        bot.generate_weekly_report()


if __name__ == '__main__':
    main()
