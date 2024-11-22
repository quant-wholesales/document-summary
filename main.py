import streamlit as st
from utils import gcloud, openai


def set_key_callback(key, value):
    def callback():
        st.session_state[key] = value

    return callback


if "form_submited" not in st.session_state:
    st.session_state["form_submited"] = False


openai_assistant = openai.retrieve_assistant()

with st.form("awesome form", enter_to_submit=False, clear_on_submit=False):

    st.write("Assistant ID")
    st.code(openai_assistant.id, language="markdown", wrap_lines=True)

    st.write("Assistant Name")
    st.code(openai_assistant.name, language="markdown", wrap_lines=True)

    st.write("GPT Model")
    model_options = ["gpt-4o", "gpt-4o-mini"]
    current_model_idx = None
    for idx, model in enumerate(model_options):
        if model == openai_assistant.model:
            current_model_idx = idx
            break
    gpt_model = st.selectbox(
        label="",
        options=model_options,
        index=current_model_idx,
        label_visibility="collapsed",
    )

    st.write("Instructions")
    with st.expander("Click here to see the full instructions"):
        st.markdown(openai_assistant.instructions)

    uploaded_file = st.file_uploader("Upload a file", accept_multiple_files=False)
    if uploaded_file is not None:
        document = gcloud.storage_create_object(uploaded_file)
        doc_entity, new_doc_created = gcloud.datastore_create_document(document, gpt_model)
        if new_doc_created:
            summary = openai.summarize_document(
                file_content=uploaded_file.getvalue(),
                file_name=uploaded_file.name,
                gpt_model=gpt_model,
            )
            doc_entity.update({"summary": summary})
            gcloud.datastore_service_client().put(doc_entity)

        if st.session_state.form_submited:
            st.code(doc_entity.get("summary"), language="markdown", wrap_lines=True)

    st.form_submit_button("Submit", on_click=set_key_callback("form_submited", True))
