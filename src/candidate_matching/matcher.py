import time

from telegram import Update

from src.bot.utils import send_message
from src.candidate_matching.candidates_processing.candidate_llm_processor import process_candidates_with_llm
from src.candidate_matching.candidates_processing.filtering import primary_filtering_by_vacancy
from src.candidate_matching.candidates_processing.format_candidates import generate_candidates_summary, \
    generate_final_response
from src.candidate_matching.candidates_processing.input_candidates import get_df_for_vacancy_search
from src.candidate_matching.vacancy_processing.vacancy_llm_processor import extract_vacancy_info
from src.candidate_matching.vacancy_processing.vacancy_googlesheet import check_existing_vacancy, save_vacancy_description
from src.candidate_matching.vacancy_processing.vacancy_splitter import split_vacancies
from src.logger import logger
from src.data_processing.nlp.llm_handler import LLMHandler

def get_roles(df):
    # Split the roles and explode them into separate rows
    roles_series = df['Role'].str.split(',').explode()
    # Get unique roles
    unique_roles = roles_series.str.strip().unique()
    unique_roles.sort()
    return unique_roles

async def find_candidates_for_vacancy(vacancy, llm_handler, user):
    start_time = time.time()
    vacancy_dict = {}  # Initialize vacancy_dict to store all necessary information

    # Step 0: Check if a similar vacancy exists
    step0_start_time = time.time()
    prev_call = check_existing_vacancy(vacancy)
    vacancy_dict['step0_time'] = time.time() - step0_start_time

    if (prev_call is not None) and \
       ('first_answer' in prev_call) and \
       int(prev_call['step1 num number of initial candidates']) == len(get_df_for_vacancy_search()):
        return prev_call['first_answer']

    # Step 1: Initialize list of candidates
    step1_start_time = time.time()
    initial_candidates_df = get_df_for_vacancy_search()
    vacancy_dict['step1_candidates_number'] = len(initial_candidates_df)
    vacancy_dict['step1_time'] = time.time() - step1_start_time

    # Step 2: Extract key information from the vacancy
    step2_start_time = time.time()
    vacancy_dict.update(extract_vacancy_info(vacancy, llm_handler))
    vacancy_dict['step2_time'] = time.time() - step2_start_time

    # Step 3: Filter candidates by vacancy information
    step3_start_time = time.time()
    filtered_candidates_df, vacancy_dict['technologies_coverage'] = primary_filtering_by_vacancy(vacancy_dict, initial_candidates_df)
    vacancy_dict['list_of_filtered_candidates'] = ", ".join(filtered_candidates_df['Full Name'])
    vacancy_dict['step3_candidates_number'] = len(filtered_candidates_df)
    vacancy_dict['step3_time'] = time.time() - step3_start_time
    logger.info(f"number of candidates after consign_similarity_threshold() {vacancy_dict['step3_candidates_number']}")

    # Step 4: Process candidates with LLM
    step4_start_time = time.time()
    better_fit_df, lesser_fit_df, vacancy_dict = process_candidates_with_llm(vacancy, filtered_candidates_df, vacancy_dict, llm_handler)
    vacancy_dict['step4_candidates_number'] = len(better_fit_df)
    vacancy_dict['step4_time'] = time.time() - step4_start_time
    logger.info(vacancy_dict)
    logger.info(f"len(better_fit_df) = {vacancy_dict['step4_candidates_number']}")
    logger.info(f"len(filtered_df) = {vacancy_dict['step3_candidates_number']}")
    logger.info(f"len(lesser_fit_df) = {len(lesser_fit_df)}")

    # Step 5: Generate answer
    step5_start_time = time.time()
    better_fit_df, lesser_fit_df = generate_candidates_summary(better_fit_df, lesser_fit_df, vacancy_dict.get('Extracted Technologies', ''))
    vacancy_dict['final_answer'] = generate_final_response(better_fit_df, lesser_fit_df, vacancy_dict)
    vacancy_dict['step5_time'] = time.time() - step5_start_time

    # Step 6: Save results to Google Sheets
    vacancy_dict['total_time'] = time.time() - start_time
    save_vacancy_description(vacancy, prev_call, vacancy_dict, user)

    return vacancy_dict['final_answer']



async def match_candidats(update: Update,  text, user_name, llm_handler=None) -> None:
    if llm_handler is None:
        llm_handler = LLMHandler()
    vacancies = split_vacancies(text, llm_handler)

    logger.info(f"number of vacancies in the request: {len(vacancies)}")

    if len(vacancies) == 0:
      pass
    else:
      if len(vacancies) == 1:
          vacancy = vacancies[0]
          if len(vacancy) > len(text):
              vacancy = text
          result = await find_candidates_for_vacancy(vacancy, llm_handler, user_name)
          logger.info("ready_to_send_message")
          await send_message(update, result)
      else:
          results = []
          for vacancy in vacancies:
              candidates = await find_candidates_for_vacancy(vacancy, llm_handler, user_name)
              result = f"{vacancy}\n{candidates}\n"
              await send_message(update, result)
              # update.message.reply_text(result)



