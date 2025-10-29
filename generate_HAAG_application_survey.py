import pandas as pd
import json
import uuid
from datetime import datetime

# Mapping from Excel lab names to survey display names
LAB_NAME_MAPPING = {
    'Alexander': 'Law, Data, & Design Lab',
    'Freeman': 'Freeman Lab',
    'Handika': 'BioVision Lab',
    'McGuire': 'SEPL',
    'Mukhopadhyay': 'Mukhopadhyay Lab',
    'Mussman': 'Mussman Lab',
    'Porto': 'BioVision Lab',  # Porto also appears as BioVision Lab
    'Postiglione': 'Postiglione Lab',
    'Stroud': 'Stroud Lab'
}

# Project name mappings - projects that need special formatting
PROJECT_NAME_MAPPING = {
    'ConstructConnect': 'ConstructConnect Search Project',
    'Summarization': 'Legal summarization',
    'Audio': "audio analysis of Hume's Leaf Warbler",
    'Behave': "Behavior analysis of Hume's Leaf Warbler bird from camera traps",
    'Natural History Museum Digital Catalog': 'Natural History Museum Digital Catalog',
    'BioCosmos': 'BioCosmos',
    '3D Modeling': 'Predicting 3-D Models',
    'Photogrametry': 'Photogrammetry Project',
    'animal detection': 'Detection of Wildlife from camera traps at Stone Mountain',
    'ecological modeling': 'Ecological condition prediction via Bison data',
    'Animal detection: Spatial Camera': None,  # Not in application - separate from animal detection
    'animal detection: spatial Camera': None,  # Not in application - separate from animal detection
    '3D Generative Models': 'Advanced Generative Models for 3D Biological Shape Completion',
    'Vector Quantization': 'Principled vector quantization for vector DB',
    'Vector DB': 'Vector DB methods with retrieval guarantees but no resource-usage guarantees',
    'Training Batch Selection': 'Light-weight training batch selection using only past training batch statistics',
    'Charleston Train': 'Understanding the predictability of rail crossing delays in the Charleston, SC port area',
    'LLM Interpretability': 'Black-Box Interpretability of Large Language Models: A Model-Agnostic Framework',
    'Lizard movement': 'Lizard movement tracking',
    'Lizard Class': 'Florida Anole Species Classification',
    'Lizard Toe Pad Landmarking': 'Automation of Lizard Landmark Analysis',
    'R For Evolution': 'R Package Development for Evolution',
    'Lidar': 'Terrestrial LiDAR Vegetation Analysis project',
    'Bankruptcy Docket': 'Bankruptcy Docket Project',
    'Criminal Sentences': 'Criminal Sentences Project',
    'D&O': None,  # Not in application form
    'Letters': None,  # Not in application form
    'Sentencias': None,  # Not in application form
    'Lizard X-Ray': None,  # Not in application form
}

# Special notes for some projects
PROJECT_SPECIAL_NOTES = {
    'Lidar': 'Stroud Lab/Jones Center: ',  # Has special prefix
}

def read_excel_data(filepath):
    """Read the Excel file and return structured data from individual lab sheets"""
    xl_file = pd.ExcelFile(filepath)
    
    # Sheets to ignore
    ignore_sheets = ['CS8903', 'CS6999', 'Sheet1', 'AggrigatedLabs']
    
    # Get all lab sheets (sheet name = lab name)
    lab_sheets = [s for s in xl_file.sheet_names if s not in ignore_sheets]
    
    structure = {}
    
    for lab_name in lab_sheets:
        df = pd.read_excel(filepath, sheet_name=lab_name)
        
        # Find the Student column (might be 'Student' or 'Student ' with trailing space)
        student_col = None
        for col in df.columns:
            if 'Student' in str(col):
                student_col = col
                break
        
        if student_col is None:
            print(f"Warning: No Student column found in sheet '{lab_name}', skipping")
            continue
        
        # Find the Project column
        project_col = None
        for col in df.columns:
            if 'Project' in str(col):
                project_col = col
                break
        
        if project_col is None:
            print(f"Warning: No Project column found in sheet '{lab_name}', skipping")
            continue
        
        # Forward-fill the Project column (project name is usually only in first row of group)
        df[project_col] = df[project_col].ffill()
        
        # Filter out rows with missing students
        df = df[df[student_col].notna()]
        
        # Initialize lab in structure
        if lab_name not in structure:
            structure[lab_name] = {}
        
        # Group by Project and collect students
        for _, row in df.iterrows():
            project = row[project_col]
            student = row[student_col]
            
            # Skip rows with missing project or student
            if pd.isna(project) or pd.isna(student):
                continue
            
            # Convert to string and strip whitespace
            project = str(project).strip()
            student = str(student).strip()
            
            # Skip empty strings
            if not project or not student:
                continue
            
            # Initialize project in lab structure
            if project not in structure[lab_name]:
                structure[lab_name][project] = []
            
            # Only add if student name is not already in the list (avoid duplicates)
            if student not in structure[lab_name][project]:
                structure[lab_name][project].append(student)
    
    return structure

