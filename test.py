
import re

def parse_candidates_from_answer(text):
    text = re.sub(r'Available From \d{4}-\d{2}-\d{2}', '', text)
    candidate_pattern = re.compile(
        r'(\d+)\.\s*<a\s+href=[\'"](https://docs\.google\.com/spreadsheets/d/.*?)[\'"]>(.*?)<\/a>\s*(\d+)%.*?(?:🟥(.*?)🟨|$)',
        re.DOTALL
    )
    candidates = []
    for match in candidate_pattern.finditer(text):
        number = match.group(1)
        suitability = match.group(4).strip()
        name = match.group(3).strip()
        link = match.group(2)
        ewr_text = match.group(5).strip() if match.group(5) else None

        candidate_str = f"{number}. {suitability}% {name}"
        if ewr_text and ewr_text != "_":
            candidate_str += f" {ewr_text}"
        candidate_str += f" {link}"
        candidates.append(candidate_str)
    return "\n".join(candidates)


# Пример использования
text = """<b>🎯 Best-fit:</b>
1. <a href='https://docs.google.com/spreadsheets/d/1-ueQGTxTqaPzxlE_CC3g6yxcDafO2eVjKYSqP5GaYDI/edit#gid=0&range=A26'>Dmytro S</a> 75% CHISW 📄Proposed Senior FullStack Web Developer 🇺🇦Ukraine —  <code>JavaScript, React.js, Tailwind CSS, React Query, React Query Redux, TypeORM, Zustand, React Testing Library</code> EN-B2 <a href='https://t.me/mariiakobtseva'>Telegram</a> / _
<b>Dmytro S</b> was selected because he has extensive experience in the healthcare industry, which is a major plus for this role. His tech stack includes JavaScript and React, and he has worked on projects that involve patient management systems. However, he does not have experience with Kotlin, which is a requirement.
🟥_ 🟨_ 🟩_

2. <a href='https://docs.google.com/spreadsheets/d/1-ueQGTxTqaPzxlE_CC3g6yxcDafO2eVjKYSqP5GaYDI/edit#gid=0&range=A63'>Andrii Ch</a> 70% CHISW 📄Proposed Senior FullStack Web Developer 🇺🇦Ukraine —  <code>Spring, GitLab, JavaScript, Oracle, Terraform, GitHub, ReactJS, Cassandra, GitHub Actions, React, Bootstrap, Testcontainers, Portainer, Spring Boot Admin</code> EN-B2 <a href='https://t.me/mariiakobtseva'>Telegram</a> / _
<b>Andrii Ch</b> was selected due to his extensive experience in Java and microservices, which are relevant to the role. He has worked on healthcare-related projects, which is a significant advantage. However, he does not have experience with Kotlin or React.
🟥_ 🟨_ 🟩_

3. <a href='https://docs.google.com/spreadsheets/d/1-ueQGTxTqaPzxlE_CC3g6yxcDafO2eVjKYSqP5GaYDI/edit#gid=0&range=A3'>Vitali Chapiolkin</a> 65% Andrus ✅English checked, 🔓Ready to work with Middle AI Engineer 🇵🇱Poland —  <code>Pandas, PyTorch, LangChain, Git, CI/CD (CI/CD (GitHub Actions)), OpenAI API, Kotlin, Seaborn, TensorFlow, TorchVision, Reinforcement learning, Data augmentation and normalization, Email generation, Project management automation, Model fine-tuning and optimization, Network latency handling, Error handling for hardware communication, Custom data augmentation and normalization, Project status updates processing, Context extraction for LLMs, Contextually relevant responses for LLMs, Automated reporting workflows, Automated data collection workflows</code> EN-B2 <a href='https://drive.google.com/file/d/1IXdRnwRqIQ8-llxXBzDp1y19zOrZWj1N/view?usp=sharing'>CV</a>/_ <a href='t.me/Radzibil'>Telegram</a> / <a href='wa.me/508652071'>WhatsApp</a> / <a href='https://www.linkedin.com/in/vchapiolkin'>LinkedIn</a>
<b>Vitali Chapiolkin</b> was selected as a strong candidate because he has a diverse tech stack that includes Kotlin and Java, which are essential for the role. His experience in AI and his location in Poland align well with the job requirements. However, he lacks direct experience in the healthcare domain, which is a significant aspect of the job description.
🟥$16,00/hr 🟨$32,00/hr 🟩≈$16.00/hr

4. <a href='https://docs.google.com/spreadsheets/d/1-ueQGTxTqaPzxlE_CC3g6yxcDafO2eVjKYSqP5GaYDI/edit#gid=0&range=A15'>Tsimafei Rebesh</a> 60% Andrus 🙋Eager Applicant, 🤝Interviewed Senior FullStack Web Developer 🇵🇱Poland —  <code>JavaScript, React.js, TailwindCSS, Git, PrimeReact, Bootstrap, React Testing Library, GitHub, Storybook, OpenAI, Git Extensions, Formik, React-hook-form</code> EN-B2 <a href='https://drive.google.com/file/d/1CtzaRRollN2mu8TI1OXCwCctBafmlFXGc_Y3bhugu6U/edit?tab=t.0#heading=h.ivrkvj111n25'>CV</a>/_ <a href='http://t.me/Timarebesh'>Telegram</a> / <a href='http://wa.me/48502558320'>WhatsApp</a> / <a href='https://www.linkedin.com/in/timothy-rebesh-261b3243/'>LinkedIn</a>
<b>Tsimafei Rebesh</b> was also selected due to his seniority and experience with React, which is crucial for the role. He has worked on AI-related projects and has strong communication skills, but he does not have direct experience in the healthcare domain, which is a key requirement.
🟥$19,00/hr 🟨$33,00/hr 🟩≈$14.00/hr

5. <a href='https://docs.google.com/spreadsheets/d/1-ueQGTxTqaPzxlE_CC3g6yxcDafO2eVjKYSqP5GaYDI/edit#gid=0&range=A97'>Evgenii Tkachenko</a> 55% ProfUa, freelance 🏁WorkED, 📄Proposed Senior AI Engineer 🏰Belarus —  <code>React, JavaScript, OpenAI, Bootstrap, TensorFlow, PyTorch, Business Process Model and Notation (BPMN), GitHub Actions, Terraform, React Router, React Query, Storybook, TypeORM, Amazon Simple Storage Service (S3), Terraform, Stability AI, LangChain, Amazon Elastic Container Registry (ECR), Amazon Elastic Container Service (ECS), Amazon Simple Email Service (SES), AWS CloudFormation, AWS CloudTrail, AWS Identity and Access Management (IAM), GitLab</code> English С1 <a href='https://drive.google.com/file/d/1yUkLGDscv3wG4kntMBjHGWTOH4q6WY3e/view?usp=sharing'>CV</a>/_ <a href='https://t.me/evgenytk'>Telegram</a> / <a href='https://www.linkedin.com/in/evgenii-tkachenko/'>LinkedIn</a>
<b>Evgenii Tkachenko</b> was selected due to his experience as an AI Engineer and his strong tech stack that includes React. However, he lacks experience in healthcare, which is a critical requirement.
🟥$25,00/hr 🟨_ 🟩_

<b>🧩 Low-fit:</b>
6. <a href='https://docs.google.com/spreadsheets/d/1-ueQGTxTqaPzxlE_CC3g6yxcDafO2eVjKYSqP5GaYDI/edit#gid=0&range=A50'>Eugene Yarmash</a> 50% freelance 🚀 Actively Applying Senior FullStack Web Developer 🇵🇱Poland —  <code>Javascript, git, GitHub, GitLab, Tornado, Bootstrap, Yandex.Direct, Plaid</code> EN-B2 <a href='https://drive.google.com/file/d/1jjkatyK_EX4b19FFLnUE3vImSJYj6kdA/view?usp=sharing'>CV</a>/_ <a href='http://t.me/yyarmash'>Telegram</a> / <a href='https://www.linkedin.com/in/yarmash'>LinkedIn</a>
<b>Eugene Yarmash</b> was selected due to his strong background in Python and full-stack development, which includes experience with React. He has worked in the financial services industry, but lacks direct experience in healthcare, which is a significant drawback.
🟥_ 🟨_ 🟩_

3. <a href='https://docs.google.com/spreadsheets/d/1-ueQGTxTqaPzxlE_CC3g6yxcDafO2eVjKYSqP5GaYDI/edit#gid=0&range=A43'>Yevhen Fishchuk</a> Available From 2026-03-01 65% Job post 💬In Talks Middle Data Engineer 🇵🇱Poland, 🇸🇬Singapore, 🇺🇦Ukraine —  <code>Python, SQL, Git, MySQL, AWS</code> EN-B2 <a href='https://drive.google.com/file/d/17cWtWLENhoS9175lCfNLQsAZhn-merzL_hXSZi6skTU/view?usp=sharing'>CV</a>/_ <a href='https://www.linkedin.com/in/efischuk/'>LinkedIn</a> / <a href='tel:+48794298108'>+48794298108</a>
<b>Yevhen Fishchuk</b> was selected as he has solid experience as a Data Engineer, with hands-on knowledge of SQL, AWS, and Git. He has worked on projects involving data pipelines and ETL processes, which aligns well with the job description. However, he does not mention experience with dbt, which is a key requirement.
🟥$30,00/hr 🟨$46,00/hr 🟩≈$16.00/hr
"""

