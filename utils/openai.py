import streamlit as st
import openai
from openai.types.beta import Assistant
from io import BytesIO


def retrieve_assistant() -> Assistant:
    """
    Retrieves the OpenAI assistant.

    Returns:
        Assistant: The OpenAI assistant.
    """
    client = openai.Client(api_key=st.secrets.openai.api_key)
    assistant = client.beta.assistants.retrieve(
        assistant_id=st.secrets.openai.assistant_id
    )

    return assistant


def summarize_document(file_content: bytes, file_name: str, gpt_model: str) -> str:
    """
    Summarizes a document using the OpenAI API.

    Args:
        file_content (bytes): The content of the document to be summarized.

    Returns:
        str: The summarized content of the document.
    """
    client = openai.Client(api_key=st.secrets.openai.api_key)

    # 1. Upload the file to the OpenAI
    uploaded_file = client.files.create(
        file=(file_name, BytesIO(file_content)), purpose="assistants"
    )

    # 2. Create a new thread and run the assistant
    thread = client.beta.threads.create(
        messages=[
            {
                "role": "user",
                "content": "Follow my instructions to summarize the document below",
                "attachments": [
                    {"file_id": uploaded_file.id, "tools": [{"type": "file_search"}]}
                ],
            }
        ]
    )

    assistant = retrieve_assistant()

    run = client.beta.threads.runs.create_and_poll(
        assistant_id=assistant.id,
        thread_id=thread.id,
        model=gpt_model,
    )
    run_steps = client.beta.threads.runs.steps.list(thread_id=thread.id, run_id=run.id)
    run_steps = list(run_steps)

    # 3. Retrieve the summarized content from the assistant's response
    message_id = run_steps[0].step_details.message_creation.message_id
    message = client.beta.threads.messages.retrieve(
        message_id=message_id, thread_id=thread.id
    )

    return message.content[0].text.value