def format_project_choice(lab_name, project_name):
    """Format a lab and project name into the survey choice format"""
    # Get the lab display name
    lab_display = LAB_NAME_MAPPING.get(lab_name, f"{lab_name} Lab")
    
    # Get the project display name
    if project_name in PROJECT_NAME_MAPPING:
        project_display = PROJECT_NAME_MAPPING[project_name]
        if project_display is None:
            return None  # Skip projects not in application form
    else:
        project_display = project_name
    
    # Handle special cases (like Lidar with special prefix)
    if project_name in PROJECT_SPECIAL_NOTES:
        prefix = PROJECT_SPECIAL_NOTES[project_name]
        return f"{prefix}{project_display}"
    
    # Handle projects that map to same display name but should be filtered
    # Check if this exact mapping should be skipped
    if project_name != 'animal detection' and 'animal detection' in project_name.lower():
        return None  # Skip variants of animal detection that aren't the main one
    
    return f"{lab_display}: {project_display}"

def generate_project_choices(data):
    """Generate the list of project choices for QID7"""
    choices = {}
    choice_order = []
    choice_id = 1
    
    # Filter out non-lab keys (like _semester)
    lab_data = {k: v for k, v in data.items() if isinstance(v, dict)}
    
    # Sort labs and projects for consistent ordering
    for lab_name in sorted(lab_data.keys()):
        projects = lab_data[lab_name]
        for project_name in sorted(projects.keys()):
            formatted_choice = format_project_choice(lab_name, project_name)
            if formatted_choice is not None:
                choices[str(choice_id)] = {"Display": formatted_choice}
                choice_order.append(choice_id)
                choice_id += 1
    
    return choices, choice_order

