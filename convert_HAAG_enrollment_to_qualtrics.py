import pandas as pd
import json
import uuid
from datetime import datetime

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

def generate_qualtrics_qsf(data):
    """Generate a Qualtrics QSF file from the structured data"""

    # Generate IDs
    survey_id = "SV_" + datetime.now().strftime("%Y%m%d%H%M%S")
    response_set_id = "RS_" + datetime.now().strftime("%Y%m%d%H%M%S")

    # Base survey structure
    # Extract semester from data if available
    semester = data.get('_semester', 'Fall 2025')
    
    survey = {
        "SurveyEntry": {
            "SurveyID": survey_id,
            "SurveyName": f"HAAG {semester} - Weekly Research Team Progress Check",
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
    
    # Question counter
    qid_counter = 1

    # Create blocks dictionary to store all blocks
    blocks = {}
    questions = []
    
    # Create initial lab selection block
    lab_selection_block = {
        "Type": "Default",
        "Description": "Lab Check",
        "ID": "BL_1",
        "BlockElements": [],
        "Options": {
            "BlockLocking": "false",
            "RandomizeQuestions": "false",
            "BlockVisibility": "Expanded"
        }
    }

    # Q1: Full Name
    q1_id = f"QID{qid_counter}"
    qid_counter += 1
    lab_selection_block["BlockElements"].append({"Type": "Question", "QuestionID": q1_id})

    questions.append({
        "SurveyID": survey_id,
        "Element": "SQ",
        "PrimaryAttribute": q1_id,
        "SecondaryAttribute": "Please enter your full name",
        "TertiaryAttribute": None,
        "Payload": {
            "QuestionText": "Please enter your full name",
            "DataExportTag": "Q1",
            "QuestionType": "TE",
            "Selector": "SL",
            "Configuration": {
                "QuestionDescriptionOption": "UseText"
            },
            "QuestionDescription": "Please enter your full name",
            "Validation": {
                "Settings": {
                    "ForceResponse": "ON",
                    "ForceResponseType": "ON",
                    "Type": "None"
                }
            },
            "GradingData": [],
            "Language": [],
            "NextChoiceId": 4,
            "NextAnswerId": 1,
            "QuestionID": q1_id
        }
    })
    
    # Q2: Which Lab
    q2_id = f"QID{qid_counter}"
    qid_counter += 1
    lab_selection_block["BlockElements"].append({"Type": "Question", "QuestionID": q2_id})
    
    # Create choices for labs
    lab_choices = {}
    # Filter out non-lab keys (like _semester)
    lab_data = {k: v for k, v in data.items() if isinstance(v, dict)}
    lab_names = sorted(lab_data.keys())
    for idx, lab in enumerate(lab_names, 1):
        lab_choices[str(idx)] = {
            "Display": lab
        }
    
    questions.append({
        "SurveyID": survey_id,
        "Element": "SQ",
        "PrimaryAttribute": q2_id,
        "SecondaryAttribute": "Which Labs are you reporting on?",
        "TertiaryAttribute": None,
        "Payload": {
            "QuestionText": "Which Labs are you reporting on? (You can select multiple labs)",
            "DataExportTag": "Q2",
            "QuestionType": "MC",
            "Selector": "MAVR",
            "SubSelector": "TX",
            "Configuration": {
                "QuestionDescriptionOption": "UseText"
            },
            "QuestionDescription": "Which Labs are you reporting on?",
            "Choices": lab_choices,
            "ChoiceOrder": list(range(1, len(lab_names) + 1)),
            "Validation": {
                "Settings": {
                    "ForceResponse": "ON",
                    "ForceResponseType": "ON",
                    "Type": "None"
                }
            },
            "Language": [],
            "NextChoiceId": len(lab_names) + 1,
            "NextAnswerId": 1,
            "QuestionID": q2_id
        }
    })
    
    # Store the lab selection block
    blocks["0"] = lab_selection_block
    
    # Create a separate block for each lab
    block_counter = 2  # Start from BL_2 since BL_1 is the lab selection block
    
    for lab_idx, lab_name in enumerate(lab_names, 1):
        projects = lab_data[lab_name]
        
        # Create a new block for this lab
        lab_block_id = f"BL_{block_counter}"
        lab_block = {
            "Type": "Standard",
            "Description": lab_name,
            "ID": lab_block_id,
            "BlockElements": [],
            "Options": {
                "BlockLocking": "false",
                "RandomizeQuestions": "false",
                "BlockVisibility": "Expanded"
            }
        }
        
        # Q: Which project in this lab?
        q_proj_id = f"QID{qid_counter}"
        qid_counter += 1
        lab_block["BlockElements"].append({"Type": "Question", "QuestionID": q_proj_id})
        
        project_choices = {}
        project_names = sorted(projects.keys())
        for idx, proj in enumerate(project_names, 1):
            project_choices[str(idx)] = {
                "Display": proj
            }
        
        # Project selection question with display logic
        questions.append({
            "SurveyID": survey_id,
            "Element": "SQ",
            "PrimaryAttribute": q_proj_id,
            "SecondaryAttribute": f"Which projects in {lab_name}?",
            "TertiaryAttribute": None,
            "Payload": {
                "QuestionText": f"Which projects are you reporting on in {lab_name} Lab? (You can select multiple projects)",
                "DataExportTag": f"Q_{lab_name}_Project",
                "QuestionType": "MC",
                "Selector": "MAVR",
                "SubSelector": "TX",
                "Configuration": {
                    "QuestionDescriptionOption": "UseText"
                },
                "QuestionDescription": f"Which projects in {lab_name}",
                "Choices": project_choices,
                "ChoiceOrder": list(range(1, len(project_names) + 1)),
                "Validation": {
                    "Settings": {
                        "ForceResponse": "ON",
                        "Type": "None"
                    }
                },
                "DisplayLogic": {
                    "0": {
                        "0": {
                            "LogicType": "Question",
                            "QuestionID": q2_id,
                            "QuestionIsInLoop": "no",
                            "ChoiceLocator": f"q://{q2_id}/SelectableChoice/{lab_idx}",
                            "Operator": "Selected",
                            "QuestionIDFromLocator": q2_id,
                            "LeftOperand": f"q://{q2_id}/SelectableChoice/{lab_idx}",
                            "Type": "Expression"
                        },
                        "Type": "If"
                    },
                    "Type": "BooleanExpression",
                    "inPage": False
                },
                "Language": [],
                "NextChoiceId": len(project_names) + 1,
                "QuestionID": q_proj_id
            }
        })
        
        # For each project, create researcher evaluation question
        for proj_idx, project_name in enumerate(project_names, 1):
            researchers = projects[project_name]
            
            q_eval_id = f"QID{qid_counter}"
            qid_counter += 1
            lab_block["BlockElements"].append({"Type": "Question", "QuestionID": q_eval_id})
            
            # Create researcher choices in matrix format
            researcher_choices = {}
            for idx, researcher in enumerate(sorted(researchers), 1):
                researcher_choices[str(idx)] = {
                    "Display": researcher
                }
            
            # Answer choices: Good, Needs Improvement, Poor
            answer_choices = {
                "1": {"Display": "Good"},
                "2": {"Display": "Needs Improvement"},
                "3": {"Display": "Poor"}
            }
            
            questions.append({
                "SurveyID": survey_id,
                "Element": "SQ",
                "PrimaryAttribute": q_eval_id,
                "SecondaryAttribute": f"Evaluate {project_name}",
                "TertiaryAttribute": None,
                "Payload": {
                    "QuestionText": f"How do you evaluate the contributions of the following researchers in {lab_name} Lab - {project_name} Project?",
                    "DataExportTag": f"Q_{lab_name}_{project_name}",
                    "QuestionType": "Matrix",
                    "Selector": "Likert",
                    "SubSelector": "SingleAnswer",
                    "Configuration": {
                        "QuestionDescriptionOption": "UseText",
                        "TextPosition": "inline",
                        "ChoiceColumnWidth": 25,
                        "RepeatHeaders": "none",
                        "WhiteSpace": "OFF",
                        "MobileFirst": True
                    },
                    "QuestionDescription": f"Evaluate {project_name}",
                    "Choices": researcher_choices,
                    "ChoiceOrder": list(range(1, len(researchers) + 1)),
                    "Answers": answer_choices,
                    "AnswerOrder": ["1", "2", "3"],
                    "Validation": {
                        "Settings": {
                            "ForceResponse": "ON",
                            "Type": "None"
                        }
                    },
                    "DisplayLogic": {
                        "0": {
                            "0": {
                                "LogicType": "Question",
                                "QuestionID": q_proj_id,
                                "QuestionIsInLoop": "no",
                                "ChoiceLocator": f"q://{q_proj_id}/SelectableChoice/{proj_idx}",
                                "Operator": "Selected",
                                "QuestionIDFromLocator": q_proj_id,
                                "LeftOperand": f"q://{q_proj_id}/SelectableChoice/{proj_idx}",
                                "Type": "Expression"
                            },
                            "Type": "If"
                        },
                        "Type": "BooleanExpression",
                        "inPage": False
                    },
                    "Language": [],
                    "NextChoiceId": len(researchers) + 1,
                    "NextAnswerId": 4,
                    "QuestionID": q_eval_id
                }
            })
            
            # Add overall progress question for this project
            q_progress_id = f"QID{qid_counter}"
            qid_counter += 1
            lab_block["BlockElements"].append({"Type": "Question", "QuestionID": q_progress_id})
            
            questions.append({
                "SurveyID": survey_id,
                "Element": "SQ",
                "PrimaryAttribute": q_progress_id,
                "SecondaryAttribute": f"How do you evaluate the team's overall progress toward publication in {project_name}?",
                "TertiaryAttribute": None,
                "Payload": {
                    "QuestionText": f"How do you evaluate the team's overall progress toward publication in {lab_name} Lab - {project_name} Project?",
                    "DataExportTag": f"Q_{lab_name}_{project_name}_Progress",
                    "QuestionID": q_progress_id,
                    "QuestionType": "MC",
                    "Selector": "SAHR",
                    "SubSelector": "TX",
                    "Configuration": {
                        "QuestionDescriptionOption": "SpecifyLabel",
                        "TextPosition": "inline",
                        "LabelPosition": "BELOW"
                    },
                    "QuestionDescription": f"How do you evaluate the team's overall progress toward publication in {project_name}?",
                    "Choices": {
                        "1": {"Display": "On Track"},
                        "2": {"Display": "Needs Improvement"},
                        "3": {"Display": "Blocked"}
                    },
                    "ChoiceOrder": [1, "2", "3"],
                    "Validation": {
                        "Settings": {
                            "ForceResponse": "ON",
                            "ForceResponseType": "ON",
                            "Type": "None"
                        }
                    },
                    "DisplayLogic": {
                        "0": {
                            "0": {
                                "LogicType": "Question",
                                "QuestionID": q_proj_id,
                                "QuestionIsInLoop": "no",
                                "ChoiceLocator": f"q://{q_proj_id}/SelectableChoice/{proj_idx}",
                                "Operator": "Selected",
                                "QuestionIDFromLocator": q_proj_id,
                                "LeftOperand": f"q://{q_proj_id}/SelectableChoice/{proj_idx}",
                                "Type": "Expression"
                            },
                            "Type": "If"
                        },
                        "Type": "BooleanExpression",
                        "inPage": False
                    },
                    "GradingData": [],
                    "Language": [],
                    "NextChoiceId": 4,
                    "NextAnswerId": 4
                }
            })
            
            # Add comments question for this project
            q_comments_id = f"QID{qid_counter}"
            qid_counter += 1
            lab_block["BlockElements"].append({"Type": "Question", "QuestionID": q_comments_id})
            
            questions.append({
                "SurveyID": survey_id,
                "Element": "SQ",
                "PrimaryAttribute": q_comments_id,
                "SecondaryAttribute": f"Anything else you'd like to share about {project_name}?",
                "TertiaryAttribute": None,
                "Payload": {
                    "QuestionText": f"Anything else you'd like to share about this team's performance and progress in {lab_name} Lab - {project_name} Project?<i> (blockers, concerns, or positive notes)</i><br>",
                    "DataExportTag": f"Q_{lab_name}_{project_name}_Comments",
                    "QuestionID": q_comments_id,
                    "QuestionType": "TE",
                    "Selector": "ML",
                    "Configuration": {
                        "QuestionDescriptionOption": "UseText"
                    },
                    "QuestionDescription": f"Anything else you'd like to share about {project_name}? (blockers, concerns...)",
                    "Validation": {
                        "Settings": {
                            "ForceResponse": "OFF",
                            "Type": "None"
                        }
                    },
                    "DisplayLogic": {
                        "0": {
                            "0": {
                                "LogicType": "Question",
                                "QuestionID": q_proj_id,
                                "QuestionIsInLoop": "no",
                                "ChoiceLocator": f"q://{q_proj_id}/SelectableChoice/{proj_idx}",
                                "Operator": "Selected",
                                "QuestionIDFromLocator": q_proj_id,
                                "LeftOperand": f"q://{q_proj_id}/SelectableChoice/{proj_idx}",
                                "Type": "Expression"
                            },
                            "Type": "If"
                        },
                        "Type": "BooleanExpression",
                        "inPage": False
                    },
                    "GradingData": [],
                    "Language": [],
                    "NextChoiceId": 4,
                    "NextAnswerId": 1,
                    "SearchSource": {
                        "AllowFreeResponse": "false"
                    }
                }
            })
        
        # Store the lab block
        blocks[str(block_counter - 1)] = lab_block
        block_counter += 1
    
    # Build SurveyElements in the correct order
    # 1. Blocks element (BL) - Payload is a dict, not array
    survey["SurveyElements"].append({
        "SurveyID": survey_id,
        "Element": "BL",
        "PrimaryAttribute": "Survey Blocks",
        "SecondaryAttribute": None,
        "TertiaryAttribute": None,
        "Payload": blocks
    })

    # 2. Survey flow (FL) - Create flow that shows all lab blocks
    flow_elements = [
        {
            "ID": "BL_1",
            "Type": "Block",
            "FlowID": "FL_1"
        }
    ]
    
    # Add all lab blocks to the flow (they will be shown/hidden based on display logic)
    for lab_idx, lab_name in enumerate(lab_names, 1):
        lab_block_id = f"BL_{lab_idx + 1}"  # BL_2, BL_3, etc.
        flow_elements.append({
            "Type": "Standard",
            "ID": lab_block_id,
            "FlowID": f"FL_{lab_idx + 10}",
            "Autofill": []
        })

    survey_flow = {
        "Type": "Root",
        "FlowID": "FL_1",
        "Flow": flow_elements,
        "Properties": {
            "Count": len(flow_elements),
            "RemovedFieldsets": []
        }
    }

    survey["SurveyElements"].append({
        "SurveyID": survey_id,
        "Element": "FL",
        "PrimaryAttribute": "Survey Flow",
        "SecondaryAttribute": None,
        "TertiaryAttribute": None,
        "Payload": survey_flow
    })

    # 3. Preview Link (PL)
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

    # 4. Project (PROJ)
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

    # 5. Question Count (QC)
    survey["SurveyElements"].append({
        "SurveyID": survey_id,
        "Element": "QC",
        "PrimaryAttribute": "Survey Question Count",
        "SecondaryAttribute": str(len(questions)),
        "TertiaryAttribute": None,
        "Payload": None
    })

    # 6. Response Set (RS)
    survey["SurveyElements"].append({
        "SurveyID": survey_id,
        "Element": "RS",
        "PrimaryAttribute": response_set_id,
        "SecondaryAttribute": "Default Response Set",
        "TertiaryAttribute": None,
        "Payload": None
    })

    # 7. Scoring (SCO)
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

    # 8. Survey Options (SO)
    survey["SurveyElements"].append({
        "SurveyID": survey_id,
        "Element": "SO",
        "PrimaryAttribute": "Survey Options",
        "SecondaryAttribute": None,
        "TertiaryAttribute": None,
        "Payload": {
            "BackButton": "false",
            "SaveAndContinue": "false",
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
            "PreviousButton": " ← ",
            "NextButton": " → ",
            "SurveyTitle": "Qualtrics Survey | Qualtrics Experience Management",
            "SkinLibrary": "gatech",
            "SkinType": "MQ",
            "Skin": "gatech3blue",
            "NewScoring": 1
        }
    })

    # 9. Finally, add all questions (SQ elements)
    survey["SurveyElements"].extend(questions)

    return survey

def main():
    """Main function to convert Excel to QSF"""
    
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
    for lab, projects in data.items():
        if isinstance(projects, dict):  # Skip non-dict entries like _semester
            print(f"  {lab}: {len(projects)} projects")
    
    # Generate QSF
    print("\nGenerating Qualtrics QSF file...")
    data['_semester'] = semester  # Pass semester to generation function
    survey = generate_qualtrics_qsf(data)
    
    # Save to file
    output_file = f"HAAG_{semester.replace(' ', '_')}_Survey.qsf"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(survey, f, indent=2, ensure_ascii=False)
    
    print(f"\nSurvey saved to: {output_file}")
    print("\nTo import into Qualtrics:")
    print("1. Go to your Qualtrics account")
    print("2. Click 'Create project' > 'Survey' > 'From file'")
    print("3. Upload the generated .qsf file")
    print("4. Review and customize as needed")
    print("\nNote: All questions are in a single block with display logic.")
    print("Questions will show/hide based on lab and project selections.")

if __name__ == "__main__":
    main()