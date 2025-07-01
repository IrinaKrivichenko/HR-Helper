import re
import traceback
from typing import Dict
import pandas as pd

from src.data_processing.jaccard_similarity import calculate_jaccard_similarity, find_most_similar_row
from src.data_processing.json_conversion import df_to_json
from src.logger import logger
from src.nlp.llm_handler import LLMHandler


def parse_llm_response(response: str) -> Dict[str, str]:
    # Split the response into sections
    sections = response.split("## ")[1:]
    data = {}
    for section in sections:
        # Split each section into title and content
        lines = section.split("\n")
        title = lines[0].strip()
        content = "\n".join(lines[1:]).strip()
        # Replace commas with new lines for specific sections
        if title in ["Extracted Technologies", "Selected Candidates"]:
            # Replace commas with new lines
            data[title] = content.replace(", ", "\n")
        else:
            data[title] = content
    return data


def process_candidates_with_llm(
        vacancy: str,  # - vacancy (str): The vacancy description.
        filtered_df,   # - filtered_df (pd.DataFrame): DataFrame containing filtered candidate data.
        vacancy_info: dict,   # - vacancy_info (dict): Dictionary containing extracted information from the vacancy.
        llm_handler: LLMHandler,
        model="gpt-4.1-mini-2025-04-14" #"gpt-4o-mini"
):
    """
    Processes the candidates using the language model (LLM) to select the best matches.

    Returns:
    - tuple: A tuple containing the DataFrame of LLM selected candidates and the extracted data from LLM.
    """
    # Initialize a list to collect error logs
    error_logs = []

    # Initialize lists to store selected and rejected candidates
    llm_selected_indices = []

    # Add 'Reasoning' column to filtered_df
    filtered_df['Reasoning'] = ''
    filtered_df['Suitability Score'] = 0.0
    vacancy_info['Reasoning'] = ''
    vacancy_info['Selected Candidates'] = ''
    try_time = 1

    # Initialize DataFrames to store better and lesser fit candidates
    better_fit_df = pd.DataFrame(columns=filtered_df.columns)
    lesser_fit_df = pd.DataFrame(columns=filtered_df.columns)

    # Process candidates in batches
    while len(filtered_df) and try_time<5:
        try:
            # Convert the filtered DataFrame to JSON format
            columns_to_json = [
                'Full Name', 'Seniority', 'Role',
                'Stack', 'Industry', 'Expertise', 'Works hrs/mnth',
                'English', 'Location', 'Sell rate', 'Row in Spreadsheets'
            ]
            logger.info(filtered_df.columns)
            candidates_json = df_to_json(filtered_df[columns_to_json])

            # Prepare the prompt for the LLM
            prompt = [
                {"role": "system", "content": "You are an expert in matching candidates to job descriptions."},
                {"role": "user", "content": (
                    f"Your task is to process the provided input, which contains a job description and a list of candidates. Based on the input, you must:\n\n"
                    f"1. Analyze ten candidates in order. Ensure that each candidate is evaluated against the job description and technologies required.\n"
                    f"2. Select candidates who are the best match for the role and justify why they were selected. If multiple candidates are suitable, all of them should be listed. Ensure that no candidate is overlooked.\n"
                    f"3. Provide a suitability score for each candidate, ranging from 0 to 1, where 1 is a perfect match.\n"
                    f"4. Format the selected candidates in the format: 'Full Name iin spreadsheet row number X' (e.g., 'John Doe in spreadsheet row number 17'), each on a new line.\n"
                    f"\n"
                    f"The output should be formatted in Markdown with the following sections:\n"
                    f"- **Reasoning**: An explanation or justification for why certain candidates were selected. If no reasoning can be provided, return the reason why. Ensure that the reasoning covers all selected candidates, each candidate should be reasoned about in a separate line.\n"
                    f"- **Suitability Scores**: A list of suitability scores for each candidate, formatted as 'Full Name: score', each on a new line.\n"
                    f"- **Selected Candidates**: A list of candidates selected by the language model as the most suitable, each on a new line and formatted as 'Full Name in spreadsheet row number X'. If no candidates are selected, return 'No candidates are selected'.\n"
                    f"\n"
                    f"# Here is an example:\n\n"
                    f"# Example Input:\n"
                    f"## Job Description:\n"
                    f"We are looking for a Senior Machine Learning Engineer with expertise in Deep Learning (DL), Computer Vision (CV), and Python. The ideal candidate should have experience in the healthcare industry and be proficient in English at B2 level or above. Location: EU (preferably Poland, Warsaw). Rate: $30.\n"
                    f"## Candidates:\n"
                    f"```json\n"
                    f"    {{\n"
                    f"      \"Full Name\": \"Alice Smith\",\n"
                    f"      \"Seniority\": \"Senior\",\n"
                    f"      \"Role\": \"Machine Learning Engineer\",\n"
                    f"      \"Stack\": \"Deep Learning, Computer Vision, Python\",\n"
                    f"      \"Industry\": \"medicine\",\n"
                    f"      \"Expertise\": \"Healthcare\",\n"
                    f"      \"English\": \"C1\",\n"
                    f"      \"Location\": \"Poland\",\n"
                    f"      \"Sell rate\": \"\\\$37\",\n"
                    f"      \"Row in Spreadsheets\": 16\n"
                    f"    }},\n"
                    f"    {{\n"
                    f"      \"Full Name\": \"Charlie Brown\",\n"
                    f"      \"Seniority\": \"Senior\",\n"
                    f"      \"Role\": \"AI Engineer\",\n"
                    f"      \"Stack\": \"Computer Vision, Python\",\n"
                    f"      \"Industry\": \"medicine\",\n"
                    f"      \"Expertise\": \"Healthcare\",\n"
                    f"      \"English\": \"C1\",\n"
                    f"      \"Location\": \"Belarus\",\n"
                    f"      \"Sell rate\": \"\\\$30\",\n"
                    f"      \"Row in Spreadsheets\": 34\n"
                    f"    }},\n"
                    f"    {{\n"
                    f"      \"Full Name\": \"Bob Johnson\",\n"
                    f"      \"Seniority\": \"Middle\",\n"
                    f"      \"Role\": \"Data Scientist\",\n"
                    f"      \"Stack\": \"Deep Learning, NLP, Python\",\n"
                    f"      \"Industry\": \"Finance\",\n"
                    f"      \"Expertise\": \"Data Analysis\",\n"
                    f"      \"English\": \"B2\",\n"
                    f"      \"Location\": \"Serbia\",\n"
                    f"      \"Sell rate\": \"\\\$26\",\n"
                    f"      \"Row in Spreadsheets\": 28\n"
                    f"    }}\n"
                    f"  ]\n"
                    f"}}\n"
                    f"```\n\n"
                    f"# Example Output:\n"
                    f"## Reasoning\n"
                    f"1. **Alice Smith** was selected as the top candidate because she is a Senior Machine Learning Engineer with all the required skills, including Deep Learning (DL), Computer Vision (CV), and Python. Her experience in the healthcare industry and excellent English proficiency (C1) make her an ideal match for the job description. Additionally, Additionally, her location in Poland fits the requirement of being in the EU and is preferred. However, her rate of $37 is above the specified rate of $30.\n"
                    "2. **Charlie Brown** was rejected because, although he has expertise in Computer Vision (CV) and Python, and he has significant experience in the healthcare industry, his location in Belarus does not fit the requirement of being in the EU. His rate of $30 is competitive but the location is a decisive factor.\n"
                    f"3. **Bob Johnson** was rejected because, although he has experience with Deep Learning (DL) and Python, his expertise lies in the finance industry, and he does not have experience in Computer Vision (CV), which is a key requirement. His location in Serbia fits the requirement of being in the EU. His rate of $26 is competitive but his expertise does not fully match the job requirements.\n\n"
                    f"## Suitability Scores\n"
                    f"Alice Smith: 0.85\n"
                    f"Charlie Brown: 0.25\n"
                    f"Bob Johnson: 0.65\n"
                    f"## Selected Candidates\n"
                    f"Alice Smith in spreadsheet row number 16\n"
                    f"\n"
                    f"# Here is the input:\n\n"
                    f"## Job Description:\n"
                    f"{vacancy}\"\n"
                    # f"Here is the extracted information:\n\n"
                    # f"- **Extracted Technologies**:\n{vacancy_info.get('Extracted Technologies', 'No technologies are found')}\n\n"
                    # f"- **Extracted Role**:\n{vacancy_info.get('Extracted Role', 'No role is found')}\n\n"
                    # f"- **Extracted Industry**:\n{vacancy_info.get('Extracted Industry', 'No industry is found')}\n\n"
                    # f"- **Extracted Expertise**:\n{vacancy_info.get('Extracted Expertise', 'No expertise is found')}\n\n"
                    f"- **Vacancy Location**:\n{vacancy_info.get('Extracted Location', 'Any location')}\n\n"
                    # f"```\n\n"
                    f"## Candidates:\n"
                    f"```json\n"
                    f"{candidates_json}\n"
                    f"Analyze the first 10 candidates provided.```\n"
                )}
            ]

            # Send the prompt to the LLM handler and get the response
            approximate_tokens = len(filtered_df) * 100 + 100
            response = llm_handler.get_answer(prompt, model=model, max_tokens=approximate_tokens)

            logger.info(f"try_time {try_time}")
            logger.info(response)
            try_time += 1

            # Parse the response from the LLM
            extracted_data = parse_llm_response(response)

            # Extract reasoning and find candidates mentioned in reasoning
            reasoning = extracted_data.get("Reasoning", "")
            vacancy_info['Reasoning'] = f"{vacancy_info['Reasoning']}\n{reasoning}"
            reasoning_list = reasoning.split("\n")
            reasoning_candidate_indices = []

            # Update 'Reasoning' column for candidates mentioned in reasoning
            for reasoning_for_candidate in reasoning_list:
                candidate_match = re.findall(r'\*\*(.*?)\*\*', reasoning_for_candidate)
                if len(candidate_match)==1:
                    candidate_name = candidate_match[0].strip()
                    if candidate_name:
                        candidate_row = filtered_df[filtered_df['Full Name'].apply(lambda x: calculate_jaccard_similarity(set(candidate_name), set(x)) >= 0.9)]
                        if not candidate_row.empty:
                            # Save the index to be able to delete the candidat row from filtered_df in the end of while loop
                            reasoning_candidate_indices.extend(candidate_row.index.tolist())
                            # Remove the number and dot at the beginning of the line
                            reasoning_for_candidate = re.sub(r'^\d+\.\s*', '', reasoning_for_candidate)
                            # Update candidate reasoning in filtered_df
                            filtered_df.loc[candidate_row.index, 'Reasoning'] = reasoning_for_candidate

            # Extract suitability scores
            suitability_scores = extracted_data.get("Suitability Scores", "")
            if suitability_scores:
                scores_list = suitability_scores.split("\n")
                for score in scores_list:
                    if score:
                        parts = score.split(":")
                        if len(parts) == 2:
                            name = parts[0].strip()
                            score_value = float(parts[1].strip())
                            # Update candidate suitability score in filtered_df
                            candidate_row = filtered_df[filtered_df['Full Name'].apply(
                                lambda x: calculate_jaccard_similarity(set(name), set(x)) >= 0.9)]
                            if not candidate_row.empty:
                                filtered_df.loc[candidate_row.index, 'Suitability Score'] = score_value

            # Extract the list of selected candidates
            selected_candidates = extracted_data.get("Selected Candidates", "")
            vacancy_info['Selected Candidates'] = f"{vacancy_info['Selected Candidates']}\n{selected_candidates}"
            if selected_candidates.startswith('No'):
                selected_candidates_list = []
            else:
                selected_candidates_list = selected_candidates.split("\n")

            # Filter the DataFrame to include only the selected candidates
            selected_candidate_was_not_found = False
            for candidate in selected_candidates_list:
                if candidate:
                    parts = candidate.split(" in spreadsheet row number")
                    if len(parts) == 2:
                        name = parts[0].strip()
                        row_number = int(parts[1].strip())
                    else:
                         raise Exception(f"Wrong format in 'Selected Candidates' section: {candidate}")
                    set_name = set(name)

                    # Check if the row number exists in the filtered DataFrame
                    row_data = filtered_df[filtered_df['Row in Spreadsheets'] == row_number]
                    if not row_data.empty:
                        # Check if the name matches
                        full_name_df = row_data.iloc[0]['Full Name']
                        if calculate_jaccard_similarity(set_name, set(full_name_df)) >= 0.9:
                            llm_selected_indices.append(row_data.index[0])
                            better_fit_df = pd.concat([better_fit_df, row_data])
                        else:
                            selected_candidate_was_not_found = True
                            # Log the mismatch
                            error_logs.append(f"Mismatch for candidate: {candidate}, Data: {row_data.to_dict(orient='records')}")
                    else:
                        selected_candidate_was_not_found = True
                        # Log the missing row
                        error_logs.append(f"NO SUCH ROW IN FILTERED CANDIDATES for candidate: {candidate}")

                    # Search for matches by 'First Name' and 'Last Name' if not already matched
                    if selected_candidate_was_not_found:
                        # Use find_most_similar_row to find the most similar candidate
                        most_similar_row = find_most_similar_row(filtered_df['Full Name'], name)
                        if most_similar_row:
                            index, similar_name = most_similar_row
                            llm_selected_indices.append(index)
                            better_fit_df = pd.concat([better_fit_df, filtered_df.loc[[index]]])
                            selected_candidate_was_not_found = False

            # Form lesser_fit_df using indices from reasoning_candidate_indices not in llm_selected_indices
            lesser_fit_indices = [idx for idx in reasoning_candidate_indices if idx not in llm_selected_indices]
            lesser_fit_df = pd.concat([lesser_fit_df, filtered_df.loc[lesser_fit_indices]])

            # Filter out the processed candidates
            logger.info(f"reasoning_candidate_indices {reasoning_candidate_indices}")
            filtered_df = filtered_df[~filtered_df.index.isin(reasoning_candidate_indices)]
            logger.info(f"len(filtered_df) { len(filtered_df)}")

        except Exception as e:
            error_message = f"An error occurred: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_message)
            error_logs.append(error_message)
            continue

    # Sort DataFrames by 'Suitability Score' in descending order
    better_fit_df = better_fit_df.sort_values(by='Suitability Score', ascending=False)
    lesser_fit_df = lesser_fit_df.sort_values(by='Suitability Score', ascending=False)

    # Add error logs to the extracted data
    vacancy_info['error_logs'] = '\n'.join(error_logs)
    logger.info(f"vacancy_info['error_logs']; {vacancy_info['error_logs']}")

    return better_fit_df, lesser_fit_df, vacancy_info