def generate_qualtrics_qsf(data):
    """Generate a Qualtrics QSF file for the HAAG Application survey"""
    
    # Generate IDs
    survey_id = "SV_" + datetime.now().strftime("%Y%m%d%H%M%S")
    response_set_id = "RS_" + datetime.now().strftime("%Y%m%d%H%M%S")
    
    # Base survey structure
    # Extract semester from data if available
    semester = data.get('_semester', 'Fall 2025')
    
    survey = {
        "SurveyEntry": {
            "SurveyID": survey_id,
            "SurveyName": f"HAAG Application {semester}",
            "SurveyDescription": None,
            "SurveyOwnerID": "UR_XXXXXXXXXXXXX",
            "SurveyBrandID": "gatech",
            "DivisionID": None,
            "SurveyLanguage": "EN",
            "SurveyActiveResponseSet": response_set_id,
            "SurveyStatus": "Active",
            "SurveyStartDate": "0000-00-00 00:00:00",
            "SurveyExpirationDate": "0000-00-00 00:00:00",
            "SurveyCreationDate": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "CreatorID": "UR_XXXXXXXXXXXXX",
            "LastModified": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "LastAccessed": "0000-00-00 00:00:00",
            "LastActivated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Deleted": None
        },
        "SurveyElements": []
    }
    
    # Create blocks - matching original QID assignments and order
    block_id = "BL_4OBEy50KtowDs8u"
    block = {
        "Type": "Default",
        "Description": "Default Question Block",
        "ID": block_id,
        "BlockElements": []
    }
    
    questions = []
    
    # QID1: Introduction text
    q1_id = "QID1"
    block["BlockElements"].append({"Type": "Question", "QuestionID": q1_id})
    
    questions.append({
        "SurveyID": survey_id,
        "Element": "SQ",
        "PrimaryAttribute": q1_id,
        "SecondaryAttribute": "Thank you for your interest in The Human-Augmented Analytics (HAAG) OMSCS Fall 2025 research team...",
        "TertiaryAttribute": None,
        "Payload": {
            "QuestionText": "Thank you for your interest in The Human-Augmented Analytics (HAAG) OMSCS Fall 2025 research team!&nbsp;<b>(Any projects from Dr. Lytle's document with Breanna Shi listed as team lead are HAAG projects).</b>&nbsp;Please answer the questions thoroughly, you will be evaluated by the effort you put into this document. You may be asked to verify your experience in a follow-up technical exercise if applicable.<br>\n<br>\nTo do well on this exercise you will need to conduct a preliminary reading/testing on the project which you are interested in and demonstrate a preliminary effort towards your study.&nbsp;<br>\n<br>\nAnswers will be submitted to a Plagiarism and AI writing detector. Feel free to use AI for help with sentence structure and clarity, but all ideas must be your own.&nbsp;<br>\n<br>\nAlthough you may have received multiple emails based on your selection of project/lab interests,&nbsp;<b><i>YOU ONLY NEED TO FILL THIS FORM OUT ONCE TO BE CONSIDERED FOR HAAG RESEARCH</i>.</b><br>\n&nbsp;",
            "DefaultChoices": False,
            "DataExportTag": "",
            "QuestionID": q1_id,
            "QuestionType": "DB",
            "Selector": "TB",
            "DataVisibility": {"Private": False, "Hidden": False},
            "Configuration": {"QuestionDescriptionOption": "UseText"},
            "QuestionDescription": "Thank you for your interest in The Human-Augmented Analytics (HAAG) OMSCS Fall 2025 research team...",
            "ChoiceOrder": [],
            "Validation": {"Settings": {"Type": "None"}},
            "GradingData": [],
            "Language": [],
            "NextChoiceId": 4,
            "NextAnswerId": 1
        }
    })
    
    # QID2: Full name
    q2_id = "QID2"
    block["BlockElements"].append({"Type": "Question", "QuestionID": q2_id})
    
    questions.append({
        "SurveyID": survey_id,
        "Element": "SQ",
        "PrimaryAttribute": q2_id,
        "SecondaryAttribute": "What is your full name?",
        "TertiaryAttribute": None,
        "Payload": {
            "QuestionText": "What is your full name?",
            "DefaultChoices": False,
            "DataExportTag": "Q1",
            "QuestionType": "TE",
            "Selector": "ML",
            "DataVisibility": {"Private": False, "Hidden": False},
            "Configuration": {"QuestionDescriptionOption": "UseText"},
            "QuestionDescription": "What is your full name?",
            "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None", "MinChars": "1"}},
            "GradingData": [],
            "Language": [],
            "NextChoiceId": 4,
            "NextAnswerId": 1,
            "SearchSource": {"AllowFreeResponse": "false"},
            "QuestionID": q2_id
        }
    })
    
    # QID3: Email
    q3_id = "QID3"
    block["BlockElements"].append({"Type": "Question", "QuestionID": q3_id})
    
    questions.append({
        "SurveyID": survey_id,
        "Element": "SQ",
        "PrimaryAttribute": q3_id,
        "SecondaryAttribute": "What is your GT/official email address?",
        "TertiaryAttribute": None,
        "Payload": {
            "QuestionText": "What is your GT/official email address?<br>",
            "DefaultChoices": False,
            "DataExportTag": "Q2",
            "QuestionType": "TE",
            "Selector": "ML",
            "DataVisibility": {"Private": False, "Hidden": False},
            "Configuration": {"QuestionDescriptionOption": "UseText"},
            "QuestionDescription": "What is your GT/official email address?",
            "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
            "GradingData": [],
            "Language": [],
            "NextChoiceId": 4,
            "NextAnswerId": 1,
            "SearchSource": {"AllowFreeResponse": "false"},
            "QuestionID": q3_id
        }
    })
    
    # QID4: Courses
    q4_id = "QID4"
    block["BlockElements"].append({"Type": "Question", "QuestionID": q4_id})
    
    questions.append({
        "SurveyID": survey_id,
        "Element": "SQ",
        "PrimaryAttribute": q4_id,
        "SecondaryAttribute": "Please list all computing-focused graduate-level courses you've taken (course number, course titl...",
        "TertiaryAttribute": None,
        "Payload": {
            "QuestionText": "Please list all computing-focused graduate-level courses you've taken (course number, course title, host institution if not OMSCS).",
            "DefaultChoices": False,
            "DataExportTag": "Q3",
            "QuestionType": "TE",
            "Selector": "ML",
            "DataVisibility": {"Private": False, "Hidden": False},
            "Configuration": {"QuestionDescriptionOption": "UseText"},
            "QuestionDescription": "Please list all computing-focused graduate-level courses you've taken (course number, course titl...",
            "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
            "GradingData": [],
            "Language": [],
            "NextChoiceId": 4,
            "NextAnswerId": 1,
            "SearchSource": {"AllowFreeResponse": "false"},
            "QuestionID": q4_id
        }
    })
    
    # QID16: Professional experience (appears early in block order)
    q16_id = "QID16"
    block["BlockElements"].append({"Type": "Question", "QuestionID": q16_id})
    
    questions.append({
        "SurveyID": survey_id,
        "Element": "SQ",
        "PrimaryAttribute": q16_id,
        "SecondaryAttribute": "What other professional experience do you have that will assist you with this project, if applica...",
        "TertiaryAttribute": None,
        "Payload": {
            "QuestionText": "What other professional experience do you have that will assist you with this project, if applicable?&nbsp;<br>",
            "DefaultChoices": False,
            "DataExportTag": "Q4",
            "QuestionType": "TE",
            "Selector": "ML",
            "DataVisibility": {"Private": False, "Hidden": False},
            "Configuration": {"QuestionDescriptionOption": "UseText"},
            "QuestionDescription": "What other professional experience do you have that will assist you with this project, if applica...",
            "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
            "GradingData": [],
            "Language": [],
            "NextChoiceId": 4,
            "NextAnswerId": 1,
            "SearchSource": {"AllowFreeResponse": "false"},
            "QuestionID": q16_id
        }
    })
    
    # QID8: Intro to Research course
    q8_id = "QID8"
    block["BlockElements"].append({"Type": "Question", "QuestionID": q8_id})
    
    questions.append({
        "SurveyID": survey_id,
        "Element": "SQ",
        "PrimaryAttribute": q8_id,
        "SecondaryAttribute": "Have you taken Dr. Lytle's Intro to Research course (CS 8803 O24)?",
        "TertiaryAttribute": None,
        "Payload": {
            "QuestionText": "Have you taken Dr. Lytle's Intro to Research course (CS 8803 O24)?",
            "DefaultChoices": False,
            "DataExportTag": "Q5",
            "QuestionType": "MC",
            "Selector": "SAVR",
            "SubSelector": "TX",
            "DataVisibility": {"Private": False, "Hidden": False},
            "Configuration": {"QuestionDescriptionOption": "UseText", "Autoscale": {"YScale": {"Name": "yesNo", "Type": "likert", "Reverse": False}}},
            "QuestionDescription": "Have you taken Dr. Lytle's Intro to Research course (CS 8803 O24)?",
            "Choices": {"1": {"Display": "No"}, "2": {"Display": "Yes"}},
            "ChoiceOrder": [1, 2],
            "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
            "GradingData": [],
            "Language": [],
            "NextChoiceId": 3,
            "NextAnswerId": 1,
            "QuestionID": q8_id
        }
    })
    
    # QID20: Research experience
    q20_id = "QID20"
    block["BlockElements"].append({"Type": "Question", "QuestionID": q20_id})
    
    questions.append({
        "SurveyID": survey_id,
        "Element": "SQ",
        "PrimaryAttribute": q20_id,
        "SecondaryAttribute": "Do you have previous experience with academic research? If so, what was the outcome (was the work...",
        "TertiaryAttribute": None,
        "Payload": {
            "QuestionText": "Do you have previous experience with academic research? If so, what was the outcome (was the work published, presented, etc)?<br><br>Please note: this is <b>not</b> a requirement, but it can make your experience a bit smoother in certain places.<br>",
            "DefaultChoices": False,
            "DataExportTag": "Q6",
            "QuestionID": q20_id,
            "QuestionType": "TE",
            "Selector": "ML",
            "DataVisibility": {"Private": False, "Hidden": False},
            "Configuration": {"QuestionDescriptionOption": "UseText"},
            "QuestionDescription": "Do you have previous experience with academic research? If so, what was the outcome (was the work...",
            "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
            "GradingData": [],
            "Language": [],
            "NextChoiceId": 4,
            "NextAnswerId": 1,
            "SearchSource": {"AllowFreeResponse": "false"}
        }
    })
    
    # QID5: Time commitment
    q5_id = "QID5"
    block["BlockElements"].append({"Type": "Question", "QuestionID": q5_id})
    
    questions.append({
        "SurveyID": survey_id,
        "Element": "SQ",
        "PrimaryAttribute": q5_id,
        "SecondaryAttribute": "What is your expected weekly time-commitment for this research opportunity?",
        "TertiaryAttribute": None,
        "Payload": {
            "QuestionText": "What is your expected weekly time-commitment for this research opportunity?",
            "DefaultChoices": False,
            "DataExportTag": "Q7",
            "QuestionType": "MC",
            "Selector": "SAVR",
            "SubSelector": "TX",
            "DataVisibility": {"Private": False, "Hidden": False},
            "Configuration": {"QuestionDescriptionOption": "UseText"},
            "QuestionDescription": "What is your expected weekly time-commitment for this research opportunity?",
            "Choices": {
                "1": {"Display": "Less Than 10 Hours per Week"},
                "2": {"Display": "10 Hours per week"},
                "3": {"Display": "More than 10 hours per week"},
                "4": {"Display": "Other", "TextEntry": "true"}
            },
            "ChoiceOrder": [1, 2, 3, 4],
            "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
            "GradingData": [],
            "Language": [],
            "NextChoiceId": 5,
            "NextAnswerId": 1,
            "QuestionID": q5_id
        }
    })
    
    # QID6: Computing resources
    q6_id = "QID6"
    block["BlockElements"].append({"Type": "Question", "QuestionID": q6_id})
    
    questions.append({
        "SurveyID": survey_id,
        "Element": "SQ",
        "PrimaryAttribute": q6_id,
        "SecondaryAttribute": "What computing resources do you have at your disposal? For example, do you have a GPU on your loc...",
        "TertiaryAttribute": None,
        "Payload": {
            "QuestionText": "What computing resources do you have at your disposal? For example, do you have a GPU on your local machine? Do you have experience with computing on PACE?",
            "DefaultChoices": False,
            "DataExportTag": "Q8",
            "QuestionID": q6_id,
            "QuestionType": "TE",
            "Selector": "ML",
            "DataVisibility": {"Private": False, "Hidden": False},
            "Configuration": {"QuestionDescriptionOption": "UseText"},
            "QuestionDescription": "What computing resources do you have at your disposal? For example, do you have a GPU on your loc...",
            "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
            "GradingData": [],
            "Language": [],
            "NextChoiceId": 4,
            "NextAnswerId": 1,
            "SearchSource": {"AllowFreeResponse": "false"}
        }
    })
    
    # Page Break
    block["BlockElements"].append({"Type": "Page Break"})
    
    # QID18: Reference PDF text
    q18_id = "QID18"
    block["BlockElements"].append({"Type": "Question", "QuestionID": q18_id})
    
    questions.append({
        "SurveyID": survey_id,
        "Element": "SQ",
        "PrimaryAttribute": q18_id,
        "SecondaryAttribute": "The following questions require you to reference specific projects and labs. Please refer to the...",
        "TertiaryAttribute": None,
        "Payload": {
            "QuestionText": "The following questions require you to reference specific projects and labs. Please refer to the PDF file at the top of the page for the relevant information. If the PDF is not visible, please reference&nbsp;<a href=\"https://gtvault.sharepoint.com/:b:/s/HAAG/EeUlqWw0uZhBmgjnFRdTojAB8At1pB6qoDK4KqlTajHreA?e=mlFb0K\">this link.</a>",
            "DefaultChoices": False,
            "DataExportTag": "",
            "QuestionType": "DB",
            "Selector": "TB",
            "DataVisibility": {"Private": False, "Hidden": False},
            "Configuration": {"QuestionDescriptionOption": "UseText"},
            "QuestionDescription": "The following questions require you to reference specific projects and labs. Please refer to the...",
            "ChoiceOrder": [],
            "Validation": {"Settings": {"Type": "None"}},
            "GradingData": [],
            "Language": [],
            "NextChoiceId": 4,
            "NextAnswerId": 1,
            "QuestionID": q18_id
        }
    })
    
    # QID19: PDF iframe
    q19_id = "QID19"
    block["BlockElements"].append({"Type": "Question", "QuestionID": q19_id})
    
    questions.append({
        "SurveyID": survey_id,
        "Element": "SQ",
        "PrimaryAttribute": q19_id,
        "SecondaryAttribute": None,
        "TertiaryAttribute": None,
        "Payload": {
            "QuestionText": " \n\n<iframe width=\"1200\" src=\"https://gatech.co1.qualtrics.com/ControlPanel/File.php?F=F_qdHEkYdARSq7UBH\" height=\"750\"></iframe>",
            "DefaultChoices": False,
            "DataExportTag": "",
            "QuestionType": "DB",
            "Selector": "TB",
            "DataVisibility": {"Private": False, "Hidden": False},
            "Configuration": {"QuestionDescriptionOption": "UseText"},
            "ChoiceOrder": [],
            "Validation": {"Settings": {"Type": "None"}},
            "GradingData": [],
            "Language": [],
            "NextChoiceId": 4,
            "NextAnswerId": 1,
            "QuestionID": q19_id
        }
    })
    
    # QID7: Projects/labs selection (dynamically generated)
    q7_id = "QID7"
    block["BlockElements"].append({"Type": "Question", "QuestionID": q7_id})
    
    project_choices, choice_order = generate_project_choices(data)
    
    questions.append({
        "SurveyID": survey_id,
        "Element": "SQ",
        "PrimaryAttribute": q7_id,
        "SecondaryAttribute": "Which projects/labs are you most interested in being considered for?",
        "TertiaryAttribute": None,
        "Payload": {
            "QuestionText": "Which projects/labs are you most interested in being considered for?",
            "DefaultChoices": False,
            "DataExportTag": "Q9",
            "QuestionID": q7_id,
            "QuestionType": "MC",
            "Selector": "MAVR",
            "SubSelector": "TX",
            "DataVisibility": {"Private": False, "Hidden": False},
            "Configuration": {"QuestionDescriptionOption": "UseText"},
            "QuestionDescription": "Which projects/labs are you most interested in being considered for?",
            "Choices": project_choices,
            "ChoiceOrder": choice_order,
            "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
            "GradingData": [],
            "Language": [],
            "NextChoiceId": len(project_choices) + 1,
            "NextAnswerId": 1
        }
    })
    
    # QID14: Top priority project (dynamic choices from QID7)
    q14_id = "QID14"
    block["BlockElements"].append({"Type": "Question", "QuestionID": q14_id})
    
    questions.append({
        "SurveyID": survey_id,
        "Element": "SQ",
        "PrimaryAttribute": q14_id,
        "SecondaryAttribute": "You will need to answer supplementary questions related to your top priority project; you will st...",
        "TertiaryAttribute": None,
        "Payload": {
            "QuestionText": "You will need to answer supplementary questions related to your top priority project; you will still be considered for all projects that you are interested in.<br>\n<br>Of the ones you selected which project is your top priority selection?",
            "DataExportTag": "Q10",
            "QuestionType": "MC",
            "Selector": "SAVR",
            "SubSelector": "TX",
            "DataVisibility": {"Private": False, "Hidden": False},
            "Configuration": {"QuestionDescriptionOption": "UseText"},
            "QuestionDescription": "You will need to answer supplementary questions related to your top priority project; you will st...",
            "Choices": [],
            "ChoiceOrder": [],
            "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
            "Language": [],
            "NextChoiceId": 1,
            "NextAnswerId": 1,
            "QuestionID": q14_id,
            "DynamicChoices": {
                "DynamicType": "ChoiceGroup",
                "Locator": f"q://{q7_id}/ChoiceGroup/SelectedChoices",
                "Type": "Dynamic"
            },
            "DynamicChoicesData": []
        }
    })
    
    # QID9: 10-step plan
    q9_id = "QID9"
    block["BlockElements"].append({"Type": "Question", "QuestionID": q9_id})
    
    questions.append({
        "SurveyID": survey_id,
        "Element": "SQ",
        "PrimaryAttribute": q9_id,
        "SecondaryAttribute": "Create a 10-step plan with specific language and tools for how you will solve the questions propo...",
        "TertiaryAttribute": None,
        "Payload": {
            "QuestionText": "Create a 10-step plan with specific language and tools for how you will solve the questions proposed in the project you selected as your top priority. Detail is encouraged, but do not add fluff with no purpose. Academic papers and tools should be used to justify that your plan is logical.<br />\n<br />\nHere is a good and a bad example:&nbsp;\n<ul>\n\t<li>Bad: &ldquo;I will run a computer vision model on the data.&rdquo;</li>\n\t<li>Better: &ldquo;I will train a YOLO11 model on 1000 annotations of the object for 100 epochs using PACE compute resources and validate the fitness of the model via the F1 score.&rdquo;</li>\n</ul>\n<br />\nYou can do even better than the latter example by adapting your answer to the specific questions in the project proposal.&nbsp;<br />\n<br />\nAgain, you may reference the embedded PDF. If the PDF is not visible, please reference&nbsp;<a href=\"https://gtvault.sharepoint.com/:b:/s/HAAG/EeUlqWw0uZhBmgjnFRdTojAB8At1pB6qoDK4KqlTajHreA?e=mlFb0K\">this link.</a>",
            "DefaultChoices": False,
            "DataExportTag": "Q11",
            "QuestionType": "TE",
            "Selector": "ML",
            "DataVisibility": {"Private": False, "Hidden": False},
            "Configuration": {"QuestionDescriptionOption": "UseText"},
            "QuestionDescription": "Create a 10-step plan with specific language and tools for how you will solve the questions propo...",
            "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
            "GradingData": [],
            "Language": [],
            "NextChoiceId": 4,
            "NextAnswerId": 1,
            "SearchSource": {"AllowFreeResponse": "false"},
            "QuestionID": q9_id
        }
    })
    
    # QID10: Online resources
    q10_id = "QID10"
    block["BlockElements"].append({"Type": "Question", "QuestionID": q10_id})
    
    questions.append({
        "SurveyID": survey_id,
        "Element": "SQ",
        "PrimaryAttribute": q10_id,
        "SecondaryAttribute": "What online resources will you use to solve this problem?",
        "TertiaryAttribute": None,
        "Payload": {
            "QuestionText": "What online resources will you use to solve this problem?<br>",
            "DefaultChoices": False,
            "DataExportTag": "Q12",
            "QuestionType": "TE",
            "Selector": "ML",
            "DataVisibility": {"Private": False, "Hidden": False},
            "Configuration": {"QuestionDescriptionOption": "UseText"},
            "QuestionDescription": "What online resources will you use to solve this problem?",
            "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
            "GradingData": [],
            "Language": [],
            "NextChoiceId": 4,
            "NextAnswerId": 1,
            "SearchSource": {"AllowFreeResponse": "false"},
            "QuestionID": q10_id
        }
    })
    
    # QID12: Plan if stuck
    q12_id = "QID12"
    block["BlockElements"].append({"Type": "Question", "QuestionID": q12_id})
    
    questions.append({
        "SurveyID": survey_id,
        "Element": "SQ",
        "PrimaryAttribute": q12_id,
        "SecondaryAttribute": "What is your plan of action if you get stuck in your project?",
        "TertiaryAttribute": None,
        "Payload": {
            "QuestionText": "What is your plan of action if you get stuck in your project?",
            "DefaultChoices": False,
            "DataExportTag": "Q13",
            "QuestionType": "TE",
            "Selector": "ML",
            "DataVisibility": {"Private": False, "Hidden": False},
            "Configuration": {"QuestionDescriptionOption": "UseText"},
            "QuestionDescription": "What is your plan of action if you get stuck in your project?",
            "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
            "GradingData": [],
            "Language": [],
            "NextChoiceId": 4,
            "NextAnswerId": 1,
            "SearchSource": {"AllowFreeResponse": "false"},
            "QuestionID": q12_id
        }
    })
    
    # QID13: Future contact
    q13_id = "QID13"
    block["BlockElements"].append({"Type": "Question", "QuestionID": q13_id})
    
    questions.append({
        "SurveyID": survey_id,
        "Element": "SQ",
        "PrimaryAttribute": q13_id,
        "SecondaryAttribute": "If you are not chosen for this semester's group, would you still like to be contacted for future...",
        "TertiaryAttribute": None,
        "Payload": {
            "QuestionText": "If you are not chosen for this semester's group, would you still like to be contacted for future research opportunities?",
            "DefaultChoices": False,
            "DataExportTag": "Q14",
            "QuestionType": "MC",
            "Selector": "SAVR",
            "SubSelector": "TX",
            "DataVisibility": {"Private": False, "Hidden": False},
            "Configuration": {"QuestionDescriptionOption": "UseText"},
            "QuestionDescription": "If you are not chosen for this semester's group, would you still like to be contacted for future...",
            "Choices": {"1": {"Display": "Yes"}, "2": {"Display": "No"}},
            "ChoiceOrder": [1, 2],
            "Validation": {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}},
            "GradingData": [],
            "Language": [],
            "NextChoiceId": 3,
            "NextAnswerId": 1,
            "QuestionID": q13_id
        }
    })
    
    # Build SurveyElements in the correct order
    # Note: Blocks payload should be a list, not a dict for this survey format
    survey["SurveyElements"].append({
        "SurveyID": survey_id,
        "Element": "BL",
        "PrimaryAttribute": "Survey Blocks",
        "SecondaryAttribute": None,
        "TertiaryAttribute": None,
        "Payload": [
            block,
            {
                "Type": "Trash",
                "Description": "Trash / Unused Questions",
                "ID": "BL_77foailghyqe5y6",
                "BlockElements": []
            }
        ]
    })

    # Survey flow
    survey["SurveyElements"].append({
        "SurveyID": survey_id,
        "Element": "FL",
        "PrimaryAttribute": "Survey Flow",
        "SecondaryAttribute": None,
        "TertiaryAttribute": None,
        "Payload": {
            "Flow": [{
                "ID": block_id,
                "Type": "Block",
                "FlowID": "FL_2"
            }],
            "Properties": {"Count": 2},
            "FlowID": "FL_1",
            "Type": "Root"
        }
    })

    # Preview Link
    survey["SurveyElements"].append({
        "SurveyID": survey_id,
        "Element": "PL",
        "PrimaryAttribute": "Preview Link",
        "SecondaryAttribute": None,
        "TertiaryAttribute": None,
        "Payload": {
            "PreviewType": "Brand",
            "PreviewID": str(uuid.uuid4())
        }
    })

    # Project
    survey["SurveyElements"].append({
        "SurveyID": survey_id,
        "Element": "PROJ",
        "PrimaryAttribute": "CORE",
        "SecondaryAttribute": None,
        "TertiaryAttribute": "1.1.0",
        "Payload": {
            "ProjectCategory": "CORE",
            "SchemaVersion": "1.1.0"
        }
    })

    # Question Count
    survey["SurveyElements"].append({
        "SurveyID": survey_id,
        "Element": "QC",
        "PrimaryAttribute": "Survey Question Count",
        "SecondaryAttribute": str(len(questions)),
        "TertiaryAttribute": None,
        "Payload": None
    })

    # Response Set
    survey["SurveyElements"].append({
        "SurveyID": survey_id,
        "Element": "RS",
        "PrimaryAttribute": response_set_id,
        "SecondaryAttribute": "Default Response Set",
        "TertiaryAttribute": None,
        "Payload": None
    })

    # Scoring
    survey["SurveyElements"].append({
        "SurveyID": survey_id,
        "Element": "SCO",
        "PrimaryAttribute": "Scoring",
        "SecondaryAttribute": None,
        "TertiaryAttribute": None,
        "Payload": {
            "ScoringCategories": [],
            "ScoringCategoryGroups": [],
            "ScoringSummaryCategory": None,
            "ScoringSummaryAfterQuestions": 0,
            "ScoringSummaryAfterSurvey": 0,
            "DefaultScoringCategory": None,
            "AutoScoringCategory": None
        }
    })

    # Survey Options
    survey["SurveyElements"].append({
        "SurveyID": survey_id,
        "Element": "SO",
        "PrimaryAttribute": "Survey Options",
        "SecondaryAttribute": None,
        "TertiaryAttribute": None,
        "Payload": {
            "BackButton": "true",
            "SaveAndContinue": "true",
            "SurveyProtection": "PublicSurvey",
            "BallotBoxStuffingPrevention": "false",
            "NoIndex": "Yes",
            "SecureResponseFiles": "true",
            "SurveyExpiration": "None",
            "SurveyTermination": "DefaultMessage",
            "Header": "",
            "Footer": "",
            "ProgressBarDisplay": "None",
            "PartialData": "+1 week",
            "ValidationMessage": None,
            "PreviousButton": "",
            "NextButton": "",
            "SurveyTitle": "Qualtrics Survey | Qualtrics Experience Management",
            "SkinLibrary": "Qualtrics",
            "SkinType": "templated",
            "Skin": {"brandingId": None, "templateId": "*base", "overrides": None},
            "NewScoring": 1,
            "SurveyMetaDescription": "The most powerful, simple and trusted way to gather experience data. Start your journey to experience management and try a free account today.",
            "ProtectSelectionIds": True,
            "EOSMessage": None,
            "ShowExportTags": "false",
            "CollectGeoLocation": "false",
            "PasswordProtection": "No",
            "AnonymizeResponse": "No",
            "RefererCheck": "No",
            "BallotBoxStuffingPreventionBehavior": None,
            "BallotBoxStuffingPreventionMessage": None,
            "BallotBoxStuffingPreventionMessageLibrary": None,
            "BallotBoxStuffingPreventionURL": None,
            "RecaptchaV3": "false",
            "ConfirmStart": False,
            "AutoConfirmStart": False,
            "RelevantID": "false",
            "RelevantIDLockoutPeriod": "+30 days",
            "UseCustomSurveyLinkCompletedMessage": None,
            "SurveyLinkCompletedMessage": None,
            "SurveyLinkCompletedMessageLibrary": None,
            "ResponseSummary": "No",
            "EOSMessageLibrary": None,
            "EOSRedirectURL": None,
            "EmailThankYou": "false",
            "ThankYouEmailMessageLibrary": None,
            "ThankYouEmailMessage": None,
            "ValidateMessage": "false",
            "ValidationMessageLibrary": None,
            "InactiveSurvey": "DefaultMessage",
            "PartialDeletion": None,
            "PartialDataCloseAfter": "LastActivity",
            "InactiveMessageLibrary": None,
            "InactiveMessage": None,
            "AvailableLanguages": {"EN": []},
            "SurveyName": f"HAAG Application {semester}"
        }
    })

    # Add all questions
    survey["SurveyElements"].extend(questions)
    
    # Add Survey Statistics
    survey["SurveyElements"].append({
        "SurveyID": survey_id,
        "Element": "STAT",
        "PrimaryAttribute": "Survey Statistics",
        "SecondaryAttribute": None,
        "TertiaryAttribute": None,
        "Payload": {
            "MobileCompatible": True,
            "ID": "Survey Statistics"
        }
    })

    return survey