candidates = parse_candidates_from_answer(text)
print(candidates)


#
#
# from dotenv import load_dotenv
#
# from src.google_services.sheets import write_dict_to_sheet
#
# load_dotenv()
#
# # bot.py
# from telegram import Update
# from telegram.ext import filters, MessageHandler, ApplicationBuilder, ContextTypes, CommandHandler
#
# import os
#
# async def handle_forwarded(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     bot_user = await context.bot.get_me()
#     print(bot_user.name == '@ostlab_hr_bot')
#
#     msg = update.message.forward_origin.sender_user_name
#
#
#
# # https://t.me/belaiplatform/1496  "👥 Кланіраванне ..." from _
# #     удалось выяснить
# #     msg.forward_origin.chat.username = belaiplatform
# #     msg.forward_origin.chat.message_id = 1496
# #
# # https://t.me/c/2442766780/1575/2363  "Hey-hey!🌞..." from ejikqueen
# #     удалось выяснить
# #     msg.forward_origin.sender_user.link = https://t.me/ejikqueen
# #     msg.forward_origin.sender_user.username = ejikqueen
# #
# # https://t.me/c/3010920963/1/644 "Дарагая, дабранач" from AndrusKr
# #     единственное что удалось выяснить про оригинальное сообщение
# #     msg.forward_origin.sender_user_name = Λndruś Kryvičenka
# #
# # https://t.me/c/2482564467/649 "Я ў Кракаве" from AndrusKr
# #     единственное что удалось выяснить про оригинальное сообщение
# #     msg.forward_origin.sender_user_name = Λndruś Kryvičenka
#
#     msg.chat.username
#     msg.date
#     sales_cells_dict = {}
#     sales_cells_dict["№"] = "=[№]3+1"
#
#     if hasattr(msg.forward_origin, 'date'):
#         msg_forward_origin_date = update.message.forward_origin.date
#         origin_msg_date = msg_forward_origin_date.strftime('%Y-%m-%d %a')
#         print(origin_msg_date)
#         sales_cells_dict['Дата'] = origin_msg_date
#
#     user = update.effective_user
#     user_name = user.username if user.username else user.first_name
#     sales_cells_dict['Хто занёс'] = user_name
#
#     if hasattr(msg.forward_origin, 'sender_user'):
#         sender_user_link = msg.forward_origin.sender_user.link
#         print(sender_user_link)
#         # sender_user_username = msg.forward_origin.sender_user.username
#         # print(sender_user_username)
#         sales_cells_dict['Прадстаўнік замоўцы'] = sender_user_link
#
#     if hasattr(msg.forward_origin, 'message_id') and hasattr(msg.forward_origin, 'chat'):
#         message_id = msg.forward_origin.message_id
#         chat_link = msg.forward_origin.chat.link
#         chat_username = msg.forward_origin.chat.username
#         message_link = f"{chat_username}/{message_id}"
#         print(message_link)
#         sales_cells_dict['Крыніца'] = message_link
#
#     write_dict_to_sheet(data_dict=sales_cells_dict, spreadsheet_env_name="SALES_SPREADSHEET_ID", sheet_name="Запыты")
#     #
#     # attrs_to_check = [
#     #     #'CHANNEL', 'CHAT', 'HIDDEN_USER', 'USER',
#     #     'message_id', 'sender_user']
#     # for attr_name in attrs_to_check:
#     #     if hasattr(msg.forward_origin, attr_name):
#     #         attr_value = getattr(msg.forward_origin, attr_name)
#     #         print(f"msg.forward_origin.{attr_name}: {attr_value}")
#     #         print()
#     #
#     # msg_forward_origin = update.message.forward_origin
#     # print("dir(msg.forward_origin)")
#     # # print(len(dir(msg_forward_origin)))
#     # # print(dir(msg_forward_origin))
#
#
#
#
# BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# app = ApplicationBuilder().token(BOT_TOKEN).build()
# app.add_handler(MessageHandler(filters.ALL, handle_forwarded))
# app.run_polling()