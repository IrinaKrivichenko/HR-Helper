import gradio as gr
from frontend.functions import filter_and_update_specialists, update_specialist_info
import pandas as pd

def create_interface(df):
    with gr.Blocks(title="Project Management Interface", elem_id="project-description-tab") as demo:
        with gr.Tab("Project Description"):
            with gr.Row():
                with gr.Column(scale=4):
                    project_desc = gr.TextArea(
                        label="Project Description",
                        placeholder="Enter project description here...",
                        lines=30
                    )
                with gr.Column(scale=1):
                    threshold = gr.Textbox(
                        label="Cosine distance threshold value",
                        value="0.6",  # Устанавливаем значение по умолчанию
                        info="Recommended value: 0.6",
                        scale=1
                    )
                    filter_btn = gr.Button("Filter", scale=0)

        with gr.Tab("Staff", elem_id="staff-tab"):
            with gr.Row():
                # Первый блок - поиск и список
                with gr.Column(scale=1):
                    with gr.Row():
                        download_staff_btn = gr.Button("Download Staff", scale=0)
                        download_bench_btn = gr.Button("Download Bench", scale=0)
                    specialists = gr.DataFrame(
                        value=df[["First Name", "Last Name"]],
                        headers=["First Name", "Last Name"],
                        datatype=["str", "str"],
                        col_count=(2, "fixed"),
                        row_count=30,
                        interactive=True
                    )

                # Второй блок - информация о специалисте
                with gr.Column(scale=3):
                    with gr.Row():
                        fname = gr.Textbox(label="First Name")
                        lname = gr.Textbox(label="Last Name")
                    with gr.Row():
                        engagement = gr.Textbox(label="LVL of engagement")
                        work_hours = gr.Textbox(label="Works hrs/day")
                    # Группа личной информации
                    with gr.Group():
                        gr.Markdown("## Contacts")
                        linkedin = gr.Textbox(label="LinkedIn")
                        telegram = gr.Textbox(label="Telegram")
                        phone = gr.Textbox(label="Phone")
                        email = gr.Textbox(label="Email")

                    # Группа профессиональной информации
                    with gr.Group():
                        gr.Markdown("## Professional Information")
                        seniority = gr.Textbox(label="Seniority")
                        role = gr.TextArea(label="Role", lines=3)
                        stack = gr.TextArea(label="Stack", lines=3)
                        industry = gr.TextArea(label="Industry", lines=3)
                        expertise = gr.TextArea(label="Expertise", lines=3)

                    # Группа языков и локации
                    with gr.Group():
                        gr.Markdown("## Languages & Location")
                        belarusian = gr.Textbox(label="Belarusian")
                        english = gr.Textbox(label="English")
                        location = gr.Textbox(label="Location")

                    # Группа финансовой информации
                    with gr.Group():
                        gr.Markdown("## Financial Information")
                        with gr.Row():
                            rate_in = gr.Textbox(label="Rate In")
                            month_in = gr.Textbox(label="Month In (entry point)")
                        with gr.Row():
                            rate_in_exp = gr.Textbox(label="Rate In expected")
                            month_exp = gr.Textbox(label="Month In (expected)")
                        sell_rate = gr.Textbox(label="Sell Rate")

                    # Группа документов
                    with gr.Group():
                        gr.Markdown("## Documents")
                        cv_orig = gr.Textbox(label="CV (original)")
                        cv_white = gr.Textbox(label="CV white label (gdocs)")
                        folder = gr.Textbox(label="Folder")
                        nda = gr.Textbox(label="NDA")

                    # Комментарий
                    comment = gr.Textbox(label="Comment")

        df_state = gr.State(df)

        # Настраиваем обработчик событий для кнопки filter_btn
        filter_btn.click(
            filter_and_update_specialists,  # Функция для фильтрации и обновления
            inputs=[df_state, project_desc, threshold],  # Используем State для передачи DataFrame и порог фильтрации
            outputs=specialists  # Обновляем компонент specialists
        )
        specialists.select(update_specialist_info, [df_state], [
            fname, lname, engagement, work_hours, linkedin, telegram, phone, email,
            seniority, role, stack, industry, expertise, belarusian, english, location,
            cv_orig, cv_white, folder, rate_in, rate_in_exp, sell_rate, month_in, month_exp, nda, comment
        ])

    return demo