def main():
    """Main function to convert Excel to Application Survey QSF"""
    
    # Prompt user for semester
    semester = input("Enter the semester (e.g., 'Fall 2025', 'Spring 2026'): ").strip()
    if not semester:
        semester = "Fall 2025"  # Default
        print(f"Using default: {semester}")
    
    # Read Excel file
    print("Reading Excel file...")
    excel_file = "HAAG_Fall_Enrollment_Students.xlsx"
    data = read_excel_data(excel_file)
    
    print(f"Found {len(data)} labs")
    total_projects = sum(len(projects) for projects in data.values())
    print(f"Total projects: {total_projects}")
    
    # Generate QSF
    print("\nGenerating Qualtrics Application Survey QSF file...")
    data['_semester'] = semester  # Pass semester to generation function
    survey = generate_qualtrics_qsf(data)
    
    # Save to file
    output_file = f"HAAG_Application_{semester.replace(' ', '_')}.qsf"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(survey, f, indent=2, ensure_ascii=False)
    
    print(f"\nSurvey saved to: {output_file}")
    print("\nTo import into Qualtrics:")
    print("1. Go to your Qualtrics account")
    print("2. Click 'Create project' > 'Survey' > 'From file'")
    print("3. Upload the generated .qsf file")
    print("4. Review and customize as needed")
    
    # Show project choices that were generated
    project_choices, _ = generate_project_choices(data)
    print(f"\nGenerated {len(project_choices)} project choices for QID7:")
    for idx, choice_id in enumerate(sorted(map(int, project_choices.keys())), 1):
        print(f"  {idx}. {project_choices[str(choice_id)]['Display']}")

if __name__ == "__main__":
    main()

