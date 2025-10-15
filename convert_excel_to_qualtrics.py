import pandas as pd
import json
import uuid
from datetime import datetime

def read_excel_data(filepath):
    """Read the Excel file and return structured data"""
    df = pd.read_excel(filepath, sheet_name='AggrigatedLabs')
    
    # Group by Lab and Project
    structure = {}
    for _, row in df.iterrows():
        lab = row['Lab']
        project = row['Project']
        student = row['Student']
        
        if pd.isna(lab) or pd.isna(project) or pd.isna(student):
            continue
            
        if lab not in structure:
            structure[lab] = {}
        if project not in structure[lab]:
            structure[lab][project] = []
        structure[lab][project].append(student)
    
    return structure

def generate_qualtrics_qsf(data):
    """Generate a Qualtrics QSF file from the structured data"""

    # Generate IDs
    survey_id = "SV_" + datetime.now().strftime("%Y%m%d%H%M%S")
    response_set_id = "RS_" + datetime.now().strftime("%Y%m%d%H%M%S")

    # Base survey structure
    survey = {
        "SurveyEntry": {
            "SurveyID": survey_id,
            "SurveyName": "HAAG Fall 2025 - Weekly Research Team Progress Check",
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

    # Single block containing all questions
    main_block = {
        "Type": "Default",
        "Description": "Default Question Block",
        "ID": "BL_1",
        "BlockElements": [],
        "Options": {
            "BlockLocking": "false",
            "RandomizeQuestions": "false",
            "BlockVisibility": "Expanded"
        }
    }

    # Collect all questions here first
    questions = []

    # Q1: Full Name
    q1_id = f"QID{qid_counter}"
    qid_counter += 1
    main_block["BlockElements"].append({"Type": "Question", "QuestionID": q1_id})

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
    main_block["BlockElements"].append({"Type": "Question", "QuestionID": q2_id})
    
    # Create choices for labs
    lab_choices = {}
    lab_names = sorted(data.keys())
    for idx, lab in enumerate(lab_names, 1):
        lab_choices[str(idx)] = {
            "Display": lab
        }
    
    questions.append({
        "SurveyID": survey_id,
        "Element": "SQ",
        "PrimaryAttribute": q2_id,
        "SecondaryAttribute": "Which Lab are you reporting on?",
        "TertiaryAttribute": None,
        "Payload": {
            "QuestionText": "Which Lab are you reporting on?",
            "DataExportTag": "Q2",
            "QuestionType": "MC",
            "Selector": "SAVR",
            "SubSelector": "TX",
            "Configuration": {
                "QuestionDescriptionOption": "UseText"
            },
            "QuestionDescription": "Which Lab are you reporting on?",
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
    
    # For each lab, create project and researcher questions
    for lab_idx, lab_name in enumerate(lab_names, 1):
        projects = data[lab_name]
        
        # Q: Which project in this lab?
        q_proj_id = f"QID{qid_counter}"
        qid_counter += 1
        main_block["BlockElements"].append({"Type": "Question", "QuestionID": q_proj_id})
        
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
            "SecondaryAttribute": f"Which project in {lab_name}?",
            "TertiaryAttribute": None,
            "Payload": {
                "QuestionText": f"Which project are you reporting on in {lab_name} Lab?",
                "DataExportTag": f"Q_{lab_name}_Project",
                "QuestionType": "MC",
                "Selector": "SAVR",
                "SubSelector": "TX",
                "Configuration": {
                    "QuestionDescriptionOption": "UseText"
                },
                "QuestionDescription": f"Which project in {lab_name}",
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
            main_block["BlockElements"].append({"Type": "Question", "QuestionID": q_eval_id})
            
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
                    "QuestionText": f"How do you evaluate the contributions of the following researchers?",
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
    
    # Build SurveyElements in the correct order
    # 1. Blocks element (BL) - Payload is a dict, not array
    survey["SurveyElements"].append({
        "SurveyID": survey_id,
        "Element": "BL",
        "PrimaryAttribute": "Survey Blocks",
        "SecondaryAttribute": None,
        "TertiaryAttribute": None,
        "Payload": {
            "0": main_block
        }
    })

    # 2. Survey flow (FL)
    survey_flow = {
        "Flow": [
            {
                "ID": "BL_1",
                "Type": "Block",
                "FlowID": "FL_1"
            }
        ],
        "Properties": {
            "Count": 1,
            "RemovedFieldsets": []
        },
        "FlowID": "FL_1",
        "Type": "Root"
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
    
    # Read Excel file
    print("Reading Excel file...")
    excel_file = "HAAG_Fall_Enrollment_Students.xlsx"
    data = read_excel_data(excel_file)
    
    print(f"Found {len(data)} labs")
    for lab, projects in data.items():
        print(f"  {lab}: {len(projects)} projects")
    
    # Generate QSF
    print("\nGenerating Qualtrics QSF file...")
    survey = generate_qualtrics_qsf(data)
    
    # Save to file
    output_file = "HAAG_Fall_2025_Survey.qsf"
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