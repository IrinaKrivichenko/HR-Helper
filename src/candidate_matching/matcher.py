import time

from telegram import Update

from src.bot.utils import send_message
from src.candidate_matching.candidates_processing.candidate_llm_processor import process_candidates_with_llm
from src.candidate_matching.candidates_processing.embedding_filter import filter_candidates_by_embedding
from src.candidate_matching.candidates_processing.format_candidates import generate_candidates_summary, \
    generate_final_response
from src.candidate_matching.candidates_processing.input_candidates import get_df_for_vacancy_search
from src.candidate_matching.vacancy_processing.vacancy_llm_processor import extract_vacancy_info
from src.candidate_matching.vacancy_processing.vacancy_googlesheet import check_existing_vacancy, save_vacancy_description
from src.candidate_matching.vacancy_processing.vacancy_splitter import split_vacancies
from src.logger import logger
from src.nlp.embedding_handler import EmbeddingHandler
from src.nlp.llm_handler import LLMHandler


async def find_candidates_for_vacancy(vacancy, df, embedding_handler, llm_handler, user):
    start_time = time.time()
    # Check if a similar vacancy exists
    prev_call = check_existing_vacancy(vacancy)

    if (prev_call is not None) and \
        ('first_answer' in prev_call) and \
        int(prev_call['number of initial candidates']) == len(df):
             return prev_call['first_answer']

    step0_num = len(df)

    # Step 1: Filter candidates by embedding similarity
    llm_extracted_data = extract_vacancy_info(vacancy, llm_handler)
    filtered_df, consign_similarity_threshold = filter_candidates_by_embedding(llm_extracted_data,
                                                                               df,
                                                                               embedding_handler)
    list_of_filtered_candidated = ", ".join(filtered_df['Full Name'])
    step1_num = len(filtered_df)
    logger.info(f"number of candidates after consign_similarity_threshold() {len(filtered_df)}" )

    # Step 2: Process candidates with LLM
    better_fit_df, lesser_fit_df, llm_extracted_data = process_candidates_with_llm(vacancy,
                                                                           filtered_df,
                                                                           llm_extracted_data,
                                                                           llm_handler)

    step3_num = len(better_fit_df)
    logger.info(llm_extracted_data)
    logger.info(f"len(better_fit_df) = {len(better_fit_df)}" )
    logger.info(f"len(filtered_df) = {step1_num}" )
    logger.info(f"len(lesser_fit_df) = {len(lesser_fit_df)}" )
    # Step 3: Generete answer
    better_fit_df, lesser_fit_df = generate_candidates_summary(better_fit_df, lesser_fit_df, llm_extracted_data.get('Extracted Technologies', ''))

    final_answer = generate_final_response(better_fit_df, lesser_fit_df, llm_extracted_data.get('Extracted Technologies', ''))

    # Step 4: Save results to Google Sheets
    time_taken = time.time() - start_time
    save_vacancy_description(vacancy, prev_call, llm_extracted_data, final_answer, user ,
                             step0_num, consign_similarity_threshold, step1_num, step3_num,
                             list_of_filtered_candidated, time_taken )

    return final_answer

async def match_candidats(update: Update,  text, user_name, llm_handler=None) -> None:
    if llm_handler is None:
        llm_handler = LLMHandler()
    embedding_handler = EmbeddingHandler()
    vacancies = split_vacancies(text, llm_handler)

    logger.info(f"number of vacancies in the request: {len(vacancies)}")

    if len(vacancies) == 0:
      pass
    else:
      df = get_df_for_vacancy_search()
      if len(vacancies) == 1:
          vacancy = vacancies[0]
          if len(vacancy) > text:
              vacancy = text
          result = await find_candidates_for_vacancy(vacancy, df, embedding_handler, llm_handler, user_name)
          logger.info("ready_to_send_message")
          await send_message(update, result)
      else:
          results = []
          for vacancy in vacancies:
              candidates = await find_candidates_for_vacancy(vacancy, df, embedding_handler, llm_handler, user_name)
              result = f"{vacancy}\n{candidates}\n"
              await send_message(update, result)
              # update.message.reply_text(result)



