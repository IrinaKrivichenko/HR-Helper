import gradio as gr
from frontend.functions import filter_and_update_specialists, update_specialist_info, adjust_dataframe_structure, \
    get_field_options, sort_dataframe, download_staff_df, download_bench_df
import pandas as pd

def create_interface(df, fields_values_df):
    # Adjust the structure of the DataFrame to ensure it's compatible with the interface
    df = adjust_dataframe_structure(df)

    # Retrieve options for the engagement level filter
    engagement_options = get_field_options(fields_values_df, "LVL of engagement")
    location_options = get_field_options(df, "Location")
    print(location_options)

    # Define options for the working hours filter
    hours_options = ["4", "8"]

    # Read custom CSS styles from a file
    with open("frontend/styles.css", "r") as file:
        custom_css = file.read()

    # Create the Gradio interface using Blocks with custom CSS
    with gr.Blocks(css=custom_css) as demo:
        # Initialize the state of the DataFrame
        df_state = gr.State(df)

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
                        value=engagement_options[:-1],
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

                    # Button to apply filters
                    filter_btn = gr.Button("Filter", scale=0)


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
                        interactive=True
                    )

                # Second column - specialist information
                with gr.Column(scale=3):
                    with gr.Row():
                        # Textboxes for first and last name
                        fname = gr.Textbox(label="First Name")
                        lname = gr.Textbox(label="Last Name")
                    with gr.Row():
                        # Dropdown for engagement level and textbox for working hours
                        engagement = gr.Dropdown(
                            label="LVL of engagement",
                            choices=engagement_options,
                            multiselect=False
                        )
                        work_hours = gr.Textbox(label="Works hrs/day")

                    # Group for contact information
                    with gr.Group():
                        gr.Markdown("## Contacts")
                        linkedin = gr.Textbox(label="LinkedIn")
                        telegram = gr.Textbox(label="Telegram")
                        phone = gr.Textbox(label="Phone")
                        email = gr.Textbox(label="Email")

                    # Group for professional information
                    with gr.Group():
                        gr.Markdown("## Professional Information")
                        seniority = gr.Textbox(label="Seniority")
                        role = gr.TextArea(label="Role", lines=3)
                        stack = gr.TextArea(label="Stack", lines=3)
                        industry = gr.TextArea(label="Industry", lines=3)
                        expertise = gr.TextArea(label="Expertise", lines=3)

                    # Group for languages and location
                    with gr.Group():
                        gr.Markdown("## Languages & Location")
                        belarusian = gr.Textbox(label="Belarusian")
                        english = gr.Textbox(label="English")
                        location = gr.Textbox(label="Location")

                    # Group for financial information
                    with gr.Group():
                        gr.Markdown("## Financial Information")
                        with gr.Row():
                            rate_in = gr.Textbox(label="Rate In")
                            month_in = gr.Textbox(label="Month In (entry point)")
                        with gr.Row():
                            rate_in_exp = gr.Textbox(label="Rate In expected")
                            month_exp = gr.Textbox(label="Month In (expected)")
                        sell_rate = gr.Textbox(label="Sell Rate")

                    # Group for documents
                    with gr.Group():
                        gr.Markdown("## Documents")
                        cv_orig = gr.Textbox(label="CV (original)")
                        cv_white = gr.Textbox(label="CV white label (gdocs)")
                        folder = gr.Textbox(label="Folder")
                        nda = gr.Textbox(label="NDA")

                    # Textbox for comments
                    comment = gr.Textbox(label="Comment")

        # Event handler for the filter button
        filter_btn.click(
            filter_and_update_specialists,
            inputs=[df_state, project_desc, threshold, hours_checkboxes, engagement_checkboxes],
            outputs=[specialists, df_state, filter_status_markdown, specialist_count_markdown]
        )
        download_staff_btn.click( # !!!!! HTTPS protocol is required
            download_staff_df,
            inputs=df_state,
            outputs=download_btn_hidden
        ).then(
            fn=None,
            inputs=None,
            outputs=None,
            js="() => document.querySelector('#download_btn_hidden').click()"
        )
        download_bench_btn.click( # !!!!! HTTPS protocol is required
            download_bench_df,
            inputs=df_state,
            outputs=download_btn_hidden
        ).then(
            fn=None,
            inputs=None,
            outputs=None,
            js="() => document.querySelector('#download_btn_hidden').click()"
        )
        # Event handler for sorting the DataFrame
        sort_column.change(
            sort_dataframe,
            inputs=[df_state, sort_column],
            outputs=[specialists, df_state]
        )

        # Event handler for updating specialist information
        specialists.select(
            update_specialist_info,
            inputs=[df_state],
            outputs=[
                fname, lname, engagement, work_hours,
                linkedin, telegram, phone, email,
                seniority, role, stack, industry, expertise,
                belarusian, english, location,
                rate_in, rate_in_exp, sell_rate, month_in, month_exp,
                cv_orig, cv_white, folder, nda,
                comment
            ]
        )
    return demo
