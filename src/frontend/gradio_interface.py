import gradio as gr
from src.frontend import functions as fn


def create_interface(df_path, fields_values_df):
    df = fn.load_data(df_path)

    # Retrieve options for the engagement level filter
    engagement_options = fn.get_field_options(fields_values_df, "LVL of engagement")
    location_options = fn.get_field_options(df, "Location")
    print(location_options)

    # Define options for the working hours filter
    hours_options = ["4", "8"]

    # Read custom CSS styles from a file
    with open("frontend/styles.css", "r") as file:
        custom_css = file.read()

    # Create the Gradio interface using Blocks with custom CSS
    with (gr.Blocks(css=custom_css) as demo):
        # Initialize the state of the DataFrame
        mode_state = gr.State("standard")
        full_df_state = gr.State(None)
        df_path_state = gr.State(df_path)
        df_state = gr.State(df)
        current_row = gr.Number(value=len(df), precision=0, visible=False)

        # Tab for project description
        with gr.Tab("Project Description"):
            with gr.Row():
                with gr.Column(scale=4):
                    # Text area for entering project description
                    project_desc = gr.TextArea(
                        label="Project Description",
                        placeholder="Enter project description here...",
                        lines=40
                    )
                with gr.Column(scale=1):
                    # Textbox for setting the cosine distance threshold value
                    threshold = gr.Textbox(
                        label="Minimum number of technologies",
                        value="5",  # Set default value
                        info="""This parameter specifies the minimum number of technologies that must match between a specialist's skills and the project's requirements for the specialist to be considered suitable for the project.""",
                        scale=1
                    )

                    # Checkboxes for filtering by working hours per day
                    hours_checkboxes = gr.CheckboxGroup(
                        visible=False,
                        label="Filter by Works hrs/day",
                        choices=hours_options,
                        value=hours_options,
                        interactive=True
                    )

                    # Checkboxes for filtering by engagement level
                    engagement_checkboxes = gr.CheckboxGroup(
                        label="Filter by Engagement Level",
                        choices=engagement_options,
                        value=engagement_options[:-2],
                        interactive=True,
                        elem_classes="checkbox-column"
                    )
                    # # Checkboxes for filtering by Location
                    # location_checkboxes = gr.CheckboxGroup(
                    #     visible=False,
                    #     label="Filter by Location",
                    #     choices=location_options,
                    #     value=location_options,
                    #     interactive=True,
                    #     elem_classes="checkbox-column"
                    # )
                    with gr.Row():
                        # Button to apply filters
                        filter_btn = gr.Button("Filter", scale=0)
                        reload_btn = gr.Button("Reset", scale=0)

        # Tab for staff information
        with gr.Tab("Staff", elem_id="staff-tab"):
            with gr.Row():
                # First column - list of specialists
                with gr.Column(scale=1):
                    with gr.Row():
                        # Buttons to download staff and bench data
                        download_staff_btn = gr.DownloadButton("Download Staff", scale=0)
                        download_bench_btn = gr.DownloadButton("Download Bench", scale=0)
                        download_btn_hidden = gr.DownloadButton(visible=False, elem_id="download_btn_hidden")

                    # Markdown elements to display filter status and specialist count
                    filter_status_markdown = gr.Markdown(value="**Showing full specialist base**")
                    specialist_count_markdown = gr.Markdown(value=f"**Total number of specialists:** {len(df)}")

                    # Dropdown to select the sort column
                    sort_column = gr.Dropdown(
                        label="Sort by",
                        choices=["First Name", "Last Name"],
                        value="First Name",
                        interactive=True
                    )

                    # DataFrame component to display specialists
                    specialists = gr.DataFrame(
                        value=df[["First Name", "Last Name"]],
                        headers=["First Name", "Last Name"],
                        datatype=["str", "str"],
                        col_count=(2, "fixed"),
                        max_height=500,
                        interactive=False
                    )
                    check_specialist_btn = gr.Button("Check and update list of specialists", scale=1)
                    with gr.Row():
                        del_specialist_btn = gr.Button("Del specialist", scale=0)
                        add_specialist_btn = gr.Button("Add specialist", scale=0)
                    save_specialist_btn = gr.Button("Save list of specialists", scale=1)
                # Second column - specialist information
                with gr.Column(scale=3):
                    with gr.Row():
                        # Textboxes for first and last name
                        fname = gr.Textbox(label="First Name", interactive=True)
                        lname = gr.Textbox(label="Last Name", interactive=True)
                    with gr.Row():
                        # Dropdown for engagement level and textbox for working hours
                        engagement = gr.Dropdown(
                            label="LVL of engagement",
                            choices=engagement_options,
                            multiselect=False, interactive=True
                        )
                        work_hours = gr.Textbox(label="Works hrs/day", interactive=True)

                    # Group for contact information
                    with gr.Group():
                        gr.Markdown("## Contacts")
                        linkedin = gr.Textbox(label="LinkedIn", interactive=True)
                        telegram = gr.Textbox(label="Telegram", interactive=True)
                        phone = gr.Textbox(label="Phone", interactive=True)
                        email = gr.Textbox(label="Email", interactive=True)

                    # Group for professional information
                    with gr.Group():
                        gr.Markdown("## Professional Information")
                        seniority = gr.Textbox(label="Seniority", interactive=True)
                        stack = gr.TextArea(label="Stack", lines=3, interactive=True)
                        role = gr.TextArea(label="Role", lines=3, interactive=True)
                        industry = gr.TextArea(label="Industry", lines=3, interactive=True)
                        expertise = gr.TextArea(label="Expertise", lines=3, interactive=True)

                    # Group for languages and location
                    with gr.Group():
                        gr.Markdown("## Languages & Location")
                        belarusian = gr.Textbox(label="Belarusian", interactive=True)
                        english = gr.Textbox(label="English", interactive=True)
                        location = gr.Textbox(label="Location", interactive=True)

                    # Group for financial information
                    with gr.Group():
                        gr.Markdown("## Financial Information")
                        with gr.Row():
                            rate_in = gr.Textbox(label="Rate In", interactive=True)
                            month_in = gr.Textbox(label="Month In (entry point)", interactive=True)
                        with gr.Row():
                            rate_in_exp = gr.Textbox(label="Rate In expected", interactive=True)
                            month_exp = gr.Textbox(label="Month In (expected)", interactive=True)
                        sell_rate = gr.Textbox(label="Sell Rate", interactive=True)

                    # Group for documents
                    with gr.Group():
                        gr.Markdown("## Documents")
                        cv_orig = gr.Textbox(label="CV (original)", interactive=True)
                        cv_white = gr.Textbox(label="CV white label (gdocs)", interactive=True)
                        folder = gr.Textbox(label="Folder", interactive=True)
                        nda = gr.Textbox(label="NDA", interactive=True)

                    # Textbox for comments
                    comment = gr.Textbox(label="Comment", interactive=True)

        specialist_fields = [
                fname, lname, engagement, work_hours,
                linkedin, telegram, phone, email,
                seniority, role, stack, industry, expertise,
                belarusian, english, location,
                rate_in, rate_in_exp, sell_rate, month_in, month_exp,
                cv_orig, cv_white, folder, nda,
                comment
            ]

        edit_specialists_btns = [check_specialist_btn, del_specialist_btn, add_specialist_btn, save_specialist_btn]
        # Event handler for the filter button
        filter_btn.click(
            fn.filter_and_update_specialists,
            inputs=[df_state, project_desc, threshold, hours_checkboxes, engagement_checkboxes],
            outputs=[specialists, df_state, filter_status_markdown, specialist_count_markdown,
                     *edit_specialists_btns, *specialist_fields]
        )
        # Event handler for the reload button
        reload_btn.click(None, [], [], js="window.location.reload()")

        download_staff_btn.click( # !!!!! HTTPS protocol is required
            fn.download_staff_df,
            inputs=df_state,
            outputs=download_btn_hidden
        ).then(
            fn=None, inputs=None, outputs=None,
            js="() => document.querySelector('#download_btn_hidden').click()"
        )
        download_bench_btn.click( # !!!!! HTTPS protocol is required
            fn.download_bench_df,
            inputs=df_state,
            outputs=download_btn_hidden
        ).then(
            fn=None, inputs=None, outputs=None,
            js="() => document.querySelector('#download_btn_hidden').click()"
        )
        # Event handler for sorting the DataFrame
        sort_column.change(
            fn.sort_dataframe,
            inputs=[df_state, sort_column],
            outputs=[specialists, df_state]
        )

        # Event handler for updating specialist information
        specialists.select(
            fn.update_specialist_info,
            inputs=[df_state],
            outputs=[*specialist_fields, current_row]
        )

        # Event handler for switching to validation mode
        check_specialist_btn.click(
            fn.switch_to_validation_mode,
            inputs=[df_state],
            outputs=[mode_state, df_state, specialists, full_df_state, *edit_specialists_btns[:-1],
                     filter_status_markdown, specialist_count_markdown]
        )
        # Event handler for deleting a specialist
        del_specialist_btn.click(
            fn.delete_specialist,
            inputs=[current_row, df_state],
            outputs=[df_state, specialists,
                     current_row, filter_status_markdown, specialist_count_markdown,
                     *edit_specialists_btns, *specialist_fields ]
        )

        # Event handler for adding a new specialist
        add_specialist_btn.click(
            fn.clear_specialists_fields,
            inputs=[df_state],
            outputs=[current_row, filter_status_markdown, specialist_count_markdown,
                     *edit_specialists_btns, *specialist_fields]
        )

        # Event handler for saving specialist data
        save_specialist_btn.click(
            fn.save_specialist_data,
            inputs=[mode_state, df_state, full_df_state, df_path_state],
            outputs=[mode_state, df_state, full_df_state, specialists,
                     current_row, filter_status_markdown, specialist_count_markdown,
                     *edit_specialists_btns, *specialist_fields ]
        )
        # .then(
        #     fn=None, inputs=None, outputs=None,
        #     js="window.location.reload()"
        # )
        # blur event: Used to call a function when the field loses focus
        for field in specialist_fields:
            field.blur(
                fn.update_specialist_field,
                inputs=[field, current_row, gr.State(field.label), df_state],
                outputs=[df_state, specialists]
            )

    return demo

